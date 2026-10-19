"use client";
import { FinancialCloudControls } from "@/features/auth/financial-controls";import { ExactFinancialScenarios } from "./exact-scenarios";
import { dataMode } from "@/services/config";
import { useState } from "react";
import { Bookmark, RotateCcw } from "lucide-react";
import { PageHeader, money, ErrorState } from "@/components/shared";
import { defaultPlan } from "@/data/mock";
import { defaultFilters } from "@/services/repository";
import { useCatalogQuery } from "@/hooks/use-catalog-query";
import { DataConnection, Pagination } from "@/components/shared/catalog";
import { FinancialReferencePicker } from "./reference-picker";
import { calculateBudget } from "@/lib/calculations/finance";
import type { FinancialPlan } from "@/types";
import { usePersistentState } from "@/hooks/use-persistent-state";
import {
  financialPlanSchema as planSchema,
  isFinancialPlan as isPlan,
} from "@/lib/validation/financial-plan";
const fields: { key: keyof FinancialPlan; label: string; period: string }[] = [
  { key: "years", label: "Degree duration", period: "years" },
  { key: "tuition", label: "Tuition", period: "per year" },
  { key: "accommodation", label: "Accommodation", period: "per month" },
  { key: "food", label: "Food", period: "per month" },
  { key: "transportation", label: "Transportation", period: "per month" },
  { key: "insurance", label: "Health insurance", period: "per year" },
  { key: "other", label: "Other living expenses", period: "per month" },
  { key: "scholarship", label: "Scholarship funding", period: "per year" },
  { key: "relocation", label: "Initial relocation", period: "one time" },
  { key: "emergency", label: "Emergency fund", period: "one time" },
];
export function CostBreakdown({ plan }: { plan: FinancialPlan }) {
  const rows = [
    {
      name: "Tuition",
      value: plan.tuition * plan.years,
      color: "var(--primary)",
    },
    {
      name: "Accommodation",
      value: plan.accommodation * 12 * plan.years,
      color: "var(--teal)",
    },
    { name: "Food", value: plan.food * 12 * plan.years, color: "#99a5db" },
    {
      name: "Transport & other",
      value: (plan.transportation + plan.other) * 12 * plan.years,
      color: "#b8d9d5",
    },
    {
      name: "Insurance & one-time funds",
      value: plan.insurance * plan.years + plan.relocation + plan.emergency,
      color: "#d5d9e7",
    },
  ];
  const total = calculateBudget(plan).total;
  return (
    <div className="panel cost-breakdown">
      <div className="section-heading">
        <h2>Where your budget goes</h2>
        <span className="tag">Full degree</span>
      </div>
      <div
        className="expense-bar"
        role="img"
        aria-label="Degree cost distribution; amounts are listed below"
      >
        {rows.map((r) => (
          <span
            key={r.name}
            style={{
              width: (total ? (r.value / total) * 100 : 0) + "%",
              background: r.color,
            }}
          />
        ))}
      </div>
      {rows.map((r) => (
        <div className="cost-line" key={r.name}>
          <span>
            <i className="dot" style={{ background: r.color }} />
            {r.name}
          </span>
          <strong>{money(r.value, plan.currency)}</strong>
        </div>
      ))}
    </div>
  );
}
export function BudgetSummary({ plan }: { plan: FinancialPlan }) {
  const result = calculateBudget(plan);
  return (
    <section className="budget-summary">
      <span className="eyebrow">YOUR FINANCIAL TWIN · ESTIMATE</span>
      <h2>A clearer view of your investment.</h2>
      <small>Scholarship-adjusted degree cost</small>
      <strong className="budget-total">
        {money(result.adjusted, plan.currency)}
      </strong>
      <div className="summary-lines">
        <div>
          <span>Monthly living costs</span>
          <strong>{money(result.monthly, plan.currency)}</strong>
        </div>
        <div>
          <span>Annual recurring costs</span>
          <strong>{money(result.annual, plan.currency)}</strong>
        </div>
        <div>
          <span>Total before scholarship</span>
          <strong>{money(result.total, plan.currency)}</strong>
        </div>
        <div>
          <span>Illustrative degree funding</span>
          <strong>−{money(result.funding, plan.currency)}</strong>
        </div>
      </div>
      <p>Planning estimate only. Funding is not guaranteed.</p>
    </section>
  );
}
export function FinancialTwin() {
  const [plan, setPlan] = usePersistentState<FinancialPlan>(
    "financial-plan",
    defaultPlan,
    isPlan,
  );
  const [scenario, setScenario] = usePersistentState<FinancialPlan | null>(
    "financial-scenario",
    null,
    (v): v is FinancialPlan | null => v === null || isPlan(v),
  );
  const [error, setError] = useState("");
  const [universitySearch, setUniversitySearch] = useState("");
  const [universityPage, setUniversityPage] = useState(1);
  const catalog = useCatalogQuery("universities", {
    ...defaultFilters,
    query: universitySearch,
    country:
      plan.country === "Other destination" ? "Other destination" : plan.country,
    page: universityPage,
    pageSize: 3,
    unfiltered: true,
  });
  const countries = useCatalogQuery("countries");
  const universities = catalog.data?.items ?? [];
  const catalogError = catalog.error ?? countries.error;
  const result = calculateBudget(plan);
  function change(key: keyof FinancialPlan, value: string | number) {
    const next = { ...plan, [key]: value };
    const parsed = planSchema.safeParse(next);
    if (!parsed.success) {
      setError("Use a duration from 1–10 years and costs from 0–100,000,000.");
      return;
    }
    setError("");
    setPlan(parsed.data);
  }
  return (
    <>
      <PageHeader
        eyebrow="PLAN WITH PERSPECTIVE"
        title="Your Financial Twin"
        description="Turn the unknown into a plan. Explore the real shape of your study budget."
        action={
          <button
            className="button"
            onClick={() => {
              setPlan(defaultPlan);
              setError("");
            }}
          >
            <RotateCcw size={16} />
            Reset sample plan
          </button>
        }
      />
      <FinancialCloudControls plan={plan} baseline={scenario}/>      <ExactFinancialScenarios />
      <DataConnection loading={catalog.loading} error={catalogError} />
      {catalogError && (
        <ErrorState
          message={catalogError}
          retry={() => {
            catalog.retry();
            countries.retry();
          }}
        />
      )}
      <div className="financial-layout">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Build your scenario</h2>
              <p>All figures are editable planning inputs.</p>
            </div>
            <span className="tag">{dataMode === "api" ? "Unsaved draft · save to your account" : "Local demo"}</span>
          </div>
          {error && <ErrorState message={error} />}
          <div className="form-grid">
            <label>
              Destination country
              <select
                value={plan.country}
                onChange={(e) => {
                  setPlan({ ...plan, country: e.target.value, university: "" });
                  setUniversityPage(1);
                }}
              >
                {countries.data?.map((country) => (
                  <option key={country.id}>{country.name}</option>
                ))}
                {!countries.data?.some(
                  (country) => country.name === plan.country,
                ) &&
                  plan.country !== "Other destination" && (
                    <option>{plan.country}</option>
                  )}
                <option>Other destination</option>
              </select>
            </label>
            <label>
              Search university catalog
              <input
                value={universitySearch}
                onChange={(e) => {
                  setUniversitySearch(e.target.value);
                  setUniversityPage(1);
                }}
                placeholder="University name or city"
              />
            </label>
            <label>
              University
              <select
                value={plan.university}
                onChange={(e) => {
                  if (!e.target.value) {
                    change("university", "");
                    return;
                  }
                  const u = universities.find((u) => u.id === e.target.value);
                  if (u)
                    setPlan({
                      ...plan,
                      university: u.id,
                      country: u.country,
                    });
                }}
              >
                <option value="">Independent estimate</option>
                {plan.university &&
                  !universities.some((u) => u.id === plan.university) && (
                    <option value={plan.university}>
                      Saved selection · {plan.university}
                    </option>
                  )}
                {universities
                  .filter((u) => u.country === plan.country)
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
              </select>
            </label>
            <div className="full-field">
              {catalog.data && (
                <Pagination
                  {...catalog.data.meta}
                  onChange={setUniversityPage}
                />
              )}
            </div>
            <label className="full-field">
              Planning currency
              <select
                value={plan.currency}
                onChange={(e) => change("currency", e.target.value)}
              >
                <option>CNY</option>
                <option>USD</option>
                <option>BDT</option>
              </select>
              <small>
                Changing currency relabels your inputs; enter amounts in the new
                currency. No exchange rate or conversion is applied.
              </small>
            </label>
            {fields.map((f) => (
              <label key={f.key}>
                {f.label}
                <div className="number-input">
                  <input
                    type="number"
                    min={f.key === "years" ? 1 : 0}
                    max={f.key === "years" ? 10 : 100000000}
                    step={f.key === "years" ? 1 : 100}
                    value={plan[f.key]}
                    onChange={(e) => change(f.key, Number(e.target.value))}
                  />
                  <span>{f.period}</span>
                </div>
              </label>
            ))}
          </div>
          {plan.university && (
            <FinancialReferencePicker
              key={plan.university}
              plan={plan}
              onApply={setPlan}
            />
          )}
        </section>
        <div>
          <BudgetSummary plan={plan} />
          <div className="assumptions panel">
            <h3>Assumptions, made visible</h3>
            <ul>
              <li>12 months of living expenses per study year.</li>
              <li>Tuition and insurance repeat annually.</li>
              <li>Relocation and emergency funds are added once.</li>
              <li>
                Scholarship is an annual input, with no guarantee of receipt or
                renewal.
              </li>
              <li>No inflation, exchange conversion, or employment income.</li>
              <li>
                Tuition and duration change only when you explicitly apply a
                compatible program reference.
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div className="two-column section-gap">
        <CostBreakdown plan={plan} />
        <section className="panel">
          <div className="section-heading">
            <h2>Compare your scenarios</h2>
            <button className="button" onClick={() => setScenario({ ...plan })}>
              <Bookmark size={15} />
              Save baseline
            </button>
          </div>
          {scenario ? (
            <>
              <div className="cost-line">
                <span>Saved baseline ({scenario.currency})</span>
                <strong>
                  {money(calculateBudget(scenario).adjusted, scenario.currency)}
                </strong>
              </div>
              <div className="cost-line">
                <span>Current scenario ({plan.currency})</span>
                <strong>{money(result.adjusted, plan.currency)}</strong>
              </div>
              {scenario.currency === plan.currency ? (
                <div className="scenario-difference">
                  {money(
                    Math.abs(
                      result.adjusted - calculateBudget(scenario).adjusted,
                    ),
                    plan.currency,
                  )}{" "}
                  {result.adjusted <= calculateBudget(scenario).adjusted
                    ? "less"
                    : "more"}{" "}
                  than your baseline
                </div>
              ) : (
                <p className="info-note">
                  Choose the same currency to compare costs. No conversion is
                  available.
                </p>
              )}
              <button className="text-button" onClick={() => setScenario(null)}>
                Remove baseline
              </button>
            </>
          ) : (
            <p>
              Save your current plan as a baseline, then adjust housing,
              tuition, or funding to explore another scenario.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
