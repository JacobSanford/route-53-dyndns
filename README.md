# Amazon Route 53 dynamic DNS

Keeps one A record in Amazon Route 53 pointed at the host's current public IP.

## Before you start

- A public Route 53 hosted zone for your domain, e.g. `example.com`.
- An IAM user with the [IAM policy](docs/configuration.md#iam-policy), and an access key for it.

## Quickstart

The image `ghcr.io/jacobsanford/route53-dyndns` (linux/amd64, linux/arm64) updates the record on start, then
every `ROUTE53_UPDATE_FREQUENCY` seconds.

1. Download `compose.yaml` into a new directory:

    ```sh
    mkdir route53-dyndns && cd route53-dyndns
    curl -fsSLO https://raw.githubusercontent.com/JacobSanford/route-53-dyndns/2.x/compose.yaml
    ```

2. In `compose.yaml`, set `ROUTE53_DOMAIN_A_RECORD` to your record, e.g. `home.example.com`.

3. Put the IAM user's access key in `.env` beside it. Compose reads it automatically.

    ```sh
    cat > .env <<'EOF'
    AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
    AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>
    EOF
    chmod 600 .env
    ```

4. Run once as a dry run:

    ```sh
    docker compose run --rm -e ROUTE53_UPDATE_FREQUENCY=0 -e ROUTE53_DRY_RUN=1 route53-dyndns
    ```

    Expected output, for a record that does not exist yet:

    ```text
    INFO:root:Current IP is 203.0.113.7.
    INFO:botocore.credentials:Found credentials in environment variables.
    INFO:root:Using hosted zone /hostedzone/Z0123456789ABCDEFGHIJ.
    INFO:root:[dry run] Record not found, creating home.example.com A 203.0.113.7 (TTL 600).
    ```

    For an existing record, the last line starts `[dry run] Updating`, or reads `Record IP matches, doing nothing.`

5. Start it:

    ```sh
    docker compose up -d
    docker compose logs
    ```

    Each update logs the lines from step 4. A failed update also logs `Update failed, retrying in 10800 seconds.`

## Container variables

Set these under `environment:` in `compose.yaml`.

| Variable | Description |
|---|---|
| `ROUTE53_DOMAIN_A_RECORD` | The A record to update. Required. |
| `ROUTE53_IP_URL` | URL that returns the current IP. Default `https://checkip.amazonaws.com`. |
| `ROUTE53_UPDATE_FREQUENCY` | Seconds between updates. Default `10800`. `0` runs once and exits; use it with `docker compose run`, as in step 4. |
| `ROUTE53_TTL` | Passed as `--ttl`. |
| `ROUTE53_DRY_RUN` | `1` passes `--dry-run`. |
| `ROUTE53_ZONE`, `ROUTE53_ZONE_ID` | See [Configuration](docs/configuration.md#environment-variables). |

The `2.x` tag follows the `2.x` branch. Each push also gets an immutable `<short-sha>-<timestamp>` tag.

The Docker Hub image `jacobsanford/route53-dyndns` is the old Python 2 version and is no longer updated.

## More

- [Configuration](docs/configuration.md): script options, zone selection, credentials, IAM policy.
- [Running from source](docs/running-from-source.md): virtualenv install, cron, development.

## License

MIT: <https://opensource.org/licenses/MIT>. Optional attribution: `Amazon Route53 Dynamic DNS by Jacob Sanford`.
