"use client";
import { useState } from "react";
import { useCatalogQuery } from "@/hooks/use-catalog-query";
import { ErrorState } from "@/components/shared";
import { ProvenanceInfo, Pagination } from "@/components/shared/catalog";
import { applyFinancialReference } from "@/lib/calculations/reference";
import type { FinancialPlan } from "@/types";
import type { FinancialReference } from "@/services/contracts";

export function FinancialReferenceSummary({ reference }: { reference: FinancialReference }) {
  return <>
    <div className="reference-costs">
      {reference.tuition_amount === null
        ? "Tuition unavailable"
        : `${reference.tuition_currency} ${reference.tuition_amount.toLocaleString()} / ${reference.tuition_period}`} · {reference.duration_months} months
    </div>
    <ProvenanceInfo value={reference.provenance} label="Program and tuition" />
    {reference.living_cost ? <>
      <p>Living cost reference: {reference.living_cost.currency} {reference.living_cost.amount.toLocaleString()} / {reference.living_cost.period}. Your living-cost inputs remain unchanged.</p>
      <ProvenanceInfo value={reference.living_cost.provenance} label="Living costs" />
    </> : <p>Living cost reference: not available. Not yet verified.</p>}
  </>;
}
export function FinancialReferencePicker({
  plan,
  onApply,
}: {
  plan: FinancialPlan;
  onApply: (plan: FinancialPlan) => void;
}) {
  const [page, setPage] = useState(1);
  const [selection, setSelection] = useState("");
  const [error, setError] = useState("");
  const references = useCatalogQuery("references", plan.university, page);
  const selected = references.data?.items.find(
    (r) => r.program_id === selection,
  );
  return (
    <section className="reference-loader">
      <h3>Available program cost inputs</h3>
      <p>
        Select a reference to review it, then apply it explicitly. Your housing,
        living costs, funding, and baseline remain unchanged.
      </p>
      {references.error ? (
        <ErrorState message={references.error} retry={references.retry} />
      ) : references.loading ? (
        <p role="status">Loading program references…</p>
      ) : references.data?.items.length ? (
        <>
          <label>
            Program reference
            <select
              value={selection}
              onChange={(e) => {
                setSelection(e.target.value);
                setError("");
              }}
            >
              <option value="">Choose a program</option>
              {references.data.items.map((r) => (
                <option key={r.program_id} value={r.program_id}>
                  {r.program_name}
                </option>
              ))}
            </select>
          </label>
          {selected && (
            <>
              <FinancialReferenceSummary reference={selected} />
              <p>
                Annualization: yearly × 1; semester × 2; monthly × 12; degree
                total ÷ study years. No currency conversion. Whole-year
                durations only.
              </p>
              <button
                className="button"
                disabled={selected.tuition_amount === null}
                onClick={() => {
                  try {
                    onApply(applyFinancialReference(plan, selected));
                    setError("");
                  } catch (error) {
                    setError(
                      error instanceof Error
                        ? error.message
                        : "Reference could not be applied.",
                    );
                  }
                }}
              >
                Apply tuition and duration
              </button>
            </>
          )}
          {references.data.meta.pages > 1 && (
            <Pagination {...references.data.meta} onChange={setPage} />
          )}
        </>
      ) : (
        <p>
          No program costs are available. Continue with your manual estimate.
        </p>
      )}
      {error && <ErrorState message={error} />}
    </section>
  );
}
