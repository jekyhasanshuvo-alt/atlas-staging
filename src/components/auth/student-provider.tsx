"use client";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { dataMode } from "@/services/config";
import {
  studentRequest,
  StudentApiError,
  toStudent,
  toProfile,
  planValues,
  type Account,
  type Identity,
  type CloudWorkspace,
  type CloudPlan,
} from "@/services/student";
import { defaultPlan } from "@/data/mock";
import type { Student } from "@/types";

type Values = Record<string, unknown>;
interface StudentContext {
  user: Account | null;
  loading: boolean;
  error: string;
  busy: boolean;
  csrf: string;
  values: Values;
  workspace: CloudWorkspace | null;
  plans: CloudPlan[];
  refresh: (background?: boolean) => Promise<void>;
  clear: () => void;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>;
  update: (key: string, value: unknown) => Promise<void>;
  draft: (key: string, value: unknown) => void;
}
export const StudentState = createContext<StudentContext | null>(null);
export const privateKeys = new Set([
  "student-profile",
  "saved-universities",
  "saved-scholarships",
  "comparison",
  "preparation",
  "life-checklist",
  "career-checklist",
  "financial-plan",
  "financial-scenario",
  "new-user",
]);
export function StudentProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<Account | null>(null),
    [csrf, setCsrf] = useState("atlas"),
    [loading, setLoading] = useState(dataMode === "api"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [values, setValues] = useState<Values>({}),
    [workspace, setWorkspace] = useState<CloudWorkspace | null>(null),
    [plans, setPlans] = useState<CloudPlan[]>([]);
  const generation = useRef(0),
    currentUser = useRef<string | null>(null),
    pending = useRef(false);
  const clear = useCallback(() => {
    generation.current++;
    currentUser.current = null;
    setUser(null);
    setCsrf("atlas");
    setWorkspace(null);
    setValues({});
    setPlans([]);
  }, []);
  const refresh = useCallback(
    async (background = false) => {
      if (dataMode !== "api" || pending.current) return;
      const run = ++generation.current;
      if (!background) setLoading(true);
      setError("");
      try {
        const identity = await studentRequest<Identity>("/auth/me");
        if (run !== generation.current) return;
        if (currentUser.current !== identity.user.id) {
          setLoading(true);
          setValues({});
          setWorkspace(null);
          setPlans([]);
        }
        currentUser.current = identity.user.id;
        setUser(identity.user);
        setCsrf(identity.csrf_token);
        if (identity.user.email_verified) {
          const [w, p] = await Promise.all([
            studentRequest<CloudWorkspace>("/me/workspace"),
            studentRequest<{ items: CloudPlan[] }>(
              "/me/financial-plans?page_size=100",
            ),
          ]);
          if (run !== generation.current) return;
          setWorkspace(w);
          setPlans(p.items);
          setValues((previous) => ({
            ...previous,
            "student-profile": toStudent(w.profile),
            "saved-universities": w.universities,
            "saved-scholarships": w.scholarships,
            comparison: w.comparison,
            ...w.checklists,
            "new-user": false,
            ...(!previous["financial-plan"]
              ? {
                  "financial-plan": p.items[0]
                    ? planValues(p.items[0])
                    : defaultPlan,
                  "financial-scenario": p.items[0]?.baseline
                    ? planValues(p.items[0].baseline)
                    : null,
                }
              : {}),
          }));
        }
      } catch (e) {
        if (run !== generation.current) return;
        if (e instanceof StudentApiError && e.status === 401) {
          clear();
        } else {
          if (!background) setWorkspace(null);
          setError(
            e instanceof Error ? e.message : "Unable to load workspace.",
          );
        }
      } finally {
        if (run === generation.current || currentUser.current === null)
          setLoading(false);
      }
    },
    [clear],
  );
  useEffect(() => {
    const initialTimer = setTimeout(() => void refresh(), 0);
    const changed = () => {
      clear();
      void refresh();
    };
    const storage = (event: StorageEvent) => {
      if (event.key === "atlas-auth-change") changed();
    };
    const focus = () => {
      void refresh(true);
    };
    window.addEventListener("storage", storage);
    window.addEventListener("focus", focus);
    const timer = setInterval(focus, 60000);
    return () => {
      clearTimeout(initialTimer);
      window.removeEventListener("storage", storage);
      window.removeEventListener("focus", focus);
      clearInterval(timer);
    };
  }, [refresh, clear]);
  async function request<T>(
    path: string,
    method = "GET",
    body?: unknown,
  ): Promise<T> {
    const run = generation.current;
    try {
      return await studentRequest<T>(path, method, body, csrf);
    } catch (e) {
      if (
        run === generation.current &&
        e instanceof StudentApiError &&
        e.status === 401
      ) {
        clear();
        setError("Your session expired. Sign in again.");
      }
      throw e;
    }
  }
  async function update(key: string, value: unknown) {
    if (!user) {
      router.push(
        "/login?returnTo=" + encodeURIComponent(window.location.pathname),
      );
      return;
    }
    if (pending.current) {
      setError("A save is still in progress. Please try again.");
      throw new Error("A save is still in progress. Please try again.");
    }
    if (!workspace) throw new Error("Load your cloud workspace before saving.");
    pending.current = true;
    setBusy(true);
    setError("");
    const run = generation.current;
    try {
      if (key === "student-profile") {
        const profile = await request<CloudWorkspace["profile"]>(
          "/me/profile",
          "PATCH",
          toProfile(value as Student),
        );
        if (run === generation.current) {
          setWorkspace((w) => (w ? { ...w, profile } : w));
          setValues((v) => ({ ...v, [key]: toStudent(profile) }));
        }
      } else if (key === "comparison") {
        const result = await request<{ ids: string[] }>(
          "/me/comparison",
          "PUT",
          { ids: value },
        );
        if (run === generation.current)
          setValues((v) => ({ ...v, [key]: result.ids }));
      } else if (key === "saved-universities" || key === "saved-scholarships") {
        const path =
          "/me/" +
          (key === "saved-universities" ? "universities" : "scholarships");
        const before = (values[key] ?? []) as string[],
          after = value as string[];
        for (const id of before.filter((id) => !after.includes(id)))
          await request(path + "/" + encodeURIComponent(id), "DELETE");
        for (const id of after.filter((id) => !before.includes(id)))
          await request(path, "POST", { id });
        if (run === generation.current)
          setValues((v) => ({ ...v, [key]: after }));
      } else if (
        ["preparation", "life-checklist", "career-checklist"].includes(key)
      ) {
        const result = await request<Record<string, string[]>>(
          "/me/checklists",
          "PUT",
          { category: key, completed: value },
        );
        if (run === generation.current) setValues((v) => ({ ...v, ...result }));
      } else if (run === generation.current)
        setValues((v) => ({ ...v, [key]: value }));
    } catch (e) {
      if (run === generation.current)
        setError(e instanceof Error ? e.message : "Unable to save. Retry.");
      throw e;
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return (
    <StudentState.Provider
      value={{
        user,
        csrf,
        loading,
        error,
        busy,
        values,
        workspace,
        plans,
        refresh,
        clear,
        request,
        update,
        draft: (key, value) => setValues((v) => ({ ...v, [key]: value })),
      }}
    >
      {children}
    </StudentState.Provider>
  );
}
export function useStudent() {
  const value = useContext(StudentState);
  if (!value) throw new Error("StudentProvider is required");
  return value;
}
export function broadcastAuth() {
  try {
    localStorage.setItem("atlas-auth-change", String(Date.now()));
  } catch {
    /* No credentials or account data stored. */
  }
}
export function WorkspaceGuard({ children }: { children: React.ReactNode }) {
  const s = useStudent(),
    path = usePathname(),
    router = useRouter();
  const publicPage =
    path.startsWith("/universities") || path === "/programs" || path.startsWith("/programs/") || path === "/compare" || path === "/scholarships" || path.startsWith("/scholarships/");
  useEffect(() => {
    if (dataMode === "api" && !publicPage && !s.loading && !s.error) {
      if (!s.user)
        router.replace("/login?returnTo=" + encodeURIComponent(path));
      else if (!s.user.email_verified) router.replace("/verify-email");
    }
  }, [path, publicPage, s.loading, s.error, s.user, router]);
  if (dataMode === "demo")
    return (
      <>
        <p className="info-note">
          Offline demo workspace · saved only in this browser
        </p>
        {children}
      </>
    );
  if (
    !publicPage &&
    (s.loading || !s.user || !s.user.email_verified || !s.workspace)
  )
    return (
      <section className="panel">
        <h1>
          {s.loading ? "Opening your workspace…" : "Your student workspace"}
        </h1>
        {s.error ? (
          <>
            <p role="alert">{s.error}</p>
            <button className="button" onClick={() => void s.refresh()}>
              Retry
            </button>
            <Link href="/login" className="button">
              Sign in
            </Link>
          </>
        ) : (
          <Link href="/login">Sign in to continue</Link>
        )}
      </section>
    );
  return (
    <>
      {s.error && (
        <div className="info-note" role="alert">
          {s.error}{" "}
          <button className="text-button" onClick={() => void s.refresh()}>
            Retry cloud sync
          </button>
        </div>
      )}
      {s.busy && <p role="status">Saving to your account…</p>}
      {children}
    </>
  );
}
