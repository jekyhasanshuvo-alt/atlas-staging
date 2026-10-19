"use client";
import { AccountSettings } from "@/features/auth/account-settings";
import { dataMode } from "@/services/config";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  ShieldCheck,
  Globe2,
  Monitor,
  Trash2,
} from "lucide-react";
import { Checklist, PageHeader } from "@/components/shared";
import { ThemeToggle } from "@/components/layout/app-shell";
import { lifeTasks, careerTasks } from "@/data/mock";
export function Resources({ kind }: { kind: "life" | "career" }) {
  const isLife = kind === "life";
  return (
    <>
      <PageHeader
        eyebrow={
          isLife ? "FEEL AT HOME, A LITTLE SOONER" : "BUILD WHAT COMES NEXT"
        }
        title={
          isLife
            ? "A new place. Your next chapter."
            : "A world of future possibilities."
        }
        description={
          isLife
            ? "A practical starting point for life beyond the classroom."
            : "Connect your education with the skills and experiences you want to build."
        }
      />
      <div className="resource-hero">
        <Globe2 size={42} />
        <div>
          <h2>
            {isLife
              ? "Arrive with a little more confidence."
              : "Your career starts before graduation."}
          </h2>
          <p>
            {isLife
              ? "Use this sample checklist to organize research and conversations with your institution."
              : "Explore roles, grow your skills, and build a portfolio one step at a time."}
          </p>
        </div>
      </div>
      <div className="two-column section-gap">
        <section className="panel">
          <div className="section-heading">
            <h2>
              {isLife
                ? "Pre-departure & arrival checklist"
                : "Career preparation checklist"}
            </h2>
            <span className="tag">Sample guide</span>
          </div>
          <Checklist
            tasks={isLife ? lifeTasks : careerTasks}
            storageKey={isLife ? "life-checklist" : "career-checklist"}
          />
        </section>
        <div>
          <section className="panel">
            <span className="icon-box teal">
              <ShieldCheck size={22} />
            </span>
            <h2>
              {isLife
                ? "Research before you arrive"
                : "Explore with reliable information"}
            </h2>
            <p>
              {isLife
                ? "Housing, insurance, banking, and mobile services vary by city and provider. Confirm terms, fees, and requirements directly before committing."
                : "Internship access, employment eligibility, and post-graduation pathways depend on your circumstances and current rules. Verify information with official authorities and qualified advisers."}
            </p>
            <p>
              These are general sample planning prompts. No visa, immigration,
              or work authorization eligibility has been assessed.
            </p>
          </section>
          <section className="panel section-gap">
            <h2>
              {isLife
                ? "Keep your research together"
                : "Turn interests into a plan"}
            </h2>
            <p>
              {isLife
                ? "Update your study preferences, shortlist locations, and set a budget for your move."
                : "Use your profile to record career goals and identify skills you want to develop."}
            </p>
            <Link href="/profile" className="text-link">
              Update your goals <ArrowUpRight size={16} />
            </Link>
          </section>
        </div>
      </div>
    </>
  );
}
export function Settings(){return dataMode === "api" ? <AccountSettings/> : <DemoSettings/>;}
function DemoSettings() {
  const [cleared, setCleared] = useState(false);
  const [confirm, setConfirm] = useState(false);
  function clear() {
    [
      "saved-universities",
      "saved-scholarships",
      "comparison",
      "student-profile",
      "financial-plan",
      "financial-scenario",
      "preparation",
      "life-checklist",
      "career-checklist",
      "new-user",
    ].forEach((k) => localStorage.removeItem(k));
    window.dispatchEvent(new Event("storage"));
    setCleared(true);
    setConfirm(false);
  }
  return (
    <>
      <PageHeader
        title="Make yourself at home"
        eyebrow="WORKSPACE SETTINGS"
        description="A few simple controls for your demo experience."
      />
      <div className="settings-stack">
        <section className="panel settings-row">
          <div className="row">
            <span className="icon-box">
              <Monitor />
            </span>
            <div>
              <h2>Appearance</h2>
              <p>Switch between light and dark mode.</p>
            </div>
          </div>
          <ThemeToggle />
        </section>
        <section className="panel">
          <div className="row">
            <span className="icon-box teal">
              <ShieldCheck />
            </span>
            <div>
              <h2>Your data stays on this browser</h2>
              <p>
                This development workspace has no account server, connected AI,
                or cloud synchronization.
              </p>
            </div>
          </div>
          <div className="settings-row section-gap">
            <div>
              <h3>Reset demo workspace</h3>
              <p>
                Remove saved universities, scholarships, comparisons,
                checklists, budget scenarios, and profile preferences.
              </p>
            </div>
            <button className="button danger" onClick={() => setConfirm(true)}>
              <Trash2 size={16} />
              Reset demo data
            </button>
          </div>
          {confirm && (
            <div className="info-note" role="alert">
              <p>Reset all locally saved demo planning data?</p>
              <div className="row">
                <button className="button danger" onClick={clear}>
                  Yes, reset demo data
                </button>
                <button className="button" onClick={() => setConfirm(false)}>
                  Cancel
                </button>
              </div>
            </div>
          )}
          {cleared && (
            <p className="success-state" role="status">
              Your demo workspace has been reset.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
