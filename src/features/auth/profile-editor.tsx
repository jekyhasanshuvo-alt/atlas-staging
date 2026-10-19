"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useStudent } from "@/components/auth/student-provider";
import type { CloudProfile } from "@/services/student";
import { PageHeader } from "@/components/shared";

const groups = [
  [
    { key: "full_name", label: "Full name", required: true },
    { key: "nationality", label: "Nationality", required: true },
    { key: "current_country", label: "Current country", required: true },
  ],
  [
    {
      key: "education_level",
      label: "Current education level",
      required: true,
    },
    { key: "academic_background", label: "Academic background (optional)" },
  ],
  [
    {
      key: "preferred_destination",
      label: "Preferred study destination",
      required: true,
    },
  ],
  [
    {
      key: "budget_amount",
      label: "Budget ceiling (choose its period when comparing programs)",
      required: true,
      type: "number",
    },
    { key: "budget_currency", label: "Budget currency", required: true },
  ],
  [
    { key: "preferred_subject", label: "Preferred subject", required: true },
    { key: "language_proficiency", label: "Language proficiency (optional)" },
    { key: "career_goals", label: "Career goals (optional)" },
  ],
] as const;
const steps = [
  "Personal",
  "Academic",
  "Destination",
  "Funding",
  "Goals",
  "Review",
];
export function CloudProfileEditor({
  onboarding = false,
}: {
  onboarding?: boolean;
}) {
  const s = useStudent(),
    router = useRouter();
  const [profile, setProfile] = useState<CloudProfile>(s.workspace!.profile),
    [step, setStep] = useState(() => {
      const first = groups.findIndex((group) =>
        group.some(
          (f) =>
            "required" in f &&
            f.required &&
            (f.key === "budget_amount"
              ? Number(s.workspace!.profile[f.key]) <= 0
              : String(s.workspace!.profile[f.key as keyof CloudProfile]).trim()
                  .length < 2),
        ),
      );
      return first < 0 ? 5 : first;
    }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  function valid() {
    const fields = onboarding && step < 5 ? groups[step] : groups.flat();
    return fields.every(
      (f) =>
        !("required" in f && f.required) ||
        (f.key === "budget_amount"
          ? Number(profile[f.key]) > 0
          : String(profile[f.key as keyof CloudProfile]).trim().length >= 2),
    );
  }
  async function save(next: boolean, finish = false) {
    setError("");
    setMessage("");
    if ((next || finish) && !valid()) {
      setError("Complete the required fields before continuing.");
      return;
    }
    setBusy(true);
    try {
      const { onboarding_completed_at: _completed, ...payload } = profile;
      void _completed;
      const clean = Object.fromEntries(
        Object.entries(payload).filter(([key]) => key !== "updated_at"),
      );
      const result = await s.request<CloudProfile>("/me/profile", "PATCH", {
        ...clean,
        complete_onboarding: finish,
      });
      setProfile(result);
      setMessage("Progress saved to your account.");
      if (finish) {
        await s.refresh();
        router.push("/dashboard");
      } else if (next) setStep(Math.min(5, step + 1));
      else if (!onboarding) await s.refresh(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save.");
    } finally {
      setBusy(false);
    }
  }
  const fields = onboarding ? (step < 5 ? groups[step] : []) : groups.flat();
  return (
    <>
      <PageHeader
        eyebrow={onboarding ? "YOUR ATLAS STARTING POINT" : "STUDENT PROFILE"}
        title={
          onboarding ? "Make this journey yours" : "Your journey, your way"
        }
        description="Save your preferences securely. No identity documents are requested."
      />
      <section className="panel auth-stack">
        {onboarding && (
          <ol className="auth-progress" aria-label="Onboarding progress">
            {steps.map((name, i) => (
              <li
                className={i === step ? "active" : ""}
                aria-current={i === step ? "step" : undefined}
                key={name}
              >
                {i + 1}. {name}
              </li>
            ))}
          </ol>
        )}
        <form
          id="profile-fields"
          onSubmit={(e) => {
            e.preventDefault();
            void save(onboarding && step < 5, onboarding && step === 5);
          }}
        >
          <p>Academic background and language proficiency are self-reported text, not verified grades or test records. Budget period is not stored; select an explicit original tuition period when matching programs.</p>
          <div className="form-grid">
            {fields.map((f) => (
              <label key={f.key}>
                {f.label}
                {"required" in f && f.required ? " *" : ""}
                {f.key === "budget_currency" ? (
                  <select
                    value={profile.budget_currency}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        budget_currency: e.target
                          .value as CloudProfile["budget_currency"],
                      })
                    }
                  >
                    <option>CNY</option>
                    <option>USD</option>
                    <option>BDT</option>
                  </select>
                ) : (
                  <input
                    aria-label={f.label}
                    type={"type" in f ? f.type : "text"}
                    min={f.key === "budget_amount" ? 0 : undefined}
                    max={f.key === "budget_amount" ? 100000000 : undefined}
                    step={f.key === "budget_amount" ? "0.01" : undefined}
                    maxLength={f.key === "career_goals" ? 1000 : 200}
                    value={String(profile[f.key])}
                    onChange={(e) =>
                      setProfile({ ...profile, [f.key]: e.target.value })
                    }
                  />
                )}
              </label>
            ))}
          </div>
          {(!onboarding || step === 3) && (
            <label className="check-inline section-gap">
              <input
                type="checkbox"
                checked={profile.scholarship_preference}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    scholarship_preference: e.target.checked,
                  })
                }
              />
              Interested in scholarships (funding is not guaranteed)
            </label>
          )}
          {onboarding && step === 5 && (
            <div className="onboarding-review">
              {groups.flat().map((f) => (
                <div key={f.key}>
                  <strong>{f.label}</strong>
                  <p>{String(profile[f.key]) || "Not provided"}</p>
                </div>
              ))}
            </div>
          )}
          <div className="row section-gap">
            {onboarding && step > 0 && (
              <button
                type="button"
                className="button"
                disabled={busy}
                onClick={() => setStep(step - 1)}
              >
                Back
              </button>
            )}
            <button
              type="button"
              className="button"
              disabled={busy}
              onClick={() => void save(false)}
            >
              Save progress
            </button>
            <button className="button primary" disabled={busy}>
              {busy
                ? "Saving…"
                : onboarding
                  ? step === 5
                    ? "Finish onboarding"
                    : "Save and continue"
                  : "Save profile"}
            </button>
          </div>
        </form>
        {error && (
          <p role="alert" className="field-error">
            {error}
          </p>
        )}
        {message && (
          <p role="status" className="success-state">
            {message}
          </p>
        )}
      </section>
    </>
  );
}
