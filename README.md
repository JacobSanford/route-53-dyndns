# Amazon Route53 Dynamic DNS Tool
### Leverage Amazon Route53 As a Dynamic DNS Service

This project leverages the Amazon Route53 API to provide a dynamic DNS service through A (alias/subdomain) records.

## Setup
As indicated by the Area53 documentation, users need to set the following environment variables:

```bash
export AWS_ACCESS_KEY_ID="<Insert your AWS Access Key>"
export AWS_SECRET_ACCESS_KEY="<Insert your AWS Secret Key>"
```
before an authenticated connection can be made.

## Use
```r53dyndns.py --record=RECORD_TO_UPDATE --url=IP_GET_URL```

## Dependencies :
+   A URL that returns the client IP address. A regexp will extract the first IP address found on the page.
+   Area53 interface : https://github.com/bigmlcom/Area53
+   boto : https://github.com/boto/boto

## License
- Amazon Route53 Dynamic DNS Tool is licensed under the MIT License:
  - http://opensource.org/licenses/mit-license.html
- Attribution is not required, but much appreciated:
  - `Amazon Route53 Dynamic DNS Tool by Jacob Sanford`
