"use client";
import { useState } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { planValues, type CloudPlan } from "@/services/student";
import { dataMode } from "@/services/config";
import { defaultPlan } from "@/data/mock";
import type { FinancialPlan } from "@/types";
export function FinancialCloudControls({
  plan,
  baseline,
}: {
  plan: FinancialPlan;
  baseline: FinancialPlan | null;
}) {
  const s = useStudent();
  const [loaded, setLoaded] = useState<{ id: string; version: number } | null>(
    null,
  );
  const [selected, setSelected] = useState(""),
    [name, setName] = useState("My study plan"),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [confirm, setConfirm] = useState(false);
  if (dataMode !== "api") return null;
  function load() {
    const p = s.plans.find((p) => p.id === selected);
    setLoaded(p ? { id: p.id, version: p.version } : null);
    s.draft("financial-plan", p ? planValues(p) : { ...defaultPlan });
    s.draft("financial-scenario", p?.baseline ? planValues(p.baseline) : null);
    setName(p?.name ?? "My study plan");
    setMessage(
      p
        ? "Saved plan loaded. Your previous unsaved draft was replaced."
        : "New unsaved scenario.",
    );
  }
  async function save(copy: boolean) {
    setError("");
    setBusy(true);
    try {
      const existing = s.plans.find((p) => p.id === selected);
      if (existing && !copy && loaded?.id !== existing.id)
        throw new Error(
          "Load the selected plan before updating it, or save this draft as a new plan.",
        );
      const result = await s.request<CloudPlan>(
        existing && !copy
          ? "/me/financial-plans/" + existing.id
          : "/me/financial-plans",
        existing && !copy ? "PATCH" : "POST",
        {
          ...plan,
          name,
          baseline,
          ...(existing && !copy ? { version: loaded!.version } : {}),
        },
      );
      setSelected(result.id);
      setLoaded({ id: result.id, version: result.version });
      setName(result.name);
      setMessage("Plan saved to your account.");
      await s.refresh(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save.");
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setError("");
    setBusy(true);
    try {
      await s.request("/me/financial-plans/" + selected, "DELETE");
      s.draft("financial-plan", defaultPlan);
      s.draft("financial-scenario", null);
      setSelected("");
      setConfirm(false);
      await s.refresh(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to delete.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel section-gap">
      <h2>Your cloud plans</h2>
      <p>
        Inputs are an unsaved draft until you save. Loading replaces the current
        draft; references apply only when requested.
      </p>
      <div className="cloud-toolbar">
        <label>
          Saved plan
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">New scenario</option>
            {s.plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.currency}
              </option>
            ))}
          </select>
        </label>
        <button className="button" onClick={load} disabled={busy}>
          Load selected plan
        </button>
        <label>
          Plan name
          <input
            maxLength={120}
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <button
          className="button primary"
          disabled={busy || !name.trim()}
          onClick={() => void save(false)}
        >
          Save plan
        </button>
        <button
          className="button"
          disabled={busy || !name.trim()}
          onClick={() => void save(true)}
        >
          Save as new plan
        </button>
        {selected && (
          <button
            className="button danger"
            disabled={busy}
            onClick={() => setConfirm(true)}
          >
            Delete plan
          </button>
        )}
      </div>
      {confirm && (
        <div role="alert">
          <p>Delete this saved plan?</p>
          <button
            className="button danger"
            onClick={() => void remove()}
            disabled={busy}
          >
            Confirm plan deletion
          </button>
          <button className="button" onClick={() => setConfirm(false)}>
            Cancel
          </button>
        </div>
      )}
      {error && (
        <p role="alert" className="field-error">
          {error} Your draft has been preserved.
        </p>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
