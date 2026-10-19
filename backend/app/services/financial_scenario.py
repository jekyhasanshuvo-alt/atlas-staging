"""Decimal-only total scenario; no persistence, annualization or external price lookup."""

from decimal import ROUND_HALF_UP, Decimal

from app.schemas.financial_scenario import ScenarioInput, ScenarioResult


def calculate(data: ScenarioInput) -> ScenarioResult:
    assumptions = [
        "All figures are explicit user estimates or manually copied references, not an official quote.",
        "Original tuition period and currency are preserved; no exchange conversion or automatic annualization.",
        "Monthly living input repeats for the explicitly entered study months.",
        "One-time costs and hypothetical support apply once to this whole scenario.",
        "No inflation, visa cost, employment income or other missing cost is invented.",
        "This optional scenario does not update your saved plan or dashboard totals.",
    ]
    missing = []
    if data.study_months is None:
        missing.append("study_months")
    for key in ("tuition", "monthly_living", "one_time_costs"):
        value = getattr(data, key)
        if value is None:
            missing.append(key)
        elif value.currency != data.currency:
            missing.append(key + ".currency_alignment")
    if (
        data.tuition
        and data.tuition.period in {"year", "semester"}
        and data.tuition_payments is None
    ):
        missing.append("tuition_payments")
    if (
        data.tuition
        and data.tuition.period in {"month", "degree"}
        and data.tuition_payments is not None
    ):
        missing.append("tuition_payments_must_be_unset_for_month_or_degree")
    if data.hypothetical_support_enabled:
        if data.hypothetical_support is None:
            missing.append("hypothetical_support")
        elif data.hypothetical_support.currency != data.currency:
            missing.append("hypothetical_support.currency_alignment")
    elif data.hypothetical_support is not None:
        missing.append("hypothetical_support_must_be_unset_when_disabled")
    common = {
        "currency": data.currency,
        "missing_inputs": missing,
        "tuition_period": data.tuition.period if data.tuition else None,
        "input_basis": data.tuition.input_basis if data.tuition else None,
        "assumptions": assumptions,
        "disclaimer": "Hypothetical planning only. No scholarship award, affordability or financial sufficiency is established.",
    }
    if missing:
        return ScenarioResult(status="missing_inputs", breakdown=None, formulas=[], **common)
    payments = (
        1
        if data.tuition.period == "degree"
        else data.study_months
        if data.tuition.period == "month"
        else data.tuition_payments
    )
    tuition = data.tuition.amount * payments
    living = data.monthly_living.amount * data.study_months
    one_time = data.one_time_costs.amount
    support = data.hypothetical_support.amount if data.hypothetical_support_enabled else Decimal(0)
    gross = tuition + living + one_time
    net = max(Decimal(0), gross - support)

    def money(value):
        return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")

    formulas = [
        f"Tuition: {money(data.tuition.amount)} / {data.tuition.period} × {payments} explicit payments = {money(tuition)}",
        f"Living: {money(data.monthly_living.amount)} / month × {data.study_months} months = {money(living)}",
        f"Gross: {money(tuition)} + {money(living)} + {money(one_time)} one-time = {money(gross)}",
        f"Hypothetical remainder: max(0, {money(gross)} − {money(support)} explicit hypothetical support) = {money(net)}",
    ]
    return ScenarioResult(
        status="complete",
        breakdown={
            key: money(value)
            for key, value in {
                "tuition": tuition,
                "living": living,
                "one_time": one_time,
                "gross": gross,
                "hypothetical_support": support,
                "remainder": net,
            }.items()
        },
        formulas=formulas,
        **common,
    )
