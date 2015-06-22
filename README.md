Amazon Route53 Dynamic DNS Tool
=============
Provide a simple dynamic DNS creation and update service via Amazon Route53 and A (alias/subdomain) records.

Dependencies
-----------
- [boto](https://github.com/boto/boto)

QuickStart
-----------
1. Clone this repository

        git clone git://github.com/JacobSanford/route-53-dyndns.git
        cd route-53-dyndns

2. Install dependencies ([virtualenv](http://virtualenv.readthedocs.org/en/latest/) is recommended.)

        pip install -r requirements.txt

3. Export environment variables

        export AWS_ACCESS_KEY_ID="<Insert your AWS Access Key>"
        export AWS_SECRET_ACCESS_KEY="<Insert your AWS Secret Key>"
        export AWS_CONNECTION_REGION="us-east-1"

4. Run the script

        ./r53dyndns.py -U http://www.whatismyip.com/ -R example.domain.com


Running as a 'Service'
-----------
Users would benefit from running this tool periodically. On linux systems, one option to do so is through the cron
system.

1. Create a calling script

        > vi /etc/cron.hourly/updateDynDNS

        #!/usr/bin/env bash
        export AWS_ACCESS_KEY_ID=""
        export AWS_SECRET_ACCESS_KEY=""
        export AWS_CONNECTION_REGION="us-east-1"
        /var/opt/route-53-dyndns/r53dyndns.py -U http://www.whatismyip.com/ -R example.domain.com

2. Create a calling script

        chmod +x /etc/cron.hourly/updateDynDNS

3. (Test by running script directly)

        > /etc/cron.hourly/updateDynDNS


License
-----------
- Amazon Route53 Dynamic DNS is licensed under the MIT License:
  - http://opensource.org/licenses/mit-license.html
- Attribution is not required, but much appreciated:
  - `Amazon Route53 Dynamic DNS by Jacob Sanford`
