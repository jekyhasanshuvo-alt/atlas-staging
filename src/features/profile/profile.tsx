"use client";
import { CloudProfileEditor } from "@/features/auth/profile-editor";
import { ProfileCompleteness } from "@/features/matching/matching";
import { dataMode } from "@/services/config";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Save } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { profileSchema } from "@/lib/validation/profile";
import { student } from "@/data/mock";
import { usePersistentState } from "@/hooks/use-persistent-state";
import type { Student } from "@/types";
const profileFields: {
  key: keyof Student;
  label: string;
  type?: string;
  options?: string[];
}[] = [
  { key: "fullName", label: "Full name" },
  { key: "nationality", label: "Nationality" },
  { key: "currentCountry", label: "Current country" },
  { key: "destination", label: "Preferred study destination" },
  {
    key: "education",
    label: "Current education level",
    options: ["High school", "Bachelor", "Master", "PhD"],
  },
  { key: "background", label: "Academic background" },
  { key: "subject", label: "Preferred subject" },
  { key: "budget", label: "Annual budget range ceiling (CNY)", type: "number" },
  { key: "language", label: "Language proficiency" },
];
function ProfileForm({
  profile,
  onSave,
}: {
  profile: Student;
  onSave: (s: Student) => void;
}) {
  const [success, setSuccess] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Student>({
    resolver: zodResolver(profileSchema),
    values: profile,
  });
  return (
    <form
      className="panel profile-form"
      onChange={() => setSuccess(false)}
      onSubmit={handleSubmit((data) => {
        onSave(data);
        setSuccess(true);
      })}
      noValidate
    >
      <div className="section-heading">
        <div>
          <h2>Make this journey yours</h2>
          <p>Demo preferences are saved in this browser.</p>
        </div>
        <span className="avatar">
          {profile.fullName
            .split(" ")
            .map((s) => s[0])
            .slice(0, 2)
            .join("")}
        </span>
      </div>
      <div className="form-grid">
        {profileFields.map((f) => (
          <label key={f.key}>
            {f.label}
            {f.options ? (
              <select
                {...register(f.key)}
                aria-invalid={!!errors[f.key]}
                aria-describedby={errors[f.key] ? f.key + "-error" : undefined}
              >
                {f.options.map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            ) : (
              <input
                aria-label={f.label}
                type={f.type ?? "text"}
                {...register(f.key, { valueAsNumber: f.type === "number" })}
                aria-invalid={!!errors[f.key]}
                aria-describedby={errors[f.key] ? f.key + "-error" : undefined}
              />
            )}
            <span className="field-error" id={f.key + "-error"}>
              {errors[f.key]?.message}
            </span>
          </label>
        ))}
        <label className="full-field">
          Career goals
          <textarea
            rows={4}
            {...register("careerGoals")}
            aria-invalid={!!errors.careerGoals}
            aria-describedby="careerGoals-error"
          />
          <span className="field-error" id="careerGoals-error">
            {errors.careerGoals?.message}
          </span>
        </label>
        <label className="check-inline full-field">
          <input type="checkbox" {...register("scholarship")} />
          I’m interested in scholarship opportunities.
        </label>
      </div>
      <div className="form-footer">
        <p>No documents or identity verification are requested.</p>
        <button className="button primary" disabled={isSubmitting}>
          <Save size={16} />
          Save preferences
        </button>
      </div>
      {success && (
        <p className="success-state" role="status">
          <Check size={17} />
          Your demo preferences have been saved on this browser.
        </p>
      )}
    </form>
  );
}
export function Profile() {
  return dataMode === "api" ? <><CloudProfileEditor/><ProfileCompleteness/></> : <DemoProfile/>;
}
function DemoProfile() {
  const [profile, setProfile] = usePersistentState<Student>(
    "student-profile",
    student,
    (v): v is Student => profileSchema.safeParse(v).success,
  );
  return (
    <>
      <PageHeader
        title="Your journey, your way"
        eyebrow="STUDENT PROFILE"
        description="A few thoughtful details give your study plan a better starting point."
      />
      <ProfileForm profile={profile} onSave={setProfile} />
    </>
  );
}
