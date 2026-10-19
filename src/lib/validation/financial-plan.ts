import { z } from "zod";
import type { FinancialPlan } from "@/types";
const cost = z.number().finite().min(0).max(100000000);
export const financialPlanSchema = z.object({
  country: z.string(),
  university: z.string(),
  years: z.number().finite().int().min(1).max(10),
  tuition: cost,
  accommodation: cost,
  food: cost,
  transportation: cost,
  insurance: cost,
  other: cost,
  scholarship: cost,
  relocation: cost,
  emergency: cost,
  currency: z.enum(["CNY", "USD", "BDT"]),
});
export const isFinancialPlan = (value: unknown): value is FinancialPlan =>
  financialPlanSchema.safeParse(value).success;
