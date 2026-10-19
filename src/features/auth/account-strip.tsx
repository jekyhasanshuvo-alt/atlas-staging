"use client";
import Link from "next/link";
import { useStudent } from "@/components/auth/student-provider";
import { dataMode } from "@/services/config";
export function AccountStrip() {
  const s = useStudent();
  if (dataMode !== "api") return null;
  return (
    <div className="account-strip">
      {s.loading ? (
        <span>Checking account…</span>
      ) : s.user ? (
        <>
          <span>
            {s.user.email} ·{" "}
            {s.user.email_verified
              ? "Cloud workspace"
              : "Email verification required"}
          </span>
          <Link href="/settings">Account settings</Link>
        </>
      ) : (
        <>
          <span>Public catalog · sign in to save your plans</span>
          <Link href="/login">Sign in</Link>
          <Link href="/signup">Create account</Link>
        </>
      )}
    </div>
  );
}
