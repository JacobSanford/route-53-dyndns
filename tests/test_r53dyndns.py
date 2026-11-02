import http.server
import threading

import boto3
import pytest
from moto import mock_aws

import r53dyndns


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    for var in ('AWS_PROFILE', 'AWS_CONNECTION_REGION', 'ROUTE53_ZONE', 'ROUTE53_ZONE_ID'):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def route53():
    with mock_aws():
        yield boto3.client('route53', region_name='us-east-1')


@pytest.fixture
def public_zone(route53):
    return route53.create_hosted_zone(Name='example.com', CallerReference='public')['HostedZone']['Id']


@pytest.fixture
def ip(monkeypatch):
    """Set the IP that get_current_ip will report."""
    state = {'ip': '1.2.3.4'}
    monkeypatch.setattr(r53dyndns, 'get_current_ip', lambda url, timeout=None: state['ip'])
    return state


def create_private_zone(client, name):
    return client.create_hosted_zone(
        Name=name, CallerReference='private-' + name,
        VPC={'VPCRegion': 'us-east-1', 'VPCId': 'vpc-12345678'},
        HostedZoneConfig={'PrivateZone': True, 'Comment': ''},
    )['HostedZone']['Id']


def a_record(client, zone_id, name):
    for rs in client.list_resource_record_sets(HostedZoneId=zone_id)['ResourceRecordSets']:
        if rs['Name'] == name.rstrip('.') + '.' and rs['Type'] == 'A':
            return sorted(r['Value'] for r in rs['ResourceRecords']), rs['TTL']
    return None


def put_a_record(client, zone_id, name, value, ttl):
    r53dyndns.upsert_a_record(client, zone_id, name, value, ttl)


def run(*extra, record='home.example.com'):
    return r53dyndns.main(['-U', 'http://unused', '-R', record, *extra])


# --- record updates --------------------------------------------------------

def test_creates_missing_record_with_default_ttl(route53, public_zone, ip):
    assert run() == 0
    assert a_record(route53, public_zone, 'home.example.com') == (['1.2.3.4'], 600)


def test_matching_record_is_left_alone(route53, public_zone, ip, monkeypatch):
    put_a_record(route53, public_zone, 'home.example.com', '1.2.3.4', 600)
    calls = []
    monkeypatch.setattr(r53dyndns, 'upsert_a_record', lambda *a: calls.append(a))
    assert run() == 0
    assert calls == []


def test_changed_ip_is_updated_and_keeps_existing_ttl(route53, public_zone, ip):
    put_a_record(route53, public_zone, 'home.example.com', '9.9.9.9', 120)
    assert run() == 0
    assert a_record(route53, public_zone, 'home.example.com') == (['1.2.3.4'], 120)


def test_ip_comparison_is_exact_not_substring(route53, public_zone, ip):
    put_a_record(route53, public_zone, 'home.example.com', '11.2.3.45', 600)
    assert run() == 0
    assert a_record(route53, public_zone, 'home.example.com') == (['1.2.3.4'], 600)


def test_ttl_option_sets_ttl_on_create(route53, public_zone, ip):
    assert run('--ttl', '60') == 0
    assert a_record(route53, public_zone, 'home.example.com') == (['1.2.3.4'], 60)


def test_ttl_option_updates_ttl_even_when_ip_matches(route53, public_zone, ip):
    put_a_record(route53, public_zone, 'home.example.com', '1.2.3.4', 600)
    assert run('--ttl', '60') == 0
    assert a_record(route53, public_zone, 'home.example.com') == (['1.2.3.4'], 60)


def test_dry_run_changes_nothing(route53, public_zone, ip):
    put_a_record(route53, public_zone, 'home.example.com', '9.9.9.9', 600)
    assert run('--dry-run') == 0
    assert a_record(route53, public_zone, 'home.example.com') == (['9.9.9.9'], 600)


def test_dry_run_does_not_create(route53, public_zone, ip):
    assert run('-n') == 0
    assert a_record(route53, public_zone, 'home.example.com') is None


# --- zone selection --------------------------------------------------------

def test_route53_zone_override(route53, public_zone, ip, monkeypatch):
    monkeypatch.setenv('ROUTE53_ZONE', 'example.com')
    assert run(record='a.b.example.com') == 0
    assert a_record(route53, public_zone, 'a.b.example.com') == (['1.2.3.4'], 600)


def test_private_zone_with_same_name_is_ignored(route53, ip):
    # Create the private zone first so it is not just "first match wins".
    private = create_private_zone(route53, 'example.com')
    public = route53.create_hosted_zone(Name='example.com', CallerReference='public')['HostedZone']['Id']
    assert run() == 0
    assert a_record(route53, public, 'home.example.com') == (['1.2.3.4'], 600)
    assert a_record(route53, private, 'home.example.com') is None


def test_only_private_zone_is_an_error(route53, ip):
    private = create_private_zone(route53, 'example.com')
    assert run() == 1
    assert a_record(route53, private, 'home.example.com') is None


def test_multiple_public_zones_is_an_error(route53, ip):
    for ref in ('one', 'two'):
        route53.create_hosted_zone(Name='example.com', CallerReference=ref)
    assert run() == 1


def test_zone_id_override_skips_lookup(route53, ip, monkeypatch):
    private = create_private_zone(route53, 'example.com')
    monkeypatch.setenv('ROUTE53_ZONE_ID', private)
    assert run() == 0
    assert a_record(route53, private, 'home.example.com') == (['1.2.3.4'], 600)


def test_missing_zone_is_an_error(route53, ip):
    assert run(record='a.nope.org') == 1


def test_similarly_named_zone_does_not_match(route53, ip):
    route53.create_hosted_zone(Name='example.com.au', CallerReference='au')
    assert run() == 1


# --- environment and errors ------------------------------------------------

def test_legacy_region_variable_still_works_with_warning(route53, public_zone, ip, monkeypatch, caplog):
    monkeypatch.setenv('AWS_CONNECTION_REGION', 'us-east-1')
    assert run() == 0
    assert 'AWS_CONNECTION_REGION is deprecated' in caplog.text


def test_aws_errors_exit_nonzero(ip, monkeypatch):
    # No moto: real endpoint with fake credentials would be slow, so force an error.
    from botocore.exceptions import NoCredentialsError

    def boom():
        raise NoCredentialsError()
    monkeypatch.setattr(r53dyndns, 'make_client', boom)
    assert run() == 1


def test_unreachable_url_exits_nonzero():
    assert r53dyndns.main(['-U', 'http://127.0.0.1:9', '-R', 'home.example.com', '--timeout', '2']) == 1


@pytest.mark.parametrize('args', [['--ttl', '-1'], ['--timeout', '0']])
def test_invalid_option_values_are_rejected(args):
    with pytest.raises(SystemExit) as exc:
        run(*args)
    assert exc.value.code == 2


# --- IP parsing ------------------------------------------------------------

@pytest.fixture
def serve():
    servers = []

    def start(body):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return 'http://127.0.0.1:%d/' % server.server_port

    yield start
    for server in servers:
        server.shutdown()


@pytest.mark.parametrize('body, expected', [
    ('203.0.113.7\n', '203.0.113.7'),
    ('<html><body>Your IP is <b>203.0.113.7</b></body></html>', '203.0.113.7'),
    ('version 999.1.2.3 then 203.0.113.7', '203.0.113.7'),
    ('no address here', None),
])
def test_get_current_ip_parsing(serve, body, expected):
    assert r53dyndns.get_current_ip(serve(body)) == expected
