"use client";
import { useEffect, useRef, useState } from "react";
import { Sparkles, Plus, ArrowUp, BookOpen, MessageSquare } from "lucide-react";
import { PageHeader, Spinner, ErrorState } from "@/components/shared";
type Message = { id: number; role: "user" | "assistant"; text: string };
const suggestions = [
  "How should I build my university shortlist?",
  "What should I include in a study budget?",
  "How can I research scholarships?",
];
const demoReply =
  "This is a scripted interface preview, not an AI-generated answer. Start by recording your preferences in Profile, compare sample university options, and use Financial Twin to explore costs. Verify admissions, fees, funding, and requirements directly with official sources.";
export function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [simulateError, setSimulateError] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [messages, loading]);
  function send(text: string) {
    if (!text.trim() || loading) return;
    setDraft("");
    setError("");
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", text: text.trim() },
    ]);
    setLoading(true);
    timer.current = setTimeout(() => {
      setLoading(false);
      if (simulateError) {
        setError(
          "Demo error preview: the example message could not be displayed. Turn off the error preview and try again.",
        );
        return;
      }
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: "assistant", text: demoReply },
      ]);
    }, 800);
  }
  function reset() {
    if (timer.current) clearTimeout(timer.current);
    setLoading(false);
    setMessages([]);
    setError("");
  }
  return (
    <>
      <PageHeader
        title="A little guidance. A clearer path."
        eyebrow="AI STUDY ASSISTANT · INTERFACE DEMO"
        description="Explore the conversation experience. No AI service is connected."
      />
      <div className="assistant-layout panel">
        <aside className="chat-history">
          <button className="button full" onClick={reset}>
            <Plus size={17} />
            New demo conversation
          </button>
          <span className="eyebrow">CONVERSATIONS</span>
          <p>
            <MessageSquare size={17} /> Your conversations will appear here.
          </p>
          <small>
            History is a placeholder. Messages stay in memory for this visit.
          </small>
          <label className="check-inline error-preview">
            <input
              type="checkbox"
              checked={simulateError}
              onChange={(e) => setSimulateError(e.target.checked)}
            />
            Preview error state
          </label>
        </aside>
        <section className="chat-main" aria-label="Demo conversation">
          <div className="chat-messages" role="log" aria-live="polite">
            {messages.length === 0 ? (
              <div className="chat-welcome">
                <span className="assistant-symbol">
                  <Sparkles size={30} />
                </span>
                <span className="eyebrow">THINK BIG. START HERE.</span>
                <h2>What’s on your mind?</h2>
                <p>
                  Your study journey has a lot of moving parts.
                  <br />
                  This demo shows how a future assistant could help.
                </p>
                <div className="suggestions">
                  {suggestions.map((s) => (
                    <button key={s} onClick={() => send(s)}>
                      {s}
                      <ArrowUp size={15} />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <div className={"message " + m.role} key={m.id}>
                  <span className="message-avatar">
                    {m.role === "assistant" ? <Sparkles size={17} /> : "You"}
                  </span>
                  <div>
                    {m.role === "assistant" && (
                      <span className="eyebrow">SCRIPTED DEMO RESPONSE</span>
                    )}
                    <p>{m.text}</p>
                    {m.role === "assistant" && (
                      <details className="source-placeholder">
                        <summary>
                          <BookOpen size={14} />
                          Sources · placeholder
                        </summary>
                        <p>
                          No sources retrieved. A future connected assistant
                          will show verifiable references here.
                        </p>
                      </details>
                    )}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="message assistant" role="status">
                <Spinner />
                <span>Preparing scripted preview…</span>
              </div>
            )}
            {error && <ErrorState message={error} />}
            <div ref={end} />
          </div>
          <form
            className="chat-composer"
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
            }}
          >
            <label className="sr-only" htmlFor="chat-input">
              Your demo message
            </label>
            <textarea
              id="chat-input"
              maxLength={2000}
              placeholder="Ask about your study journey…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(draft);
                }
              }}
            />
            <button
              className="button primary"
              disabled={loading || !draft.trim()}
              aria-label="Send demo message"
            >
              <ArrowUp size={20} />
            </button>
          </form>
          <small className="chat-disclaimer">
            Demo only · Scripted responses · No admissions, financial, or
            immigration advice
          </small>
        </section>
      </div>
    </>
  );
}
