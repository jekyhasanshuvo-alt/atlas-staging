"use client";
import { useEffect, useRef, useState } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { dataMode } from "@/services/config";
import { calculateScenario, scenarioDifference, type ScenarioRequest, type ScenarioResult } from "@/services/financial-scenarios";
import type { Requester } from "@/services/profile-intelligence";
export function ScenarioResults({ result }: {
    result: ScenarioResult;
}) {
    return <div className="exact-scenario-result" aria-live="polite">
    {result.status === "missing_inputs" ? <p role="status">Missing or incompatible inputs: {result.missing_inputs.join(", ")}. Unknown values are not zero.</p> : <>
      <dl className="summary-lines">
        {Object.entries(result.breakdown!).map(([label, value]) => <div key={label}><dt>{label.replaceAll("_", " ")}</dt><dd>{result.currency} {value}</dd></div>)}
      </dl>
      <p>Tuition basis: {result.tuition_period}; {result.input_basis === "copied_reference" ? "manually copied reference, verification not established here" : "user-entered estimate"}.</p>
    </>}
    <details><summary>Formulas and assumptions</summary><ul>{[...result.formulas, ...result.assumptions].map((line) => <li key={line}>{line}</li>)}</ul></details>
    <p>{result.disclaimer}</p>
  </div>;
}
function ScenarioInputField({ label, value, integer = false, onChange }: {
    label: string;
    value: string;
    integer?: boolean;
    onChange: (value: string) => void;
}) {
    return <label>{label}<input type="text" inputMode={integer ? "numeric" : "decimal"} value={value} onChange={(event) => onChange(event.target.value)} aria-describedby="exact-scenario-help" maxLength={integer ? 3 : 12}/></label>;
}
function Workbench({ send }: {
    send: Requester;
}) {
    const [currency, setCurrency] = useState<ScenarioRequest["currency"]>("CNY");
    const [tuitionCurrency, setTuitionCurrency] = useState<ScenarioRequest["currency"]>("CNY");
    const [period, setPeriod] = useState<NonNullable<ScenarioRequest["tuition"]>["period"]>("degree");
    const [basis, setBasis] = useState<"user_estimate" | "copied_reference">("user_estimate");
    const [values, setValues] = useState({ months: "", payments: "", tuition: "", living: "", oneTime: "", support: "" });
    const [supportEnabled, setSupportEnabled] = useState(false);
    const [result, setResult] = useState<ScenarioResult | null>(null);
    const [baseline, setBaseline] = useState<ScenarioResult | null>(null);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const generation = useRef(0);
    useEffect(() => () => { generation.current++; }, []);
    function invalidate() { generation.current++; setResult(null); setBusy(false); setError(""); }
    function change(key: keyof typeof values, value: string) { invalidate(); setValues({ ...values, [key]: value }); }
    async function calculate(event: React.FormEvent) {
        event.preventDefault();
        const run = ++generation.current;
        setError("");
        setBusy(true);
        setResult(null);
        try {
            const money = (value: string, unit = currency) => {
                if (!value.trim())
                    return null;
                if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(value))
                    throw new Error("Enter exact amounts with at most two decimal places; leave unknown amounts empty.");
                return { amount: value, currency: unit };
            };
            const integer = (value: string) => {
                if (!value.trim())
                    return null;
                if (!/^\d{1,3}$/.test(value) || Number(value) < 1 || Number(value) > 120)
                    throw new Error("Enter whole months/payment counts from 1 to 120.");
                return Number(value);
            };
            const tuition = money(values.tuition, tuitionCurrency);
            const input: ScenarioRequest = { currency, study_months: integer(values.months),
                tuition: tuition ? { ...tuition, period, input_basis: basis } : null,
                tuition_payments: period === "year" || period === "semester" ? integer(values.payments) : null,
                monthly_living: money(values.living), one_time_costs: money(values.oneTime),
                hypothetical_support_enabled: supportEnabled, hypothetical_support: supportEnabled ? money(values.support) : null };
            const next = await calculateScenario(send, input);
            if (run === generation.current)
                setResult(next);
        }
        catch (exception) {
            if (run === generation.current)
                setError(exception instanceof Error ? exception.message : "Unable to calculate. Please retry.");
        }
        finally {
            if (run === generation.current)
                setBusy(false);
        }
    }
    const difference = result && baseline ? scenarioDifference(result, baseline) : null;
    return <section className="panel exact-scenario section-gap" aria-labelledby="exact-scenario-title">
    <h2 id="exact-scenario-title">Optional exact-period scenarios</h2>
    <p id="exact-scenario-help">Request-only estimates. Leave unknown values empty; enter zero explicitly for a known zero. This calculator never changes your saved plan or dashboard totals.</p>
    <p>Saved programs, structured credentials and persisted study preferences remain unavailable pending schema and privacy approval.</p>
    <form onSubmit={calculate}>
      <fieldset><legend>Original amounts and study duration</legend><div className="form-grid">
        <label>Scenario currency<select value={currency} onChange={(e) => { invalidate(); setCurrency(e.target.value as typeof currency); }}>{["CNY", "USD", "BDT"].map((c) => <option key={c}>{c}</option>)}</select><small>Changing the label performs no currency conversion. Re-enter amounts in this currency.</small></label>
        <ScenarioInputField label="Study duration in months" integer value={values.months} onChange={(value) => change("months", value)}/>
        <ScenarioInputField label="Original tuition amount" value={values.tuition} onChange={(value) => change("tuition", value)}/>
        <label>Original tuition currency<select value={tuitionCurrency} onChange={(e) => { invalidate(); setTuitionCurrency(e.target.value as typeof tuitionCurrency); }}>{["CNY", "USD", "BDT"].map((c) => <option key={c}>{c}</option>)}</select></label>
        <label>Original tuition period<select value={period} onChange={(e) => { invalidate(); setPeriod(e.target.value as typeof period); }}>{["degree", "year", "semester", "month"].map((p) => <option key={p}>{p}</option>)}</select></label>
        <label>Tuition input basis<select value={basis} onChange={(e) => { invalidate(); setBasis(e.target.value as typeof basis); }}><option value="user_estimate">User-entered estimate</option><option value="copied_reference">Manually copied reference</option></select></label>
        {(period === "year" || period === "semester") && <ScenarioInputField label="Explicit number of tuition payments" integer value={values.payments} onChange={(value) => change("payments", value)}/>}
        <ScenarioInputField label="Monthly living estimate in scenario currency" value={values.living} onChange={(value) => change("living", value)}/>
        <ScenarioInputField label="Total one-time costs in scenario currency" value={values.oneTime} onChange={(value) => change("oneTime", value)}/>
      </div></fieldset>
      <p>Copied catalog references may be demo, stale or unverified. Review their source separately. This form cannot establish official source-backed tuition.</p>
      <label className="scenario-checkbox"><input type="checkbox" checked={supportEnabled} onChange={(e) => { invalidate(); setSupportEnabled(e.target.checked); }}/> Include hypothetical support for the whole scenario</label>
      {supportEnabled && <ScenarioInputField label="Explicit hypothetical support in scenario currency" value={values.support} onChange={(value) => change("support", value)}/>}
      <p>No scholarship award, renewal, visa cost or financial sufficiency is assumed.</p>
      <button className="button primary" disabled={busy}>{busy ? "Calculating…" : "Calculate optional scenario"}</button>
    </form>
    {busy && <p role="status">Calculating your explicit assumptions…</p>}
    {error && <p role="alert">{error}</p>}
    {result && <ScenarioResults result={result}/>}
    {result?.status === "complete" && <button className="button" onClick={() => setBaseline(result)}>Keep comparison in this page</button>}
    {baseline && <div className="section-gap"><h3>Page-only comparison</h3><p>Baseline: {baseline.currency} {baseline.breakdown!.remainder}</p>
      {result?.status === "complete" && <p>{difference ?? "Different currencies cannot be compared. No conversion is available."}</p>}
      <button className="text-button" onClick={() => setBaseline(null)}>Clear comparison</button></div>}
  </section>;
}
export function ExactFinancialScenarios() {
    const student = useStudent();
    if (dataMode !== "api" || !student.user?.email_verified || student.loading)
        return <section className="panel section-gap"><h2>Optional exact-period scenarios</h2><p>Sign in to a verified account using API mode to calculate request-only scenarios. Saved programs, structured credentials and persisted study preferences remain unavailable pending schema and privacy approval.</p></section>;
    return <Workbench key={student.user.id} send={student.request}/>;
}
