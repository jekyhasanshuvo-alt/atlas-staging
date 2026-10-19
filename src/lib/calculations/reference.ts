import { financialPlanSchema } from "@/lib/validation/financial-plan";
import type { FinancialPlan } from "@/types";
import type { FinancialReference } from "@/services/contracts";
export function annualizeTuition(
  amount: number,
  period: "year" | "semester" | "month" | "degree",
  durationMonths: number,
): number {
  if (
    !Number.isFinite(amount) ||
    amount < 0 ||
    !Number.isFinite(durationMonths) ||
    durationMonths <= 0
  )
    throw new Error("Invalid reference cost or duration.");
  return period === "month"
    ? amount * 12
    : period === "semester"
      ? amount * 2
      : period === "degree"
        ? (amount * 12) / durationMonths
        : amount;
}
export function applyFinancialReference(
  plan: FinancialPlan,
  reference: FinancialReference,
): FinancialPlan {
  if (reference.tuition_amount === null)
    throw new Error(
      "No tuition amount is available. Keep your manually entered costs.",
    );
  if (plan.currency !== reference.tuition_currency)
    throw new Error(
      "Reference currency does not match your plan. No exchange conversion is available.",
    );
  if (
    reference.duration_months % 12 !== 0 ||
    reference.duration_months / 12 > 10
  )
    throw new Error(
      "This program duration needs a manual plan. The planner currently uses whole study years from 1–10.",
    );
  const next = {
    ...plan,
    university: reference.university_id,
    country: reference.country.name,
    tuition: annualizeTuition(
      reference.tuition_amount,
      reference.tuition_period,
      reference.duration_months,
    ),
    years: reference.duration_months / 12,
  };
  if (!financialPlanSchema.safeParse(next).success)
    throw new Error(
      "This reference exceeds the planner input limits. Keep your manual costs.",
    );
  return next;
}
