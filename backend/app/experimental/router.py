"""Registered only by explicit test configuration. Gate cannot be enabled by HTTP."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel

from app.api.v1.workspace import export_data
from app.db.session import get_session
from app.experimental import schemas as s
from app.experimental import service as svc
from app.experimental.gate import require_foundation
from app.schemas.catalog import PageMeta
from app.services.security import verified

router = APIRouter(
    prefix="/api/v1/me",
    tags=["synthetic-only foundation"],
    dependencies=[Depends(require_foundation)],
)
DB = Annotated[object, Depends(get_session)]
Owner = Annotated[object, Depends(verified)]
PageNumber = Annotated[int, Query(ge=1, le=10000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


class Page[T](BaseModel):
    items: list[T]
    meta: PageMeta


@router.get("/programs", response_model=Page[s.SavedRead])
def programs(user: Owner, db: DB, page: PageNumber = 1, page_size: PageSize = 50):
    return svc.saved_list(db, user, page, page_size)


@router.post("/programs", response_model=s.SavedRead)
def save(data: s.Reference, response: Response, user: Owner, db: DB):
    item, created = svc.save_program(db, user, data.id)
    response.status_code = 201 if created else 200
    return item


@router.delete("/programs/{identifier}", status_code=204)
def remove(identifier: s.Identifier, user: Owner, db: DB):
    svc.remove_program(db, user, identifier)


@router.get("/academic-credentials", response_model=Page[s.AcademicRead])
def academics(user: Owner, db: DB, page: PageNumber = 1, page_size: PageSize = 50):
    return svc.credential_list(db, user, "academic", page, page_size)


@router.post("/academic-credentials", response_model=s.AcademicRead, status_code=201)
def add_academic(data: s.AcademicCreate, user: Owner, db: DB):
    return svc.create_credential(db, user, "academic", data)


@router.get("/academic-credentials/{identifier}", response_model=s.AcademicRead)
def academic(identifier: UUID, user: Owner, db: DB):
    return svc.credential_dto(db, "academic", svc.owned_record(db, user, "academic", identifier))


@router.patch("/academic-credentials/{identifier}", response_model=s.AcademicRead)
def patch_academic(identifier: UUID, data: s.AcademicPatch, user: Owner, db: DB):
    return svc.update_credential(db, user, "academic", identifier, data)


@router.delete("/academic-credentials/{identifier}", status_code=204)
def delete_academic(identifier: UUID, user: Owner, db: DB):
    svc.remove_credential(db, user, "academic", identifier)


@router.get("/language-credentials", response_model=Page[s.LanguageRead])
def languages(user: Owner, db: DB, page: PageNumber = 1, page_size: PageSize = 50):
    return svc.credential_list(db, user, "language", page, page_size)


@router.post("/language-credentials", response_model=s.LanguageRead, status_code=201)
def add_language(data: s.LanguageCreate, user: Owner, db: DB):
    return svc.create_credential(db, user, "language", data)


@router.get("/language-credentials/{identifier}", response_model=s.LanguageRead)
def language(identifier: UUID, user: Owner, db: DB):
    return svc.credential_dto(db, "language", svc.owned_record(db, user, "language", identifier))


@router.patch("/language-credentials/{identifier}", response_model=s.LanguageRead)
def patch_language(identifier: UUID, data: s.LanguagePatch, user: Owner, db: DB):
    return svc.update_credential(db, user, "language", identifier, data)


@router.delete("/language-credentials/{identifier}", status_code=204)
def delete_language(identifier: UUID, user: Owner, db: DB):
    svc.remove_credential(db, user, "language", identifier)


@router.get("/study-preferences", response_model=s.PreferencesRead)
def preferences(user: Owner, db: DB):
    return svc.read_preferences(db, user)


@router.put("/study-preferences", response_model=s.PreferencesRead)
def put_preferences(data: s.PreferencesReplace, user: Owner, db: DB):
    return svc.replace_preferences(db, user, data)


@router.delete("/study-preferences", status_code=204)
def clear_preferences(user: Owner, db: DB):
    svc.remove_preferences(db, user)


@router.get("/foundation/export")
def export_v2(response: Response, user: Owner, db: DB):
    # Existing v1 remains exactly v1; this separately gated path is explicitly version 2.
    original = export_data(response, user, db)
    return {**original, "export_version": 2, "foundation": svc.export_foundation(db, user)}
