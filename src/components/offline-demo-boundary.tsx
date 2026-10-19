"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
export const offlineDemoPaths = ["/", "/dashboard", "/financial-twin", "/universities", "/scholarships", "/compare", "/student-life", "/career"];
export function OfflineDemoBoundary({ children }: { children?: React.ReactNode }) {
  const path = usePathname();
  return <><p role="note" className="staging-demo-notice">DEMO ONLY · Fictional or empty data. Use hypothetical financial inputs only. No accounts, email, database or external AI. Inputs reset on reload.</p>{offlineDemoPaths.includes(path) ? children : <main className="panel section-gap"><h1>Unavailable in this public demo</h1><p>Signup, login, personal profiles, account storage and AI requests are disabled. No personal information is requested.</p><Link className="button primary" href="/dashboard">Explore demo workspace</Link><Link className="button" href="/financial-twin">Try the calculator</Link></main>}</>;
}
