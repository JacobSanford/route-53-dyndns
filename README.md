Amazon Route53 Dynamic DNS Tool
=============
Provide a simple dynamic DNS creation and update service via Amazon Route53 and A (alias/subdomain) records.

Dependencies
-----------
- Python 3.8+
- [boto3](https://github.com/boto/boto3)

Docker
-----------
Familiar with Docker? A [docker image](https://registry.hub.docker.com/u/jacobsanford/route53-dyndns/) was created to deploy this service extremely quickly.

QuickStart
-----------
1. Clone this repository

        git clone https://github.com/JacobSanford/route-53-dyndns.git
        cd route-53-dyndns

2. Install dependencies into a virtual environment

        python3 -m venv venv
        venv/bin/pip install -r requirements.txt

3. Export environment variables
   ```
   export AWS_ACCESS_KEY_ID="<Insert your AWS Access Key>"
   export AWS_SECRET_ACCESS_KEY="<Insert your AWS Secret Key>"
   export AWS_CONNECTION_REGION="us-east-1"
   (optional) export ROUTE53_ZONE="<Insert zone name>"
   ```
   If ROUTE53_ZONE is not defined, base domain (TLD + 1) is used, e.g. `example.com`. 

4. Run the script

        venv/bin/python r53dyndns.py -U https://checkip.amazonaws.com -R example.domain.com

   Add `-v` for verbose output. The script exits non-zero if it cannot determine the IP or find the hosted zone.


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
        /var/opt/route-53-dyndns/venv/bin/python /var/opt/route-53-dyndns/r53dyndns.py -U https://checkip.amazonaws.com -R example.domain.com

2. Make the script executable

        chmod +x /etc/cron.hourly/updateDynDNS

3. (Test by running script directly)

        > /etc/cron.hourly/updateDynDNS


License
-----------
- Amazon Route53 Dynamic DNS is licensed under the MIT License:
  - http://opensource.org/licenses/mit-license.html
- Attribution is not required, but much appreciated:
  - `Amazon Route53 Dynamic DNS by Jacob Sanford`
