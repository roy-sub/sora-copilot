#!/usr/bin/env python3
"""Run the SORA Copilot API.

    python main.py                 # http://127.0.0.1:8000, reloads on change
    python main.py --port 9000
    python main.py --prod          # no reload, binds 0.0.0.0, what a host runs

There is no Dockerfile and nothing to build. Every dependency is a Python wheel —
the PDF renderer and the map chart carry their own typeface — so a checkout plus
`pip install -e .` is a working backend on any machine with Python 3.12.

Settings come from ``backend/.env`` (see ``.env.example`` at the repository root).
None of them is required to start: without Supabase the store is in-process, without
an Anthropic key intake falls back to the deterministic extractor, and without Stripe
every account sits on the free plan. Each says so through ``/healthz`` rather than
failing. ``ENV=production`` is the exception — it refuses to start without the
Supabase keys, because a compliance product should not come up half-configured and
look healthy.
"""

from __future__ import annotations

import argparse
import os
import sys

DEFAULT_PORT = 8000


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Run the SORA Copilot API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", ""),
        help="Interface to bind. Defaults to 127.0.0.1, or 0.0.0.0 with --prod.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", DEFAULT_PORT)),
        help=f"Port to listen on (default {DEFAULT_PORT}, or $PORT).",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="No reload, bind every interface, and log as a server rather than a terminal.",
    )
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=None,
        help="Force auto-reload on (the default unless --prod).",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Force auto-reload off.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("WEB_CONCURRENCY", 1)),
        help="Worker processes. Only with --prod and only without reload.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        import uvicorn
    except ModuleNotFoundError:
        print(
            "uvicorn is not installed. From backend/:\n"
            "    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'\n"
            "    .venv/bin/python main.py",
            file=sys.stderr,
        )
        return 1

    host = args.host or ("0.0.0.0" if args.prod else "127.0.0.1")
    reload = (not args.prod) if args.reload is None else args.reload
    # Reload runs a supervisor in this process, so it cannot share with workers.
    workers = 1 if reload else max(1, args.workers)

    # Read once here purely to print a useful banner; the app reads settings itself.
    from app.config import get_settings

    settings = get_settings()
    print(
        f"SORA Copilot API · {settings.env} · rulebase {settings.rulebase_version}\n"
        f"  http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{args.port}\n"
        f"  docs  /docs        health  /healthz\n"
        f"  database {'supabase' if settings.supabase_configured else 'in-memory (not durable)'}"
        f" · intake {'model' if settings.anthropic_configured else 'deterministic'}"
        f" · payments {'stripe' if settings.stripe_configured else 'off'}",
        flush=True,
    )

    uvicorn.run(
        "app.main:app",
        host=host,
        port=args.port,
        reload=reload,
        workers=workers if not reload else None,
        access_log=not args.prod,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
