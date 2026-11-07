Amazon Route53 Dynamic DNS Tool
=============
Provide a simple dynamic DNS creation and update service via Amazon Route53 and A (alias/subdomain) records.

Dependencies
-----------
- Python 3.10+
- [boto3](https://github.com/boto/boto3)

Docker
-----------
An image is published to `ghcr.io/jacobsanford/route53-dyndns` for linux/amd64 and linux/arm64. It updates the
record on start, then every `ROUTE53_UPDATE_FREQUENCY` seconds.

1. Download [`compose.yaml`](compose.yaml) into a new directory, then set `ROUTE53_DOMAIN_A_RECORD` in it:

    ```sh
    mkdir route53-dyndns && cd route53-dyndns
    curl -fsSLO https://raw.githubusercontent.com/JacobSanford/route-53-dyndns/2.x/compose.yaml
    ```

2. Put the credentials in a `.env` file beside it, readable only by you. Compose reads it automatically:

    ```sh
    cat > .env <<'EOF'
    AWS_ACCESS_KEY_ID=<Insert your AWS Access Key>
    AWS_SECRET_ACCESS_KEY=<Insert your AWS Secret Key>
    EOF
    chmod 600 .env
    ```

3. Start it and check the first update:

    ```sh
    docker compose up -d
    docker compose logs -f
    ```

| Variable | Description |
|---|---|
| `ROUTE53_DOMAIN_A_RECORD` | The A record to update. Required. |
| `ROUTE53_IP_URL` | URL that returns the current IP. Default `https://checkip.amazonaws.com`. |
| `ROUTE53_UPDATE_FREQUENCY` | Seconds between updates. Default `10800`. Set `0` to run once and exit with the script's status. |
| `ROUTE53_TTL` | Passed as `--ttl`. Optional. |
| `ROUTE53_DRY_RUN` | Set `1` to pass `--dry-run`. Optional. |
| `ROUTE53_ZONE`, `ROUTE53_ZONE_ID` | See [Environment variables](#environment-variables). Optional. |

Each push to the `2.x` branch is also published with an immutable `<short-sha>-<timestamp>` tag.

The `jacobsanford/route53-dyndns` image on Docker Hub is deprecated. It runs the Python 2 version of this tool and is
no longer updated.

QuickStart
-----------
1. Clone this repository

        git clone https://github.com/JacobSanford/route-53-dyndns.git
        cd route-53-dyndns

2. Install dependencies into a virtual environment

        python3 -m venv venv
        venv/bin/pip install -r requirements.txt

3. Provide AWS credentials (see [AWS credentials](#aws-credentials) below). For a quick test, environment
   variables work:

        export AWS_ACCESS_KEY_ID="<Insert your AWS Access Key>"
        export AWS_SECRET_ACCESS_KEY="<Insert your AWS Secret Key>"

4. Check what the script would do, without changing anything

        venv/bin/python r53dyndns.py -U https://checkip.amazonaws.com -R example.domain.com --dry-run

5. Run the script

        venv/bin/python r53dyndns.py -U https://checkip.amazonaws.com -R example.domain.com

   The script exits non-zero if it cannot determine the IP, find the hosted zone, or update Route53.

Options
-----------
| Option | Description |
|---|---|
| `-R`, `--record` | The A record to create or update. Required. |
| `-U`, `--url` | URL whose content contains the current IP address. The first valid IPv4 address found is used. Required. |
| `--ttl SECONDS` | TTL for the record. New records default to 600. Existing records keep their TTL unless this is given. |
| `--timeout SECONDS` | How long to wait for the IP URL to respond. Default 30. |
| `-n`, `--dry-run` | Report what would change without modifying Route53. Implies `--verbose`. |
| `-v`, `--verbose` | Log each step. Without it, only warnings and errors are printed. |
| `--version` | Print the version and exit. |

Environment variables
-----------
| Variable | Description |
|---|---|
| `ROUTE53_ZONE` | Name of the hosted zone that holds the record. Defaults to the last two labels of the record, e.g. `example.com` for `home.example.com`. |
| `ROUTE53_ZONE_ID` | ID of the hosted zone, e.g. `Z0123456789ABCDEFGHIJ`. Skips the zone lookup. Required if more than one public zone has the same name, or to update a private zone. |
| `AWS_CONNECTION_REGION` | Deprecated. Route53 is a global service, so no region is needed. Still honoured for now, with a warning. Use `AWS_REGION` if you need a non-default partition. |

Without `ROUTE53_ZONE_ID`, the script only considers **public** hosted zones. Private zones with the same name are ignored.

AWS credentials
-----------
The script uses boto3's standard [credential chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html),
so any of these work, from most to least preferred:

- An IAM role, on EC2 or other AWS compute. Nothing to configure.
- A credentials file with a named profile, selected by `AWS_PROFILE`.
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables.

Use a dedicated IAM user or role limited to what the script needs. Replace `ZONEID` with your hosted zone ID and
`home.example.com` with your record (lowercase, no trailing dot):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "route53:ListHostedZonesByName",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "route53:ListResourceRecordSets",
      "Resource": "arn:aws:route53:::hostedzone/ZONEID"
    },
    {
      "Effect": "Allow",
      "Action": "route53:ChangeResourceRecordSets",
      "Resource": "arn:aws:route53:::hostedzone/ZONEID",
      "Condition": {
        "ForAllValues:StringEquals": {
          "route53:ChangeResourceRecordSetsNormalizedRecordNames": ["home.example.com"],
          "route53:ChangeResourceRecordSetsRecordTypes": ["A"],
          "route53:ChangeResourceRecordSetsActions": ["UPSERT"]
        }
      }
    }
  ]
}
```

If you set `ROUTE53_ZONE_ID`, you can drop the `ListHostedZonesByName` statement.

Running as a 'Service'
-----------
Users would benefit from running this tool periodically. On linux systems, one option to do so is through the cron
system. These steps assume the repository is cloned to `/var/opt/route-53-dyndns` and the QuickStart install steps
were run there.

1. Store the credentials in a file only root can read, instead of in the cron script

        mkdir -p /root/.aws
        cat > /root/.aws/credentials <<'EOF'
        [dyndns]
        aws_access_key_id = <Insert your AWS Access Key>
        aws_secret_access_key = <Insert your AWS Secret Key>
        EOF
        chmod 600 /root/.aws/credentials

2. Create a calling script

        > vi /etc/cron.hourly/updateDynDNS

        #!/usr/bin/env bash
        export AWS_PROFILE="dyndns"
        /var/opt/route-53-dyndns/venv/bin/python /var/opt/route-53-dyndns/r53dyndns.py -U https://checkip.amazonaws.com -R example.domain.com

   The script prints nothing on success, so cron only sends mail when something goes wrong.

3. Make the script executable

        chmod +x /etc/cron.hourly/updateDynDNS

4. (Test by running script directly)

        > /etc/cron.hourly/updateDynDNS

Development
-----------
    python3 -m venv venv
    venv/bin/pip install -r requirements-dev.txt
    venv/bin/pytest

The tests use [moto](https://github.com/getmoto/moto) to mock Route53, so no AWS account is needed.

License
-----------
- Amazon Route53 Dynamic DNS is licensed under the MIT License:
  - http://opensource.org/licenses/mit-license.html
- Attribution is not required, but much appreciated:
  - `Amazon Route53 Dynamic DNS by Jacob Sanford`
