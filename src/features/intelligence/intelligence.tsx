"use client";
import Link from "next/link";
import {ProfileAssessmentLink} from "@/features/matching/assessment-link";
import { useEffect, useState } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { usePersistentState, isStringList } from "@/hooks/use-persistent-state";
import { PageHeader, FilterPanel, EmptyState, ErrorState, LoadingSkeleton } from "@/components/shared";
import { Pagination } from "@/components/shared/catalog";
import { safeScholarshipLink } from "@/services/scholarships-v2";
import { intelligenceList, intelligenceDetail, intelligenceCompare, tuitionQuote, comparisonSelection, type Intelligence, type CatalogKind } from "@/services/intelligence";
function useRemote<T>(key: string, request: () => Promise<T>) {
    const [state, setState] = useState<{
        key: string;
        data?: T;
        error?: string;
    }>({ key: "" }), [retry, setRetry] = useState(0);
    useEffect(() => {
        let active = true;
        const timer = setTimeout(() => {
            request().then(data => {
                if (active)
                    setState({ key, data });
            }).catch(e => {
                if (active)
                    setState({ key, error: e instanceof Error ? e.message : "Catalog unavailable" });
            });
        }, 250);
        return () => { active = false; clearTimeout(timer); };
        // The serialized key identifies the entire request; retry clears old data.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key, retry]);
    return { data: state.key === key ? state.data : undefined, error: state.key === key ? state.error : undefined, loading: state.key !== key || (!state.data && !state.error), retry: () => { setState({ key: "" }); setRetry(v => v + 1); } };
}
function SourceLink({ url, label }: {
    url: string | null;
    label: string;
}) { const safe = safeScholarshipLink(url); return safe ? <a href={safe} target="_blank" rel="noopener noreferrer">{label} ↗</a> : <span>Source link unavailable</span>; }
export function EvidenceFacts({ item }: {
    item: Intelligence;
}) {
    return <dl className="intelligence-facts">{Object.entries(item.facts).map(([field, fact]) => <div key={field}><dt>{field.replaceAll("_", " ")}</dt><dd>{fact.value === null || fact.value === "" ? "Unknown" : String(fact.value)} · <strong>{item.is_demo ? "Demo · unverified" : fact.verification_status}</strong><p>{fact.caveat}</p><details><summary>Evidence for {field.replaceAll("_", " ")}</summary>{fact.evidence.length ? fact.evidence.map((e, i) => <div key={e.evidence_reference + i} className="source-record"><p>{e.source.title} · {e.source.publisher} · Source type: {e.source.source_type}</p><p>Reference: {e.evidence_reference}</p><p>Retrieved: {e.source.retrieved_at ?? "Unknown"} · Reviewed: {e.reviewed_at ?? "No review date"} · {e.verification_status}</p><SourceLink url={e.source.source_url} label="Inspect source"/></div>) : <p>No field evidence available. Unverified.</p>}</details></dd></div>)}</dl>;
}
function SaveUniversity({ item }: {
    item: Intelligence;
}) {
    const s = useStudent(), [error, setError] = useState("");
    if (item.kind === "program")
        return <p>Account program saving is not available yet.</p>;
    if (!s.user)
        return <Link href={"/login?returnTo=" + encodeURIComponent("/universities/" + item.id)}>Sign in to save university</Link>;
    if (!s.user.email_verified)
        return <Link href="/verify-email">Verify email to save</Link>;
    const saved = (s.values["saved-universities"] ?? []) as string[], selected = saved.includes(item.id);
    return <><button className="button" disabled={s.loading || s.busy || !s.workspace} aria-pressed={selected} onClick={async () => {
            setError("");
            try {
                await s.update("saved-universities", selected ? saved.filter(id => id !== item.id) : [...saved, item.id]);
            }
            catch (e) {
                setError(e instanceof Error ? e.message : "Saving failed");
            }
        }}>{selected ? "Remove saved university" : "Save university"}</button>{error && <p role="alert">{error}</p>}</>;
}
function CompareButton({ item }: {
    item: Intelligence;
}) {
    const kind = item.kind === "program" ? "programs" : "universities", [ids, setIds] = usePersistentState<string[]>("intelligence-compare-" + kind, [], isStringList), selected = ids.includes(item.id);
    return <button className="button" aria-pressed={selected} disabled={!selected && ids.length >= 4} onClick={() => setIds(previous => comparisonSelection(previous, item.id))}>{selected ? "Remove from comparison" : "Add to comparison"}</button>;
}
export function RecordSummary({ item }: {
    item: Intelligence;
}) { return <><p>{item.city.name}, {item.country.name} · {item.is_demo ? "Demo data · Unverified" : item.verification_status}</p>{item.kind === "program" ? <><p>{item.university_name} · {item.degree_level} · {item.field_of_study}</p><p>{item.duration_months ?? "Unknown"} months · {item.language_of_instruction || "Language unknown"}</p><p>{tuitionQuote(item)}</p></> : <p>{item.institution_type || "Institution type unknown"}</p>}</>; }
export function IntelligenceExplorer({ kind, universityId }: {
    kind: CatalogKind;
    universityId?: string;
}) {
    const [filters, setFilters] = useState<Record<string, string>>({}), [page, setPage] = useState(1), query = { ...filters, ...(universityId ? { university: universityId } : {}), page, page_size: 12 };
    const key = JSON.stringify({ kind, ...query }), result = useRemote(key, () => intelligenceList(kind, query));
    const set = (name: string, value: string) => { setPage(1); setFilters(previous => ({ ...previous, [name]: value })); };
    const fields = kind === "programs" ? [["q", "Search programs"], ["country", "Country code or name"], ["city", "City"], ["university", "University name (exact)"], ["subject", "Field of study (exact)"], ["language", "Teaching language (exact description)"], ["tuition_currency", "Tuition currency (e.g. CNY)"], ["min_tuition", "Minimum tuition"], ["max_tuition", "Maximum tuition"], ["min_duration", "Minimum months"], ["max_duration", "Maximum months"]] : [["q", "Search universities"], ["country", "Country code or name"], ["city", "City"], ["institution_type", "Institution type (exact)"], ["language", "Program teaching language (exact description)"]];
    return <><PageHeader title={kind === "programs" ? "Explore academic programs" : "Explore universities"} eyebrow="CATALOG INTELLIGENCE" description="Compare stored facts and their evidence. A listing does not guarantee admission or eligibility." action={<div className="row"><Link className="button" href={kind === "programs" ? "/universities" : "/programs"}>{kind === "programs" ? "Universities" : "Programs"}</Link><Link className="button" href="/compare">Compare options</Link></div>}/><p className="info-note">Live catalog · No sample fallback. Demo records are labelled. Intake and admission requirements are unknown. Language descriptions do not establish full-program English coverage.</p>
 <FilterPanel>{fields.filter(([name]) => !universityId || name !== "university").map(([name, label]) => <label key={name}>{label}<input maxLength={200} type={(name.includes("tuition") && name !== "tuition_currency") || name.includes("duration") ? "number" : "text"} min="0" step={name.includes("duration") ? "1" : "0.01"} value={filters[name] ?? ""} onChange={e => set(name, name === "tuition_currency" ? e.target.value.toUpperCase() : e.target.value)}/></label>)}<label>Degree<select value={filters.degree ?? ""} onChange={e => set("degree", e.target.value)}><option value="">All degrees</option>{["Bachelor", "Master", "PhD"].map(v => <option key={v}>{v}</option>)}</select></label>
 {kind === "programs" && <><label>Original tuition period<select value={filters.tuition_period ?? ""} onChange={e => set("tuition_period", e.target.value)}><option value="">Any period (no cost bounds)</option>{["year", "semester", "month", "degree"].map(v => <option key={v}>{v}</option>)}</select></label><label>Sort<select value={filters.sort ?? "name"} onChange={e => set("sort", e.target.value)}><option value="name">Name</option><option value="tuition">Tuition in selected currency and period</option><option value="duration">Duration</option></select></label></>}
 <label>Verification<select value={filters.verification ?? ""} onChange={e => set("verification", e.target.value)}><option value="">Any review state</option>{["verified", "unverified", "under_review", "stale", "rejected"].map(v => <option key={v}>{v}</option>)}</select></label><button className="button" onClick={() => { setFilters({}); setPage(1); }}>Reset filters</button></FilterPanel>
 <p>Tuition bounds and sorting require both the original currency and period. Unknown fees are excluded by a numerical bound. No exchange conversion or annualization is applied.</p><p role="status">{result.loading ? "Loading catalog…" : result.error ? "Catalog unavailable" : `${result.data?.meta.total ?? 0} matching ${kind}`}</p>
 {result.error ? <ErrorState message={result.error} retry={result.retry}/> : result.loading ? <LoadingSkeleton /> : result.data?.items.length ? <div className="university-grid">{result.data.items.map(item => <article className="panel intelligence-card" key={item.id}><h2><Link href={`/${kind}/${encodeURIComponent(item.id)}`}>{item.name}</Link></h2><RecordSummary item={item}/><div className="row"><CompareButton item={item}/><SaveUniversity item={item}/></div></article>)}</div> : <EmptyState title="No matching records" description="Try fewer filters. Missing facts and evidence are never filled with assumed values."/>}{result.data && !result.error && !result.loading && <Pagination {...result.data.meta} onChange={setPage}/>}</>;
}
export function IntelligenceDetail({ kind, id }: {
    kind: CatalogKind;
    id: string;
}) {
    const result = useRemote(JSON.stringify({ kind, id }), () => intelligenceDetail(kind, id)), item = result.data;
    return <><Link href={`/${kind}`}>← All {kind}</Link>{result.error ? <ErrorState message={result.error} retry={result.retry}/> : !item ? <LoadingSkeleton /> : <><PageHeader title={item.name} eyebrow={item.is_demo ? "DEMO CATALOG RECORD" : "CATALOG RECORD"} description={item.description ?? "Program terms and field evidence"}/><section className="panel"><RecordSummary item={item}/>{item.kind === "program" && <p><Link href={`/universities/${item.university_id}`}>View university</Link></p>}<CompareButton item={item}/><SaveUniversity item={item}/>{item.kind === "program" && <ProfileAssessmentLink id={item.id}/>}<p>No admission guarantee or individual eligibility determination is made. Stored fees may have undocumented conditions; confirm the applicable intake with the institution.</p>{item.official_website && <SourceLink url={item.official_website} label="University website"/>}<EvidenceFacts item={item}/></section>{item.kind === "university" && <IntelligenceExplorer kind="programs" universityId={item.id}/>}</>}</>;
}
export function IntelligenceComparisonTable({ items, onRemove }: {
    items: Intelligence[];
    onRemove: (id: string) => void;
}) {
    const fields = Array.from(new Set(items.flatMap(item => Object.keys(item.facts))));
    return <div className="panel table-scroll intelligence-comparison" tabIndex={0} role="region" aria-label="Side-by-side comparison; scroll horizontally on small screens"><table><caption>Original values and field evidence · No ranking or quality score</caption><thead><tr><th scope="col">Attribute</th>{items.map(item => <th scope="col" key={item.id}><Link href={`/${item.kind === "program" ? "programs" : "universities"}/${item.id}`}>{item.name}</Link><button className="button" aria-label={`Remove ${item.name}`} onClick={() => onRemove(item.id)}>Remove</button></th>)}</tr></thead><tbody><tr><th scope="row">Location and record state</th>{items.map(item => <td key={item.id}>{item.city.name}, {item.country.name} · {item.is_demo ? "Demo · unverified" : item.verification_status}</td>)}</tr>{items.some(i => i.kind === "program") && <tr><th scope="row">Original tuition quotation</th>{items.map(item => <td key={item.id}>{tuitionQuote(item)}</td>)}</tr>}{fields.map(field => <tr key={field}><th scope="row">{field.replaceAll("_", " ")}</th>{items.map(item => <td key={item.id}><EvidenceFacts item={{ ...item, facts: { [field]: item.facts[field] ?? { value: null, verification_status: "unverified", evidence: [], caveat: "Unknown" } } }}/></td>)}</tr>)}</tbody></table></div>;
}
function ComparisonPanel({ kind }: {
    kind: CatalogKind;
}) {
    const [raw, setIds] = usePersistentState<string[]>("intelligence-compare-" + kind, [], isStringList), ids = Array.from(new Set(raw)).slice(0, 4), key = JSON.stringify({ kind, ids });
    const result = useRemote(key, () => ids.length ? intelligenceCompare(kind, ids) : Promise.resolve({ items: [] as Intelligence[], unavailable_ids: [] as string[] }));
    return <section><h2>Compare {kind}</h2><p>Up to four options · This browser stores only comparison selections. No ranking or admissions promise.</p><div className="row"><Link className="button" href={`/${kind}`}>Add {kind}</Link><button className="button" disabled={!raw.length} onClick={() => setIds([])}>Clear {kind} comparison</button></div>{result.error ? <ErrorState message={result.error} retry={result.retry}/> : result.loading ? <LoadingSkeleton /> : result.data?.items.length ? <IntelligenceComparisonTable items={result.data.items} onRemove={id => setIds(previous => previous.filter(v => v !== id))}/> : <EmptyState title={`Choose ${kind} to compare`} description="Add options from discovery. No records are preselected."/>}{!!result.data?.unavailable_ids.length && <p role="status">{result.data.unavailable_ids.length} selected records are unavailable. Clear the comparison to choose again.</p>}</section>;
}
export function IntelligenceComparison() { return <><PageHeader title="Compare your options" eyebrow="CATALOG COMPARISON" description="Original facts, sources and unknowns side by side. Tuition periods and currencies remain separate."/><ComparisonPanel kind="universities"/><ComparisonPanel kind="programs"/></>; }
