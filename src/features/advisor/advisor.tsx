"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { StudentApiError } from "@/services/student";
import { PageHeader, LoadingSkeleton, ErrorState } from "@/components/shared";
import { advisorCapability, askAdvisor, intents, type AdvisorAnswer, type AdvisorRequest } from "@/services/advisor";
import { safeScholarshipLink } from "@/services/scholarships-v2";
import { ScenarioResults } from "@/features/financial-twin/exact-scenarios";
import type { ScenarioRequest } from "@/services/financial-scenarios";
import "./advisor.css";
export function AdvisorUnavailable() { return <section className="panel advisor-panel"><h1>Offline advisor is unavailable</h1><p>This experimental advisor is not enabled for your current environment. It requires a separately approved rollout. No external model is connected and no question has been saved.</p><Link href="/programs">Browse catalog information</Link></section>; }
export function AdvisorResponse({ answer, sourcePrefix = "advisor" }: {
    answer: AdvisorAnswer;
    sourcePrefix?: string;
}) {
    return <article className="panel advisor-panel"><p className="eyebrow">OFFLINE DETERMINISTIC RESPONSE · {answer.status.replaceAll("_", " ")}</p><h2>{answer.summary}</h2><p><strong>Admissions eligibility: NOT ASSESSED</strong> · {answer.scope.replaceAll("_", " ")}</p>{answer.status === "INTERNAL_ERROR" && <p role="alert">Retry with a smaller, supported question.</p>}{answer.claims.map(claim => <section className="advisor-claim" key={claim.id}><p>{claim.text}</p><small>{claim.basis.replaceAll("_", " ")} · {claim.verification_status}</small>{claim.supporting_citation_ids.length > 0 && <p>Supporting stored-field citations: {claim.supporting_citation_ids.map(id => <a key={id} href={"#" + sourcePrefix + "-source-" + id}>{id.slice(0, 8)} </a>)}</p>}{claim.context_citation_ids.length > 0 && <p>Context only, not verified support: {claim.context_citation_ids.map(id => <a key={id} href={"#" + sourcePrefix + "-source-" + id}>{id.slice(0, 8)} </a>)}</p>}</section>)}{answer.scenario_result && <ScenarioResults result={answer.scenario_result}/>}<h3>Unknowns and missing evidence</h3>{answer.unknowns.length ? <ul>{answer.unknowns.map((s, i) => <li key={i}>{s}</li>)}</ul> : <p>No additional missing fields in this scoped response. This is not an eligibility assessment.</p>}<details open={answer.citations.length > 0}><summary>Sources and applicability · {answer.citations.length}</summary>{answer.citations.length ? answer.citations.map(source => { const href = safeScholarshipLink(source.source_url); return <section className="advisor-claim" id={sourcePrefix + "-source-" + source.id} key={source.id}><h4>{source.source_title}</h4><p>{source.publisher} · {source.source_type} · {source.verification_status}</p><p>{source.entity_kind}/{source.entity_id} · {source.field} · {source.role.replaceAll("_", " ")}</p><p>Retrieved snapshot: {source.retrieved_at ?? "Unknown"} · Reviewed: {source.reviewed_at ?? "Unknown"}</p><p>{source.freshness.replaceAll("_", " ")} · {source.applicability}</p><p>Intake: UNKNOWN · Capture custody: UNKNOWN · Never fetched live by this advisor.</p>{href ? <a href={href} target="_blank" rel="noopener noreferrer">Inspect source website</a> : <span>Safe source link unavailable</span>}</section>; }) : <p>No supporting source citation was available. Source existence alone is not evidence.</p>}</details><details><summary>Limitations</summary><ul>{answer.limitations.map((s, i) => <li key={i}>{s}</li>)}</ul></details></article>;
}
export function Advisor() {
    const s = useStudent();
    if (s.loading)
        return <LoadingSkeleton />;
    if (!s.user?.email_verified)
        return <section className="panel"><h1>Your offline advisor preview</h1><p>A verified account is required. No stored profile or credentials are read for this feature.</p><Link href="/login?returnTo=%2Fadvisor">Sign in</Link></section>;
    return <AccountAdvisor key={s.user.id}/>;
}
function AccountAdvisor() {
    const s = useStudent(), [cap, setCap] = useState(false), [unavailable, setUnavailable] = useState(false), [error, setError] = useState(""), [attempt, setAttempt] = useState(0);
    const [question, setQuestion] = useState(""), [intent, setIntent] = useState<AdvisorRequest["intent"]>("auto"), [search, setSearch] = useState(""), [ids, setIds] = useState("");
    const [preferences, setPreferences] = useState({ degree: "", subject: "", language: "" }), [stage, setStage] = useState("");
    const [money, setMoney] = useState({ currency: "", period: "", months: "", payments: "", tuition: "", living: "", oneTime: "", support: "" }), [support, setSupport] = useState(false);
    const [busy, setBusy] = useState(false), [turns, setTurns] = useState<{
        question: string;
        answer: AdvisorAnswer;
    }[]>([]);
    const generation = useRef(0), submitting = useRef(false);
    useEffect(() => {
        let active = true;
        advisorCapability(s.request).then(() => {
            if (active) {
                setCap(true);
                setUnavailable(false);
                setError("");
            }
        }).catch(e => {
            if (active) {
                setCap(false);
                if (e instanceof StudentApiError && [404, 503].includes(e.status))
                    setUnavailable(true);
                else
                    setError(e instanceof Error ? e.message : "Advisor unavailable");
            }
        });
        return () => { active = false; };
    }, [s.request, attempt]);
    useEffect(() => () => { generation.current++; }, []);
    function reset() { generation.current++; submitting.current = false; setTurns([]); setQuestion(""); setSearch(""); setIds(""); setIntent("auto"); setPreferences({ degree: "", subject: "", language: "" }); setStage(""); setMoney({ currency: "", period: "", months: "", payments: "", tuition: "", living: "", oneTime: "", support: "" }); setSupport(false); setError(""); setBusy(false); }
    async function submit(e: FormEvent) {
        e.preventDefault();
        if (submitting.current || busy || !question.trim())
            return;
        const run = ++generation.current;
        submitting.current = true;
        setBusy(true);
        setError("");
        try {
            const request: AdvisorRequest = { question, intent, search, entity_ids: ids.split(",").map(s => s.trim()).filter(Boolean) };
            if (request.entity_ids.length > 4)
                throw new Error("Select at most four exact catalog IDs.");
            if (intent === "matching")
                request.preferences = Object.fromEntries(Object.entries(preferences).filter(([, value]) => value !== "")) as AdvisorRequest["preferences"];
            if (intent === "planning" && stage)
                request.personal_stage = stage;
            if (intent === "financial") {
                if (!money.currency)
                    throw new Error("Choose the scenario's explicit original currency.");
                const currency = money.currency as ScenarioRequest["currency"];
                request.scenario = { currency, study_months: money.months ? Number(money.months) : null, tuition: money.tuition && money.period ? { amount: money.tuition, currency, period: money.period as NonNullable<ScenarioRequest["tuition"]>["period"], input_basis: "user_estimate" } : null, tuition_payments: money.payments ? Number(money.payments) : null, monthly_living: money.living ? { amount: money.living, currency } : null, one_time_costs: money.oneTime ? { amount: money.oneTime, currency } : null, hypothetical_support_enabled: support, hypothetical_support: support && money.support ? { amount: money.support, currency } : null };
            }
            const answer = await askAdvisor(s.request, request);
            if (run === generation.current) {
                setTurns(previous => [...previous, { question, answer }].slice(-4));
                setQuestion("");
            }
        }
        catch (e) {
            if (run === generation.current)
                setError(e instanceof Error ? e.message : "Advisor request failed");
        }
        finally {
            if (run === generation.current) {
                submitting.current = false;
                setBusy(false);
            }
        }
    }
    if (unavailable)
        return <AdvisorUnavailable />;
    if (!cap)
        return error ? <ErrorState message={error} retry={() => setAttempt(v => v + 1)}/> : <LoadingSkeleton />;
    const change = (name: keyof typeof money, value: string) => setMoney(old => ({ ...old, [name]: value }));
    return <div className="advisor"><PageHeader title="A clearer next step" eyebrow="OFFLINE STUDENT ADVISOR · EXPERIMENTAL" description="Deterministic catalog explanations and personal planning guidance. No live LLM or external model is connected."/><p className="info-note">Questions stay in page memory, with up to four recent responses. No chat history is saved. Do not enter names, email addresses, passport numbers, credentials or document contents. Only explicit inputs below are used; saved profiles, credentials and application records are not read.</p><div className="advisor-tools"><Link href="/programs">Browse catalog IDs</Link><button className="button" onClick={reset}>Clear conversation and inputs</button></div>{turns.length === 0 && <section className="panel advisor-panel"><h2>Start with a supported question</h2><p>Ask about stored university/program fields, scholarship evidence, why eligibility is unassessed, a hypothetical budget or general planning.</p></section>}<div aria-label="Offline advisor conversation" role="log" aria-live="polite">{turns.map((turn, i) => <section key={i}><p className="advisor-question">Your question: {turn.question}</p><AdvisorResponse answer={turn.answer} sourcePrefix={"response-" + i}/>{turn.answer.follow_ups.map(q => <button className="button" key={q} onClick={() => setQuestion(q)}>{q}</button>)}</section>)}</div><form className="panel advisor-panel" onSubmit={submit}><label>Question<textarea required maxLength={1200} value={question} onChange={e => setQuestion(e.target.value)} placeholder="Explain why eligibility is not assessed"/></label><label>Question type<select value={intent} onChange={e => setIntent(e.target.value as typeof intent)}>{intents.map(v => <option key={v} value={v}>{v}</option>)}</select></label><div className="advisor-fields"><label>Catalog name search (optional)<input maxLength={120} value={search} onChange={e => setSearch(e.target.value)}/></label><label>Exact catalog IDs, comma separated (optional, maximum four)<input maxLength={150} value={ids} onChange={e => setIds(e.target.value)}/></label></div>{intent === "matching" && <fieldset><legend>Explicit preferences for this question only</legend><label>Degree preference<select value={preferences.degree} onChange={e => setPreferences(p => ({ ...p, degree: e.target.value }))}><option value="">Unknown</option>{["Bachelor", "Master", "PhD"].map(x => <option key={x}>{x}</option>)}</select></label>{(["subject", "language"] as const).map(key => <label key={key}>{key} preference<input maxLength={120} value={preferences[key]} onChange={e => setPreferences(p => ({ ...p, [key]: e.target.value }))}/></label>)}</fieldset>}{intent === "planning" && <label>Your personal stage (optional, unverified)<select value={stage} onChange={e => setStage(e.target.value)}><option value="">Not supplied</option>{["RESEARCHING", "SHORTLISTED", "PREPARING", "READY_TO_SUBMIT", "SUBMITTED", "UNDER_REVIEW", "OFFER_RECEIVED", "REJECTED", "WITHDRAWN", "ENROLLED"].map(x => <option key={x}>{x}</option>)}</select></label>}{intent === "financial" && <fieldset><legend>Hypothetical Financial Twin scenario · explicit inputs only</legend><label>Original currency<select value={money.currency} onChange={e => change("currency", e.target.value)}><option value="">Choose explicitly</option>{["CNY", "USD", "BDT"].map(x => <option key={x}>{x}</option>)}</select></label><label>Original tuition period<select value={money.period} onChange={e => change("period", e.target.value)}><option value="">Unknown</option>{["degree", "year", "semester", "month"].map(x => <option key={x}>{x}</option>)}</select></label><div className="advisor-fields">{([["months", "Study months"], ["payments", "Explicit year/semester tuition payments"], ["tuition", "Tuition in original period"], ["living", "Monthly living estimate"], ["oneTime", "One-time cost estimate"]] as const).map(([name, label]) => <label key={name}>{label}<input inputMode="decimal" maxLength={12} value={money[name]} onChange={e => change(name, e.target.value)}/></label>)}</div><label className="check-inline"><input type="checkbox" checked={support} onChange={e => setSupport(e.target.checked)}/>Include explicit hypothetical support; no award is established</label>{support && <label>Whole-scenario hypothetical support<input inputMode="decimal" maxLength={12} value={money.support} onChange={e => change("support", e.target.value)}/></label>}<p>Leave missing values blank; enter an explicit zero if you mean zero. No currency conversion or average cost is inserted.</p></fieldset>}{error && <p role="alert">{error}</p>}{busy && <p role="status">Retrieving bounded stored evidence…</p>}<button className="button primary" disabled={busy || !question.trim()}>{busy ? "Preparing offline response…" : "Ask offline advisor"}</button></form></div>;
}
