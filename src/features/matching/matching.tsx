"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { PageHeader, ErrorState, EmptyState, LoadingSkeleton, FilterPanel } from "@/components/shared";
import { Pagination } from "@/components/shared/catalog";
import { RecordSummary } from "@/features/intelligence/intelligence";
import { safeScholarshipLink } from "@/services/scholarships-v2";
import { profileCompleteness, programMatches, programAssessment, preferenceLabel, type Completeness, type ProgramMatch, type ProgramAssessment, type AssessmentOptions, type MatchingOptions } from "@/services/profile-intelligence";
function usePrivateResult<T>(identity: string, enabled: boolean, load: () => Promise<T>) {
    const [state, setState] = useState<{
        identity: string;
        data?: T;
        error?: string;
    }>({ identity: "" }), [retry, setRetry] = useState(0);
    useEffect(() => {
        let active = true;
        if (!enabled)
            return;
        const timer = setTimeout(() => {
            load().then(data => {
                if (active)
                    setState({ identity, data });
            }).catch(e => {
                if (active)
                    setState({ identity, error: e instanceof Error ? e.message : "Profile intelligence unavailable" });
            });
        }, 0);
        return () => { active = false; clearTimeout(timer); };
        // Identity includes account, profile snapshot and all request options. No private cache/storage.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [identity, enabled, retry]);
    return { data: enabled && state.identity === identity ? state.data : undefined, error: enabled && state.identity === identity ? state.error : undefined,
        loading: enabled && (state.identity !== identity || (!state.data && !state.error)), retry: () => { setState({ identity: "" }); setRetry(v => v + 1); } };
}
function accountIdentity(s: ReturnType<typeof useStudent>) { return JSON.stringify([s.user?.id, s.workspace?.profile]); }
function enabled(s: ReturnType<typeof useStudent>) { return !!s.user?.email_verified && !!s.workspace && !s.loading; }
function AccountPrompt() { return <section className="panel"><h2>Your private study comparisons</h2><p>A verified account is required. Public catalog pages do not receive your profile.</p><Link href="/login?returnTo=%2Fmatches">Sign in</Link></section>; }
export function CompletenessView({ value }: {
    value: Completeness;
}) {
    return <section className="panel matching-panel"><h2>Your profile information</h2><p role="status">{value.provided} of {value.supported} supported fields supplied</p><p>{value.explanation}</p><ul className="matching-dimensions">{value.dimensions.map(d => <li key={d.field}><strong>{d.label}</strong> · {d.status.replaceAll("_", " ")}<p>{d.explanation}</p></li>)}</ul><Link href="/profile#profile-fields">Update supported profile fields</Link></section>;
}
export function ProfileCompleteness() {
    const s = useStudent(), result = usePrivateResult(accountIdentity(s), enabled(s), () => profileCompleteness(s.request));
    if (!enabled(s))
        return s.loading ? <LoadingSkeleton /> : <AccountPrompt />;
    return result.error ? <ErrorState message={result.error} retry={result.retry}/> : result.data ? <CompletenessView value={result.data}/> : <LoadingSkeleton />;
}
export function MatchReasons({ item }: {
    item: ProgramMatch;
}) {
    return <section><h3>{preferenceLabel(item.preference_result)}</h3><p><strong>Admissions: NOT ASSESSED</strong></p><p>{item.explanation}</p><dl className="intelligence-facts">{item.reasons.map(r => <div key={r.attribute}><dt>{r.attribute.replaceAll("_", " ")}</dt><dd><strong>{r.outcome.replaceAll("_", " ")}</strong><p>Input used: {r.input_used ?? "Not supplied"}</p><p>Stored program value: {r.program_value ?? "Unknown"}</p><p>{r.logic}</p><p>{r.uncertainty}</p><details><summary>Catalog evidence · {r.catalog_verification}</summary>{r.evidence.length ? r.evidence.map((e, i) => { const href = safeScholarshipLink(e.source.source_url); return <div className="source-record" key={e.evidence_reference + i}><p>{e.evidence_reference} · {e.source.title} · {e.source.publisher}</p><p>Retrieved {e.source.retrieved_at ?? "Unknown"} · Reviewed {e.reviewed_at ?? "No review date"} · {e.verification_status}</p>{href ? <a href={href} target="_blank" rel="noopener noreferrer">Inspect catalog evidence</a> : <span>Source link unavailable</span>}</div>; }) : <p>No field evidence available. Confirm the stored value with the institution.</p>}</details></dd></div>)}</dl></section>;
}
export function AssessmentView({ value }: {
    value: ProgramAssessment;
}) {
    return <section className="panel matching-panel"><RecordSummary item={value.program}/><MatchReasons item={value}/><h2>Admissions uncertainty</h2>{value.eligibility_checks.map(check => <section className="matching-check" key={check.category}><h3>{check.category} · {check.status.replaceAll("_", " ")}</h3><p>{check.requirement}</p><dl>{Object.entries(check.student_input_used).map(([field, input]) => <div key={field}><dt>{field.replaceAll("_", " ")}</dt><dd>{input ?? "Unknown"}</dd></div>)}</dl><p>{check.comparison_logic}</p><p>{check.uncertainty}</p><p>Official requirement source: unavailable</p></section>)}</section>;
}
function TemporaryOptions({ values, onChange }: {
    values: Record<string, string>;
    onChange: (key: string, value: string) => void;
}) {
    return <><label>Preferred degree for this comparison<select value={values.preferred_degree ?? ""} onChange={e => onChange("preferred_degree", e.target.value)}><option value="">Not specified</option>{["Bachelor", "Master", "PhD"].map(v => <option key={v}>{v}</option>)}</select></label><label>Teaching-language preference (exact text)<input maxLength={120} value={values.teaching_language ?? ""} onChange={e => onChange("teaching_language", e.target.value)}/></label><label>Apply my budget to this original tuition period<select value={values.budget_period ?? ""} onChange={e => onChange("budget_period", e.target.value)}><option value="">Period unknown · do not compare</option>{["year", "semester", "month", "degree"].map(v => <option key={v}>{v}</option>)}</select></label></>;
}
function clean(values: Record<string, string>) { return Object.fromEntries(Object.entries(values).filter(([, value]) => value.trim() !== "")); }
export function ProgramMatching() {
    const s = useStudent(), [draft, setDraft] = useState<Record<string, string>>({}), [filters, setFilters] = useState<Record<string, string>>({}), [page, setPage] = useState(1);
    const query = { ...filters, page, page_size: 12 } as MatchingOptions, key = accountIdentity(s) + JSON.stringify(query);
    const result = usePrivateResult(key, enabled(s), () => programMatches(s.request, query));
    const change = (name: string, value: string) => setDraft(previous => ({ ...previous, [name]: value }));
    if (!enabled(s))
        return s.loading ? <LoadingSkeleton /> : <AccountPrompt />;
    return <><PageHeader title="Programs and your preferences" eyebrow="PRIVATE STUDY COMPARISONS" description="Preference matches are not admissions eligibility. No admission, scholarship or visa outcome is predicted." action={<Link className="button" href="/profile">Review my profile</Link>}/><p className="info-note">Uses your saved destination, subject and budget. Degree, teaching-language and budget-period choices below apply only to this comparison. Language proficiency and current education are not repurposed as preferences. Results use stable name order, without a compatibility score.</p><form onSubmit={e => { e.preventDefault(); setPage(1); setFilters(clean(draft)); }}><FilterPanel><label>Search program name<input maxLength={200} value={draft.q ?? ""} onChange={e => change("q", e.target.value)}/></label><label>University name (exact)<input maxLength={200} value={draft.university ?? ""} onChange={e => change("university", e.target.value)}/></label><TemporaryOptions values={draft} onChange={change}/><label>Stored preference result<select value={draft.preference_result ?? "all"} onChange={e => change("preference_result", e.target.value)}><option value="all">All results</option><option value="MATCHES">Matches stored preferences</option><option value="DIFFERS">Differs from stored preferences</option><option value="UNKNOWN">Unknown comparison</option></select></label><label>Catalog review state<select value={draft.verification ?? ""} onChange={e => change("verification", e.target.value)}><option value="">Any state</option>{["verified", "unverified", "under_review", "stale", "rejected"].map(v => <option key={v}>{v}</option>)}</select></label><button className="button primary" type="submit">Find programs</button><button className="button" type="button" onClick={() => { setDraft({}); setFilters({}); setPage(1); }}>Reset options</button></FilterPanel></form><p role="status">{result.loading ? "Comparing stored preferences…" : result.error ? "Comparison unavailable" : `${result.data?.meta.total ?? 0} program comparisons`}</p>{result.error ? <ErrorState message={result.error} retry={result.retry}/> : !result.data ? <LoadingSkeleton /> : result.data.items.length ? <div className="matching-results">{result.data.items.map(item => <article className="panel matching-panel" key={item.program.id}><h2><Link href={"/programs/" + encodeURIComponent(item.program.id)}>{item.program.name}</Link></h2><RecordSummary item={item.program}/><MatchReasons item={item}/><Link className="button" href={"/matches/" + encodeURIComponent(item.program.id)}>Inspect admissions uncertainty</Link></article>)}</div> : <EmptyState title="No comparisons match these filters" description="Broaden your search or review your supported preferences. No unknown requirement is treated as satisfied."/>}{result.data && !result.error && <Pagination {...result.data.meta} onChange={setPage}/>}</>;
}
export function ProgramProfileAssessment({ id }: {
    id: string;
}) {
    const s = useStudent(), [draft, setDraft] = useState<Record<string, string>>({}), [options, setOptions] = useState<AssessmentOptions>({});
    const result = usePrivateResult(accountIdentity(s) + JSON.stringify({ id, options }), enabled(s), () => programAssessment(s.request, id, options));
    if (!enabled(s))
        return s.loading ? <LoadingSkeleton /> : <AccountPrompt />;
    return <><PageHeader title="Your profile and this program" eyebrow="PRIVATE EXPLAINABLE COMPARISON" description="Official structured admissions rules are unavailable. Admissions remain NOT ASSESSED."/><Link href="/matches">← Program matching</Link><form onSubmit={e => { e.preventDefault(); setOptions(clean(draft) as AssessmentOptions); }}><FilterPanel><TemporaryOptions values={draft} onChange={(name, value) => setDraft(previous => ({ ...previous, [name]: value }))}/><button className="button primary" type="submit">Compare preferences</button></FilterPanel></form>{result.error ? <ErrorState message={result.error} retry={result.retry}/> : result.data ? <AssessmentView value={result.data}/> : <LoadingSkeleton />}</>;
}
