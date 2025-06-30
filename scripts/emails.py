import smtplib
from email.mime.text import MIMEText
import os

def create_email_body(payload):
    service_lines = "\n".join(
        f"  - {service}: ${float(amount):.2f}" for service, amount in payload["previous_bill_breakdown"].items()
    )
    return f"""
Projected Bill for the upcoming month: {float(payload["monthly_forecast"]):.2f} {payload["monthly_forecast_unit"]}
Bill From Previous Month: {float(payload["previous_months_bill"]):.2f} {payload["previous_months_bill_unit"]}
        
Breakdown by Service (AWS):
{service_lines}
    """

def send_email(body, to_email, from_email, password):
    msg = MIMEText(body)
    msg["Subject"] = "Cloud Monthly Cost Report"
    msg["From"] = from_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)