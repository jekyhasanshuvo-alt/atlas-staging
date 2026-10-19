import argparse
import json
import sys

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import build_engine
from app.schemas.curated import load_batch
from app.services.curated_import import ImportConflict, apply_import, preview_import


class DatabasePreflightError(RuntimeError):
    pass


def scholarship_database_preflight(session, settings, *, read_only):
    """Check the connected database before planning or applying version-2 input."""
    if read_only:
        session.execute(text("SET TRANSACTION READ ONLY"))
    identity = dict(
        session.execute(
            text(
                "SELECT current_database() AS name, host(inet_server_addr()) AS server_address, "
                "inet_server_port() AS server_port, "
                "current_setting('transaction_read_only') AS read_only"
            )
        )
        .mappings()
        .one()
    )
    expected = make_url(settings.database_url.get_secret_value())
    if identity["name"] != expected.database:
        raise DatabasePreflightError("Database identity mismatch; no import changes committed")
    revisions = session.scalars(text("SELECT version_num FROM public.alembic_version")).all()
    if revisions != ["0004"]:
        raise DatabasePreflightError("Scholarship import requires exactly revision 0004")
    if read_only and identity["read_only"] != "on":
        raise DatabasePreflightError("Preview requires a read-only PostgreSQL transaction")
    return {**identity, "revision": "0004"}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate, preview or create curated catalog records; never overwrite"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "preview", "apply"):
        command = commands.add_parser(name)
        command.add_argument("path")
        if name == "apply":
            command.add_argument("--confirm", action="store_true", required=True)
    args = parser.parse_args(argv)
    engine = None
    try:
        batch = load_batch(args.path)
        if args.command == "validate":
            print(
                json.dumps(
                    {
                        "valid": True,
                        "database_checked": False,
                        **(
                            {"scholarships": len(batch.scholarships), "schema_version": 2}
                            if batch.schema_version == 2
                            else {
                                "universities": len(batch.universities),
                                "programs": len(batch.programs),
                            }
                        ),
                        "sources": len(batch.sources),
                        "evidence": len(batch.evidence),
                    }
                )
            )
            return 0
        settings = Settings()
        engine = build_engine(settings)
        database = None
        with Session(engine) as session, session.begin():
            if batch.schema_version == 2:
                database = scholarship_database_preflight(
                    session, settings, read_only=args.command == "preview"
                )
            if args.command == "apply":
                plan = apply_import(session, batch, confirmed=args.confirm)
            else:
                plan = preview_import(session, batch)
        report = plan.report(applied=args.command == "apply")
        if database is not None:
            report["database"] = database
        print(json.dumps(report))
        return 1 if plan.conflicts else 0
    except DatabasePreflightError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    except ImportConflict as error:
        print(json.dumps(error.plan.report()))
        return 1
    except ValidationError as error:
        print(
            json.dumps(
                {
                    "error": "Invalid input or configuration",
                    "fields": error.errors(
                        include_input=False, include_context=False, include_url=False
                    ),
                }
            ),
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError, UnicodeError, RecursionError):
        print(
            json.dumps(
                {
                    "error": "Invalid or unreadable import file; check schema, bounds, JSON and UTF-8 encoding"
                }
            ),
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError:
        print(
            json.dumps(
                {
                    "error": "Database operation failed; no import changes committed. Check connectivity or concurrent conflicts and retry preview."
                }
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
