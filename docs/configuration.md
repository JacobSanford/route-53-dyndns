# Configuration

## Options

| Option | Description |
|---|---|
| `-R`, `--record` | The A record to create or update. Required. |
| `-U`, `--url` | URL whose content contains the current IP. The first valid IPv4 address in it is used. Required. |
| `--ttl SECONDS` | Record TTL. New records default to 600. Existing records keep their TTL unless this is set. |
| `--timeout SECONDS` | Seconds to wait for the IP URL. Default 30. |
| `-n`, `--dry-run` | Report what would change without modifying Route 53. Implies `--verbose`. |
| `-v`, `--verbose` | Log each step. Otherwise only warnings and errors are printed. |
| `--version` | Print the version and exit. |

The container sets `-U`, `-R` and `-v` from its [variables](../README.md#container-variables).

## Environment variables

| Variable | Description |
|---|---|
| `ROUTE53_ZONE` | Hosted zone name. Defaults to the record's last two labels: `example.com` for `home.example.com`. Set it for multi-label suffixes such as `example.co.uk`. |
| `ROUTE53_ZONE_ID` | Hosted zone ID. Skips the zone lookup. Required if several public zones share the name, or to update a private zone. |
| `AWS_CONNECTION_REGION` | Deprecated; logs a warning. Route 53 is global. Use `AWS_REGION` for a non-default partition. |

## AWS credentials

The script uses boto3's [credential chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).
In order of preference:

- An IAM role on EC2 or other AWS compute.
- A named profile in a credentials file, selected with `AWS_PROFILE`.
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. The compose file uses these.

## IAM policy

Replace `<ZONE_ID>` with the hosted zone ID without the `/hostedzone/` prefix, e.g. `Z0123456789ABCDEFGHIJ`. It is in
the Route 53 console, or in the `Id` field of `aws route53 list-hosted-zones-by-name --dns-name example.com`.
Replace `home.example.com` with your record (lowercase, no trailing dot).

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
      "Resource": "arn:aws:route53:::hostedzone/<ZONE_ID>"
    },
    {
      "Effect": "Allow",
      "Action": "route53:ChangeResourceRecordSets",
      "Resource": "arn:aws:route53:::hostedzone/<ZONE_ID>",
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

With `ROUTE53_ZONE_ID` set, the `ListHostedZonesByName` statement can be removed.
