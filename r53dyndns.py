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
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.8',
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-R', '--record', dest='record_to_update', required=True, help='The A record to update.')
    parser.add_argument('-U', '--url', dest='ip_get_url', required=True, help='URL that returns the current IP address.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
    return parser.parse_args(argv)


def get_current_ip(url):
    """Return the first valid IPv4 address found in the content at url."""
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as page:
        content = page.read().decode('utf-8', errors='replace')
    for candidate in re.findall(r'[0-9]+(?:\.[0-9]+){3}', content):
        try:
            return str(ipaddress.IPv4Address(candidate))
        except ipaddress.AddressValueError:
            continue
    return None


def find_zone_id(client, zone_name):
    """Return the hosted zone ID for zone_name, or None if it does not exist."""
    fqdn = zone_name.rstrip('.') + '.'
    response = client.list_hosted_zones_by_name(DNSName=fqdn, MaxItems='1')
    for zone in response['HostedZones']:
        if zone['Name'].lower() == fqdn.lower():
            return zone['Id']
    return None


def get_a_record_values(client, zone_id, record_name):
    """Return the set of values in the existing A record, or None if it does not exist."""
    fqdn = record_name.rstrip('.') + '.'
    response = client.list_resource_record_sets(
        HostedZoneId=zone_id,
        StartRecordName=fqdn,
        StartRecordType='A',
        MaxItems='1',
    )
    for record_set in response['ResourceRecordSets']:
        if record_set['Name'].lower() == fqdn.lower() and record_set['Type'] == 'A':
            return {r['Value'] for r in record_set.get('ResourceRecords', [])}
    return None


def upsert_a_record(client, zone_id, record_name, ip):
    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Comment': 'Updated by r53dyndns',
            'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': record_name,
                    'Type': 'A',
                    'TTL': DEFAULT_TTL,
                    'ResourceRecords': [{'Value': ip}],
                },
            }],
        },
    )


def main(argv=None):
    options = parse_args(argv)
    if options.verbose:
        logging.basicConfig(level=logging.INFO)

    record_to_update = options.record_to_update
    zone_to_update = os.getenv('ROUTE53_ZONE') or '.'.join(record_to_update.rstrip('.').split('.')[-2:])

    try:
        current_ip = get_current_ip(options.ip_get_url)
    except (urllib.error.URLError, OSError) as e:
        logging.error('Could not retrieve content from %s: %s', options.ip_get_url, e)
        return 1
    if current_ip is None:
        logging.error('Unable to find an IP address from within the URL: %s', options.ip_get_url)
        return 1

    try:
        return update_record(record_to_update, zone_to_update, current_ip)
    except (BotoCoreError, ClientError) as e:
        logging.error('Route53 request failed: %s', e)
        return 1


def update_record(record_to_update, zone_to_update, current_ip):
    client = boto3.client('route53', region_name=os.getenv('AWS_CONNECTION_REGION', 'us-east-1'))

    zone_id = find_zone_id(client, zone_to_update)
    if zone_id is None:
        logging.error('Hosted zone not found: %s', zone_to_update)
        return 1

    existing_values = get_a_record_values(client, zone_id, record_to_update)
    if existing_values is None:
        logging.info('Record not found, add needed.')
    elif existing_values == {current_ip}:
        logging.info('Record IP matches, doing nothing.')
        return 0
    else:
        logging.info('IP does not match, update needed.')

    upsert_a_record(client, zone_id, record_to_update, current_ip)
    logging.info('Set %s A %s', record_to_update, current_ip)
    return 0


if __name__ == '__main__':
    sys.exit(main())
