"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useStudent, broadcastAuth } from "@/components/auth/student-provider";
import { collectLocalImport } from "@/services/local-import";
import { PageHeader } from "@/components/shared";
import { ThemeToggle } from "@/components/layout/app-shell";

interface Session {
  id: string;
  created_at: string;
  expires_at: string;
  last_used_at: string;
  current: boolean;
}
export function AccountSettings() {
  const s = useStudent(),
    router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [password, setPassword] = useState(""),
    [confirmation, setConfirmation] = useState(""),
    [deleting, setDeleting] = useState(false);
  const [preview, setPreview] = useState<unknown>(null),
    [candidate, setCandidate] = useState<ReturnType<
      typeof collectLocalImport
    > | null>(null),
    [approved, setApproved] = useState(false);
  useEffect(() => {
    let active = true;
    s.request<Session[]>("/auth/sessions")
      .then((rows) => {
        if (active) setSessions(rows);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [s.user?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  async function perform(action: () => Promise<void>) {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    await s.request("/auth/logout", "POST");
    s.clear();
    broadcastAuth();
    router.replace("/login");
  }
  async function exportData() {
    const data = await s.request("/me/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "atlas-personal-data.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMessage("Personal data export downloaded.");
  }
  async function inspectImport() {
    const data = collectLocalImport(localStorage);
    const result = await s.request("/me/import/preview", "POST", {
      payload: data.payload,
    });
    setCandidate(data);
    setPreview(result);
    setApproved(false);
  }
  async function confirmImport() {
    if (!candidate || !approved) return;
    const result = await s.request<{ message: string }>("/me/import", "POST", {
      payload: candidate.payload,
      confirmed: true,
    });
    setMessage(result.message);
    setPreview(null);
    setCandidate(null);
    await s.refresh(true);
  }
  async function deleteAccount() {
    await s.request("/me/account", "DELETE", { password, confirmation });
    setPassword("");
    s.clear();
    broadcastAuth();
    router.replace("/login");
  }
  return (
    <>
      <PageHeader
        eyebrow="ACCOUNT & PRIVACY"
        title="Make yourself at home"
        description="Control your account, active sessions, and personal workspace."
      />
      <div className="settings-stack">
        <section className="panel settings-row">
          <div>
            <h2>Appearance</h2>
            <p>Theme preferences stay on this browser.</p>
          </div>
          <ThemeToggle />
        </section>
        <section className="panel">
          <h2>Your account</h2>
          <p>
            {s.user?.email} ·{" "}
            {s.user?.email_verified ? "Email verified" : "Verification pending"}
          </p>
          <button
            className="button"
            disabled={busy}
            onClick={() => void perform(logout)}
          >
            Sign out
          </button>
        </section>
        <section className="panel auth-stack">
          <h2>Active sessions</h2>
          <p>
            Up to 100 most recent active sessions. Revoke any session you no
            longer use.
          </p>
          {sessions.map((session) => (
            <div key={session.id} className="settings-row">
              <div>
                <strong>
                  {session.current ? "This session" : "Another session"}
                </strong>
                <p>
                  Started {new Date(session.created_at).toLocaleString()} ·
                  Expires {new Date(session.expires_at).toLocaleString()}
                </p>
              </div>
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  void perform(async () => {
                    await s.request("/auth/sessions/" + session.id, "DELETE");
                    if (session.current) {
                      s.clear();
                      broadcastAuth();
                      router.replace("/login");
                    } else
                      setSessions((rows) =>
                        rows.filter((row) => row.id !== session.id),
                      );
                  })
                }
              >
                Revoke session
              </button>
            </div>
          ))}
          <button
            className="button"
            disabled={busy}
            onClick={() =>
              void perform(async () => {
                await s.request("/auth/sessions", "DELETE");
                setSessions((rows) => rows.filter((row) => row.current));
                setMessage("Other sessions revoked.");
              })
            }
          >
            Sign out other sessions
          </button>
        </section>
        <section className="panel auth-stack">
          <h2>Bring your browser workspace with you</h2>
          <p>
            Nothing is imported automatically. Review this browser’s data and
            confirm it belongs to you. Existing cloud preferences and newer
            records are preserved. Browser data remains available after import.
          </p>
          <button
            className="button"
            disabled={busy}
            onClick={() => void perform(inspectImport)}
          >
            Preview browser data import
          </button>
          {candidate && (
            <p>Skipped locally: {candidate.skipped.join("; ") || "None"}</p>
          )}
          {preview !== null && (
            <>
              <pre className="privacy-preview">
                {JSON.stringify({ preview, data: candidate?.payload }, null, 2)}
              </pre>
              <label className="check-inline">
                <input
                  type="checkbox"
                  checked={approved}
                  onChange={(e) => setApproved(e.target.checked)}
                />
                This is my data. I reviewed the import and conflict policy.
              </label>
              <button
                className="button primary"
                disabled={busy || !approved}
                onClick={() => void perform(confirmImport)}
              >
                Confirm import into my account
              </button>
              <button
                className="button"
                onClick={() => {
                  setCandidate(null);
                  setPreview(null);
                }}
              >
                Cancel import
              </button>
            </>
          )}
        </section>
        <section className="panel auth-stack">
          <h2>Export your data</h2>
          <p>
            Download portable JSON containing your profile, saves, comparison,
            plans, checklists and import history. Authentication secrets are
            excluded.
          </p>
          <button
            className="button"
            disabled={busy}
            onClick={() => void perform(exportData)}
          >
            Download personal data
          </button>
        </section>
        <section className="panel auth-stack">
          <h2>Delete your account</h2>
          <p>
            This deletes your personal workspace and revokes every session.
            Shared university and scholarship records remain. Development email
            previews and database backups have separate retention; see the
            project privacy notes.
          </p>
          <button className="button danger" onClick={() => setDeleting(true)}>
            Delete account…
          </button>
          {deleting && (
            <form
              className="auth-stack"
              onSubmit={(e) => {
                e.preventDefault();
                void perform(deleteAccount);
              }}
            >
              <label>
                Confirm your current password
                <input
                  type="password"
                  autoComplete="current-password"
                  maxLength={128}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <label>
                Type DELETE MY ACCOUNT
                <input
                  required
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                />
              </label>
              <button
                className="button danger"
                disabled={busy || confirmation !== "DELETE MY ACCOUNT"}
              >
                Permanently delete my account
              </button>
              <button
                type="button"
                className="button"
                onClick={() => {
                  setDeleting(false);
                  setPassword("");
                  setConfirmation("");
                }}
              >
                Cancel
              </button>
            </form>
          )}
        </section>
        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="success-state" role="status">
            {message}
          </p>
        )}
      </div>
    </>
  );
}
