"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useStudent } from "@/components/auth/student-provider";
import { PageHeader, Checklist, money } from "@/components/shared";
import { studyPlan } from "@/data/mock";
interface Dashboard {
  profile_completion: number;
  saved_university_count: number;
  saved_scholarship_count: number;
  active_financial_plan: {
    name: string;
    currency: string;
    totals: { adjusted: string };
  } | null;
  checklist_progress: Record<string, { completed: number; total: number }>;
  next_steps: string[];
}
export function CloudDashboard() {
  const s = useStudent();
  const [data, setData] = useState<Dashboard | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    s.request<Dashboard>("/me/dashboard")
      .then((data) => {
        if (active) setData(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [s.values]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <>
      <PageHeader
        eyebrow="YOUR STUDENT WORKSPACE"
        title={
          "Welcome back" +
          (s.workspace?.profile.full_name
            ? ", " + s.workspace.profile.full_name.split(" ")[0]
            : "")
        }
        description="Your plans and preparation, synced to your account."
        action={
          <Link className="button" href="/profile">
            Edit study preferences
          </Link>
        }
      />
      {error && (
        <div role="alert">
          {error}
          <button className="button" onClick={() => void s.refresh()}>
            Retry
          </button>
        </div>
      )}
      {data ? (
        <>
          <div className="stats-grid">
            {[
              ["Profile completion", data.profile_completion + "%"],
              ["Saved universities", data.saved_university_count],
              ["Saved scholarships", data.saved_scholarship_count],
              [
                "Latest plan estimate",
                data.active_financial_plan
                  ? money(
                      Number(data.active_financial_plan.totals.adjusted),
                      data.active_financial_plan.currency,
                    )
                  : "No saved plan",
              ],
            ].map(([label, value]) => (
              <section className="panel" key={label}>
                <p>{label}</p>
                <h2>{value}</h2>
              </section>
            ))}
          </div>
          <div className="two-column section-gap">
            <section className="panel">
              <h2>Your next steps</h2>
              <p>Based on your workspace progress.</p>
              <ul>
                {data.next_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
              <div className="auth-links">
                <Link href="/onboarding">Resume onboarding</Link>
                <Link href="/universities">Explore universities</Link>
                <Link href="/financial-twin">Plan your budget</Link>
              </div>
            </section>
            <section className="panel">
              <h2>Preparation checklist</h2>
              <Checklist tasks={studyPlan.tasks} />
            </section>
          </div>
          <section className="panel section-gap">
            <h2>Preparation progress</h2>
            {Object.entries(data.checklist_progress).map(([key, p]) => (
              <p key={key}>
                {key}: {p.completed} of {p.total} complete
              </p>
            ))}
          </section>
        </>
      ) : (
        !error && <p role="status">Loading your dashboard…</p>
      )}
    </>
  );
}
