from dotenv import load_dotenv
import json
import os

import aws_requests
import emails

def main():
    aws_cost_data = aws_requests.generate_cost_summary()
    email_body = emails.create_email_body(aws_cost_data)
    # emails.send_email(email_body, os.getenv("EMAIL_RECIPIENT"), os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
    emails.notify("CLOUD MONTHLY COST OVERVIEW", email_body)

if __name__ == '__main__':
    load_dotenv()
    main()