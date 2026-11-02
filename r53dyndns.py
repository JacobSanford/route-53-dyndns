#!/usr/bin/env python3
"""Updates a Route53 hosted A record with the current IP of the system.
"""
import argparse
import ipaddress
import logging
import os
import re
import sys
import urllib.error
import urllib.request

import boto3
from botocore.exceptions import BotoCoreError, ClientError

__author__ = "Jacob Sanford"
__license__ = "MIT"
__version__ = "2.0.0"
__maintainer__ = "Jacob Sanford"
__email__ = "jacob.josh.sanford@gmail.com"
__status__ = "Development"

DEFAULT_TTL = 600
DEFAULT_TIMEOUT = 30
FALLBACK_REGION = 'us-east-1'
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.8',
}


class ZoneLookupError(Exception):
    """The hosted zone could not be determined unambiguously."""


def non_negative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError('must be 0 or greater')
    return number


def positive_float(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be greater than 0')
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-R', '--record', dest='record_to_update', required=True, help='The A record to update.')
    parser.add_argument('-U', '--url', dest='ip_get_url', required=True, help='URL that returns the current IP address.')
    parser.add_argument('--ttl', type=non_negative_int, default=None,
                        help='TTL in seconds. New records default to %d; existing records keep their TTL '
                             'unless this is given.' % DEFAULT_TTL)
    parser.add_argument('--timeout', type=positive_float, default=DEFAULT_TIMEOUT,
                        help='Seconds to wait for the IP URL to respond (default: %(default)s).')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Report what would change without modifying Route53. Implies --verbose.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    return parser.parse_args(argv)


def get_current_ip(url, timeout=DEFAULT_TIMEOUT):
    """Return the first valid IPv4 address found in the content at url."""
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as page:
        content = page.read().decode('utf-8', errors='replace')
    for candidate in re.findall(r'[0-9]+(?:\.[0-9]+){3}', content):
        try:
            return str(ipaddress.IPv4Address(candidate))
        except ipaddress.AddressValueError:
            continue
    return None


def find_zone_id(client, zone_name):
    """Return the ID of the single public hosted zone named zone_name.

    Private zones are ignored, since dynamic DNS updates are meant for public
    resolution. Raises ZoneLookupError if there is no public zone by that name,
    or more than one.
    """
    fqdn = zone_name.rstrip('.').lower() + '.'
    public, private = [], []
    paginator_kwargs = {'DNSName': fqdn}
    while True:
        response = client.list_hosted_zones_by_name(**paginator_kwargs)
        for zone in response['HostedZones']:
            # Results are sorted by name starting at DNSName, so the first
            # non-matching name means there are no more matches.
            if zone['Name'].lower() != fqdn:
                break
            if zone.get('Config', {}).get('PrivateZone'):
                private.append(zone['Id'])
            else:
                public.append(zone['Id'])
        else:
            if response.get('IsTruncated'):
                paginator_kwargs = {
                    'DNSName': response['NextDNSName'],
                    'HostedZoneId': response['NextHostedZoneId'],
                }
                continue
        break

    if len(public) == 1:
        return public[0]
    if len(public) > 1:
        raise ZoneLookupError(
            'Multiple public hosted zones named %s (%s); set ROUTE53_ZONE_ID to choose one.'
            % (fqdn, ', '.join(public)))
    if private:
        raise ZoneLookupError(
            'Only private hosted zones named %s exist (%s); set ROUTE53_ZONE_ID to update one explicitly.'
            % (fqdn, ', '.join(private)))
    raise ZoneLookupError('Hosted zone not found: %s' % fqdn)


def get_a_record(client, zone_id, record_name):
    """Return (set of values, TTL) for the existing A record, or None if it does not exist."""
    fqdn = record_name.rstrip('.').lower() + '.'
    response = client.list_resource_record_sets(
        HostedZoneId=zone_id,
        StartRecordName=fqdn,
        StartRecordType='A',
        MaxItems='1',
    )
    for record_set in response['ResourceRecordSets']:
        if record_set['Name'].lower() == fqdn and record_set['Type'] == 'A':
            values = {r['Value'] for r in record_set.get('ResourceRecords', [])}
            return values, record_set.get('TTL')
    return None


def upsert_a_record(client, zone_id, record_name, ip, ttl):
    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Comment': 'Updated by r53dyndns',
            'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': record_name,
                    'Type': 'A',
                    'TTL': ttl,
                    'ResourceRecords': [{'Value': ip}],
                },
            }],
        },
    )


def make_client():
    """Create a Route53 client.

    Route53 is a global service, so the region only matters for partitions
    other than the standard AWS one. AWS_CONNECTION_REGION is still honoured
    for backwards compatibility, but the standard AWS_REGION /
    AWS_DEFAULT_REGION / profile configuration is preferred.
    """
    legacy_region = os.getenv('AWS_CONNECTION_REGION')
    if legacy_region:
        logging.warning('AWS_CONNECTION_REGION is deprecated and will be removed; '
                        'Route53 is global, so it can usually be unset. Use AWS_REGION if needed.')
        region = legacy_region
    else:
        region = boto3.session.Session().region_name or FALLBACK_REGION
    return boto3.client('route53', region_name=region)


def update_record(client, zone_id, record_name, current_ip, ttl=None, dry_run=False):
    """Create or update record_name in zone_id to point at current_ip. Returns an exit code."""
    prefix = '[dry run] ' if dry_run else ''
    existing = get_a_record(client, zone_id, record_name)

    if existing is None:
        target_ttl = DEFAULT_TTL if ttl is None else ttl
        logging.info('%sRecord not found, creating %s A %s (TTL %d).', prefix, record_name, current_ip, target_ttl)
    else:
        existing_values, existing_ttl = existing
        target_ttl = existing_ttl if ttl is None else ttl
        if existing_ttl is None:
            # Alias records have no TTL of their own.
            target_ttl = DEFAULT_TTL if ttl is None else ttl
        if existing_values == {current_ip} and existing_ttl == target_ttl:
            logging.info('Record IP matches, doing nothing.')
            return 0
        logging.info('%sUpdating %s A %s (TTL %s) -> %s (TTL %d).', prefix, record_name,
                     ', '.join(sorted(existing_values)) or '(none)', existing_ttl, current_ip, target_ttl)

    if not dry_run:
        upsert_a_record(client, zone_id, record_name, current_ip, target_ttl)
    return 0


def main(argv=None):
    options = parse_args(argv)
    logging.basicConfig(level=logging.INFO if (options.verbose or options.dry_run) else logging.WARNING)

    record_to_update = options.record_to_update
    zone_to_update = os.getenv('ROUTE53_ZONE') or '.'.join(record_to_update.rstrip('.').split('.')[-2:])
    zone_id = os.getenv('ROUTE53_ZONE_ID')

    try:
        current_ip = get_current_ip(options.ip_get_url, options.timeout)
    except (urllib.error.URLError, OSError) as e:
        logging.error('Could not retrieve content from %s: %s', options.ip_get_url, e)
        return 1
    if current_ip is None:
        logging.error('Unable to find an IP address from within the URL: %s', options.ip_get_url)
        return 1
    logging.info('Current IP is %s.', current_ip)

    try:
        client = make_client()
        if not zone_id:
            zone_id = find_zone_id(client, zone_to_update)
        logging.info('Using hosted zone %s.', zone_id)
        return update_record(client, zone_id, record_to_update, current_ip, options.ttl, options.dry_run)
    except ZoneLookupError as e:
        logging.error('%s', e)
        return 1
    except (BotoCoreError, ClientError) as e:
        logging.error('Route53 request failed: %s', e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
