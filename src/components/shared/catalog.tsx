"use client";
import type { Provenance } from "@/services/contracts";
import { dataMode } from "@/services/config";
const labels = {
  unverified: "Unverified",
  under_review: "Under review",
  verified: "Verified",
  stale: "Outdated",
  rejected: "Rejected",
};
export function DataConnection({
  loading,
  error,
}: {
  loading?: boolean;
  error?: string;
}) {
  return (
    <div className="catalog-connection" role="status">
      <span className={"connection-dot " + (error ? "failed" : "")} />
      {dataMode === "demo"
        ? "Demo mode · Offline sample adapter"
        : error
          ? "API connection failed · No demo fallback"
          : loading
            ? "API mode · Loading catalog…"
            : "API mode · PostgreSQL catalog"}
      <small>
        {dataMode === "demo"
          ? "Student preferences remain on this browser."
          : "Your account keeps saved preferences across devices."}
      </small>
    </div>
  );
}
function safeSourceUrl(value: string | null) {
  if (
    !value || value.includes("\\") || Array.from(value).some((char) =>
      /\s/.test(char) || char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127,
    )
  ) return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
      ? value : null;
  } catch {
    return null;
  }
}
export function ProvenanceInfo({
  value,
  compact = false,
  label,
}: {
  value?: Provenance;
  compact?: boolean;
  label?: string;
}) {
  const demo = value?.is_demo === true || (!value && dataMode === "demo");
  return (
    <div className="provenance">
      {label && <strong>{label}</strong>}
      <span
        className={
          "provenance-badge " + (value?.verification_status ?? "unverified")
        }
      >
        {demo ? "Demo Data" : labels[value?.verification_status ?? "unverified"]}
      </span>
      {!compact && (
        <>
          <span className="provenance-description">
            {demo ? (
              "Illustrative data. No admissions or funding information has been verified."
            ) : (
              <>
                {value?.verification_status === "under_review" &&
                  "This record is not fully verified. "}
                Review status covers the named record fields only. Program fees
                and living estimates have separate provenance.
              </>
            )}
          </span>
          <details>
            <summary>Sources and verification</summary>
            {value?.records.length ? (
              value.records.map((record, i) => {
                const sourceUrl = safeSourceUrl(record.source.source_url);
                return (
                <div className="source-record" key={record.source.id + "-" + i}>
                  <strong>{record.source.title}</strong>
                  <p>Publisher: {record.source.publisher}</p>
                  {sourceUrl ? (
                    <a
                      className="text-link"
                      href={sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open source ↗
                    </a>
                  ) : (
                    <p>
                      Source URL: not available
                    </p>
                  )}
                  <p>
                    Retrieved:{" "}
                    {record.source.retrieved_at
                      ? new Date(record.source.retrieved_at).toLocaleDateString(
                          "en-GB",
                        )
                      : "Not retrieved"}
                  </p>
                  <p>
                    Review: {labels[record.verification_status]} ·{" "}
                    {record.reviewed_at
                      ? new Date(record.reviewed_at).toLocaleDateString("en-GB")
                      : "No review date"}
                  </p>
                  <p>
                    Reviewed fields:{" "}
                    {record.reviewed_fields.join(", ") || "None"}
                  </p>
                  <p>
                    Validity: {record.valid_from ?? "Not specified"} —{" "}
                    {record.valid_until ?? "Not specified"}
                  </p>
                  <p>{record.notes}</p>
                </div>
              );
              })
            ) : (
              <p>
                {demo
                  ? "Offline demo record. No external source or review date is claimed."
                  : "Source not available. Not yet verified."}
              </p>
            )}
          </details>
        </>
      )}
    </div>
  );
}
export function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  return (
    <nav className="pagination" aria-label="Catalog pagination">
      <span>
        {total} records · Page {page} of {Math.max(1, pages)}
      </span>
      <div className="row">
        <button
          className="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Previous
        </button>
        <button
          className="button"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
