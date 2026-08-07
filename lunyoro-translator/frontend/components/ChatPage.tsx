"use client";
import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ChatItem = { role: "user" | "assistant"; content: string; reply_marian?: string | null; reply_nllb?: string | null };

const QUICK_CHIPS = ["Greetings", "Directions", "Food", "Emergency", "Numbers"];

export default function ChatPage() {
  const [msg, setMsg] = useState("");
  const [history, setHistory] = useState<ChatItem[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [history, loading]);

  async function send(text?: string) {
    const t = text ?? msg;
    if (!t.trim() || loading) return;
    const next: ChatItem[] = [...history, { role: "user", content: t }];
    setHistory(next); setMsg(""); setLoading(true);
    if (inputRef.current) inputRef.current.style.height = "40px";
    try {
      const r = await fetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: t, history }),
      });
      if (r.status === 429) { setHistory([...next, { role: "assistant", content: "Too fast — wait a moment." }]); return; }
      const d = await r.json();
      setHistory([...next, { role: "assistant", content: d.reply || "No response.", reply_marian: d.reply_marian, reply_nllb: d.reply_nllb }]);
    } catch { setHistory([...next, { role: "assistant", content: "Chat unavailable." }]); }
    finally { setLoading(false); }
  }

  function speak(text: string) {
    const u = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(u);
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
  }

  return (
    <div className="max-w-screen-xl mx-auto flex flex-col" style={{ height: "calc(100vh - 160px)" }}>

      {/* Scrollable messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pt-4 pb-2 space-y-4">

        {/* Welcome card — shown when no messages */}
        {history.length === 0 && (
          <div className="bg-surface-container-lowest border border-outline-variant/40 rounded-2xl p-6 text-center premium-shadow mb-4">
            <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-primary-fixed/50 flex items-center justify-center">
              <span className="material-symbols-outlined text-[28px] text-primary">translate</span>
            </div>
            <h3 className="text-lg font-bold text-on-background">AI Stick Translation</h3>
            <p className="text-sm text-on-surface-variant mt-1 max-w-[280px] mx-auto">
              Your local language assistant is ready. Speak or type to begin translating.
            </p>
          </div>
        )}

        {/* Date separator */}
        {history.length === 0 && (
          <div className="flex justify-center">
            <span className="text-xs text-on-surface-variant bg-surface-container px-3 py-1 rounded-full">Today</span>
          </div>
        )}

        {/* Messages */}
        {history.map((item, i) => (
          <div key={i} className={`flex items-end gap-2 ${item.role === "user" ? "justify-end" : "justify-start"}`}>
            {/* Bot avatar */}
            {item.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center flex-shrink-0 mb-6">
                <span className="material-symbols-outlined text-[16px] text-primary">translate</span>
              </div>
            )}

            <div className={`max-w-[75%] ${item.role === "user" ? "order-1" : ""}`}>
              {item.role === "user" ? (
                /* User bubble — gold/primary */
                <div className="bg-primary-container text-on-primary-container px-4 py-3 rounded-2xl rounded-br-sm text-sm shadow-sm">
                  {item.content}
                </div>
              ) : (
                /* Assistant bubble — white card */
                <div>
                  <div className="bg-surface-container-lowest border border-outline-variant/40 px-4 py-3 rounded-2xl rounded-bl-sm text-sm text-on-surface shadow-sm">
                    {item.content.split("\n").filter(Boolean).map((line, j) => (
                      <p key={j} className="leading-relaxed">{line}</p>
                    ))}
                  </div>
                  {/* Action icons below assistant bubble */}
                  <div className="flex gap-3 mt-1.5 ml-1">
                    <button onClick={() => speak(item.content)} className="text-on-surface-variant hover:text-primary transition-colors">
                      <span className="material-symbols-outlined text-[18px]">volume_up</span>
                    </button>
                    <button onClick={() => copy(item.content)} className="text-on-surface-variant hover:text-primary transition-colors">
                      <span className="material-symbols-outlined text-[18px]">content_copy</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* User avatar */}
            {item.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center flex-shrink-0 mb-1 order-2">
                <span className="material-symbols-outlined text-[16px] text-on-secondary-container">person</span>
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-end gap-2">
            <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] text-primary">translate</span>
            </div>
            <div className="bg-surface-container-lowest border border-outline-variant/40 px-4 py-3 rounded-2xl rounded-bl-sm shadow-sm">
              <div className="flex space-x-1">{[0,1,2].map(i => <div key={i} className="w-2 h-2 bg-primary-container rounded-full animate-bounce" style={{animationDelay:`${i*0.2}s`}} />)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Quick chips */}
      <div className="flex-shrink-0 px-4 py-2 flex gap-2 overflow-x-auto">
        {QUICK_CHIPS.map(chip => (
          <button key={chip} onClick={() => send(`How do I say "${chip.toLowerCase()}" phrases in Runyoro-Rutooro?`)}
            className="flex-shrink-0 px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded-full text-xs font-semibold text-on-surface-variant hover:border-primary hover:text-primary transition-all active:scale-95">
            {chip}
          </button>
        ))}
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 px-4 pb-4 pt-2">
        <div className="flex items-center gap-2 bg-surface-container-lowest border border-outline-variant/50 rounded-full px-4 py-2 premium-shadow">
          <textarea ref={inputRef} rows={1}
            className="flex-1 bg-transparent outline-none text-sm text-on-surface resize-none placeholder:text-outline/60 leading-5"
            style={{height: 24, maxHeight: 72}}
            placeholder="Type or speak to translate..."
            value={msg}
            onChange={e => { setMsg(e.target.value); e.target.style.height = "24px"; e.target.style.height = Math.min(e.target.scrollHeight, 72) + "px"; }}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }}} />
          <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors">
            <span className="material-symbols-outlined text-[20px]">mic</span>
          </button>
          <button onClick={() => send()} disabled={loading || !msg.trim()}
            className="w-10 h-10 rounded-full bg-primary text-on-primary flex items-center justify-center hover:opacity-90 disabled:opacity-40 transition-all active:scale-90 shadow-md">
            <span className="material-symbols-outlined text-[20px]">send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
