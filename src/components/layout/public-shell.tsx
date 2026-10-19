import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Logo, ThemeToggle } from "./app-shell";
export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="marketing">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>{" "}
      <header className="public-header">
        <Logo />
        <nav aria-label="Public navigation">
          <a href="#possibilities">The platform</a>
          <a href="#how-it-works">How it works</a>
          <a href="#our-approach">Our approach</a>
        </nav>
        <div className="row">
          <ThemeToggle />
          <Link href="/login">Sign in</Link>
          <Link className="button primary" href="/dashboard">
            Open workspace <ArrowUpRight size={16} />
          </Link>
        </div>
      </header>
      <main id="main-content">{children}</main>{" "}
      <footer className="public-footer">
        <div>
          <Logo />
          <p>Thoughtful decisions. Global possibilities.</p>
        </div>
        <div>
          <Link href="/universities">Universities</Link>
          <Link href="/programs">Programs</Link>
          <Link href="/scholarships">Scholarships</Link>
          <Link href="/financial-twin">Financial Twin</Link>
          <a href="#our-approach">Transparency</a>
        </div>
        <small>
          © {new Date().getFullYear()} Atlas. Phase 3 development.
        </small>
      </footer>
    </div>
  );
}
