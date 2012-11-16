#! /usr/bin/env python
"""Updates a Route53 hosted A alias record with the current ip of the system.
"""
from area53 import route53
import logging
from optparse import OptionParser
from re import search
import socket
import sys
from urllib2 import urlopen

__author__ = "Jacob Sanford"
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Jacob Sanford"
__email__ = "jacob.josh.sanford@gmail.com"
__status__ = "Development"

parser = OptionParser()
parser.add_option('-R', '--record', type = 'string', dest = 'record_to_update', help = 'The A record to monitor and update.')
parser.add_option('-U', '--url', type = 'string', dest = 'ip_get_url', help = 'A URL that returns the current IP address.')
parser.add_option('-v', '--verbose', dest = 'verbose', default=False, help = 'Enable Verbose Output.', action='store_true')
(options, args) = parser.parse_args()

if options.record_to_update is None :
    logging.error('Please specify an A record with the -R switch.')
    parser.print_help()
    sys.exit(-1)
if options.ip_get_url is None :
    logging.error('Please specify a URL that returns the current IP address with the -U switch.')
    parser.print_help()
    sys.exit(-1)
if options.verbose :
    logging.basicConfig(
                        level=logging.INFO,
                        )

current_ip=urlopen(options.ip_get_url).read().strip()
record_to_update=options.record_to_update
zone_to_update='.'.join(record_to_update.split('.')[-2:])
delete_required=False

try:
    socket.inet_aton(current_ip)
    zone = route53.get_zone(zone_to_update)
    for record in zone.get_records():
        if search(r'<Record:A:' + record_to_update, str(record)) :
            if current_ip in record.to_print() :
                logging.info('Record IP matches, doing nothing.')
                sys.exit()
            delete_required=True
            logging.info('IP does not match, update needed.')
            zone.delete_a(record_to_update)
            zone.add_a(record_to_update, current_ip)
            sys.exit()
    logging.info('Record not found, add needed')
    zone.add_a(record_to_update, current_ip)
except socket.error:
    logging.info('Invalid IP format obtained from URL (' + current_ip + ')')
