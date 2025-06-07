import boto3
import os
from datetime import date, timedelta, datetime
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

AWS_SOURCE_EMAIL="EXAMPLE@EXAMPLE.com"
AWS_REGION="REGION_NAME"
AWS_DEST_EMAIL=["EXAMPLE@EXAMPLE.com"]

def get_costs():
    today = date.today()
    yesterday = today - timedelta(days=1)
    start_of_month = today.replace(day=1)

    client = boto3.client('ce')

    services = [
        "Amazon Elastic Compute Cloud - Compute",
        "EC2 - Other",
        "EC2 - ELB",
        "Amazon Elastic Block Store",
        "AWS Key Management Service",
        "Amazon Virtual Private Cloud",
        "Amazon Route 53",
        "Amazon Simple Storage Service",
        "Tax",
        "Amazon CloudFront",
        "AWS Lambda",
        "Amazon CloudWatch"
    ]

    def fetch(start, end):
        response = client.get_cost_and_usage(
            TimePeriod={"Start": str(start), "End": str(end)},
            Granularity="DAILY",
            Metrics=["BlendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            Filter={"Dimensions": {"Key": "SERVICE", "Values": services}}
        )
        return response.get("ResultsByTime", [])[0].get("Groups", [])

    costs_yesterday = fetch(yesterday, today)
    costs_mtd = fetch(start_of_month, today)

    usage = {}
    for entry in costs_yesterday:
        service = entry["Keys"][0]
        cost = float(entry["Metrics"]["BlendedCost"]["Amount"])
        usage[service] = {"yesterday": cost, "mtd": 0.0}

    for entry in costs_mtd:
        service = entry["Keys"][0]
        cost = float(entry["Metrics"]["BlendedCost"]["Amount"])
        if service in usage:
            usage[service]["mtd"] = cost
        else:
            usage[service] = {"yesterday": 0.0, "mtd": cost}

    result = [
        {"service": s, "yesterday": v["yesterday"], "mtd": v["mtd"]}
        for s, v in usage.items() if v["mtd"] > 0
    ]
    result.sort(key=lambda x: x["mtd"], reverse=True)
    return result


def get_detailed_breakdown():
    """Return list of dicts with service, usage_type, yesterday_cost, mtd_cost."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    start_of_month = today.replace(day=1)

    client = boto3.client('ce')

    services = [
        "Amazon Elastic Compute Cloud - Compute",
        "EC2 - Other",
        "EC2 - ELB",
        "Amazon Elastic Block Store",
        "AWS Key Management Service",
        "Amazon Virtual Private Cloud",
        "Amazon Route 53",
        "Amazon Simple Storage Service",
        "Tax",
        "Amazon CloudFront",
        "AWS Lambda",
        "Amazon CloudWatch"
    ]

    def fetch(start, end):
        response = client.get_cost_and_usage(
            TimePeriod={"Start": str(start), "End": str(end)},
            Granularity="DAILY",
            Metrics=["BlendedCost"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "USAGE_TYPE"}
            ],
            Filter={"Dimensions": {"Key": "SERVICE", "Values": services}}
        )
        return response.get("ResultsByTime", [])[0].get("Groups", [])

    costs_yesterday = fetch(yesterday, today)
    costs_mtd = fetch(start_of_month, today)

    usage = {}

    # Store yesterday costs keyed by (service, usage_type)
    for entry in costs_yesterday:
        service, usage_type = entry["Keys"]
        cost = float(entry["Metrics"]["BlendedCost"]["Amount"])
        usage[(service, usage_type)] = {"yesterday": cost, "mtd": 0.0}

    # Add MTD costs
    for entry in costs_mtd:
        service, usage_type = entry["Keys"]
        cost = float(entry["Metrics"]["BlendedCost"]["Amount"])
        if (service, usage_type) in usage:
            usage[(service, usage_type)]["mtd"] = cost
        else:
            usage[(service, usage_type)] = {"yesterday": 0.0, "mtd": cost}

    result = [
        {
            "service": s,
            "usage_type": u,
            "yesterday": v["yesterday"],
            "mtd": v["mtd"]
        }
        for (s, u), v in usage.items() if v["mtd"] > 0.0001
    ]

    # Sort by mtd descending
    result.sort(key=lambda x: x["mtd"], reverse=True)
    return result


def notify(cost_data):

    # Mapping full service names to simpler aliases
    service_aliases = {
        "Amazon Simple Storage Service": "S3",
        "Amazon Elastic Compute Cloud - Compute": "EC2",
        "EC2 - Other": "EC2misc",
        "EC2 - ELB": "ELB",
        "Amazon Elastic Block Store": "EBS",
        "AWS Key Management Service": "KMS",
        "Amazon Virtual Private Cloud": "VPC",
        "Amazon Route 53": "R53",
        "Tax": "Tax",
        "Amazon CloudFront": "CDN",
        "AWS Lambda": "Lambda",
        "Amazon CloudWatch": "Logs"
    }

    client = boto3.client('ce', region_name=AWS_REGION)
    today = date.today()
    start_date = str(today.replace(day=1))
    end_date = str(today)

    response1 = client.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='MONTHLY',
        Metrics=['AmortizedCost']
    )
    response2 = client.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )
    accumulated_amortized_cost = response1['ResultsByTime'][0]['Total']['AmortizedCost']['Amount']
    accumulated_unblended_cost = response2['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']

    detailed_breakdown = get_detailed_breakdown()

    def alias(service_name):
        return service_aliases.get(service_name, service_name)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AWS Cost Report</title>
    </head>
    <body style="font-family: Arial, sans-serif;">
        <h2>Monthly AWS Cost Summary</h2>
        <table style="border-collapse: collapse; margin-bottom: 30px;">
            <tr style="background-color: #f2f2f2;">
                <th style="border: 1px solid #ddd; padding: 8px;">Period</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Unblended Cost</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Amortized Cost</th>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">{start_date} - {end_date}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${float(accumulated_unblended_cost):,.4f}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${float(accumulated_amortized_cost):,.4f}</td>
            </tr>
        </table>

        <h2>Service Level Breakdown</h2>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
            <tr style="background-color: #f2f2f2;">
                <th style="border: 1px solid #ddd; padding: 8px;">Service</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Cost (Yesterday)</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Cost (Month to Date)</th>
            </tr>
    """

    for item in cost_data:
        html_content += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">{alias(item['service'])}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${item['yesterday']:.4f}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${item['mtd']:.4f}</td>
            </tr>
        """

    html_content += """
        </table>

        <h2>Detailed Breakdown by Usage Type</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background-color: #f2f2f2;">
                <th style="border: 1px solid #ddd; padding: 8px;">Service</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Usage Type</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Cost (Yesterday)</th>
                <th style="border: 1px solid #ddd; padding: 8px;">Cost (Month to Date)</th>
            </tr>
    """

    for item in detailed_breakdown:
        html_content += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">{alias(item['service'])}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['usage_type']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${item['yesterday']:.4f}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${item['mtd']:.4f}</td>
            </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    try:
        ses = boto3.client('ses', region_name=AWS_REGION)
        response = ses.send_email(
            Source=AWS_SOURCE_EMAIL,
            Destination={'ToAddresses': AWS_DEST_EMAIL},
            Message={
                'Subject': {
                    'Data': 'Daily AWS Cost Report',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': html_content,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        print("Email sent! Message ID:", response['MessageId'])

    except NoCredentialsError:
        print("Credentials not available.")
    except PartialCredentialsError:
        print("Incomplete credentials configuration.")
    except Exception as e:
        print("Error occurred:", str(e))



def lambda_handler(a, b):
    cost_data = get_costs()
    notify(cost_data)
