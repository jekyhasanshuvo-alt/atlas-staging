"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/layout/app-shell";
import { useStudent, broadcastAuth } from "@/components/auth/student-provider";
import {
  studentRequest,
  safeReturnTo,
  type Identity,
} from "@/services/student";
export type AuthKind =
  | "login"
  | "signup"
  | "verify-email"
  | "forgot-password"
  | "reset-password";
const titles: Record<AuthKind, string> = {
  login: "Welcome back",
  signup: "Your next chapter starts here",
  "verify-email": "Verify your email",
  "forgot-password": "Find your way back",
  "reset-password": "Choose a new password",
};
export function AuthPage({ kind }: { kind: AuthKind }) {
  const s = useStudent(),
    router = useRouter();
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [visible, setVisible] = useState(false),
    [token, setToken] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    if (fragment.has("token")) {
      queueMicrotask(() => setToken(fragment.get("token") ?? ""));
      history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
    }
  }, []);
  const needsEmail = ["login", "signup", "forgot-password"].includes(kind),
    needsPassword = ["login", "signup", "reset-password"].includes(kind);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (kind === "login") {
        s.clear();
        const result = await studentRequest<Identity>("/auth/login", "POST", {
          email,
          password,
        });
        setPassword("");
        broadcastAuth();
        await s.refresh();
        if (!result.user.email_verified) {
          router.replace("/verify-email");
          return;
        }
        const profile = await studentRequest<{
          onboarding_completed_at: string | null;
        }>("/me/profile");
        router.replace(
          profile.onboarding_completed_at
            ? safeReturnTo(
                new URLSearchParams(window.location.search).get("returnTo"),
              )
            : "/onboarding",
        );
      } else {
        const body =
          kind === "signup"
            ? { email, password }
            : kind === "forgot-password"
              ? { email }
              : kind === "reset-password"
                ? { token, password }
                : { token };
        const result = await studentRequest<{ message: string }>(
          "/auth/" + (kind === "signup" ? "register" : kind),
          "POST",
          body,
        );
        setMessage(result.message);
        setPassword("");
        if (kind === "verify-email") {
          setToken("");
          await s.refresh();
          broadcastAuth();
        }
        if (kind === "reset-password") setToken("");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  async function resend() {
    setBusy(true);
    setError("");
    try {
      const result = await studentRequest<{ message: string }>(
        "/auth/resend-verification",
        "POST",
        { email: email || s.user?.email },
      );
      setMessage(result.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please retry.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <Logo />
      <section className="panel section-gap">
        <span className="eyebrow">ATLAS STUDENT ACCOUNT</span>
        <h1>{titles[kind]}</h1>
        <p>
          {kind === "verify-email"
            ? "Open the single-use link sent to your email, then confirm below. Local development messages are in the private mail preview folder."
            : "Keep your study plans together, wherever you are."}
        </p>
        <form onSubmit={submit}>
          {needsEmail && (
            <label>
              Email address
              <input
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          )}
          {needsPassword && (
            <label>
              Password
              <div className="password-control">
                <input
                  aria-label="Password"
                  type={visible ? "text" : "password"}
                  autoComplete={
                    kind === "login" ? "current-password" : "new-password"
                  }
                  minLength={12}
                  maxLength={128}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  className="button"
                  type="button"
                  aria-pressed={visible}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? "Hide" : "Show"}
                </button>
              </div>
              <small>
                12–128 characters. Include a letter and number for a new
                password.
              </small>
            </label>
          )}
          {((kind === "verify-email" && token) ||
            needsEmail ||
            needsPassword) && (
            <button
              className="button primary"
              disabled={busy || (kind === "reset-password" && !token)}
            >
              {busy
                ? "Please wait…"
                : kind === "login"
                  ? "Sign in"
                  : kind === "signup"
                    ? "Create account"
                    : kind === "verify-email"
                      ? "Confirm email verification"
                      : kind === "forgot-password"
                        ? "Send recovery email"
                        : "Reset password"}
            </button>
          )}
          {kind === "reset-password" && !token && !message && (
            <p role="alert">
              Open a valid reset link from your email.{" "}
              <Link href="/forgot-password">Request another link</Link>.
            </p>
          )}
        </form>
        {kind === "verify-email" && !token && (
          <div className="auth-stack">
            <label>
              Email for verification
              <input
                type="email"
                autoComplete="email"
                value={email || s.user?.email || ""}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <button
              className="button"
              disabled={busy || !(email || s.user?.email)}
              onClick={() => void resend()}
            >
              Resend verification email
            </button>
            {s.user?.email_verified && (
              <Link className="button primary" href="/onboarding">
                Continue to onboarding
              </Link>
            )}
          </div>
        )}
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
        <nav className="auth-links" aria-label="Account navigation">
          <Link href="/login">Sign in</Link>
          <Link href="/signup">Create an account</Link>
          <Link href="/forgot-password">Forgot password?</Link>
          <Link href="/universities">Browse universities</Link>
        </nav>
      </section>
    </main>
  );
}
