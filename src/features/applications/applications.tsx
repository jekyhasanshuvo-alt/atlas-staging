"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode, type FormEvent } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { StudentApiError } from "@/services/student";
import { PageHeader, ErrorState, EmptyState, LoadingSkeleton } from "@/components/shared";
import { Pagination } from "@/components/shared/catalog";
import { useCatalogQuery } from "@/hooks/use-catalog-query";
import { defaultFilters } from "@/services/repository";
import { applicationSchema, applicationPageSchema, itemPageSchema, eventPageSchema, capabilitySchema, dashboardSchema, journeyRequest, personalLabel, personalDate, stages, documentStates, type Application, type Item, type Dashboard } from "@/services/application-journey";
import type { Requester } from "@/services/profile-intelligence";
import type { z } from "zod";
import "./applications.css";
function useResult<T>(send: Requester, path: string, schema: z.ZodType<T>, refresh = 0): {
    data?: T;
    error?: Error;
} {
    const [state, setState] = useState<{
        path: string;
        refresh: number;
        data?: T;
        error?: Error;
    }>({ path: "", refresh: -1 });
    useEffect(() => {
        let active = true;
        journeyRequest(send, path, schema).then(data => {
            if (active)
                setState({ path, refresh, data });
        })
            .catch(error => {
            if (active)
                setState({ path, refresh, error: error instanceof Error ? error : new Error("Tracking unavailable") });
        });
        return () => { active = false; };
    }, [send, path, schema, refresh]);
    return state.path === path && state.refresh === refresh ? state : {};
}
export function JourneyUnavailable() {
    return <section className="panel journey-panel"><h2>Application tracking is unavailable</h2><p>This preview requires a separately approved schema rollout. Your current account has no application tracking enabled. No application was saved.</p><p>Official admissions requirements and deadlines: UNKNOWN.</p><Link href="/universities">Browse universities</Link></section>;
}
export function JourneyCaution() {
    return <p className="info-note">Private planning preview · Your stages, tasks and document labels are user managed, not verified admissions facts. Official requirements and deadlines: UNKNOWN. Do not enter passport numbers, financial credentials, document contents or document links. Reminders appear here only; no notifications are sent.</p>;
}
function Capability({ children }: {
    children: ReactNode;
}) {
    const s = useStudent(), [attempt, setAttempt] = useState(0);
    const result = useResult(s.request, "/me/application-journey/capability", capabilitySchema, attempt);
    if (result.error)
        return result.error instanceof StudentApiError && [404, 503].includes(result.error.status) ? <JourneyUnavailable /> : <ErrorState message={result.error.message} retry={() => setAttempt(v => v + 1)}/>;
    return result.data ? <div className="journey"><JourneyCaution />{children}</div> : <LoadingSkeleton />;
}
export function ApplicationJourney({ id, create = false }: {
    id?: string;
    create?: boolean;
}) {
    const s = useStudent();
    if (s.loading)
        return <LoadingSkeleton />;
    if (!s.user?.email_verified)
        return <section className="panel"><h2>Your private application plans</h2><p>Sign in with a verified account to inspect availability.</p><Link href="/login?returnTo=%2Fapplications">Sign in</Link></section>;
    return <Capability key={s.user.id}>{id ? <ApplicationDetail id={id}/> : create ? <NewApplication /> : <ApplicationList />}</Capability>;
}
export function ProgressSummary({ data }: {
    data: Dashboard;
}) {
    return <section className="panel journey-panel"><h2>Your stored planning progress</h2><div className="journey-stats"><p><strong>{data.total_applications}</strong> active plans</p><p><strong>{data.pending_personal_tasks}</strong> pending tasks</p><p><strong>{data.completed_personal_tasks}</strong> completed tasks</p><p><strong>{data.overdue_personal_tasks}</strong> overdue personal tasks</p></div><p>{data.explanation}</p><p>Archived: {data.archived_applications} · Plans with cycle unknown: {data.missing_cycle} · Program not selected: {data.missing_program}</p><details><summary>Personal stages</summary><ul>{Object.entries(data.by_stage).map(([stage, count]) => <li key={stage}>{personalLabel(stage)}: {count}</li>)}</ul></details><h3>Upcoming personal reminders</h3>{data.upcoming_personal_reminders.length ? <ul>{data.upcoming_personal_reminders.map(item => <li key={item.id}><Link href={`/applications/${item.application_id}`}>{item.title}</Link> · {personalDate(item)}</li>)}</ul> : <p>No upcoming personal reminders.</p>}<h3>Recent personal changes</h3>{data.recent_personal_events.length ? <ul>{data.recent_personal_events.map(item => <li key={item.id}><Link href={`/applications/${item.application_id}`}>{personalLabel(item.new_stage)}</Link> · {new Date(item.changed_at).toLocaleString()}</li>)}</ul> : <p>No stage changes yet.</p>}</section>;
}
function ApplicationList() {
    const s = useStudent(), [page, setPage] = useState(1), [archived, setArchived] = useState(false), [stage, setStage] = useState(""), [attempt, setAttempt] = useState(0);
    const result = useResult(s.request, `/me/applications?page=${page}&archived=${archived}${stage ? "&stage=" + stage : ""}`, applicationPageSchema, attempt);
    const dashboard = useResult(s.request, "/me/application-journey/dashboard", dashboardSchema, attempt);
    const retry = () => setAttempt(v => v + 1);
    return <><PageHeader title="Your application plans" eyebrow="PRIVATE PERSONAL TRACKER" description="Organize your own preparation. No institution receives these records." action={<Link className="button primary" href="/applications/new">Create application plan</Link>}/>{dashboard.data ? <ProgressSummary data={dashboard.data}/> : dashboard.error ? <ErrorState message={dashboard.error.message} retry={retry}/> : <LoadingSkeleton />}<div className="panel journey-fields"><label>Plans<select value={String(archived)} onChange={e => { setArchived(e.target.value === "true"); setPage(1); }}><option value="false">Active plans</option><option value="true">Archived plans</option></select></label><label>Personal stage<select value={stage} onChange={e => { setStage(e.target.value); setPage(1); }}><option value="">All stages</option>{stages.map(v => <option key={v} value={v}>{personalLabel(v)}</option>)}</select></label></div>{result.error ? <ErrorState message={result.error.message} retry={retry}/> : !result.data ? <LoadingSkeleton /> : result.data.items.length ? <div className="journey-cards">{result.data.items.map(item => <article className="panel journey-panel" key={item.id}><h2><Link href={`/applications/${item.id}`}>{item.label}</Link></h2><p>Personal stage: {personalLabel(item.stage)}</p><p>Planning cycle: {item.cycle_key ?? "Unknown"} · Route: {item.route_key ?? "Unknown"}</p><p>{item.link_available ? "Catalog link available" : "Catalog link unavailable"} · Official requirements UNKNOWN</p></article>)}</div> : <EmptyState title="No application plans here" description="Create a private plan or adjust the stage and archive filters."/>}{result.data && <Pagination {...result.data.meta} onChange={setPage}/>}</>;
}
function CatalogFields({ value, onChange }: {
    value: {
        university_id: string;
        program_id: string;
    };
    onChange: (university_id: string, program_id: string) => void;
}) {
    const [query, setQuery] = useState(""), [page, setPage] = useState(1);
    const catalog = useCatalogQuery("universities", { ...defaultFilters, query, unfiltered: true, page, pageSize: 20 });
    const selected = catalog.data?.items.find(u => u.id === value.university_id);
    return <><label>Find catalog university<input value={query} maxLength={120} onChange={e => { setQuery(e.target.value); setPage(1); onChange("", ""); }}/></label>{catalog.error ? <ErrorState message={catalog.error} retry={catalog.retry}/> : !catalog.data ? <LoadingSkeleton /> : <><label>University<select required value={value.university_id} onChange={e => onChange(e.target.value, "")}><option value="">Select an existing catalog record</option>{catalog.data.items.map(u => <option key={u.id} value={u.id}>{u.name}{u.provenance?.is_demo ? " · demo" : ""}</option>)}</select></label><Pagination {...catalog.data.meta} onChange={p => { setPage(p); onChange("", ""); }}/><label>Program (optional)<select value={value.program_id} disabled={!selected} onChange={e => onChange(value.university_id, e.target.value)}><option value="">Not selected · Unknown</option>{selected?.programs.map(p => <option key={p.id} value={p.id}>{p.subject} · {p.degree}</option>)}</select></label></>}</>;
}
function NewApplication() {
    const s = useStudent(), router = useRouter(), [draft, setDraft] = useState({ label: "", university_id: "", program_id: "", cycle_key: "", route_key: "" });
    const [busy, setBusy] = useState(false), [error, setError] = useState("");
    const field = (key: keyof typeof draft, value: string) => setDraft(v => ({ ...v, [key]: value }));
    async function submit(e: FormEvent) {
        e.preventDefault();
        setBusy(true);
        setError("");
        try {
            const record = await journeyRequest(s.request, "/me/applications", applicationSchema, "POST", { ...draft, program_id: draft.program_id || null, cycle_key: draft.cycle_key || null, route_key: draft.route_key || null });
            router.push(`/applications/${record.id}`);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Plan could not be saved");
        }
        finally {
            setBusy(false);
        }
    }
    return <><PageHeader title="Create an application plan" eyebrow="PERSONAL PLANNING" description="Cycle and route are your own labels, not official application rounds."/><Link href="/applications">← Application plans</Link><form className="panel journey-panel journey-fields" onSubmit={submit}><label>Plan label<input required maxLength={160} value={draft.label} onChange={e => field("label", e.target.value)}/></label><CatalogFields value={draft} onChange={(u, p) => setDraft(v => ({ ...v, university_id: u, program_id: p }))}/><label>Personal cycle label (optional)<input maxLength={80} value={draft.cycle_key} onChange={e => field("cycle_key", e.target.value)}/></label><label>Personal route label (optional)<input maxLength={80} value={draft.route_key} onChange={e => field("route_key", e.target.value)}/></label>{error && <p role="alert">{error}</p>}<button className="button primary" disabled={busy || !draft.university_id}>{busy ? "Saving…" : "Save private plan"}</button></form></>;
}
function ApplicationDetail({ id }: {
    id: string;
}) {
    const s = useStudent(), router = useRouter(), [attempt, setAttempt] = useState(0), [error, setError] = useState(""), [busy, setBusy] = useState(false);
    const [page, setPage] = useState(1), [eventPage, setEventPage] = useState(1), [kind, setKind] = useState(""), [completion, setCompletion] = useState(""), [due, setDue] = useState("");
    const result = useResult(s.request, `/me/applications/${encodeURIComponent(id)}`, applicationSchema, attempt);
    const items = useResult(s.request, `/me/applications/${encodeURIComponent(id)}/items?page=${page}${kind ? "&kind=" + kind : ""}${completion ? "&completed=" + completion : ""}${due ? "&due_before=" + due : ""}`, itemPageSchema, attempt);
    const events = useResult(s.request, `/me/applications/${encodeURIComponent(id)}/timeline?page=${eventPage}`, eventPageSchema, attempt);
    const refresh = useCallback(() => setAttempt(v => v + 1), []);
    async function mutate(path: string, method: string, body?: unknown, remove = false) {
        setBusy(true);
        setError("");
        try {
            await s.request(path, method, body);
            if (remove)
                router.push("/applications");
            else
                refresh();
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Change was not saved");
            if (e instanceof StudentApiError && e.status === 409)
                refresh();
        }
        finally {
            setBusy(false);
        }
    }
    if (result.error)
        return <ErrorState message={result.error.message} retry={refresh}/>;
    if (!result.data)
        return <LoadingSkeleton />;
    const app = result.data, base = `/me/applications/${app.id}`;
    return <><PageHeader title={app.label} eyebrow="PERSONAL APPLICATION PLAN" description={`Your recorded stage: ${personalLabel(app.stage)}. This does not confirm institution receipt or admission.`}/><Link href="/applications">← Application plans</Link><p>{app.archived ? "Archived plan" : "Active plan"} · Updated {new Date(app.updated_at).toLocaleString()}</p>{app.link_available ? <p><Link href={`/universities/${app.university_id}`}>University catalog record</Link>{app.program_id && <> · <Link href={`/programs/${app.program_id}`}>Program catalog record</Link></>}</p> : <p>Catalog link unavailable. Your personal plan is retained.</p>}<p>Official requirements: UNKNOWN · Official deadline: UNKNOWN</p>{error && <p role="alert">{error} Review the latest record before retrying.</p>}<ApplicationControls key={`${app.id}:${app.version}`} app={app} busy={busy} mutate={mutate}/><section className="panel journey-panel"><h2>Personal tasks, document labels, reminders and notes</h2><div className="journey-fields"><label>Item type<select value={kind} onChange={e => { setKind(e.target.value); setPage(1); }}><option value="">All personal items</option>{["task", "document", "reminder", "note"].map(v => <option key={v}>{v}</option>)}</select></label><label>Completion filter<select value={completion} onChange={e => { setCompletion(e.target.value); setPage(1); }}><option value="">Any completion</option><option value="false">Pending tasks and reminders</option><option value="true">Completed tasks and reminders</option></select></label><label>Personal task due on or before<input type="date" value={due} onChange={e => { setDue(e.target.value); setPage(1); }}/></label></div>{items.error ? <ErrorState message={items.error.message} retry={refresh}/> : !items.data ? <LoadingSkeleton /> : <>{items.data.items.length ? items.data.items.map(item => <ItemEditor key={`${item.id}:${item.version}`} item={item} base={base} busy={busy} mutate={mutate}/>) : <p>No personal items match these filters.</p>}<Pagination {...items.data.meta} onChange={setPage}/></>}<ItemForm key={attempt} base={base} busy={busy} mutate={mutate}/></section><section className="panel journey-panel"><h2>Personal stage timeline</h2><p>Append-only history of your stage choices, not official application verification.</p>{events.error ? <ErrorState message={events.error.message} retry={refresh}/> : !events.data ? <LoadingSkeleton /> : <><ol>{events.data.items.map(event => <li key={event.id}><strong>{personalLabel(event.previous_stage ?? "created")} → {personalLabel(event.new_stage)}</strong><p>{new Date(event.changed_at).toLocaleString()} · {event.reason ?? "No reason supplied"} · user managed</p></li>)}</ol><Pagination {...events.data.meta} onChange={setEventPage}/></>}</section></>;
}
type Mutate = (path: string, method: string, body?: unknown, remove?: boolean) => Promise<void>;
function ApplicationControls({ app, busy, mutate }: {
    app: Application;
    busy: boolean;
    mutate: Mutate;
}) {
    const [stage, setStage] = useState(app.stage), [reason, setReason] = useState(""), [confirmation, setConfirmation] = useState("");
    const [label, setLabel] = useState(app.label), [cycle, setCycle] = useState(app.cycle_key ?? ""), [route, setRoute] = useState(app.route_key ?? "");
    const [relink, setRelink] = useState(false), [scope, setScope] = useState({ university_id: "", program_id: "" });
    const base = `/me/applications/${app.id}`, expected_version = app.version;
    return <section className="panel journey-panel"><h2>Manage your plan</h2><form className="journey-fields" onSubmit={e => { e.preventDefault(); void mutate(base, "PATCH", { expected_version, label, cycle_key: cycle || null, route_key: route || null }); }}><label>Edit plan label<input required maxLength={160} value={label} onChange={e => setLabel(e.target.value)}/></label><label>Edit personal cycle<input maxLength={80} value={cycle} onChange={e => setCycle(e.target.value)}/></label><label>Edit personal route<input maxLength={80} value={route} onChange={e => setRoute(e.target.value)}/></label><button className="button" disabled={busy}>Save plan details</button></form><details onToggle={e => setRelink(e.currentTarget.open)}><summary>Change catalog link</summary>{relink && <form className="journey-fields" onSubmit={e => { e.preventDefault(); void mutate(base, "PATCH", { expected_version, university_id: scope.university_id, program_id: scope.program_id || null }); }}><CatalogFields value={scope} onChange={(u, p) => setScope({ university_id: u, program_id: p })}/><button className="button" disabled={busy || !scope.university_id}>Save catalog link</button></form>}</details><form className="journey-fields" onSubmit={e => { e.preventDefault(); void mutate(`${base}/stage`, "PATCH", { expected_version, stage, reason: reason || null }); }}><label>New personal stage<select value={stage} onChange={e => setStage(e.target.value as Application["stage"])}>{stages.map(v => <option key={v} value={v}>{personalLabel(v)}</option>)}</select></label><label>Reason for stage change (required when reopening a terminal stage)<input maxLength={500} value={reason} onChange={e => setReason(e.target.value)}/></label><button className="button primary" disabled={busy || stage === app.stage}>Record personal stage</button></form><button className="button" disabled={busy} onClick={() => void mutate(base, "PATCH", { expected_version, archived: !app.archived })}>{app.archived ? "Restore archived plan" : "Archive plan"}</button><details><summary>Permanently delete this personal plan</summary><p>Deletes its tasks, document labels, reminders, notes and personal stage history.</p><label>Type DELETE APPLICATION<input value={confirmation} onChange={e => setConfirmation(e.target.value)}/></label><button className="button" disabled={busy || confirmation !== "DELETE APPLICATION"} onClick={() => void mutate(base, "DELETE", { expected_version, confirmation }, true)}>Delete application plan</button></details></section>;
}
function ItemForm({ base, busy, mutate, existing }: {
    base: string;
    busy: boolean;
    mutate: Mutate;
    existing?: Item;
}) {
    const [kind, setKind] = useState<Item["kind"]>(existing?.kind ?? "task"), [title, setTitle] = useState(existing?.title ?? ""), [description, setDescription] = useState(existing?.description ?? "");
    const [priority, setPriority] = useState(existing?.priority ?? "normal"), [doc, setDoc] = useState(existing?.document_state ?? "NOT_STARTED"), [date, setDate] = useState(existing?.due_date ?? existing?.reminder_date ?? "");
    const [zone, setZone] = useState(existing?.timezone ?? ""), [mode, setMode] = useState(existing?.reminder_mode ?? "date"), [instant, setInstant] = useState(existing?.reminder_at ?? "");
    // The server stores instants in UTC. An unchanged instant must not be resubmitted as a local wall-time claim.
    const [instantChanged, setInstantChanged] = useState(false);
    async function submit(e: FormEvent) {
        e.preventDefault();
        const body: Record<string, unknown> = { title, description: description || null };
        if (kind === "task")
            Object.assign(body, { priority, due_date: date || null, timezone: date ? zone : null });
        if (kind === "document")
            body.document_state = doc;
        if (kind === "reminder") {
            Object.assign(body, { reminder_mode: mode, timezone: zone, reminder_date: mode === "date" ? date : null });
            if (mode === "date")
                body.reminder_at = null;
            else if (!existing || instantChanged || existing.reminder_mode !== mode || existing.timezone !== zone)
                body.reminder_at = instant;
        }
        if (existing)
            body.expected_version = existing.version;
        else
            body.kind = kind;
        await mutate(`${base}/items${existing ? "/" + existing.id : ""}`, existing ? "PATCH" : "POST", body);
    }
    return <form className="journey-fields journey-item-form" onSubmit={submit}><h3>{existing ? "Edit personal " + kind : "Add personal item"}</h3>{!existing && <label>New item type<select value={kind} onChange={e => { setKind(e.target.value as Item["kind"]); setDate(""); setZone(""); }}>{["task", "document", "reminder", "note"].map(v => <option key={v}>{v}</option>)}</select></label>}<label>{existing ? "Edit" : "New"} {kind} label<input required maxLength={160} value={title} onChange={e => setTitle(e.target.value)}/></label><label>Planning description (plain text only)<input maxLength={2000} value={description} onChange={e => setDescription(e.target.value)}/></label>{kind === "task" && <label>Priority<select value={priority} onChange={e => setPriority(e.target.value as typeof priority)}>{["low", "normal", "high"].map(v => <option key={v}>{v}</option>)}</select></label>}{kind === "document" && <><p>Labels only. No uploads. Readiness does not confirm official compliance.</p><label>Personal document state<select value={doc} onChange={e => setDoc(e.target.value as typeof doc)}>{documentStates.map(v => <option key={v} value={v}>{personalLabel(v)}</option>)}</select></label></>}{kind === "reminder" && <label>Personal reminder mode<select value={mode} onChange={e => setMode(e.target.value as typeof mode)}><option value="date">Calendar date</option><option value="instant">Exact time with explicit offset</option></select></label>}{(kind === "task" || kind === "reminder") && <>{kind === "task" || mode === "date" ? <label>Personal {kind === "task" ? "due date (optional)" : "reminder date"}<input type="date" required={kind === "reminder"} value={date} onChange={e => setDate(e.target.value)}/></label> : <label>Reminder time with offset<input required placeholder="2030-04-10T14:00:00+06:00" value={instant} onChange={e => { setInstant(e.target.value); setInstantChanged(true); }}/></label>}<label>Explicit IANA timezone{kind === "task" && " (required with date)"}<input required={kind === "reminder" || !!date} maxLength={80} placeholder="Asia/Dhaka" value={zone} onChange={e => setZone(e.target.value)}/></label>{kind === "reminder" && <p>Confirm the explicit offset matches the timezone when changing an exact time. No reminder is sent.</p>}</>}<button className="button primary" disabled={busy}>{existing ? "Save item changes" : "Add personal item"}</button></form>;
}
function ItemEditor({ item, base, busy, mutate }: {
    item: Item;
    base: string;
    busy: boolean;
    mutate: Mutate;
}) {
    const [deleting, setDeleting] = useState(false);
    return <article className="journey-item"><h3>{item.title}</h3><p>{item.kind} · personal {item.completed === null ? "label" : item.completed ? "completed" : "pending"}{item.priority && " · " + item.priority}{item.document_state && " · " + personalLabel(item.document_state)}</p>{item.description && <p>{item.description}</p>}{(item.kind === "task" || item.kind === "reminder") && <p>{personalDate(item)}</p>}{item.completed !== null && <button className="button" disabled={busy} onClick={() => void mutate(`${base}/items/${item.id}`, "PATCH", { expected_version: item.version, completed: !item.completed })}>{item.completed ? "Reopen" : "Complete"} {item.kind}</button>}<details><summary>Edit {item.kind}</summary><ItemForm existing={item} base={base} busy={busy} mutate={mutate}/></details>{deleting ? <><p>Delete this personal item?</p><button className="button" disabled={busy} onClick={() => void mutate(`${base}/items/${item.id}?expected_version=${item.version}`, "DELETE")}>Confirm item deletion</button><button className="button" onClick={() => setDeleting(false)}>Keep item</button></> : <button className="button" disabled={busy} onClick={() => setDeleting(true)}>Delete {item.kind}</button>}</article>;
}
