import argparse
import json
import sys
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import build_engine
from app.services.review import DECISIONS, decide, history, preview


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local trusted-operator field review")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "decide", "history"):
        command = commands.add_parser(name)
        command.add_argument("kind", choices=("university", "program", "scholarship"))
        command.add_argument("identifier")
        command.add_argument("--source", required=True)
        command.add_argument("--field", required=True)
        if name == "decide":
            command.add_argument("--status", choices=DECISIONS, required=True)
            command.add_argument("--token", required=True)
            command.add_argument("--reviewer", required=True)
            command.add_argument("--reviewed-at", type=datetime.fromisoformat, required=True)
            command.add_argument("--valid-until", type=datetime.fromisoformat)
            command.add_argument("--confirm", action="store_true", required=True)
            command.add_argument("--supports-value", action="store_true")
    args = parser.parse_args(argv)
    engine = None
    try:
        settings = Settings()
        if args.command == "decide" and not settings.review_operator.strip():
            raise ValueError("Configure ATLAS_REVIEW_OPERATOR explicitly")
        engine = build_engine(settings)
        with Session(engine) as session, session.begin():
            scope = (session, args.kind, args.identifier, args.source, args.field)
            if args.command == "preview":
                result = preview(*scope)
            elif args.command == "history":
                result = history(*scope)
            else:
                record = decide(
                    *scope,
                    status=args.status,
                    token=args.token,
                    reviewer=args.reviewer,
                    operator=settings.review_operator,
                    reviewed_at=args.reviewed_at,
                    valid_until=args.valid_until,
                    confirmed=args.confirm,
                    supports_value=args.supports_value,
                )
                result = {"id": record.id, "status": record.verification_status}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ValueError:
        print(
            "Invalid review input, authority, evidence or stale preview; no decision committed.",
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError:
        print("Database operation failed; no decision committed. Preview again.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
