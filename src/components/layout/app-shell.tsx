"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import {
  Globe2,
  LayoutDashboard,
  GraduationCap,
  GitCompareArrows,
  Award,
  ChartNoAxesCombined,
  Sparkles,
  Compass,
  BriefcaseBusiness,
  Settings,
  Sun,
  Moon,
  Menu,
  X,
  Bell,
  ChevronDown,
  ArrowUpRight,
  Search,
} from "lucide-react";
import { useStudent } from "@/components/auth/student-provider";
import { dataMode, offlineDemo } from "@/services/config";
import { AccountStrip } from "@/features/auth/account-strip";
import { usePersistentState } from "@/hooks/use-persistent-state";
import { DemoNotice } from "@/components/shared";
const navigation = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/universities", label: "Universities", icon: GraduationCap },
  { href: "/programs", label: "Programs", icon: GraduationCap },
  { href: "/matches", label: "My program matches", icon: GraduationCap },
  { href: "/applications", label: "Applications", icon: BriefcaseBusiness },
  { href: "/advisor", label: "Offline advisor", icon: Sparkles },
  { href: "/compare", label: "Compare options", icon: GitCompareArrows },
  { href: "/scholarships", label: "Scholarships", icon: Award },
  {
    href: "/financial-twin",
    label: "Financial Twin",
    icon: ChartNoAxesCombined,
  },
  { href: "/assistant", label: "AI Study Assistant", icon: Sparkles },
  { href: "/student-life", label: "Student life", icon: Compass },
  { href: "/career", label: "Career intelligence", icon: BriefcaseBusiness },
];
export function Logo() {
  return (
    <Link href="/" className="logo">
      <span className="logo-mark">
        <Globe2 size={24} />
      </span>
      <span>
        atlas<span className="logo-dot">.</span>
        <small>STUDENT INTELLIGENCE</small>
      </span>
    </Link>
  );
}
export function ThemeToggle() {
  const [theme, setTheme] = usePersistentState<string>(
    "theme",
    "light",
    (v): v is string => v === "light" || v === "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  return (
    <button
      className="icon-button"
      aria-label={
        "Switch to " + (theme === "dark" ? "light" : "dark") + " mode"
      }
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}
export function Sidebar({ close }: { close: () => void }) {
  const account = useStudent();
  const accountName =
    dataMode === "api"
      ? account.workspace?.profile.full_name || "Student account"
      : "Alex Morgan";
  const path = usePathname();
  return (
    <>
      <div className="sidebar-brand">
        <Logo />
        <button
          className="icon-button mobile-only"
          onClick={close}
          aria-label="Close navigation"
        >
          <X />
        </button>
      </div>
      <div className="workspace-label">YOUR WORKSPACE</div>
      <nav aria-label="Student navigation">
        {navigation.filter(item => !offlineDemo || ["/dashboard", "/universities", "/scholarships", "/financial-twin", "/compare", "/student-life", "/career"].includes(item.href)).map(({ href, label, icon: Icon }) => (
          <Link
            onClick={close}
            className={
              "nav-item " +
              (path === href || path.startsWith(href + "/") ? "active" : "")
            }
            href={href}
            key={href}
          >
            <Icon size={19} />
            <span>{label}</span>
            {href === "/assistant" && (
              <small className="mini-badge">DEMO</small>
            )}
          </Link>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="journey-tip">
          <span className="eyebrow">A WORLD OF POSSIBILITIES</span>
          <strong>
            Your next chapter
            <br />
            starts with a plan.
          </strong>
          <Link href="/profile">
            Personalize your journey <ArrowUpRight size={15} />
          </Link>
        </div>
        <Link
          className={"nav-item " + (path === "/settings" ? "active" : "")}
          href="/settings"
        >
          <Settings size={18} />
          Settings
        </Link>
        <Link className="sidebar-user" href="/profile">
          <span className="avatar">
            {accountName
              .split(" ")
              .map((n) => n[0])
              .slice(0, 2)
              .join("")}
          </span>
          <span>
            <strong>{accountName}</strong>
            <small>
              {dataMode === "api"
                ? "Account workspace"
                : "Demo student account"}
            </small>
          </span>
          <ChevronDown size={15} />
        </Link>
      </div>
    </>
  );
}
export function Topbar({ open }: { open: () => void }) {
  const account = useStudent();
  const initials =
    dataMode === "api"
      ? (account.workspace?.profile.full_name || "Student")
          .split(" ")
          .map((n) => n[0])
          .slice(0, 2)
          .join("")
      : "AM";
  const path = usePathname();
  const [notifications, setNotifications] = useState(false);
  const current =
    navigation.find((n) => path === n.href || path.startsWith(n.href + "/"))
      ?.label ??
    (path === "/profile"
      ? "Student profile"
      : path === "/onboarding"
        ? "Onboarding"
        : "Settings");
  return (
    <header className="topbar">
      <div className="row">
        <button
          className="icon-button mobile-only"
          onClick={open}
          aria-label="Open navigation"
        >
          <Menu />
        </button>
        <span className="breadcrumb">
          Workspace <span>/</span> <strong>{current}</strong>
        </span>
      </div>
      <div className="row topbar-actions">
        <Link
          href="/universities"
          className="top-search"
          aria-label="Search universities"
        >
          <Search size={16} />
          <span>Explore your possibilities</span>
        </Link>
        <ThemeToggle />
        <div className="notification-wrapper">
          <button
            className="icon-button"
            aria-label="Notifications"
            aria-expanded={notifications}
            onClick={() => setNotifications(!notifications)}
          >
            <Bell size={19} />
          </button>
          {notifications && (
            <div className="notification-popover panel">
              <strong>You’re all caught up</strong>
              <p>This demo has no live notifications.</p>
            </div>
          )}
        </div>
        <Link
          href="/profile"
          className="avatar small"
          aria-label="Open profile"
        >
          {initials}
        </Link>
      </div>
    </header>
  );
}
export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    sidebarRef.current
      ?.querySelector<HTMLButtonElement>(
        'button[aria-label="Close navigation"]',
      )
      ?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previousFocus?.focus();
    };
  }, [open]);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {open && (
        <button
          className="drawer-overlay"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        ref={sidebarRef}
        className={"sidebar " + (open ? "open" : "")}
        aria-label="Workspace sidebar"
      >
        <Sidebar close={() => setOpen(false)} />
      </aside>
      <div className="app-main" inert={open ? true : undefined}>
        <Topbar open={() => setOpen(true)} />
        <main id="main-content" className="workspace-main">
          <AccountStrip />
          <DemoNotice />
          {children}
          <footer className="workspace-footer">
            <span>Thoughtful decisions. Global possibilities.</span>
            <span>Atlas · Phase 3 development</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
