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
import urllib2

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
hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}
req = urllib2.Request(options.ip_get_url, headers=hdr)
try:
    page = urllib2.urlopen(req)
except urllib2.HTTPError, e:
    logging.error("Could not retrieve content from url")

content = page.read()
ip_list = re.findall(r'[0-9]+(?:\.[0-9]+){3}', content)
if len(ip_list) < 1:
    logging.error("Unable to find an IP address from within the URL:  %s" % options.ip_get_url)
    sys.exit(-1)
current_ip = ip_list[0]
record_to_update = options.record_to_update

zone_to_update = os.getenv("ROUTE53_ZONE")
if zone_to_update == None:
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
