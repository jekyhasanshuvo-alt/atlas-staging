"use client";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  SlidersHorizontal,
  X,
  MapPin,
  GraduationCap,
  Languages,
  Clock,
} from "lucide-react";
import {
  PageHeader,
  UniversityCard,
  SearchBar,
  FilterPanel,
  EmptyState,
  money,
  ErrorState,
  LoadingSkeleton,
} from "@/components/shared";
import { useCatalogQuery } from "@/hooks/use-catalog-query";
import {
  DataConnection,
  Pagination,
  ProvenanceInfo,
} from "@/components/shared/catalog";
import { defaultFilters, toggleComparison } from "@/lib/utils/universities";
import { isStringList, usePersistentState } from "@/hooks/use-persistent-state";
import type { University, FinancialPlan } from "@/types";
import { defaultPlan } from "@/data/mock";
import { isFinancialPlan } from "@/lib/validation/financial-plan";
export function UniversityExplorer() {
  const [filters, setFilters] = useState(defaultFilters);
  const [onlySaved, setOnlySaved] = useState(false);
  const [pageState, setPageState] = useState({ key: "", page: 1 });
  const [city, setCity] = useState("");
  const [saved] = usePersistentState<string[]>(
    "saved-universities",
    [],
    isStringList,
  );
  const [compare] = usePersistentState<string[]>(
    "comparison",
    [],
    isStringList,
  );
  const queryKey = JSON.stringify({
    filters,
    city,
    onlySaved,
    ids: onlySaved ? saved : undefined,
  });
  const page = pageState.key === queryKey ? pageState.page : 1;
  const catalog = useCatalogQuery("universities", {
    ...filters,
    city,
    ids: onlySaved ? saved : undefined,
    page,
    pageSize: 3,
  });
  const countries = useCatalogQuery("countries");
  const options = useCatalogQuery("options");
  const results = catalog.data?.items ?? [];
  const error = catalog.error ?? countries.error ?? options.error;
  const retry = () => {
    catalog.retry();
    countries.retry();
    options.retry();
  };
  return (
    <>
      <PageHeader
        eyebrow="FIND YOUR PLACE IN THE WORLD"
        title="Explore universities"
        description="Look beyond the name. Find the right fit for your next chapter."
        action={
          <Link className="button primary" href="/compare">
            Compare ({compare.length}/4)
            <ArrowRight size={16} />
          </Link>
        }
      />
      <DataConnection loading={catalog.loading} error={error} />
      <div className="explorer-toolbar">
        <SearchBar
          value={filters.query}
          onChange={(query) => setFilters({ ...filters, query })}
        />
        <button
          className={"button " + (onlySaved ? "primary" : "")}
          aria-pressed={onlySaved}
          onClick={() => setOnlySaved(!onlySaved)}
        >
          Saved ({saved.length})
        </button>
      </div>
      <FilterPanel>
        <span className="filter-title">
          <SlidersHorizontal size={17} />
          Refine your search
        </span>
        <label>
          Country
          <select
            value={filters.country}
            onChange={(e) =>
              setFilters({ ...filters, country: e.target.value })
            }
          >
            <option value="">All countries</option>
            {countries.data?.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          City
          <select value={city} onChange={(e) => setCity(e.target.value)}>
            <option value="">All cities</option>
            {options.data?.cities.map((city) => (
              <option key={city.id} value={city.name}>
                {city.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Degree
          <select
            value={filters.degree}
            onChange={(e) => setFilters({ ...filters, degree: e.target.value })}
          >
            <option value="">All degrees</option>
            {["Bachelor", "Master", "PhD"].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <label>
          Subject
          <select
            value={filters.subject}
            onChange={(e) =>
              setFilters({ ...filters, subject: e.target.value })
            }
          >
            <option value="">All subjects</option>
            {options.data?.subjects.map((subject) => (
              <option key={subject}>{subject}</option>
            ))}
          </select>
        </label>
        <label>
          Max tuition · {money(filters.maxTuition)}
          <input
            type="range"
            min={0}
            max={60000}
            step={1000}
            value={filters.maxTuition}
            onChange={(e) =>
              setFilters({ ...filters, maxTuition: Number(e.target.value) })
            }
          />
        </label>
        <label className="check-inline">
          <input
            type="checkbox"
            checked={filters.scholarship}
            onChange={(e) =>
              setFilters({ ...filters, scholarship: e.target.checked })
            }
          />
          Sample funding
        </label>
        <button
          className="text-button"
          onClick={() => {
            setFilters(defaultFilters);
            setOnlySaved(false);
            setCity("");
          }}
        >
          Reset
        </button>
      </FilterPanel>
      <div className="result-toolbar">
        <p>
          <strong>{catalog.data?.meta.total ?? 0}</strong> universities{" "}
          <span className="muted">· Paginated catalog · CNY cost filters</span>
        </p>
        <label className="sort-control">
          Sort by
          <select
            value={filters.sort}
            onChange={(e) => setFilters({ ...filters, sort: e.target.value })}
          >
            <option value="name">University name</option>
            <option value="tuition">Lowest tuition</option>
            <option value="living">Lowest living costs</option>
          </select>
        </label>
      </div>
      {error ? (
        <ErrorState message={error} retry={retry} />
      ) : catalog.loading ? (
        <LoadingSkeleton />
      ) : results.length ? (
        <div className="university-grid">
          {results.map((u) => (
            <UniversityCard key={u.id} university={u} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No universities match yet"
          description="Try a broader search, increase your tuition range, or reset the filters."
        />
      )}
      {catalog.data && (
        <Pagination
          {...catalog.data.meta}
          onChange={(page) => setPageState({ key: queryKey, page })}
        />
      )}
      <div className="info-note">
        Cost filters use annualized tuition in CNY without exchange conversion.
        A semester assumes two terms per year. Demo records remain illustrative
        even when delivered by PostgreSQL. Review each record’s provenance and
        official sources before making decisions.
      </div>
    </>
  );
}
export function UniversityDetails({
  university: u,
}: {
  university: University;
}) {
  const [plan, setPlan] = usePersistentState<FinancialPlan>(
    "financial-plan",
    defaultPlan,
    isFinancialPlan,
  );
  const [ids, setIds] = usePersistentState<string[]>(
    "comparison",
    [],
    isStringList,
  );
  const selected = ids.includes(u.id);
  return (
    <>
      <Link href="/universities" className="text-link">
        ← Back to universities
      </Link>
      <PageHeader
        eyebrow={
          u.provenance?.is_demo === false
            ? "UNIVERSITY PROFILE"
            : "SAMPLE UNIVERSITY PROFILE"
        }
        title={u.name}
        description={u.description}
        action={
          <button
            className="button primary"
            disabled={!selected && ids.length >= 4}
            onClick={() => setIds((prev) => toggleComparison(prev, u.id))}
          >
            {selected ? "Remove from comparison" : "Add to comparison"}
          </button>
        }
      />
      <ProvenanceInfo value={u.provenance} label="University details" />
      <div className="detail-grid">
        <section className="panel">
          <div className={"detail-art campus-art " + u.color}>
            <div className="campus-building">
              <i />
              <i />
              <i />
              <i />
              <i />
            </div>
            <span className="sample-image">Illustrative campus</span>
          </div>
          <h2>At a glance</h2>
          <div className="detail-facts">
            <span>
              <MapPin />
              {u.city}, {u.country}
            </span>
            <span>
              <GraduationCap />
              {[...new Set(u.programs.map((p) => p.degree))].join(", ")}
            </span>
            <span>
              <Languages />
              {[...new Set(u.programs.map((p) => p.language))].join("; ")}
            </span>
            <span>
              <Clock />
              Duration varies by program
            </span>
          </div>
          <h2>Programs and financial references</h2>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Degree</th>
                  <th>Language</th>
                  <th>Duration</th>
                  <th>Tuition reference</th>
                </tr>
              </thead>
              <tbody>
                {u.programs.map((p) => (
                  <tr key={p.id}>
                    <th>{p.subject}</th>
                    <td>{p.degree}</td>
                    <td>{p.language}</td>
                    <td>{p.duration} years</td>
                    <td>
                      {money(
                        p.tuitionAmount === undefined
                          ? u.tuition
                          : p.tuitionAmount,
                        p.tuitionCurrency ?? u.tuitionCurrency,
                      )}{" "}
                      / {p.tuitionPeriod ?? "year"}
                      <ProvenanceInfo value={p.provenance} label="Program and tuition" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <aside className="panel fit-height">
          <span className="eyebrow">PLANNING ESTIMATES</span>
          <h2>Your financial starting point</h2>
          <div className="cost-line">
            <span>Tuition / year</span>
            <strong>{money(u.tuition, u.tuitionCurrency)}</strong>
          </div>
          <div className="cost-line">
            <span>Living / month</span>
            <strong>{money(u.living, u.livingCurrency)}</strong>
          </div>
          <div className="cost-line">
            <span>Funding indicator</span>
            <strong>{u.scholarship ? "Sample entry" : "No sample data"}</strong>
          </div>
          <p>
            Consult program and living-cost provenance separately. No funding is
            guaranteed.
          </p>
          <ProvenanceInfo value={u.livingProvenance} label="Living costs" />
          <Link
            className="button primary full"
            href="/financial-twin"
            onClick={() =>
              setPlan({
                ...plan,
                university: u.id,
                country: u.country,
              })
            }
          >
            Plan my budget <ArrowRight size={16} />
          </Link>
        </aside>
      </div>
    </>
  );
}
export function ComparisonTable({
  selected,
  onRemove,
}: {
  selected: University[];
  onRemove: (id: string) => void;
}) {
  const rows: { label: string; value: (u: University) => string }[] = [
    { label: "Country", value: (u) => u.country },
    {
      label: "Data status",
      value: (u) =>
        !u.provenance || u.provenance.is_demo
          ? "Demo Data · Unverified"
          : u.provenance.verification_status,
    },
    { label: "City", value: (u) => u.city },
    {
      label: "Degree availability",
      value: (u) => [...new Set(u.programs.map((p) => p.degree))].join(", "),
    },
    {
      label: "Tuition / year (shown currency)",
      value: (u) => money(u.tuition, u.tuitionCurrency),
    },
    {
      label: "Living / month (shown currency)",
      value: (u) => money(u.living, u.livingCurrency),
    },
    {
      label: "Scholarship information",
      value: (u) =>
        u.scholarship ? "Illustrative funding entry" : "No sample information",
    },
    {
      label: "Language of instruction",
      value: (u) => [...new Set(u.programs.map((p) => p.language))].join("; "),
    },
    {
      label: "Study duration",
      value: (u) =>
        u.programs
          .map((p) => p.duration + " years (" + p.degree + ")")
          .join("; "),
    },
  ];
  return (
    <div className="panel table-scroll comparison-table">
      <table>
        <thead>
          <tr>
            <th>What matters to you</th>
            {selected.map((u) => (
              <th key={u.id}>
                <div className="row spread">
                  <Link href={"/universities/" + u.id}>{u.name}</Link>
                  <button
                    className="icon-button"
                    aria-label={"Remove " + u.name}
                    onClick={() => onRemove(u.id)}
                  >
                    <X size={16} />
                  </button>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th>{row.label}</th>
              {selected.map((u) => (
                <td key={u.id}>{row.value(u) || "Not available"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Comparison() {
  const [ids, setIds] = usePersistentState<string[]>(
    "comparison",
    [],
    isStringList,
  );
  const catalog = useCatalogQuery("universities", {
    ...defaultFilters,
    maxTuition: 100000000,
    ids: ids.slice(0, 4),
    pageSize: 4,
    unfiltered: true,
  });
  const selected = catalog.data?.items ?? [];
  return (
    <>
      <PageHeader
        title="See the bigger picture"
        eyebrow="UNIVERSITY COMPARISON"
        description="Bring your options together. Compare up to four universities, side by side."
        action={
          <div className="row">
            <button
              className="button"
              disabled={!ids.length}
              onClick={() => setIds([])}
            >
              Clear comparison
            </button>{" "}
            <Link className="button primary" href="/universities">
              Add universities <ArrowRight size={16} />
            </Link>
          </div>
        }
      />
      <DataConnection loading={catalog.loading} error={catalog.error} />
      {catalog.error ? (
        <ErrorState message={catalog.error} retry={catalog.retry} />
      ) : catalog.loading ? (
        <LoadingSkeleton />
      ) : selected.length > 0 ? (
        <>
          <p className="info-note">
            {selected.length}/4 selected.{" "}
            {selected.length === 1 ? "Add another university to compare." : ""}{" "}
            {catalog.data && catalog.data.meta.total < ids.length && (
              <span>
                Some selected records are unavailable. Clear the comparison to
                choose new options.{" "}
              </span>
            )}
            Costs are shown in their original currencies. Demo and verification
            status apply per record.
          </p>
          <ComparisonTable
            selected={selected}
            onRemove={(id) => setIds((prev) => prev.filter((x) => x !== id))}
          />
        </>
      ) : (
        <div className="panel">
          <EmptyState
            title="Good decisions start with perspective"
            description="Add universities from the explorer to compare programs, cities, and sample costs."
            href="/universities"
          />
        </div>
      )}
    </>
  );
}
