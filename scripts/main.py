from dotenv import load_dotenv

import json
import os
import argparse

import aws_requests
import emails

def main():
    parser = argparse.ArgumentParser(description="My cron-based Python script")
    parser.add_argument("--email", action="store_true", help="Send an email with cost summary")
    args = parser.parse_args()

    aws_cost_data = aws_requests.generate_cost_summary()
    email_body = emails.create_email_body(aws_cost_data)
    
    if args.email:
        emails.send_email(email_body, os.getenv("EMAIL_RECIPIENT"), os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))

    print(email_body)

if __name__ == '__main__':
    load_dotenv()
    main()