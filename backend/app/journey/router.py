from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.v1.workspace import export_data
from app.db.session import get_session
from app.experimental.service import export_foundation
from app.journey import schemas as s
from app.journey import service as svc
from app.journey.gate import require_journey
from app.services.security import verified

router = APIRouter(
    prefix="/api/v1/me",
    tags=["synthetic-only application journey"],
    dependencies=[Depends(require_journey)],
)
DB = Annotated[object, Depends(get_session)]
Owner = Annotated[object, Depends(verified)]
PageNumber = Annotated[int, Query(ge=1, le=10000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("/application-journey/capability")
def capability(user: Owner):
    return {
        "available": True,
        "basis": "synthetic_disposable_only",
        "official_requirements": "UNKNOWN",
    }


@router.get("/application-journey/dashboard", response_model=s.Dashboard)
def dashboard(user: Owner, db: DB):
    return svc.dashboard(db, user)


@router.get("/application-journey/export")
def export(response: Response, user: Owner, db: DB):
    original = export_data(response, user, db)
    return {
        **original,
        "export_version": 3,
        "foundation": export_foundation(db, user),
        "application_journey": svc.export(db, user),
    }


@router.get("/applications", response_model=s.Page[s.ApplicationRead])
def applications(
    user: Owner,
    db: DB,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    archived: bool = False,
    stage: s.Stage | None = None,
):
    return svc.list_applications(db, user, page, page_size, archived, stage)


@router.post("/applications", response_model=s.ApplicationRead, status_code=201)
def create(data: s.ApplicationCreate, user: Owner, db: DB):
    return svc.create(db, user, data)


@router.get("/applications/{identifier}", response_model=s.ApplicationRead)
def application(identifier: UUID, user: Owner, db: DB):
    return svc.application_dto(db, svc.owned(db, user, identifier))


@router.patch("/applications/{identifier}", response_model=s.ApplicationRead)
def patch(identifier: UUID, data: s.ApplicationPatch, user: Owner, db: DB):
    return svc.update(db, user, identifier, data)


@router.patch("/applications/{identifier}/stage", response_model=s.ApplicationRead)
def stage(identifier: UUID, data: s.StageChange, user: Owner, db: DB):
    return svc.change_stage(db, user, identifier, data)


@router.delete("/applications/{identifier}", status_code=204)
def delete_application(identifier: UUID, data: s.DeleteApplication, user: Owner, db: DB):
    svc.remove(db, user, identifier, data)


@router.get("/applications/{identifier}/timeline", response_model=s.Page[s.EventRead])
def timeline(identifier: UUID, user: Owner, db: DB, page: PageNumber = 1, page_size: PageSize = 20):
    return svc.timeline(db, user, identifier, page, page_size)


@router.get("/applications/{identifier}/items", response_model=s.Page[s.ItemRead])
def items(
    identifier: UUID,
    user: Owner,
    db: DB,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    kind: Literal["task", "document", "reminder", "note"] | None = None,
    completed: bool | None = None,
    due_before: date | None = None,
):
    return svc.list_items(db, user, identifier, page, page_size, kind, completed, due_before)


@router.post("/applications/{identifier}/items", response_model=s.ItemRead, status_code=201)
def add_item(identifier: UUID, data: s.ItemCreate, user: Owner, db: DB):
    return svc.add_item(db, user, identifier, data)


@router.patch("/applications/{identifier}/items/{item_id}", response_model=s.ItemRead)
def update_item(identifier: UUID, item_id: UUID, data: s.ItemPatch, user: Owner, db: DB):
    return svc.update_item(db, user, identifier, item_id, data)


@router.delete("/applications/{identifier}/items/{item_id}", status_code=204)
def delete_item(
    identifier: UUID,
    item_id: UUID,
    user: Owner,
    db: DB,
    expected_version: Annotated[int, Query(ge=1)],
):
    svc.remove_item(db, user, identifier, item_id, expected_version)
