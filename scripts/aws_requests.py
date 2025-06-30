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

def get_previous_months_bill(client):
    """Gets previous months bill"""
    start, end = get_previous_month_dates()
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start,
            'End': end
        },
        Metrics=['UnblendedCost'],
        Granularity='MONTHLY'
    )

    return response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'], response['ResultsByTime'][0]['Total']['UnblendedCost']['Unit']


def generate_cost_summary():
    """Main AWS Function - Generates a cost summary"""
    # Initialize boto3 client for Cost Explorer
    client = boto3.client("ce")

    # get custom cost data
    monthly_forecast, monthly_forecast_unit = get_forecasted_cost(client) 
    previous_months_bill, previous_months_bill_unit = get_previous_months_bill(client)

    # print(json.dumps(response, indent=2))
    
    
    return {
        'monthly_forecast': monthly_forecast, 
        'monthly_forecast_unit': monthly_forecast_unit, 
        'previous_months_bill': previous_months_bill, 
        'previous_months_bill_unit': previous_months_bill_unit
    }