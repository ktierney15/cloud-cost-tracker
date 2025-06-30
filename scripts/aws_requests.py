import boto3

from datetime import datetime, timedelta
import json


def get_previous_month_dates():
    """Returns start and end dates in YYYY-MM-DD format for the previous month."""
    today = datetime.today()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    return str(first_day_prev_month.date()), str(last_day_prev_month.date() + timedelta(days=1))


def get_forecasted_cost(client, days=30):
    """Gets forecasted monthly/selected time cost"""
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=days)
    response = client.get_cost_forecast(
        TimePeriod={
            'Start': str(today),
            'End': str(end_date)
        },
        Metric='UNBLENDED_COST',
        Granularity='DAILY'
    )

    return response['Total']['Amount'], response['Total']['Unit']

def get_previous_months_bill(client, start, end):
    """Gets previous months bill"""
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start,
            'End': end
        },
        Metrics=['UnblendedCost'],
        Granularity='MONTHLY'
    )

    return response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'], response['ResultsByTime'][0]['Total']['UnblendedCost']['Unit']

def get_previous_bill_breakdown(client, start, end):
    """Returns an item by item breakdown of your bill"""
    output = {}
    response = client.get_cost_and_usage(
        TimePeriod={'Start': start, 'End': end},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )

    for item in response["ResultsByTime"][0]["Groups"]:
        output[item["Keys"][0]] = item["Metrics"]["UnblendedCost"]["Amount"]
    
    return output


def generate_cost_summary():
    """Main AWS Function - Generates a cost summary"""
    # Initialize boto3 client for Cost Explorer
    client = boto3.client("ce")

    # get previous months start and end dates
    start, end = get_previous_month_dates()

    # get custom cost data
    monthly_forecast, monthly_forecast_unit = get_forecasted_cost(client) 
    previous_months_bill, previous_months_bill_unit = get_previous_months_bill(client, start, end)
    previous_bill_breakdown = get_previous_bill_breakdown(client, start, end)


    # print(json.dumps(response, indent=4))

    
    
    return {
        'monthly_forecast': monthly_forecast, 
        'monthly_forecast_unit': monthly_forecast_unit, 
        'previous_months_bill': previous_months_bill, 
        'previous_months_bill_unit': previous_months_bill_unit,
        'previous_bill_breakdown' : previous_bill_breakdown 
    }