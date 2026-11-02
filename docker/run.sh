#!/bin/sh
# Update the record, then repeat every ROUTE53_UPDATE_FREQUENCY seconds.
# Set ROUTE53_UPDATE_FREQUENCY=0 to run once and exit with the script's status.
set -u

if [ -z "${ROUTE53_DOMAIN_A_RECORD:-}" ]; then
  echo "ROUTE53_DOMAIN_A_RECORD is required, e.g. home.example.com" >&2
  exit 2
fi

set -- -v -U "$ROUTE53_IP_URL" -R "$ROUTE53_DOMAIN_A_RECORD"
[ -n "${ROUTE53_TTL:-}" ] && set -- "$@" --ttl "$ROUTE53_TTL"
case "${ROUTE53_DRY_RUN:-}" in 1|true|yes) set -- "$@" --dry-run ;; esac

if [ "$ROUTE53_UPDATE_FREQUENCY" = "0" ]; then
  exec python3 /app/r53dyndns.py "$@"
fi

# sh as PID 1 ignores SIGTERM by default; exit promptly on docker stop.
trap 'exit 0' TERM INT

while :; do
  python3 /app/r53dyndns.py "$@" || echo "Update failed, retrying in $ROUTE53_UPDATE_FREQUENCY seconds." >&2
  sleep "$ROUTE53_UPDATE_FREQUENCY" &
  wait $!
done
