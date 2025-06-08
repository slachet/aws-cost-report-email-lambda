import boto3
import os
from datetime import date, timedelta, datetime
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from zoneinfo import ZoneInfo

AWS_SOURCE_EMAIL="EXAMPLE@EXAMPLE.com"
AWS_REGION="REGION_NAME"
AWS_DEST_EMAIL=["EXAMPLE@EXAMPLE.com"]

def get_all_cost_data():
    """Fetch all cost data with minimal API calls"""
    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))
    today = now_jst.date()
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
        "Amazon CloudWatch",
        "AWS Cost Explorer",
        "AWS Config"
    ]
    
    # API Call 1: Get daily breakdown for the entire month (includes yesterday)
    response_daily = client.get_cost_and_usage(
        TimePeriod={"Start": str(start_of_month), "End": str(today)},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "USAGE_TYPE"}
        ],
        Filter={"Dimensions": {"Key": "SERVICE", "Values": services}}
    )
    
    # API Call 2: Get monthly totals with both metrics
    response_monthly = client.get_cost_and_usage(
        TimePeriod={"Start": str(start_of_month), "End": str(today)},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost", "AmortizedCost"]
    )
    
    # Process the data
    service_costs = {}  # {service: {yesterday: x, mtd: y}}
    detailed_costs = {}  # {(service, usage_type): {yesterday: x, mtd: y}}
    
    # Process daily data
    for day_result in response_daily.get("ResultsByTime", []):
        day_date = datetime.strptime(day_result["TimePeriod"]["Start"], "%Y-%m-%d").date()
        is_yesterday = (day_date == yesterday)
        
        for group in day_result.get("Groups", []):
            service, usage_type = group["Keys"]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            
            # Update service-level costs
            if service not in service_costs:
                service_costs[service] = {"yesterday": 0.0, "mtd": 0.0}
            service_costs[service]["mtd"] += cost
            if is_yesterday:
                service_costs[service]["yesterday"] += cost
            
            # Update detailed costs
            key = (service, usage_type)
            if key not in detailed_costs:
                detailed_costs[key] = {"yesterday": 0.0, "mtd": 0.0}
            detailed_costs[key]["mtd"] += cost
            if is_yesterday:
                detailed_costs[key]["yesterday"] += cost
    
    # Get monthly totals
    monthly_totals = response_monthly['ResultsByTime'][0]['Total']
    accumulated_unblended_cost = monthly_totals['UnblendedCost']['Amount']
    accumulated_amortized_cost = monthly_totals['AmortizedCost']['Amount']
    
    return {
        "service_costs": service_costs,
        "detailed_costs": detailed_costs,
        "monthly_totals": {
            "unblended": accumulated_unblended_cost,
            "amortized": accumulated_amortized_cost
        },
        "period": {
            "start": str(start_of_month),
            "end": str(today)
        }
    }

def notify(cost_data):
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
        "Amazon CloudWatch": "Logs",
        "AWS Cost Explorer": "CE",
        "AWS Config": "Config"
    }
    
    def alias(service_name):
        return service_aliases.get(service_name, service_name)
    
    # Prepare service-level data
    service_list = [
        {"service": s, "yesterday": v["yesterday"], "mtd": v["mtd"]}
        for s, v in cost_data["service_costs"].items()
    ]
    service_list.sort(key=lambda x: x["mtd"], reverse=True)
    
    # Prepare detailed data
    detailed_list = [
        {
            "service": s,
            "usage_type": u,
            "yesterday": v["yesterday"],
            "mtd": v["mtd"]
        }
        for (s, u), v in cost_data["detailed_costs"].items()
        if v["mtd"] > 0.0001
    ]
    detailed_list.sort(key=lambda x: x["mtd"], reverse=True)
    
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
                <td style="border: 1px solid #ddd; padding: 8px;">{cost_data["period"]["start"]} - {cost_data["period"]["end"]}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${float(cost_data["monthly_totals"]["unblended"]):,.4f}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">${float(cost_data["monthly_totals"]["amortized"]):,.4f}</td>
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
    
    for item in service_list:
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
    
    for item in detailed_list:
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
    cost_data = get_all_cost_data()
    notify(cost_data)
