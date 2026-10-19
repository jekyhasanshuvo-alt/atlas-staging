import { offlineDemo } from "@/services/config";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  GraduationCap,
  Award,
  Wallet,
  Sparkles,
  Compass,
  BriefcaseBusiness,
  ShieldCheck,
  Check,
  Globe2,
} from "lucide-react";
const features = [
  {
    icon: GraduationCap,
    title: "University discovery",
    description:
      "Look beyond the brochure. Explore programs, compare cities, and build a shortlist that feels like you.",
    href: "/universities",
    label: "Find your fit",
  },
  {
    icon: Award,
    title: "Scholarship intelligence",
    description:
      "Bring funding into the picture early. Explore sample opportunities and organize your research.",
    href: "/scholarships",
    label: "Explore funding",
  },
  {
    icon: Wallet,
    title: "Your Financial Twin",
    description:
      "See the whole picture, from tuition to everyday life. Adjust your assumptions and compare scenarios.",
    href: "/financial-twin",
    label: "Make a plan",
  },
  {
    icon: Sparkles,
    title: "AI study assistant",
    description:
      "Preview a calmer way to navigate your questions. A clearly labeled interface demo, ready for a future connection.",
    href: "/assistant",
    label: "Meet the demo",
  },
  {
    icon: Compass,
    title: "Life beyond the classroom",
    description:
      "Prepare for a new home with practical planning prompts for arrival, housing, and everyday essentials.",
    href: "/student-life",
    label: "Get prepared",
  },
  {
    icon: BriefcaseBusiness,
    title: "A future with direction",
    description:
      "Connect your academic interests with skills, experiences, and career questions worth exploring.",
    href: "/career",
    label: "Think ahead",
  },
];
const faqs = [
  {
    q: "What is Atlas?",
    a: "Atlas is a student intelligence workspace for researching study options, comparing sample university data, and exploring financial plans. The development catalog can be served by a PostgreSQL-backed API or an explicit offline demo adapter.",
  },
  {
    q: "Is the university and scholarship information verified?",
    a: "No. This demo uses real university names with illustrative program details, costs, and funding indicators. Scholarship entries are sample categories. Confirm all details with official institutions and awarding bodies.",
  },
  {
    q: "Does the assistant use a live AI model?",
    a: "No. The assistant is an interface preview with explicitly labeled scripted messages. No AI API is connected.",
  },
  {
    q: "Where are my preferences saved?",
    a: "With a verified account, your profile, saved universities and scholarships, comparisons, financial plans, and checklists sync across devices. Existing browser preferences can be reviewed and imported from Settings. Offline demo mode keeps its data in your browser.",
  },
  {
    q: "Can I explore destinations beyond China?",
    a: "The initial sample collection focuses on China. The data models include country fields so that additional destinations can be introduced later.",
  },
];
export default function Landing() {
  if (offlineDemo) return <main className="panel section-gap"><span className="eyebrow">ATLAS AI · FICTIONAL HACKATHON DEMO</span><h1>Explore your study planning possibilities</h1><p>Try deterministic financial calculations with hypothetical inputs. Catalogs are intentionally empty. No accounts, email delivery, database, external AI or personal data collection.</p><p>All demo inputs stay in page memory and reset on reload. Do not enter real student information.</p><nav aria-label="Demo navigation"><Link className="button primary" href="/dashboard">Open demo workspace</Link><Link className="button" href="/financial-twin">Try Financial Twin</Link><Link className="button" href="/universities">Empty university catalog</Link><Link className="button" href="/scholarships">Empty scholarship catalog</Link></nav></main>;
  return (
    <>
      <section className="landing-hero">
        <div className="hero-copy">
          <span className="hero-pill">
            <span className="status-dot" />
            BIG AMBITIONS. THOUGHTFUL DECISIONS.
          </span>
          <h1>
            Your Intelligent Companion for <em>Studying Abroad</em>
          </h1>
          <p>
            Discover universities, explore scholarships, understand the true
            cost of studying abroad, and plan your international education
            journey with confidence.
          </p>
          <div className="hero-actions">
            <Link className="button primary large" href="/profile">
              Build My Study Plan <ArrowRight size={18} />
            </Link>
            <Link className="button large" href="/universities">
              Explore Universities <ArrowUpRight size={18} />
            </Link>
          </div>
          <div className="hero-footnote">
            <ShieldCheck size={16} />
            Designed for clarity. Built around your future.
          </div>
        </div>
        <div className="hero-visual">
          <div className="hero-orbit" />
          <div className="hero-orbit inner" />
          <div className="hero-coordinate">
            30° 16′ N &nbsp; 120° 09′ E<br />
            <span>A WORLD OF POSSIBILITIES</span>
          </div>
          <div className="hero-globe">
            <Globe2 strokeWidth={0.6} />
          </div>
          <div className="hero-note">
            <span className="icon-box teal">
              <Compass size={25} />
            </span>
            <div>
              <small>YOUR NEXT CHAPTER</small>
              <strong>Closer than you think.</strong>
            </div>
            <span>✦</span>
          </div>
          <div className="destination-card">
            <div className="destination-art">
              <div className="campus-building">
                <i />
                <i />
                <i />
                <i />
                <i />
              </div>
              <span>EXPLORE A NEW PERSPECTIVE</span>
            </div>
            <div>
              <span className="eyebrow">FIRST DESTINATION COLLECTION</span>
              <h3>
                Start your journey in China <ArrowUpRight size={17} />
              </h3>
              <p>Sample universities. Endless curiosity.</p>
            </div>
          </div>
          <span className="hero-visual-star">✦</span>
        </div>
      </section>
      <div className="promise-strip">
        <span>YOUR FUTURE DESERVES A CLEARER PICTURE</span>
        <div>
          <Check size={15} />
          Compare with perspective
        </div>
        <div>
          <Check size={15} />
          Plan with confidence
        </div>
        <div>
          <Check size={15} />
          Keep your goals in sight
        </div>
      </div>
      <section className="marketing-section" id="possibilities">
        <div className="marketing-heading">
          <div>
            <span className="eyebrow">LESS GUESSWORK. MORE POSSIBILITY.</span>
            <h2>
              One big decision.
              <br />A little intelligence at every step.
            </h2>
          </div>
          <p>
            From the first “what if” to a plan you can build on.
            <br />
            Bring the moving parts of studying abroad together.
          </p>
        </div>
        <div className="feature-grid">
          {features.map(
            ({ icon: Icon, title, description, href, label }, i) => (
              <article className="feature-card" key={title}>
                <div className={"icon-box " + (i % 2 ? "teal" : "")}>
                  <Icon size={25} />
                </div>
                <span className="feature-number">0{i + 1}</span>
                <h3>{title}</h3>
                <p>{description}</p>
                <Link className="text-link" href={href}>
                  {label} <ArrowRight size={16} />
                </Link>
              </article>
            ),
          )}
        </div>
      </section>
      <section className="preview-section">
        <div>
          <span className="eyebrow">A CALMER WAY TO PLAN</span>
          <h2>
            Your ambitions,
            <br />
            with a little more structure.
          </h2>
          <p>
            A single workspace for the questions, numbers, and next steps that
            shape your study journey.
          </p>
          <Link href="/dashboard" className="button primary">
            Take a look around <ArrowUpRight size={17} />
          </Link>
        </div>
        <div className="product-preview">
          <div className="preview-top">
            <span className="preview-dots">● ● ●</span>
            <span>atlas. / your workspace</span>
            <span>DEMO</span>
          </div>
          <div className="preview-content">
            <span className="eyebrow">YOUR JOURNEY, IN FOCUS</span>
            <h3>A world of possibilities, Alex.</h3>
            <div className="preview-banner">
              <div>
                <small>YOUR STUDY PLAN</small>
                <strong>Next stop: China.</strong>
                <span>Discover. Compare. Prepare.</span>
              </div>
              <Globe2 size={78} strokeWidth={0.7} />
            </div>
            <div className="preview-stats">
              <div>
                <GraduationCap size={18} />
                <strong>Your shortlist</strong>
                <small>Places to call your own</small>
              </div>
              <div>
                <Wallet size={18} />
                <strong>Your budget</strong>
                <small>See the bigger picture</small>
              </div>
            </div>
            <div className="preview-check">
              <span>
                <Check size={14} />
              </span>
              Find a direction that feels right
              <ArrowRight size={16} />
            </div>
          </div>
        </div>
      </section>
      <section className="marketing-section" id="how-it-works">
        <span className="eyebrow">SMALL STEPS. BIG HORIZONS.</span>
        <h2>A path from “what if” to “what’s next”.</h2>
        <div className="how-grid">
          {[
            {
              title: "Tell us your direction",
              text: "Set your destination, academic interests, and budget preferences.",
            },
            {
              title: "Explore the possibilities",
              text: "Discover universities and funding categories. Compare the details that matter.",
            },
            {
              title: "Build a thoughtful plan",
              text: "Map your costs, organize preparation tasks, and keep your goals in view.",
            },
          ].map((s, i) => (
            <div key={s.title}>
              <span className="step-number">0{i + 1}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="trust-section" id="our-approach">
        <span className="icon-box teal">
          <ShieldCheck size={28} />
        </span>
        <div>
          <span className="eyebrow">CLARITY INCLUDES KNOWING THE LIMITS</span>
          <h2>Good decisions need honest information.</h2>
          <p>
            This development workspace uses clearly labeled sample data.
            Financial figures are estimates, scholarship eligibility is
            unverified, and the assistant is an interface demo. We believe you
            should always know where information comes from—and what still needs
            checking.
          </p>
          <div className="trust-tags">
            <span>
              <Check size={15} />
              Visible assumptions
            </span>
            <span>
              <Check size={15} />
              No invented success stories
            </span>
            <span>
              <Check size={15} />
              Your data stays local
            </span>
          </div>
        </div>
      </section>
      <section className="faq-section">
        <div>
          <span className="eyebrow">A FEW THINGS TO KNOW</span>
          <h2>Questions, meet clarity.</h2>
          <p>A thoughtful start means knowing what to expect.</p>
        </div>
        <div>
          {faqs.map((f) => (
            <details key={f.q}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </section>
      <section className="final-cta">
        <span className="eyebrow">YOUR WORLD, WITHIN REACH</span>
        <h2>
          Every great journey
          <br />
          starts with a little clarity.
        </h2>
        <Link className="button white large" href="/profile">
          Build My Study Plan <ArrowRight size={18} />
        </Link>
        <p>A demo workspace. A real place to start thinking.</p>
      </section>
    </>
  );
}
