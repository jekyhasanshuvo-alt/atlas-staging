from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.catalog import Degree, Page, Period, Status
from app.schemas.intelligence import Comparison, IntelligenceRecord
from app.services.intelligence import compare, discover

router = APIRouter(prefix="/api/v2/intelligence", tags=["catalog intelligence"])
DB = Annotated[Session, Depends(get_session)]
Text = Annotated[str, Field(max_length=200)]
Money = Annotated[Decimal, Field(ge=0, le=100000000, max_digits=16, decimal_places=2)]


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: Text = ""
    name: Text = ""
    country: Text = ""
    city: Text = ""
    institution_type: Text = ""
    university: Text = ""
    degree: Degree | None = None
    subject: Text = ""
    language: Text = ""
    tuition_currency: Annotated[str | None, Field(pattern=r"^[A-Z]{3}$")] = None
    tuition_period: Period | None = None
    min_tuition: Money | None = None
    max_tuition: Money | None = None
    min_duration: Annotated[int | None, Field(ge=1, le=1200)] = None
    max_duration: Annotated[int | None, Field(ge=1, le=1200)] = None
    verification: Status | None = None
    sort: Literal["name", "tuition", "duration"] = "name"
    page: Annotated[int, Field(ge=1, le=100000)] = 1
    page_size: Annotated[int, Field(ge=1, le=50)] = 12

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.min_tuition is not None or self.max_tuition is not None or self.sort == "tuition"
        ) and not (self.tuition_currency and self.tuition_period):
            raise ValueError("Tuition bounds/sorting require original currency AND period")
        for low, high in (
            (self.min_tuition, self.max_tuition),
            (self.min_duration, self.max_duration),
        ):
            if low is not None and high is not None and low > high:
                raise ValueError("Minimum must not exceed maximum")
        return self


@router.get("/{kind}", response_model=Page[IntelligenceRecord])
def discovery(
    kind: Literal["universities", "programs"], session: DB, filters: Annotated[Filters, Query()]
):
    if kind == "universities" and filters.sort != "name":
        raise HTTPException(
            422, "University sorting supports name; compare program fees in their original period"
        )
    return discover(session, kind, filters.model_dump())


@router.get("/compare/{kind}", response_model=Comparison)
def comparison(
    kind: Literal["universities", "programs"],
    session: DB,
    ids: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=36)]], Query(min_length=1, max_length=4)
    ],
):
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Comparison identifiers must be distinct")
    return compare(session, kind, ids)


@router.get("/{kind}/{identifier}", response_model=IntelligenceRecord)
def detail(kind: Literal["universities", "programs"], identifier: str, session: DB):
    result = compare(session, kind, [identifier]) if len(identifier) <= 120 else None
    if not result or not result.items:
        raise HTTPException(404, "Catalog record not found")
    return result.items[0]
