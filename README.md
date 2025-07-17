# cloud-cost-tracker

This repository is for tracking your cloud spending data

## Setup
To set up this repository you first need to pull the version you want to run from this git repo
```bash
git clone --branch <version/tag> --depth 1 https://github.com/ktierney15/cloud-cost-tracker
```
Then you can rename the EXAMPLE.env file to .env and set your environment variables:   

AWS_ACCESS_KEY_ID - AWS access key ID  
AWS_SECRET_ACCESS_KEY - AWS access key secret 
AWS_DEFAULT_REGION - region you are gathering information from  
EMAIL_USER - email that you are sending from 
EMAIL_PASSWORD - email password  
EMAIL_RECIPIENT - email that you are sending the summary to

Finally, if you want this script to run on a a schedule (To send a monthly email summary for instance), you can run the run-cloud-cost-estimator.sh script as a cron job on your machine by running:
```bash
crontab -e
```
And setting the content of that file to the following:
```bash
# 7am on the first of every month
0 7 1 * * /path/to/cloud-cost-tracker/run-cloud-cost-estimator.sh >> /path/to/cron_log.txt 2>&1
```

**Optional Step** - to send emails with this script you will need to enable your email to use smtplib. For gmail for instance you have to setup multifactor authentication, then create a password for the script to use at https://myaccount.google.com/apppasswords  
if you dont want to use the email functionality you can remove the --email flag from the shell script

## Usage
To run the script locally, just run run-cloud-cost-estimator.sh or open the virtual environment and run scripts/main.py


## Coming soon
- Integration with other cloud platforms such as GCP and Azure
- other notification options such as alerts on Mac or Windows