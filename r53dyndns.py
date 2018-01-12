#! /usr/bin/env python
"""Updates a Route53 hosted A alias record with the current ip of the system.
"""
import boto.route53
import logging
import os
from optparse import OptionParser
import re
from re import search
import socket
import sys
from urllib2 import urlopen

__author__ = "Jacob Sanford"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Jacob Sanford"
__email__ = "jacob.josh.sanford@gmail.com"
__status__ = "Development"

parser = OptionParser()
parser.add_option('-R', '--record', type='string', dest='record_to_update', help='The A record to update.')
parser.add_option('-U', '--url', type='string', dest='ip_get_url', help='URL that returns the current IP address.')
parser.add_option('-v', '--verbose', dest='verbose', default=False, help='Enable Verbose Output.', action='store_true')
(options, args) = parser.parse_args()

if options.record_to_update is None:
    logging.error('Please specify an A record with the -R switch.')
    parser.print_help()
    sys.exit(-1)
if options.ip_get_url is None:
    logging.error('Please specify a URL that returns the current IP address with the -U switch.')
    parser.print_help()
    sys.exit(-1)
if options.verbose:
    logging.basicConfig(
        level=logging.INFO,
    )

content = urlopen(options.ip_get_url).read().strip()
ip_list = re.findall(r'[0-9]+(?:\.[0-9]+){3}', content)
if len(ip_list) < 1:
    logging.error("Unable to find an IP address from within the URL:  %s" % options.ip_get_url)
    sys.exit(-1)
current_ip = ip_list[0]
record_to_update = options.record_to_update
zone_to_update = '.'.join(record_to_update.split('.')[-2:])

try:
    socket.inet_aton(current_ip)
    conn = boto.route53.connect_to_region(os.getenv('AWS_CONNECTION_REGION', 'us-east-1'))
    zone = conn.get_zone(zone_to_update)
    for record in zone.get_records():
        if search(r'<Record:' + record_to_update, str(record)):
            if current_ip in record.to_print():
                logging.info('Record IP matches, doing nothing.')
                sys.exit()
            logging.info('IP does not match, update needed.')
            zone.delete_a(record_to_update)
            zone.add_a(record_to_update, current_ip)
            sys.exit()
    logging.info('Record not found, add needed')
    zone.add_a(record_to_update, current_ip)
except socket.error:
    logging.info('Invalid IP format obtained from URL (' + current_ip + ')')
