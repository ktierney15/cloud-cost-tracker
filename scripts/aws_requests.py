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



def generate_cost_summary():
    ''' Main AWS Function - Generates a cost summary'''
    # Initialize boto3 client for Cost Explorer
    output = {}
    client = boto3.client("ce")

    # get forecasted cost
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=30)
    response = client.get_cost_forecast(
        TimePeriod={
            'Start': str(today),
            'End': str(end_date)
        },
        Metric='UNBLENDED_COST',
        Granularity='DAILY'
    )

    output["monthly_forecast"] = response['Total']['Amount']
    output["monthly_forecast_unit"] = response['Total']['Unit']


    # get previous months bill
    start, end = get_previous_month_dates()
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start,
            'End': end
        },
        Metrics=['UnblendedCost'],
        Granularity='MONTHLY'
    )

    print(json.dumps(response, indent=2))
    output["previous_months_bill"] = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
    output["previous_months_bill_unit"] = response['ResultsByTime'][0]['Total']['UnblendedCost']['Unit']
    print(output)
    
    return output