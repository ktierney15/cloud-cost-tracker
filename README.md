# cloud-cost-tracker

See where every dollar of your AWS bill goes: a FastAPI backend over AWS Cost Explorer, a web dashboard, and an optional monthly email report.

```
backend/   uv project: FastAPI API, Cost Explorer client, CLI, email report, tests
ui/        static dashboard (HTML/CSS/JS + Chart.js), served by the backend at /
```

## What it covers

Everything Cost Explorer can report on for the account (or the whole AWS Organization when run from the management account):

- **Headlines**: month-to-date spend (compared with the same days last month), projected spend for the month (AWS forecast), and last month's bill
- **Spend over time**: daily or monthly, stacked by service, account, region, charge type or purchase option
- **Full breakdown** of any date range by service, linked account (with account names), region, usage type, charge type (usage, tax, credits, refunds…), purchase option (on-demand, Savings Plans, spot…), instance type, operation, or any **cost allocation tag**
- Switch between metrics: unblended, amortized, net unblended, net amortized, blended
- Filter and export any breakdown to CSV

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ktierney15/cloud-cost-tracker
cd cloud-cost-tracker/backend
cp .env.example .env   # then fill in your values
uv sync
```

The AWS credentials need `ce:GetCostAndUsage`, `ce:GetCostForecast`, `ce:GetDimensionValues` and `ce:GetTags`. You can also leave the keys out and use an AWS profile or instance role.

> Cost Explorer charges **$0.01 per API request**. Responses are cached in memory for `CACHE_TTL_SECONDS` (default 6 hours; AWS refreshes cost data a few times a day). The dashboard's **Refresh** button clears the cache.

## Run the dashboard

From the repo root:

```bash
make start   # run in the background at http://127.0.0.1:8000
make stop    # stop it (also frees the port if something else is holding it)
make help    # run, dev, restart, status, logs, test, report, email…
```

Use `PORT=8001 make start` for another port. Or run it directly:

```bash
cd backend
uv run cost-tracker serve
```

Open http://127.0.0.1:8000. API docs are at http://127.0.0.1:8000/docs.

### API

| Endpoint | Purpose |
|---|---|
| `GET /api/summary?metric=` | Month to date, projected, last month, % changes |
| `GET /api/breakdown?group_by=&start=&end=&metric=` | Every line of spend grouped by a dimension (`SERVICE`, `LINKED_ACCOUNT`, `REGION`, `USAGE_TYPE`, `RECORD_TYPE`, `PURCHASE_TYPE`, `INSTANCE_TYPE`, `OPERATION`) or `TAG:<key>` |
| `GET /api/timeseries?granularity=DAILY\|MONTHLY&group_by=&start=&end=` | Spend per period, split by a dimension |
| `GET /api/tags` | Cost allocation tag keys seen in the last 3 months |
| `GET /api/meta`, `GET /api/health` | Available metrics and dimensions; status |
| `POST /api/refresh` | Clear the Cost Explorer cache |

Dates are `YYYY-MM-DD`; `end` is exclusive. Without dates you get the current month.

## Email report

```bash
cd backend
uv run cost-tracker report           # print it
uv run cost-tracker report --email   # print and email it
```

For Gmail, turn on 2-step verification and create an app password at https://myaccount.google.com/apppasswords for `EMAIL_PASSWORD`.

To send it monthly, add `run-cloud-cost-estimator.sh` to cron (`crontab -e`):

```bash
# 7am on the first of every month
0 7 1 * * /path/to/cloud-cost-tracker/run-cloud-cost-estimator.sh >> /path/to/cron_log.txt 2>&1
```

## Development

```bash
cd backend
uv run pytest
uv run pylint src
uv run cost-tracker serve --reload
```

The UI is plain static files, so edits show up on reload with no build step.

## Coming soon

- GCP and Azure providers (the backend already has a provider interface: see `backend/src/cost_tracker/base.py`)
- Budget alerts and anomaly notifications
