"use client";
import { CloudDashboard } from "@/features/auth/cloud-dashboard";
import { dataMode } from "@/services/config";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  Award,
  Wallet,
  ListChecks,
  Compass,
  Check,
  GraduationCap,
  Sparkles,
  Circle,
} from "lucide-react";
import {
  PageHeader,
  StatCard,
  UniversityCard,
  Checklist,
  EmptyState,
  money,
} from "@/components/shared";
import { demoRepository } from "@/services/repository";
import { isStringList, usePersistentState } from "@/hooks/use-persistent-state";
import { defaultPlan, student, studyPlan } from "@/data/mock";
import { calculateBudget } from "@/lib/calculations/finance";
import { profileSchema } from "@/lib/validation/profile";
import type { Student, FinancialPlan } from "@/types";
import { isFinancialPlan } from "@/lib/validation/financial-plan";
export function Dashboard(){return dataMode === "api" ? <CloudDashboard/> : <DemoDashboard/>;}
function DemoDashboard() {
  const [financialPlan] = usePersistentState<FinancialPlan>(
    "financial-plan",
    defaultPlan,
    isFinancialPlan,
  );
  const universities = demoRepository.getUniversities();
  const [saved] = usePersistentState<string[]>(
    "saved-universities",
    [],
    isStringList,
  );
  const [awards] = usePersistentState<string[]>(
    "saved-scholarships",
    [],
    isStringList,
  );
  const [checked] = usePersistentState<string[]>(
    "preparation",
    [],
    isStringList,
  );
  const [profile] = usePersistentState<Student>(
    "student-profile",
    student,
    (v): v is Student => profileSchema.safeParse(v).success,
  );
  const [newUser, setNewUser] = usePersistentState<boolean>(
    "new-user",
    false,
    (v): v is boolean => typeof v === "boolean",
  );
  const completion =
    Object.values(profile).filter(
      (value) => typeof value === "boolean" || Boolean(value),
    ).length / Object.keys(profile).length;
  return (
    <>
      <PageHeader
        eyebrow="YOUR NEXT CHAPTER STARTS HERE"
        title={"Welcome back, " + profile.fullName.split(" ")[0] + " 👋"}
        description="A little clarity today. A world of possibilities tomorrow."
        action={
          <Link className="button" href="/profile">
            Edit study preferences <ArrowUpRight size={16} />
          </Link>
        }
      />
      <section className="journey-banner">
        <div className="journey-content">
          <span className="banner-kicker">
            <span className="status-dot" /> YOUR STUDY PLAN · SAMPLE
          </span>
          <h2>
            From ambition to
            <br />
            your next destination.
          </h2>
          <p>
            {profile.destination} <span>·</span>{" "}
            {profile.education === "Bachelor"
              ? "Master’s study"
              : profile.education + " study"}{" "}
            in {profile.subject}
            <br />
            <small>Planning for {studyPlan.intake} · Demo intake</small>
          </p>
          <Link className="button white" href="/universities">
            Continue my study plan <ArrowRight size={16} />
          </Link>
        </div>
        <div className="journey-illustration" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="globe-art">
            <span>北</span>
            <i />
            <b />
          </div>
          <div className="floating-tag destination">
            <span>CN</span>
            <div>
              <small>YOUR DESTINATION</small>
              <strong>{profile.destination}</strong>
            </div>
            <Compass size={20} />
          </div>
          <div className="floating-tag ambition">
            <GraduationCap size={22} />
            <span>A new perspective awaits.</span>
          </div>
          <span className="spark spark-one">✦</span>
          <span className="spark spark-two">✦</span>
        </div>
      </section>
      <div className="section-caption">
        <span>YOUR JOURNEY AT A GLANCE</span>
        <label className="subtle-toggle">
          <input
            type="checkbox"
            checked={newUser}
            onChange={(e) => setNewUser(e.target.checked)}
          />
          Preview new student state
        </label>
      </div>
      <div className="stats-grid">
        <StatCard
          label="Saved universities"
          value={newUser ? 0 : saved.length}
          detail="Your future, thoughtfully shortlisted"
          icon={<Bookmark size={19} />}
        />
        <StatCard
          label="Saved scholarships"
          value={newUser ? 0 : awards.length}
          detail="Funding worth exploring"
          icon={<Award size={19} />}
        />
        <StatCard
          label="Estimated study budget"
          value={money(
            calculateBudget(financialPlan).adjusted,
            financialPlan.currency,
          )}
          detail="Full degree · illustrative estimate"
          icon={<Wallet size={19} />}
        />
        <StatCard
          label="Upcoming tasks"
          value={studyPlan.tasks.filter((t) => !checked.includes(t.id)).length}
          detail="Small steps toward a big move"
          icon={<ListChecks size={19} />}
        />
      </div>
      <div className="dashboard-columns">
        <div>
          <section className="panel plan-overview">
            <div className="section-heading">
              <div>
                <span className="eyebrow">ONE STEP AT A TIME</span>
                <h2>Your study plan</h2>
              </div>
              <span className="tag">In progress</span>
            </div>
            <div className="plan-steps">
              {["Discover", "Shortlist", "Prepare", "Apply"].map((step, i) => (
                <div key={step} className={i === 0 ? "current" : ""}>
                  <span>{i === 0 ? <Compass size={18} /> : i + 1}</span>
                  <strong>{step}</strong>
                  <small>
                    {
                      [
                        "Find your fit",
                        "Explore your options",
                        "Get everything ready",
                        "Make your move",
                      ][i]
                    }
                  </small>
                </div>
              ))}
            </div>
            <div className="plan-nudge">
              <div className="icon-box">
                <Sparkles size={19} />
              </div>
              <p>
                <strong>Your next best step</strong>
                <br />
                Compare universities to understand what matters to you.
              </p>
              <Link href="/compare" aria-label="Compare universities">
                <ArrowRight size={20} />
              </Link>
            </div>
          </section>
          <section className="dashboard-section">
            <div className="section-heading">
              <div>
                <h2>Universities to explore</h2>
                <p>
                  Sample options for your {profile.destination} study journey
                </p>
              </div>
              <Link className="text-link" href="/universities">
                View all <ArrowRight size={15} />
              </Link>
            </div>
            {newUser ? (
              <div className="panel">
                <EmptyState
                  title="Your shortlist starts here"
                  description="Explore the sample university catalog and save the places that interest you."
                  href="/universities"
                />
              </div>
            ) : (
              <div className="university-grid two">
                {universities.slice(0, 2).map((u) => (
                  <UniversityCard key={u.id} university={u} compact />
                ))}
              </div>
            )}
          </section>
          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Application preparation</h2>
                <p>Build a little momentum every day.</p>
              </div>
              <span className="muted small-text">
                {studyPlan.tasks.filter((t) => checked.includes(t.id)).length} /{" "}
                {studyPlan.tasks.length}
              </span>
            </div>
            <Checklist tasks={studyPlan.tasks} />
          </section>
        </div>
        <div>
          <section className="panel profile-progress">
            <div className="section-heading">
              <h2>A plan that feels like you</h2>
              <span className="icon-box">
                <Compass size={18} />
              </span>
            </div>
            <p>Your preferences help you explore with a clearer direction.</p>
            <div className="row spread">
              <strong>Profile completeness</strong>
              <span>{Math.round(completion * 100)}%</span>
            </div>
            <progress
              aria-label="Profile completeness"
              max={100}
              value={completion * 100}
            />
            <Link className="text-link" href="/profile">
              Review my profile <ArrowRight size={15} />
            </Link>
          </section>
          <section className="panel funding-panel">
            <span className="eyebrow">MAKE ROOM FOR POSSIBILITY</span>
            <h2>A little help goes a long way.</h2>
            <p>Discover sample funding pathways to support your study plan.</p>
            {demoRepository
              .getScholarships()
              .slice(0, 2)
              .map((s) => (
                <Link className="funding-row" href="/scholarships" key={s.id}>
                  <span className="icon-box teal">
                    <Award size={19} />
                  </span>
                  <div>
                    <strong>{s.name}</strong>
                    <small>{s.funding} funding · Sample</small>
                  </div>
                  <ArrowUpRight size={16} />
                </Link>
              ))}
            <Link className="text-link" href="/scholarships">
              Explore scholarships <ArrowRight size={15} />
            </Link>
          </section>
          <section className="panel financial-mini">
            <div className="section-heading">
              <h2>Financial snapshot</h2>
              <Wallet size={18} />
            </div>
            <p>A clearer picture of the road ahead.</p>
            <strong className="big-number">
              {money(
                calculateBudget(financialPlan).monthly,
                financialPlan.currency,
              )}
              <small> / month</small>
            </strong>
            <div
              className="budget-bar"
              role="img"
              aria-label="Monthly living expense distribution"
            >
              <i style={{ flex: financialPlan.accommodation }} />
              <i style={{ flex: financialPlan.food }} />
              <i
                style={{
                  flex: financialPlan.other + financialPlan.transportation,
                }}
              />
            </div>
            <div className="legend">
              <span>
                <i className="dot indigo" />
                Housing
              </span>
              <span>
                <i className="dot teal" />
                Food
              </span>
              <span>
                <i className="dot lavender" />
                Other
              </span>
            </div>
            <small className="muted">
              Sample plan · no currency conversion
            </small>
            <Link className="text-link" href="/financial-twin">
              Open Financial Twin <ArrowRight size={15} />
            </Link>
          </section>
          <section className="panel">
            <h2>Recent activity</h2>
            <div className="activity-item">
              <Circle size={10} />
              <div>
                <strong>Demo workspace ready</strong>
                <small>Explore your planning tools</small>
              </div>
            </div>
            <div className="activity-item">
              <Check size={13} />
              <div>
                <strong>{saved.length} universities saved locally</strong>
                <small>Only on this browser</small>
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
