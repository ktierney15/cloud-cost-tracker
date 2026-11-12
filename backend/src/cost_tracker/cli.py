"""Command line entry point: `cost-tracker serve` or `cost-tracker report [--email]`."""

from __future__ import annotations

import argparse
import sys

from . import notify, service
from .config import settings


def _report(args: argparse.Namespace) -> int:
    from .api import get_provider

    provider = get_provider()
    summary = service.summary(provider, args.metric)
    start, end = service.previous_month()
    body = notify.report_body(
        summary,
        provider.breakdown(start, end, "SERVICE", args.metric),
        provider.breakdown(start, end, "LINKED_ACCOUNT", args.metric),
    )
    print(body)
    if args.email:
        missing = [
            name
            for name, val in {
                "EMAIL_USER": settings.email_user,
                "EMAIL_PASSWORD": settings.email_password,
                "EMAIL_RECIPIENT": settings.email_recipient,
            }.items()
            if not val
        ]
        if missing:
            print(f"Cannot send email, missing: {', '.join(missing)}", file=sys.stderr)
            return 1
        notify.send_email(
            body,
            to=settings.email_recipient,
            sender=settings.email_user,
            password=settings.email_password,
            host=settings.smtp_host,
            port=settings.smtp_port,
        )
        print(f"Report emailed to {settings.email_recipient}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("cost_tracker.api:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cost-tracker", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("report", help="Print (and optionally email) a cost summary")
    rep.add_argument("--email", action="store_true", help="Email the report")
    rep.add_argument("--metric", default="UnblendedCost")
    rep.set_defaults(func=_report)

    srv = sub.add_parser("serve", help="Run the API and dashboard")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8000)
    srv.add_argument("--reload", action="store_true")
    srv.set_defaults(func=_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
