"use client";
import Link from "next/link";
import { ProvenanceInfo } from "./catalog";
import { dataMode } from "@/services/config";
import {
  Search,
  ArrowUpRight,
  Bookmark,
  GitCompareArrows,
  MapPin,
  Check,
  CircleAlert,
  LoaderCircle,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";
import type { University, Scholarship, PreparationTask } from "@/types";
import { isStringList, usePersistentState } from "@/hooks/use-persistent-state";
import { toggleComparison } from "@/lib/utils/universities";
export const money = (n: number | null, currency = "CNY") =>
  n === null
    ? "Not available"
    : new Intl.NumberFormat("en", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(n);
export function PageHeader({
  eyebrow = "YOUR STUDY JOURNEY",
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function DemoNotice() {
  return (
    <div className="demo-notice">
      <Sparkles size={15} />
      <span>
        {dataMode === "api"
          ? "API catalog · Account workspace"
          : "Demo workspace"}{" "}
        <span className="notice-detail">
          · Planning estimates and provenance labels. Verify details with
          official sources.
        </span>
      </span>
    </div>
  );
}
export function StatCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <div className="panel stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className="icon-box">{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
export function EmptyState({
  title,
  description,
  href,
  label = "Explore universities",
}: {
  title: string;
  description: string;
  href?: string;
  label?: string;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Search />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {href && (
        <Link className="button primary" href={href}>
          {label}
          <ArrowUpRight size={16} />
        </Link>
      )}
    </div>
  );
}
export function LoadingSkeleton() {
  return (
    <div className="skeleton-grid" aria-label="Loading content" role="status">
      {[1, 2, 3].map((i) => (
        <div className="panel skeleton" key={i} />
      ))}
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div role="alert" className="error-state">
      <CircleAlert size={20} />
      <p>{message}</p>
      {retry && (
        <button className="button" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function SearchBar({
  value,
  onChange,
  placeholder = "Search universities or cities…",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="search-bar">
      <Search size={18} />
      <span className="sr-only">{placeholder}</span>
      <input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
export function FilterPanel({ children }: { children: ReactNode }) {
  return <div className="panel filters">{children}</div>;
}
export function UniversityCard({
  university: u,
  compact = false,
}: {
  university: University;
  compact?: boolean;
}) {
  const [saved, setSaved] = usePersistentState<string[]>(
    "saved-universities",
    [],
    isStringList,
  );
  const [comparison, setComparison] = usePersistentState<string[]>(
    "comparison",
    [],
    isStringList,
  );
  const isSaved = saved.includes(u.id);
  const selected = comparison.includes(u.id);
  return (
    <article className={"panel university-card " + (compact ? "compact" : "")}>
      <div className={"campus-art " + u.color}>
        <span className="campus-caption">
          {u.city.toUpperCase()} / {u.country.toUpperCase()}
        </span>
        <div className="campus-building">
          <i />
          <i />
          <i />
          <i />
          <i />
        </div>
        <button
          className={"bookmark " + (isSaved ? "selected" : "")}
          aria-label={(isSaved ? "Unsave " : "Save ") + u.name}
          aria-pressed={isSaved}
          onClick={() =>
            setSaved((prev) =>
              isSaved ? prev.filter((id) => id !== u.id) : [...prev, u.id],
            )
          }
        >
          <Bookmark size={17} fill={isSaved ? "currentColor" : "none"} />
        </button>
        <span className="sample-image">Illustrative campus</span>
      </div>
      <div className="university-body">
        <div className={"university-monogram " + u.color}>{u.shortName}</div>
        <h3>
          <Link href={"/universities/" + u.id}>{u.name}</Link>
        </h3>
        <p className="location">
          <MapPin size={13} />
          {u.city}, {u.country}
        </p>
        <div className="tags">
          <span>
            {[...new Set(u.programs.map((p) => p.subject))].join(" · ") ||
              "Program information pending"}
          </span>
          {u.scholarship && (
            <span className="teal-tag">
              {u.provenance?.is_demo === false
                ? "Funding references"
                : "Sample funding"}
            </span>
          )}
        </div>
        {!compact && (
          <>
            <p className="card-description">{u.description}</p>
            <ProvenanceInfo value={u.provenance} compact />
          </>
        )}
        <div className="card-bottom">
          <div>
            <strong>{money(u.tuition, u.tuitionCurrency)}</strong>
            <small>
              {" "}
              / year ·{" "}
              {u.provenance?.is_demo === false ? "estimate" : "sample tuition"}
            </small>
          </div>
          <button
            className={"icon-button " + (selected ? "selected" : "")}
            disabled={!selected && comparison.length >= 4}
            title={
              comparison.length >= 4 && !selected
                ? "Comparison limit reached"
                : "Compare university"
            }
            aria-label={
              (selected ? "Remove from comparison: " : "Compare ") + u.name
            }
            aria-pressed={selected}
            onClick={() =>
              setComparison((prev) => toggleComparison(prev, u.id))
            }
          >
            {selected ? <Check size={18} /> : <GitCompareArrows size={18} />}
          </button>
        </div>
      </div>
    </article>
  );
}
export function ScholarshipCard({
  scholarship: s,
}: {
  scholarship: Scholarship;
}) {
  const [saved, setSaved] = usePersistentState<string[]>(
    "saved-scholarships",
    [],
    isStringList,
  );
  const active = saved.includes(s.id);
  return (
    <article className="panel scholarship-card">
      <div className="row spread">
        <span className="icon-box teal">
          <Sparkles size={20} />
        </span>
        <button
          className={"icon-button " + (active ? "selected" : "")}
          aria-label={(active ? "Unsave " : "Save ") + s.name}
          aria-pressed={active}
          onClick={() =>
            setSaved((prev) =>
              active ? prev.filter((id) => id !== s.id) : [...prev, s.id],
            )
          }
        >
          <Bookmark size={18} fill={active ? "currentColor" : "none"} />
        </button>
      </div>
      <span className="eyebrow">
        {s.provenance?.is_demo === false
          ? "FUNDING REFERENCE"
          : "SAMPLE OPPORTUNITY"}{" "}
        · {s.country.toUpperCase()}
      </span>
      <h3>{s.name}</h3>
      <p>{s.description}</p>
      <div className="tags">
        <span className="teal-tag">
          {s.funding} funding{" "}
          {s.provenance?.is_demo === false ? "reference" : "example"}
        </span>
        <span>{s.degrees.join(" · ")}</span>
      </div>
      <details>
        <summary>View coverage and sources</summary>
        <p>{s.coverage}</p>
        <ProvenanceInfo value={s.provenance} />
        <small>Eligibility, deadlines, and availability are unverified.</small>
      </details>
    </article>
  );
}
export function Checklist({
  tasks,
  storageKey = "preparation",
}: {
  tasks: PreparationTask[];
  storageKey?: string;
}) {
  const [checked, setChecked] = usePersistentState<string[]>(
    storageKey,
    [],
    isStringList,
  );
  return (
    <div className="checklist">
      {tasks.map((task) => (
        <label
          className={
            "checklist-item " + (checked.includes(task.id) ? "done" : "")
          }
          key={task.id}
        >
          <input
            type="checkbox"
            checked={checked.includes(task.id)}
            onChange={() =>
              setChecked((prev) =>
                prev.includes(task.id)
                  ? prev.filter((id) => id !== task.id)
                  : [...prev, task.id],
              )
            }
          />
          <span>
            <strong>{task.title}</strong>
            <small>{task.description}</small>
          </span>
        </label>
      ))}
    </div>
  );
}
export function Spinner() {
  return <LoaderCircle size={18} className="spin" />;
}
