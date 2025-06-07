# aws-cost-report-email-lambda

Lambda function to send AWS cost report (daily and MtD).

# Modify the source

- dotenv may be better
- Paramter store may be better
- Replace the following part with actual emails addresses on your discretion: Note that AWS_SOURCE_EMAIL must be email or domain that is verified to be owned by yourself.

```
AWS_SOURCE_EMAIL="EXAMPLE@EXAMPLE.com"
AWS_REGION="REGION_NAME"
AWS_DEST_EMAIL=["EXAMPLE@EXAMPLE.com"]
```
