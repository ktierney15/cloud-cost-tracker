"""Plain-text cost report and SMTP delivery."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText


def _money(v: float | None) -> str:
    return "n/a" if v is None else f"${v:,.2f}"


def _pct(v: float | None) -> str:
    return "" if v is None else f" ({v:+.1f}%)"


def report_body(summary: dict, services: list[dict], accounts: list[dict]) -> str:
    lines = [
        f"Cloud cost report - as of {summary['as_of']} ({summary['metric']})",
        "",
        f"Month to date ({summary['month_to_date_days']} days): "
        f"{_money(summary['month_to_date'])}{_pct(summary['mtd_change_pct'])}",
        f"Projected this month: {_money(summary['projected_month'])}"
        f"{_pct(summary['projected_change_pct'])}",
        f"Last month: {_money(summary['last_month'])}",
        "",
        "Last month by service:",
        *(f"  - {s['label']}: {_money(s['amount'])}" for s in services if round(s["amount"], 2)),
    ]
    if len(accounts) > 1:
        lines += ["", "Last month by account:"]
        lines += [f"  - {a['label']}: {_money(a['amount'])}" for a in accounts]
    return "\n".join(lines) + "\n"


def send_email(body: str, *, to: str, sender: str, password: str, host: str, port: int) -> None:
    msg = MIMEText(body)
    msg["Subject"] = "Cloud Monthly Cost Report"
    msg["From"] = sender
    msg["To"] = to
    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
