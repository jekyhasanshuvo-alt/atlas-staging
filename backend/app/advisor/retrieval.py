"""Bounded adapters over existing current-review/publication contracts; no fetching."""

from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.intelligence import Fact
from app.services.intelligence import dto, statement
from app.services.scholarship_public import public_dto, visible_rows


@dataclass
class Record:
    id: str
    kind: str
    name: str
    is_demo: bool
    facts: dict[str, Fact] = field(default_factory=dict)


class Retriever(Protocol):
    def retrieve(self, kind: str, ids: list[str], search: str) -> list[Record]: ...


class CatalogRetriever:
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings

    def retrieve(self, kind, ids, search):
        if kind == "scholarship":
            # At most200 release approvals are permitted by existing Settings; no legacy fallback.
            rows = [
                row
                for row in visible_rows(self.db, self.settings)
                if (not ids or row.id in ids)
                and search.casefold() in (row.name + " " + row.provider).casefold()
            ]
            result = []
            for row in sorted(rows, key=lambda r: (r.name.casefold(), r.id))[:4]:
                value = public_dto(row)
                # Public DTO lacks per-evidence review timestamps. Do not upgrade those to advisor supporting citations.
                facts = {
                    key: Fact(
                        value=getattr(value, key),
                        verification_status="unverified",
                        evidence=[],
                        caveat="Published snapshot description; exact field review metadata unavailable to this adapter.",
                    )
                    for key in [
                        "name",
                        "provider",
                        "description",
                        "eligibility_summary",
                        "coverage",
                    ]
                }
                result.append(Record(row.id, "scholarship", row.name, False, facts))
            return result
        plural = "programs" if kind == "program" else "universities"
        filters = {"ids": ids} if ids else {"q": search}
        rows = self.db.scalars(statement(plural, filters).limit(4)).all()
        results = []
        for row in rows:
            value = dto(row)
            results.append(Record(value.id, value.kind, value.name, value.is_demo, value.facts))
        return results
