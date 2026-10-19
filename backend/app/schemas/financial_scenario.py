"""Request-only estimates, independent of proposed schema and existing saved plans."""

import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool


def exact_money(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,9}(?:\.\d{1,2})?", value):
        raise ValueError("Use a nonnegative decimal string with at most two decimal places")
    return Decimal(value)


Amount = Annotated[Decimal, BeforeValidator(exact_money), Field(ge=0, le=100000000)]
Currency = Literal["CNY", "USD", "BDT"]


class ScenarioModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MoneyInput(ScenarioModel):
    amount: Amount
    currency: Currency


class TuitionInput(MoneyInput):
    period: Literal["month", "semester", "year", "degree"]
    # A caller cannot turn an estimate into an official or human-reviewed fact.
    input_basis: Literal["user_estimate", "copied_reference"]


class ScenarioInput(ScenarioModel):
    currency: Currency
    study_months: Annotated[int, Field(strict=True, ge=1, le=120)] | None
    tuition: TuitionInput | None
    tuition_payments: Annotated[int, Field(strict=True, ge=1, le=120)] | None
    monthly_living: MoneyInput | None
    one_time_costs: MoneyInput | None
    hypothetical_support_enabled: StrictBool
    hypothetical_support: MoneyInput | None


class ScenarioResult(ScenarioModel):
    status: Literal["complete", "missing_inputs"]
    currency: Currency
    missing_inputs: list[str]
    tuition_period: Literal["month", "semester", "year", "degree"] | None
    input_basis: Literal["user_estimate", "copied_reference"] | None
    breakdown: dict[str, str] | None
    formulas: list[str]
    assumptions: list[str]
    disclaimer: str
