import hashlib
import json
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select

from app.db.session import get_session
from app.models.catalog import Scholarship, University
from app.models.student import (
    AuthSession,
    DataImportRecord,
    FinancialPlan,
    SavedScholarship,
    SavedUniversity,
    StudentChecklistItem,
    StudentComparison,
    StudentProfile,
)
from app.schemas.student import (
    CHECKLISTS,
    ChecklistInput,
    ComparisonInput,
    DeleteAccount,
    ImportInput,
    PlanCreate,
    PlanUpdate,
    ProfilePatch,
    ReferenceInput,
)
from app.services.security import audit, now, throttle, verified, verify_password

router = APIRouter(prefix="/me", tags=["private workspace"])
PROFILE_FIELDS = set(ProfilePatch.model_fields) - {"complete_onboarding"}
PLAN_FIELDS = set(PlanCreate.model_fields)


def profile_dto(profile):
    return {
        **{
            f: (
                format(getattr(profile, f), ".2f")
                if isinstance(getattr(profile, f), Decimal)
                else getattr(profile, f)
            )
            for f in PROFILE_FIELDS
        },
        "onboarding_completed_at": profile.onboarding_completed_at,
        "updated_at": profile.updated_at,
    }


def totals(plan):
    monthly = plan.accommodation + plan.food + plan.transportation + plan.other
    annual = plan.tuition + monthly * 12 + plan.insurance
    total = annual * plan.years + plan.relocation + plan.emergency
    funding = plan.scholarship * plan.years
    return {
        k: format(v, ".2f")
        for k, v in {
            "monthly": monthly,
            "annual": annual,
            "total": total,
            "funding": funding,
            "adjusted": max(Decimal(0), total - funding),
        }.items()
    }


def plan_dto(plan):
    return {
        **{
            f: (
                format(getattr(plan, f), ".2f")
                if isinstance(getattr(plan, f), Decimal)
                else getattr(plan, f)
            )
            for f in PLAN_FIELDS
        },
        "id": str(plan.id),
        "version": plan.version,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "totals": totals(plan),
    }


def profile_for(db, user):
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.get("/profile")
def get_profile(user=Depends(verified), db=Depends(get_session)):
    return profile_dto(profile_for(db, user))


def update_profile(profile, data):
    for field, value in data.model_dump(
        exclude_unset=True, exclude={"complete_onboarding"}
    ).items():
        setattr(profile, field, value)
    if data.complete_onboarding:
        required = [
            "full_name",
            "nationality",
            "current_country",
            "preferred_destination",
            "education_level",
            "preferred_subject",
        ]
        if (
            any(len(getattr(profile, f).strip()) < 2 for f in required)
            or profile.budget_amount <= 0
        ):
            raise HTTPException(
                422,
                "Complete personal, academic, destination, subject and budget fields before finishing onboarding.",
            )
        profile.onboarding_completed_at = now()


@router.patch("/profile")
def patch_profile(data: ProfilePatch, user=Depends(verified), db=Depends(get_session)):
    profile = profile_for(db, user)
    update_profile(profile, data)
    db.commit()
    return profile_dto(profile)


def saved_ids(db, user, model, field):
    return list(
        db.scalars(
            select(getattr(model, field))
            .where(model.user_id == user.id)
            .order_by(model.created_at, getattr(model, field))
            .limit(500)
        )
    )


def list_saved(db, user, model, field, page, page_size):
    query = select(model).where(model.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(model.created_at, getattr(model, field))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [{"id": getattr(row, field), "created_at": row.created_at} for row in rows],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


def save(db, user, model, catalog, field, identifier, settings=None):
    row = db.get(catalog, identifier)
    if row is None:
        raise HTTPException(404, "Catalog record no longer exists.")
    if catalog is Scholarship and row.contract_version == 2:
        from app.services.scholarship_public import visible_scholarship

        if settings is None or visible_scholarship(db, settings, identifier) is None:
            raise HTTPException(404, "Catalog record no longer exists.")
    if db.get(model, (user.id, identifier)) is None:
        count = db.scalar(select(func.count()).select_from(model).where(model.user_id == user.id))
        if count >= 500:
            raise HTTPException(409, "Saved list limit reached (500).")
        db.add(model(user_id=user.id, **{field: identifier}))
        db.flush()


@router.get("/universities")
def universities(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(50, ge=1, le=100),
    user=Depends(verified),
    db=Depends(get_session),
):
    return list_saved(db, user, SavedUniversity, "university_id", page, page_size)


@router.post("/universities")
def save_university(data: ReferenceInput, user=Depends(verified), db=Depends(get_session)):
    save(db, user, SavedUniversity, University, "university_id", data.id)
    db.commit()
    return {"id": data.id}


@router.delete("/universities/{identifier}")
def unsave_university(identifier: str, user=Depends(verified), db=Depends(get_session)):
    db.execute(
        delete(SavedUniversity).where(
            SavedUniversity.user_id == user.id, SavedUniversity.university_id == identifier
        )
    )
    db.commit()
    return {"message": "Removed."}


@router.get("/scholarships")
def scholarships(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(50, ge=1, le=100),
    user=Depends(verified),
    db=Depends(get_session),
):
    return list_saved(db, user, SavedScholarship, "scholarship_id", page, page_size)


@router.post("/scholarships")
def save_scholarship(
    data: ReferenceInput, request: Request, user=Depends(verified), db=Depends(get_session)
):
    save(
        db,
        user,
        SavedScholarship,
        Scholarship,
        "scholarship_id",
        data.id,
        request.app.state.settings,
    )
    db.commit()
    return {"id": data.id}


@router.delete("/scholarships/{identifier}")
def unsave_scholarship(identifier: str, user=Depends(verified), db=Depends(get_session)):
    db.execute(
        delete(SavedScholarship).where(
            SavedScholarship.user_id == user.id, SavedScholarship.scholarship_id == identifier
        )
    )
    db.commit()
    return {"message": "Removed."}


def comparison_ids(db, user):
    return list(
        db.scalars(
            select(StudentComparison.university_id)
            .where(StudentComparison.user_id == user.id)
            .order_by(StudentComparison.display_order)
        )
    )


@router.get("/comparison")
def comparison(user=Depends(verified), db=Depends(get_session)):
    return {"ids": comparison_ids(db, user)}


def replace_comparison(db, user, ids):
    found = set(db.scalars(select(University.id).where(University.id.in_(ids))))
    if found != set(ids):
        raise HTTPException(
            422, "One or more universities are no longer available. Refresh your selection."
        )
    db.execute(delete(StudentComparison).where(StudentComparison.user_id == user.id))
    db.flush()
    db.add_all(
        [
            StudentComparison(user_id=user.id, university_id=identifier, display_order=i)
            for i, identifier in enumerate(ids)
        ]
    )


@router.put("/comparison")
def put_comparison(data: ComparisonInput, user=Depends(verified), db=Depends(get_session)):
    replace_comparison(db, user, data.ids)
    db.commit()
    return {"ids": data.ids}


def plan_for(db, user, identifier):
    plan = db.scalar(
        select(FinancialPlan).where(
            FinancialPlan.id == identifier, FinancialPlan.user_id == user.id
        )
    )
    if plan is None:
        raise HTTPException(404, "Financial plan not found.")
    return plan


def create_plan(db, user, data):
    if (
        db.scalar(
            select(func.count()).select_from(FinancialPlan).where(FinancialPlan.user_id == user.id)
        )
        >= 100
    ):
        raise HTTPException(409, "Plan limit reached (100).")
    plan = FinancialPlan(
        user_id=user.id,
        **data.model_dump(exclude={"baseline"}),
        baseline=data.baseline.model_dump(mode="json") if data.baseline else None,
    )
    db.add(plan)
    db.flush()
    return plan


@router.get("/financial-plans")
def plans(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(verified),
    db=Depends(get_session),
):
    query = select(FinancialPlan).where(FinancialPlan.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(FinancialPlan.updated_at.desc(), FinancialPlan.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [plan_dto(p) for p in rows],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/financial-plans", status_code=201)
def post_plan(data: PlanCreate, user=Depends(verified), db=Depends(get_session)):
    plan = create_plan(db, user, data)
    db.commit()
    return plan_dto(plan)


@router.get("/financial-plans/{identifier}")
def get_plan(identifier: uuid.UUID, user=Depends(verified), db=Depends(get_session)):
    return plan_dto(plan_for(db, user, identifier))


@router.patch("/financial-plans/{identifier}")
def patch_plan(
    identifier: uuid.UUID, data: PlanUpdate, user=Depends(verified), db=Depends(get_session)
):
    plan = plan_for(db, user, identifier)
    if plan.version != data.version:
        raise HTTPException(
            409,
            "This plan changed on another device. Reload before saving; your draft has not been overwritten.",
        )
    merged = {field: getattr(plan, field) for field in PLAN_FIELDS}
    merged.update(data.model_dump(exclude_unset=True, exclude={"version"}))
    try:
        validated = PlanCreate.model_validate(merged)
    except ValueError:
        raise HTTPException(422, "Invalid financial plan fields.") from None
    for field, value in validated.model_dump(exclude={"baseline"}).items():
        setattr(plan, field, value)
    plan.baseline = validated.baseline.model_dump(mode="json") if validated.baseline else None
    plan.version += 1
    db.commit()
    return plan_dto(plan)


@router.delete("/financial-plans/{identifier}")
def delete_plan(identifier: uuid.UUID, user=Depends(verified), db=Depends(get_session)):
    db.delete(plan_for(db, user, identifier))
    db.commit()
    return {"message": "Plan deleted."}


def checklist_dto(db, user):
    rows = db.scalars(select(StudentChecklistItem).where(StudentChecklistItem.user_id == user.id))
    result = {category: [] for category in CHECKLISTS}
    for row in rows:
        if row.completed:
            result[row.category].append(row.stable_item_key)
    return result


@router.get("/checklists")
def checklists(user=Depends(verified), db=Depends(get_session)):
    return checklist_dto(db, user)


@router.put("/checklists")
def put_checklist(data: ChecklistInput, user=Depends(verified), db=Depends(get_session)):
    existing = {
        r.stable_item_key: r
        for r in db.scalars(
            select(StudentChecklistItem).where(
                StudentChecklistItem.user_id == user.id,
                StudentChecklistItem.category == data.category,
            )
        )
    }
    for key in CHECKLISTS[data.category]:
        row = existing.get(key)
        if row is None:
            row = StudentChecklistItem(user_id=user.id, category=data.category, stable_item_key=key)
            db.add(row)
        row.completed = key in data.completed
    db.commit()
    return checklist_dto(db, user)


@router.get("/dashboard")
def dashboard(user=Depends(verified), db=Depends(get_session)):
    profile = profile_for(db, user)
    fields = [
        "full_name",
        "nationality",
        "current_country",
        "preferred_destination",
        "education_level",
        "preferred_subject",
        "career_goals",
    ]
    completion = round(100 * sum(bool(getattr(profile, f)) for f in fields) / len(fields))
    count_u = db.scalar(
        select(func.count()).select_from(SavedUniversity).where(SavedUniversity.user_id == user.id)
    )
    count_s = db.scalar(
        select(func.count())
        .select_from(SavedScholarship)
        .where(SavedScholarship.user_id == user.id)
    )
    plan = db.scalar(
        select(FinancialPlan)
        .where(FinancialPlan.user_id == user.id)
        .order_by(FinancialPlan.updated_at.desc())
        .limit(1)
    )
    checked = checklist_dto(db, user)
    return {
        "profile_completion": completion,
        "saved_university_count": count_u,
        "saved_scholarship_count": count_s,
        "active_financial_plan": plan_dto(plan) if plan else None,
        "checklist_progress": {
            k: {"completed": len(v), "total": len(CHECKLISTS[k])} for k, v in checked.items()
        },
        "next_steps": (["Finish your onboarding"] if not profile.onboarding_completed_at else [])
        + (["Shortlist a university"] if not count_u else [])
        + (
            ["Create a Financial Twin plan"]
            if not plan
            else ["Review scholarship assumptions before committing funds"]
        ),
    }


@router.get("/workspace")
def workspace(user=Depends(verified), db=Depends(get_session)):
    return {
        "profile": profile_dto(profile_for(db, user)),
        "universities": saved_ids(db, user, SavedUniversity, "university_id"),
        "scholarships": saved_ids(db, user, SavedScholarship, "scholarship_id"),
        "comparison": comparison_ids(db, user),
        "checklists": checklist_dto(db, user),
    }


def import_preview(db, user, payload, settings=None):
    valid_u = set(
        db.scalars(
            select(University.id).where(
                University.id.in_(
                    payload.universities + (payload.comparison.ids if payload.comparison else [])
                )
            )
        )
    )
    valid_s = set(
        db.scalars(select(Scholarship.id).where(Scholarship.id.in_(payload.scholarships)))
    )
    from app.services.scholarship_public import visible_scholarship

    valid_s = {
        identifier
        for identifier in valid_s
        if db.get(Scholarship, identifier).contract_version == 1
        or (settings is not None and visible_scholarship(db, settings, identifier) is not None)
    }
    profile = profile_for(db, user)
    profile_empty = not any(
        getattr(profile, f) for f in PROFILE_FIELDS if f not in {"budget_currency"}
    )
    checklist_existing = {
        (r.category, r.stable_item_key)
        for r in db.scalars(
            select(StudentChecklistItem).where(StudentChecklistItem.user_id == user.id)
        )
    }
    return (
        {
            "universities": sorted(set(payload.universities) & valid_u),
            "scholarships": sorted(set(payload.scholarships) & valid_s),
            "stale_universities": sorted(
                set(payload.universities + (payload.comparison.ids if payload.comparison else []))
                - valid_u
            ),
            "stale_scholarships": sorted(set(payload.scholarships) - valid_s),
            "profile_will_import": bool(payload.profile and profile_empty),
            "comparison_will_import": bool(payload.comparison and not comparison_ids(db, user)),
            "financial_plan_will_import": bool(
                payload.financial_plan
                and not db.scalar(
                    select(func.count())
                    .select_from(FinancialPlan)
                    .where(FinancialPlan.user_id == user.id)
                )
            ),
            "existing_checklist_records_preserved": len(checklist_existing),
            "policy": "Add missing saves. Import profile, comparison and financial plan only if empty. Preserve existing checklist values, local data, and all newer cloud records.",
        },
        valid_u,
        checklist_existing,
    )


@router.post("/import/preview")
def preview(data: ImportInput, request: Request, user=Depends(verified), db=Depends(get_session)):
    return import_preview(db, user, data.payload, request.app.state.settings)[0]


@router.post("/import")
def import_local(
    data: ImportInput, request: Request, user=Depends(verified), db=Depends(get_session)
):
    if not data.confirmed:
        raise HTTPException(422, "Review the preview and explicitly confirm this import.")
    fingerprint = hashlib.sha256(
        json.dumps(
            data.payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    existing = db.scalar(
        select(DataImportRecord).where(
            DataImportRecord.user_id == user.id,
            DataImportRecord.import_version == 1,
            DataImportRecord.payload_hash == fingerprint,
        )
    )
    if existing:
        return {"message": "This payload was already imported.", "already_imported": True}
    summary, valid_u, checklist_existing = import_preview(
        db, user, data.payload, request.app.state.settings
    )
    for identifier in summary["universities"]:
        save(db, user, SavedUniversity, University, "university_id", identifier)
    for identifier in summary["scholarships"]:
        save(
            db,
            user,
            SavedScholarship,
            Scholarship,
            "scholarship_id",
            identifier,
            request.app.state.settings,
        )
    if summary["profile_will_import"]:
        update_profile(profile_for(db, user), data.payload.profile)
    if summary["comparison_will_import"]:
        replace_comparison(db, user, [i for i in data.payload.comparison.ids if i in valid_u])
    if summary["financial_plan_will_import"]:
        create_plan(db, user, data.payload.financial_plan)
    for checklist in data.payload.checklists:
        for key in checklist.completed:
            if (checklist.category, key) not in checklist_existing:
                db.add(
                    StudentChecklistItem(
                        user_id=user.id,
                        category=checklist.category,
                        stable_item_key=key,
                        completed=True,
                    )
                )
                checklist_existing.add((checklist.category, key))
    db.add(DataImportRecord(user_id=user.id, import_version=1, payload_hash=fingerprint))
    db.commit()
    audit.info("event=local_data_imported")
    return {
        "message": "Import complete. Browser data preserved.",
        "summary": summary,
        "already_imported": False,
    }


@router.get("/export")
def export_data(response: Response, user=Depends(verified), db=Depends(get_session)):
    response.headers["Content-Disposition"] = 'attachment; filename="atlas-personal-data.json"'
    return jsonable_encoder(
        {
            "export_version": 1,
            "exported_at": now(),
            "account": {
                "id": str(user.id),
                "email": user.email,
                "created_at": user.created_at,
                "email_verified_at": user.email_verified_at,
            },
            "workspace": workspace(user, db),
            "financial_plans": [
                plan_dto(p)
                for p in db.scalars(select(FinancialPlan).where(FinancialPlan.user_id == user.id))
            ],
            "imports": [
                {"version": r.import_version, "created_at": r.created_at}
                for r in db.scalars(
                    select(DataImportRecord).where(DataImportRecord.user_id == user.id)
                )
            ],
        },
        custom_encoder={Decimal: str},
    )


@router.delete("/account")
def delete_account(
    data: DeleteAccount,
    request: Request,
    response: Response,
    user=Depends(verified),
    db=Depends(get_session),
):
    throttle(request, db, "delete_account", user.email, commit=False)
    # Password is rechecked in this request, not trusted from client timestamps.
    if not verify_password(user.password_hash, data.password):
        db.commit()
        audit.info("event=account_deletion_reauthentication_failed")
        raise HTTPException(403, "Password confirmation failed.")
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.delete(user)
    db.commit()
    response.delete_cookie(
        request.app.state.settings.cookie_name,
        path="/",
        secure=request.app.state.settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    audit.info("event=account_deleted")
    return {"message": "Account and personal workspace deleted. Shared catalog retained."}
