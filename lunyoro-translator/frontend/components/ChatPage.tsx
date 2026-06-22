"use client";
import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatMessage(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];
  const flushList = (key: string) => {
    if (!listItems.length) return;
    elements.push(
      <ul key={key} className="list-none space-y-1 my-1">
        {listItems.map((item, i) => (
          <li key={i} className="flex gap-2 items-start">
            <span className="mt-1.5 w-1 h-1 rounded-full bg-primary-container flex-shrink-0 mt-2" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
    listItems = [];
  };
  lines.forEach((line, i) => {
    const t = line.trim();
    if (!t) { flushList(`l${i}`); return; }
    if (/^(\*|-|•|\d+\.)\s+/.test(t)) listItems.push(t.replace(/^(\*|-|•|\d+\.)\s+/, ""));
    else { flushList(`l${i}`); elements.push(<p key={`p${i}`} className="leading-relaxed">{t}</p>); }
  });
  flushList("end");
  return <div className="space-y-1 text-sm">{elements}</div>;
}

type ChatItem = {
  role: "user" | "assistant";
  content: string;
  reply_marian?: string | null;
  reply_nllb?: string | null;
};

const QUICK_PROMPTS = [
  { icon: "school",    label: "Grammar",      text: "Explain the R/L rule in Runyoro-Rutooro with examples." },
  { icon: "chat",      label: "Conversation", text: "Oraire otya? Nkubuuza Runyoro." },
  { icon: "museum",    label: "Culture",      text: "Tell me about a Runyoro-Rutooro proverb and its meaning." },
  { icon: "translate", label: "Vocabulary",   text: "Give me 10 common everyday Runyoro-Rutooro words." },
];

export default function ChatPage() {
  const [message, setMessage]         = useState("");
  const [history, setHistory]         = useState<ChatItem[]>([]);
  const [loading, setLoading]         = useState(false);
  const [inputHeight, setInputHeight] = useState(44);
  const scrollRef  = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, loading]);

  async function sendMessage(overrideText?: string) {
    const text = overrideText ?? message;
    if (!text.trim() || loading) return;
    const newHistory: ChatItem[] = [...history, { role: "user", content: text }];
    setHistory(newHistory);
    setMessage("");
    setInputHeight(44);
    if (textareaRef.current) textareaRef.current.style.height = "44px";
    setLoading(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      if (res.status === 429) {
        setHistory([...newHistory, { role: "assistant", content: "Too many requests — please wait a moment." }]);
        return;
      }
      const data = await res.json();
      setHistory([...newHistory, {
        role: "assistant",
        content: data.reply || "No response.",
        reply_marian: data.reply_marian,
        reply_nllb: data.reply_nllb,
      }]);
    } catch {
      setHistory([...newHistory, { role: "assistant", content: "Chat unavailable right now." }]);
    } finally {
      setLoading(false);
    }
  }

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setMessage(e.target.value);
    e.target.style.height = "44px";
    const newH = Math.min(e.target.scrollHeight, 120);
    e.target.style.height = newH + "px";
    setInputHeight(newH);
  }

  // Height of input bar = textarea + padding (24px top+bottom) + optional chips (28px)
  const inputBarHeight = inputHeight + 48;

  return (
    // Full height is managed by the parent relative container in page.tsx
    <div className="flex flex-col h-full relative">

      {/* ── Messages area ── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
        style={{ paddingBottom: inputHeight + 64 }}
      >
        {history.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-4">
            <div className="w-16 h-16 rounded-full bg-primary-fixed/40 flex items-center justify-center">
              <span className="material-symbols-outlined text-[32px] text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}>chat_bubble</span>
            </div>
            <div>
              <p className="text-xl font-bold text-on-background">Oraire otya?</p>
              <p className="text-sm text-on-surface-variant mt-1 max-w-[280px] mx-auto leading-relaxed">
                Ask about grammar, proverbs, vocabulary, or just chat in Runyoro-Rutooro.
              </p>
            </div>
            {/* Quick prompt chips */}
            <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
              {QUICK_PROMPTS.map(p => (
                <button key={p.label} onClick={() => sendMessage(p.text)}
                  className="flex items-center gap-2 px-3 py-2.5 bg-surface-container-lowest border border-outline-variant rounded-xl text-left text-xs font-semibold text-on-surface-variant hover:border-primary hover:text-primary transition-all premium-shadow active:scale-95">
                  <span className="material-symbols-outlined text-[16px] text-primary flex-shrink-0">{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          history.map((item, i) => (
            <div key={i} className={`flex ${item.role === "user" ? "justify-end" : "justify-start"}`}>
              {item.role === "user" ? (
                /* User bubble */
                <div className="max-w-[78%] bg-primary text-on-primary px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed shadow-sm">
                  {item.content}
                </div>
              ) : (item.reply_marian || item.reply_nllb) ? (
                /* Dual model response */
                <div className="w-full max-w-[95%] space-y-2">
                  {item.reply_marian && (
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-bold text-primary uppercase tracking-widest ml-1">MarianMT</span>
                      <div className="bg-surface-container-lowest border border-primary-container/40 px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm text-on-surface shadow-sm">
                        {formatMessage(item.reply_marian)}
                      </div>
                    </div>
                  )}
                  {item.reply_nllb && (
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-bold text-secondary uppercase tracking-widest ml-1">NLLB-200</span>
                      <div className="bg-surface-container-lowest border border-secondary-container/40 px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm text-on-surface shadow-sm">
                        {formatMessage(item.reply_nllb)}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Single assistant bubble */
                <div className="max-w-[85%] bg-surface-container-lowest border border-outline-variant/40 px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm text-on-surface shadow-sm">
                  {formatMessage(item.content)}
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading dots */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-container-lowest border border-outline-variant/40 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm">
              <div className="flex space-x-1">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 bg-primary-container rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Input bar — absolute within the relative chat container, sits above BottomNav ── */}
      <div className="absolute bottom-0 left-0 right-0 px-4 pb-3 pt-2 bg-background/95 backdrop-blur-md border-t border-outline-variant/30">
        <div className="flex items-end gap-2 bg-surface-container-lowest border border-outline-variant/50 rounded-2xl px-3 py-2 premium-shadow max-w-screen-xl mx-auto">
          <textarea
            ref={textareaRef}
            rows={1}
            className="flex-1 bg-transparent outline-none text-sm text-on-surface resize-none placeholder:text-outline/60 py-1.5 leading-5"
            style={{ height: inputHeight, maxHeight: 120 }}
            placeholder="Ask about Runyoro-Rutooro..."
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
            }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !message.trim()}
            className="w-9 h-9 rounded-xl bg-primary text-on-primary flex items-center justify-center hover:opacity-90 disabled:opacity-40 transition-all active:scale-90 flex-shrink-0 mb-0.5"
          >
            <span className="material-symbols-outlined text-[18px]">send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
