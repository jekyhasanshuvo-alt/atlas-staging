import type { FinancialPlan } from "@/types";
export function calculateBudget(plan: FinancialPlan) {
  const {
    years,
    tuition,
    accommodation,
    food,
    transportation,
    insurance,
    other,
    scholarship,
    relocation,
    emergency,
  } = plan;
  const numbers = [
    years,
    tuition,
    accommodation,
    food,
    transportation,
    insurance,
    other,
    scholarship,
    relocation,
    emergency,
  ];
  if (numbers.some((n) => !Number.isFinite(n) || n < 0) || years <= 0)
    throw new Error(
      "Costs must be finite and non-negative; duration must be positive.",
    );
  const monthly = accommodation + food + transportation + other;
  const annual = tuition + monthly * 12 + insurance;
  const total = annual * years + relocation + emergency;
  const funding = scholarship * years;
  return {
    monthly,
    annual,
    total,
    funding,
    adjusted: Math.max(0, total - funding),
  };
}
