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

# Permissions that Lambda function must have

For SES

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "ses:SendEmail",
            "Resource": "*"
        }
    ]
}
```

For Cost Explorer

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ce:DescribeCostCategoryDefinition",
                "ce:GetRightsizingRecommendation",
                "ce:GetCostAndUsage",
                "ce:GetSavingsPlansUtilization",
                "ce:GetAnomalies",
                "ce:GetReservationPurchaseRecommendation",
                "ce:GetCostForecast",
                "ce:GetPreferences",
                "ce:GetReservationUtilization",
                "ce:GetCostCategories",
                "ce:GetSavingsPlansPurchaseRecommendation",
                "ce:GetDimensionValues",
                "ce:GetSavingsPlansUtilizationDetails",
                "ce:GetAnomalySubscriptions",
                "ce:GetCostAndUsageWithResources",
                "ce:DescribeReport",
                "ce:GetReservationCoverage",
                "ce:GetSavingsPlansCoverage",
                "ce:GetAnomalyMonitors",
                "ce:DescribeNotificationSubscription",
                "ce:GetTags",
                "ce:GetUsageForecast"
            ],
            "Resource": "*"
        }
    ]
}
```
