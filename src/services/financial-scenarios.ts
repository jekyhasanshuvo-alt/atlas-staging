import { z } from "zod";
import type { Requester } from "./profile-intelligence";
const currency = z.enum(["CNY", "USD", "BDT"]);
const period = z.enum(["month", "semester", "year", "degree"]);
const decimal = z.string().regex(/^\d+\.\d{2}$/);
export const scenarioResultSchema = z.strictObject({
    status: z.enum(["complete", "missing_inputs"]),
    currency,
    missing_inputs: z.array(z.string()),
    tuition_period: period.nullable(),
    input_basis: z.enum(["user_estimate", "copied_reference"]).nullable(),
    breakdown: z.strictObject({ tuition: decimal, living: decimal, one_time: decimal, gross: decimal,
        hypothetical_support: decimal, remainder: decimal }).nullable(),
    formulas: z.array(z.string()),
    assumptions: z.array(z.string()),
    disclaimer: z.string(),
}).superRefine((value, context) => {
    if ((value.status === "complete") !== (value.breakdown !== null) ||
        (value.status === "complete" && value.missing_inputs.length > 0)) {
        context.addIssue({ code: "custom", message: "Inconsistent scenario result" });
    }
});
export type ScenarioResult = z.infer<typeof scenarioResultSchema>;
export type ScenarioRequest = {
    currency: "CNY" | "USD" | "BDT";
    study_months: number | null;
    tuition: {
        amount: string;
        currency: "CNY" | "USD" | "BDT";
        period: "month" | "semester" | "year" | "degree";
        input_basis: "user_estimate" | "copied_reference";
    } | null;
    tuition_payments: number | null;
    monthly_living: {
        amount: string;
        currency: "CNY" | "USD" | "BDT";
    } | null;
    one_time_costs: {
        amount: string;
        currency: "CNY" | "USD" | "BDT";
    } | null;
    hypothetical_support_enabled: boolean;
    hypothetical_support: {
        amount: string;
        currency: "CNY" | "USD" | "BDT";
    } | null;
};
export async function calculateScenario(send: Requester, input: ScenarioRequest): Promise<ScenarioResult> {
    const raw = await send<unknown>("/me/financial-scenarios/calculate", "POST", input);
    const parsed = scenarioResultSchema.safeParse(raw);
    if (!parsed.success)
        throw new Error("The scenario server returned an incompatible response. Please retry.");
    return parsed.data;
}
export function scenarioDifference(current: ScenarioResult, baseline: ScenarioResult): string | null {
    if (current.currency !== baseline.currency || !current.breakdown || !baseline.breakdown)
        return null;
    const cents = (value: string) => BigInt(value.replace(".", ""));
    const delta = cents(current.breakdown.remainder) - cents(baseline.breakdown.remainder);
    const magnitude = delta < 0n ? -delta : delta;
    return `${magnitude / 100n}.${(magnitude % 100n).toString().padStart(2, "0")} ${current.currency} ${delta < 0n ? "less" : delta > 0n ? "more" : "difference"}`;
}
