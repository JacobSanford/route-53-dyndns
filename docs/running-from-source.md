# Running from source

Requires Python 3.10+ and the [prerequisites](../README.md#before-you-start).

## Install and run

1. Clone the repository and install dependencies:

    ```sh
    git clone https://github.com/JacobSanford/route-53-dyndns.git
    cd route-53-dyndns
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
    ```

2. Provide credentials. Environment variables work for a test; see [AWS credentials](configuration.md#aws-credentials)
   for the alternatives.

    ```sh
    export AWS_ACCESS_KEY_ID="<AWS_ACCESS_KEY_ID>"
    export AWS_SECRET_ACCESS_KEY="<AWS_SECRET_ACCESS_KEY>"
    ```

3. Run once as a dry run:

    ```sh
    venv/bin/python r53dyndns.py -U https://checkip.amazonaws.com -R home.example.com --dry-run
    ```

    The output matches [Quickstart step 4](../README.md#quickstart).

4. Update the record:

    ```sh
    venv/bin/python r53dyndns.py -U https://checkip.amazonaws.com -R home.example.com -v
    ```

    Without `-v`, success prints nothing. The exit status is non-zero if the script cannot get the IP, find the
    hosted zone, or update Route 53.

## Run on a schedule with cron

Assumes the repository is at `/var/opt/route-53-dyndns`, with [Install and run](#install-and-run) step 1 done there.
Run these as root (`sudo -i`).

1. Add a credentials profile:

    ```sh
    mkdir -p /root/.aws
    cat >> /root/.aws/credentials <<'EOF'
    [dyndns]
    aws_access_key_id = <AWS_ACCESS_KEY_ID>
    aws_secret_access_key = <AWS_SECRET_ACCESS_KEY>
    EOF
    chmod 600 /root/.aws/credentials
    ```

2. Create `/etc/cron.hourly/updateDynDNS` containing:

    ```bash
    #!/usr/bin/env bash
    export AWS_PROFILE="dyndns"
    /var/opt/route-53-dyndns/venv/bin/python /var/opt/route-53-dyndns/r53dyndns.py -U https://checkip.amazonaws.com -R home.example.com
    ```

    It prints nothing on success, so cron mails only on failure.

3. Make it executable:

    ```sh
    chmod +x /etc/cron.hourly/updateDynDNS
    ```

4. Test it:

    ```sh
    /etc/cron.hourly/updateDynDNS && echo OK
    ```

    Expected output: `OK`.

## Development

```sh
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
venv/bin/pytest
```

The tests mock Route 53 with [moto](https://github.com/getmoto/moto), so they need no AWS account.
