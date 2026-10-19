import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { calculateScenario, scenarioDifference, scenarioResultSchema, type ScenarioRequest, type ScenarioResult } from "../src/services/financial-scenarios";
import { ScenarioResults, ExactFinancialScenarios } from "../src/features/financial-twin/exact-scenarios";
import { StudentState } from "../src/components/auth/student-provider";
import type { Requester } from "../src/services/profile-intelligence";
function complete(amount = "10000.10", currency: "CNY" | "USD" | "BDT" = "CNY"): ScenarioResult {
    return { status: "complete", currency, missing_inputs: [], tuition_period: "degree", input_basis: "user_estimate",
        breakdown: { tuition: amount, living: "0.00", one_time: "0.00", gross: amount, hypothetical_support: "0.00", remainder: amount },
        formulas: [`Tuition ${amount} / degree × 1 explicit payments`], assumptions: ["No annualization or currency conversion."],
        disclaimer: "Hypothetical planning only. No scholarship award or financial sufficiency established." };
}
const request: ScenarioRequest = { currency: "CNY", study_months: 24, tuition: { amount: "10000.10", currency: "CNY", period: "degree", input_basis: "user_estimate" },
    tuition_payments: null, monthly_living: { amount: "0", currency: "CNY" }, one_time_costs: { amount: "0", currency: "CNY" },
    hypothetical_support_enabled: false, hypothetical_support: null };
describe("exact-period financial scenarios", () => {
    it("sends explicit original values privately in the request body", async () => {
        const send = vi.fn().mockResolvedValue(complete());
        await calculateScenario(send as Requester, request);
        expect(send).toHaveBeenCalledWith("/me/financial-scenarios/calculate", "POST", request);
        expect(request.tuition?.period).toBe("degree");
        expect(request.hypothetical_support).toBeNull();
    });
    it("rejects incompatible payloads without exposing their contents", async () => {
        await expect(calculateScenario(vi.fn().mockResolvedValue({ private: "sensitive-sentinel" }) as Requester, request)).rejects.toThrow("incompatible response");
    });
    it("preserves account/session failures", async () => {
        const send = vi.fn().mockRejectedValue(new Error("Session expired"));
        await expect(calculateScenario(send as Requester, request)).rejects.toThrow("Session expired");
    });
    it("rejects floating-point response amounts", () => {
        expect(scenarioResultSchema.safeParse({ ...complete(), breakdown: { ...complete().breakdown, tuition: 0.1 } }).success).toBe(false);
    });
    it("rejects complete results with unknown amounts", () => {
        expect(scenarioResultSchema.safeParse({ ...complete(), breakdown: null }).success).toBe(false);
    });
    it("rejects an official-verification claim in user inputs", () => {
        expect(scenarioResultSchema.safeParse({ ...complete(), input_basis: "official_verified" }).success).toBe(false);
    });
    it.each(["0.01", "10000000000.01", "0.00"])("compares %s exactly in integer cents", amount => {
        const difference = scenarioDifference(complete(amount), complete("0.00"));
        expect(difference).toBe(`${amount} CNY ${amount === "0.00" ? "difference" : "more"}`);
    });
    it("compares a lower amount without floating-point loss", () => expect(scenarioDifference(complete("0.10"), complete("0.30"))).toBe("0.20 CNY less"));
    it("refuses to compare different currencies", () => expect(scenarioDifference(complete(), complete("10000.10", "BDT"))).toBeNull());
    it("shows period, assumptions and hypothetical disclaimers", () => {
        const html = renderToStaticMarkup(React.createElement(ScenarioResults, { result: complete() }));
        expect(html).toContain("degree");
        expect(html).toContain("10000.10");
        expect(html).toContain("No scholarship award");
        expect(html).toContain("Formulas and assumptions");
        expect(html).not.toContain("official quote");
    });
    it("shows missing inputs without fabricated totals", () => {
        const result: ScenarioResult = { ...complete(), status: "missing_inputs", breakdown: null, formulas: [], missing_inputs: ["tuition", "monthly_living"] };
        const html = renderToStaticMarkup(React.createElement(ScenarioResults, { result }));
        expect(html).toContain("Unknown values are not zero");
        expect(html).toContain("monthly_living");
        expect(html).not.toContain("10000.10");
    });
    it("does not expose signed-out account drafts", () => {
        type State = NonNullable<React.ContextType<typeof StudentState>>;
        const state: State = { user: null, loading: false, busy: false, error: "", csrf: "synthetic", values: { "financial-plan": { private: "prior-account-sentinel" } },
            workspace: null, plans: [], request: async <T>() => ({} as T), refresh: async () => { }, clear: () => { }, update: async () => { }, draft: () => { } };
        const html = renderToStaticMarkup(React.createElement(StudentState.Provider, { value: state }, React.createElement(ExactFinancialScenarios)));
        expect(html).toContain("Sign in");
        expect(html).not.toContain("prior-account-sentinel");
        expect(html).toContain("privacy approval");
    });
});
