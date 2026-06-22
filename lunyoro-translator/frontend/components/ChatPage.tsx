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
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-container flex-shrink-0" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
    listItems = [];
  };
  lines.forEach((line, i) => {
    const t = line.trim();
    if (!t) { flushList(`l${i}`); elements.push(<div key={`b${i}`} className="h-1" />); return; }
    if (/^(\*|-|•|\d+\.)\s+/.test(t)) listItems.push(t.replace(/^(\*|-|•|\d+\.)\s+/, ""));
    else { flushList(`l${i}`); elements.push(<p key={`p${i}`} className="leading-relaxed">{t}</p>); }
  });
  flushList("end");
  return <div className="space-y-1 text-sm">{elements}</div>;
}

type ChatItem = { role: "user" | "assistant"; content: string; reply_marian?: string | null; reply_nllb?: string | null };

const SECTORS = [
  { code: "ALL", label: "All Topics",     icon: "language",    prompt: "Give me a mix of Runyoro-Rutooro vocabulary." },
  { code: "DLY", label: "Daily Life",     icon: "home",        prompt: "What are common Runyoro-Rutooro words for daily life?" },
  { code: "NAR", label: "Storytelling",   icon: "auto_stories",prompt: "Tell me a short story or proverb in Runyoro-Rutooro." },
  { code: "SPR", label: "Spirituality",   icon: "self_improvement", prompt: "Tell me about spiritual terms in Runyoro-Rutooro." },
  { code: "AGR", label: "Agriculture",    icon: "grass",       prompt: "What are Runyoro-Rutooro words for farming?" },
  { code: "EDU", label: "Education",      icon: "school",      prompt: "What are Runyoro-Rutooro words for education?" },
  { code: "CUL", label: "Culture",        icon: "museum",      prompt: "Tell me about Runyoro-Rutooro culture and traditions." },
  { code: "HLT", label: "Health",         icon: "health_and_safety", prompt: "What are Runyoro-Rutooro words for health?" },
];

export default function ChatPage() {
  const [message, setMessage]           = useState("");
  const [history, setHistory]           = useState<ChatItem[]>([]);
  const [loading, setLoading]           = useState(false);
  const [selectedSector, setSelectedSector] = useState<typeof SECTORS[0] | null>(null);
  const [sectorOpen, setSectorOpen]     = useState(false);
  const [conversationMode, setConversationMode] = useState(false);
  const scrollRef   = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setSectorOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [history, loading]);

  async function sendMessage(overrideMessage?: string) {
    const text = overrideMessage || message;
    if (!text.trim() || loading) return;
    const newHistory = [...history, { role: "user" as const, content: text }];
    setHistory(newHistory); setMessage(""); setLoading(true);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history, sector: selectedSector?.code || null, conversation_mode: conversationMode }),
      });
      if (res.status === 429) {
        setHistory([...newHistory, { role: "assistant", content: "You're sending messages too fast. Please wait a moment." }]);
        return;
      }
      const data = await res.json();
      setHistory([...newHistory, { role: "assistant", content: data.reply || "No response.", reply_marian: data.reply_marian, reply_nllb: data.reply_nllb }]);
    } catch {
      setHistory([...newHistory, { role: "assistant", content: "Chat assistant unavailable. Please try again." }]);
    } finally { setLoading(false); }
  }

  function handleTextareaInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setMessage(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4 pb-4">
        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6 py-8">
            <div className="w-20 h-20 bg-primary-fixed/40 rounded-full flex items-center justify-center">
              <span className="material-symbols-outlined text-[40px] text-primary" style={{fontVariationSettings:"'FILL' 1"}}>chat_bubble</span>
            </div>
            <div>
              <h3 className="font-bold text-on-background text-xl">Oraire otya?</h3>
              <p className="text-on-surface-variant text-sm mt-1 max-w-xs mx-auto leading-relaxed">
                Ask about grammar, vocabulary, culture, or just chat in Runyoro-Rutooro.
              </p>
            </div>
            <div className="flex flex-row flex-wrap justify-center gap-2">
              <button onClick={() => sendMessage("Explain the difference between okugenda and okuija.")}
                className="text-sm bg-surface-container-lowest border border-outline-variant text-on-surface-variant px-4 py-2 rounded-full hover:border-primary hover:text-primary transition-all shadow-sm font-medium">
                Grammar Help
              </button>
              <button onClick={() => setConversationMode(true)}
                className="text-sm bg-surface-container-lowest border border-outline-variant text-on-surface-variant px-4 py-2 rounded-full hover:border-primary hover:text-primary transition-all shadow-sm font-medium">
                Conversation
              </button>
              <div className="relative" ref={dropdownRef}>
                <button onClick={() => setSectorOpen(o => !o)}
                  className="text-sm bg-surface-container-lowest border border-outline-variant text-on-surface-variant px-4 py-2 rounded-full hover:border-primary hover:text-primary transition-all shadow-sm font-medium flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">museum</span>
                  {selectedSector ? selectedSector.label : "Topics"}
                  <span className="material-symbols-outlined text-[14px]">expand_more</span>
                </button>
                {sectorOpen && (
                  <div className="absolute left-0 top-full mt-2 w-52 bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-xl z-50 overflow-hidden premium-shadow">
                    {SECTORS.map(s => (
                      <button key={s.code} onClick={() => { setSelectedSector(s); setSectorOpen(false); }}
                        className="w-full text-left px-4 py-2.5 text-sm text-on-surface hover:bg-surface-container-low flex items-center gap-3 transition-colors">
                        <span className="material-symbols-outlined text-[18px] text-primary">{s.icon}</span>
                        <span>{s.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          history.map((item, i) => (
            <div key={i} className={`flex ${item.role === "user" ? "justify-end" : "justify-start"}`}>
              {item.role === "user" ? (
                <div className="max-w-[85%] bg-primary text-on-primary px-4 py-2.5 rounded-2xl rounded-tr-sm shadow-sm text-sm leading-relaxed">
                  {item.content}
                </div>
              ) : (item.reply_marian || item.reply_nllb) ? (
                <div className="flex gap-3 w-full max-w-[95%]">
                  {item.reply_marian && (
                    <div className="flex-1 flex flex-col gap-1">
                      <span className="text-xs text-primary font-semibold px-1">MarianMT</span>
                      <div className="bg-surface-container-lowest border border-primary-container/50 px-4 py-2.5 rounded-2xl rounded-tl-sm shadow-sm text-sm text-on-surface">
                        {formatMessage(item.reply_marian)}
                      </div>
                    </div>
                  )}
                  {item.reply_nllb && (
                    <div className="flex-1 flex flex-col gap-1">
                      <span className="text-xs text-secondary font-semibold px-1">NLLB-200</span>
                      <div className="bg-surface-container-lowest border border-secondary-container/50 px-4 py-2.5 rounded-2xl rounded-tl-sm shadow-sm text-sm text-on-surface">
                        {formatMessage(item.reply_nllb)}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="max-w-[85%] bg-surface-container-lowest border border-outline-variant/40 px-4 py-2.5 rounded-2xl rounded-tl-sm shadow-sm text-sm text-on-surface">
                  {formatMessage(item.content)}
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-container-lowest border border-outline-variant/40 px-4 py-3 rounded-2xl rounded-tl-sm">
              <div className="flex space-x-1">{[0,1,2].map(i => <div key={i} className="w-1.5 h-1.5 bg-primary-container rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}} />)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Input bar — fixed at bottom above nav */}
      <div className="sticky bottom-20 left-0 w-full z-40 px-5 pb-3 pt-2 bg-background/80 backdrop-blur-md border-t border-outline-variant/30">
        {/* Context chips */}
        <div className="flex gap-2 mb-2 flex-wrap">
          {conversationMode && (
            <div className="flex items-center gap-1.5 text-xs text-secondary bg-secondary-container/40 border border-secondary-container rounded-full px-3 py-1">
              <span className="material-symbols-outlined text-[14px]">chat_bubble</span>
              <span>Runyoro mode</span>
              <button onClick={() => setConversationMode(false)} className="ml-1 text-secondary hover:text-on-secondary-container">
                <span className="material-symbols-outlined text-[14px]">close</span>
              </button>
            </div>
          )}
          {selectedSector && (
            <div className="flex items-center gap-1.5 text-xs text-primary bg-primary-fixed/40 border border-primary-container/50 rounded-full px-3 py-1">
              <span className="material-symbols-outlined text-[14px]">{selectedSector.icon}</span>
              <span>{selectedSector.label}</span>
              <button onClick={() => setSelectedSector(null)} className="ml-1">
                <span className="material-symbols-outlined text-[14px]">close</span>
              </button>
            </div>
          )}
        </div>

        <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/50 premium-shadow p-2 flex items-end gap-2">
          <textarea ref={textareaRef} rows={1}
            className="flex-grow bg-transparent outline-none text-on-surface text-sm px-2 py-1.5 resize-none placeholder:text-outline/60"
            placeholder={conversationMode ? "Ngamba omu Runyoro-Rutooro..." : "Ask about Runyoro-Rutooro..."}
            value={message} onChange={handleTextareaInput}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }}} />
          <div className="flex gap-1.5 flex-shrink-0">
            <button className="w-9 h-9 rounded-xl bg-surface-container text-on-surface-variant hover:bg-surface-container-high transition-colors flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">mic</span>
            </button>
            <button onClick={() => sendMessage()} disabled={loading || !message.trim()}
              className="w-9 h-9 rounded-xl bg-primary text-on-primary hover:opacity-90 disabled:opacity-40 transition-all active:scale-90 flex items-center justify-center">
              <span className="material-symbols-outlined text-[20px]">send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
