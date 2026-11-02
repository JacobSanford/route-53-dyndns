FROM alpine:3.24

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

ENV ROUTE53_IP_URL=https://checkip.amazonaws.com
ENV ROUTE53_UPDATE_FREQUENCY=10800

RUN apk --update --no-cache add python3 py3-boto3 && \
  adduser -D -H -u 10001 r53dyndns

COPY r53dyndns.py /app/r53dyndns.py
COPY docker/run.sh /run.sh

USER r53dyndns
ENTRYPOINT ["/run.sh"]

LABEL org.opencontainers.image.authors="Jacob Sanford <jsanford@unb.ca>" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.description="Dynamic DNS for Amazon Route53 A records." \
  org.opencontainers.image.licenses="MIT" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.source="https://github.com/JacobSanford/route-53-dyndns" \
  org.opencontainers.image.title="route53-dyndns" \
  org.opencontainers.image.version="${VERSION}"
