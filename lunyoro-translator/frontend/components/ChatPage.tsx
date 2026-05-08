"use client";
import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatMessage(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];
  const flushList = (key: string) => {
    if (!listItems.length) return;
    elements.push(<ul key={key} className="list-none space-y-1 my-1">{listItems.map((item, i) => (<li key={i} className="flex gap-2 items-start"><span className="mt-1 w-1.5 h-1.5 rounded-full bg-secondary shrink-0" /><span>{item}</span></li>))}</ul>);
    listItems = [];
  };
  lines.forEach((line, i) => {
    const t = line.trim();
    if (!t) { flushList(`l${i}`); elements.push(<div key={`b${i}`} className="h-1" />); return; }
    if (/^(\*|-|•|\d+\.)\s+/.test(t)) { listItems.push(t.replace(/^(\*|-|•|\d+\.)\s+/, "")); }
    else { flushList(`l${i}`); elements.push(<p key={`p${i}`} className="leading-relaxed">{t}</p>); }
  });
  flushList("end");
  return <div className="space-y-1 text-sm">{elements}</div>;
}

type ChatItem = { role: "user" | "assistant"; content: string; reply_marian?: string | null; reply_nllb?: string | null; };

const SECTORS = [
  { code: "ALL", label: "All Sectors",         icon: "🌐", prompt: "Give me a mix of Runyoro-Rutooro vocabulary across all topics." },
  { code: "DLY", label: "Daily Life",           icon: "🏠", prompt: "What are common Runyoro-Rutooro words used in everyday daily life?" },
  { code: "NAR", label: "Storytelling",         icon: "📖", prompt: "Tell me a short story or proverb in Runyoro-Rutooro." },
  { code: "SPR", label: "Spirituality",         icon: "🙏", prompt: "Tell me about spiritual and religious terms in Runyoro-Rutooro." },
  { code: "AGR", label: "Agriculture",          icon: "🌾", prompt: "What are common Runyoro-Rutooro words used in farming?" },
  { code: "EDU", label: "Education",            icon: "📚", prompt: "What are common Runyoro-Rutooro words used in education?" },
  { code: "CUL", label: "Culture & Traditions", icon: "🏛️", prompt: "Tell me about Runyoro-Rutooro culture and traditions." },
  { code: "HLT", label: "Health",               icon: "🏥", prompt: "What are Runyoro-Rutooro words related to health?" },
];

export default function ChatPage() {
  const [message, setMessage]           = useState("");
  const [history, setHistory]           = useState<ChatItem[]>([]);
  const [loading, setLoading]           = useState(false);
  const [sectorOpen, setSectorOpen]     = useState(false);
  const [selectedSector, setSelectedSector] = useState<typeof SECTORS[0] | null>(null);
  const [conversationMode, setConversationMode] = useState(false);
  const scrollRef  = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
    const userMsg: ChatItem = { role: "user", content: text };
    const newHistory = [...history, userMsg];
    setHistory(newHistory); setMessage(""); setLoading(true);
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
      setHistory([...newHistory, { role: "assistant", content: "Sorry, the chat assistant is unavailable right now. Please try again." }]);
    } finally { setLoading(false); }
  }

  return (
    <div className="max-w-screen-xl mx-auto w-full flex flex-col h-[calc(100vh-140px)] pb-20">
      {/* Language switcher */}
      <div className="flex justify-center py-md px-margin sticky top-0 z-40">
        <div className="bg-surface-container-highest/80 backdrop-blur-md p-xs rounded-full flex gap-xs shadow-sm">
          <button className="px-md py-xs rounded-full bg-secondary text-on-secondary text-label-sm font-semibold transition-all">English</button>
          <button className="px-md py-xs rounded-full hover:bg-surface-container-high text-on-surface-variant text-label-sm font-semibold transition-all">Runyoro-Rutooro</button>
        </div>
      </div>

      {/* Chat messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-margin py-md space-y-md">
        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 py-12">
            <div className="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center shadow-inner">
              <span className="text-4xl">💬</span>
            </div>
            <div className="space-y-2">
              <h3 className="font-bold text-gray-800 text-2xl">Oraire otya?</h3>
              <p className="text-gray-400 text-base leading-relaxed" style={{ maxWidth: "28rem" }}>I can help you translate, explain grammar, or chat about culture.</p>
            </div>
            <div className="flex flex-row flex-wrap justify-center gap-3">
              <button onClick={() => sendMessage("Explain the difference between Kwebembera and Kutandika.")} className="text-sm bg-white border border-blue-200 text-blue-600 px-5 py-2 rounded-full hover:bg-blue-50 transition-all shadow-sm font-medium">Grammar Help</button>
              <button onClick={() => setConversationMode(true)} className="text-sm bg-white border border-blue-200 text-blue-600 px-5 py-2 rounded-full hover:bg-blue-50 transition-all shadow-sm font-medium">Conversation</button>
              <div className="relative" ref={dropdownRef}>
                <button onClick={() => setSectorOpen(o => !o)} className="text-sm bg-white border border-blue-200 text-blue-600 px-5 py-2 rounded-full hover:bg-blue-50 transition-all shadow-sm font-medium flex items-center gap-1">
                  {selectedSector ? `${selectedSector.icon} ${selectedSector.label}` : "🏛️ Culture & Sectors"} <span className="text-xs">▾</span>
                </button>
                {sectorOpen && (
                  <div className="absolute left-0 top-full mt-xs w-56 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-lg z-50 overflow-hidden">
                    {SECTORS.map(s => (
                      <button key={s.code} onClick={() => { setSelectedSector(s); setSectorOpen(false); }} className="w-full text-left px-md py-sm text-sm text-on-surface hover:bg-surface-container-low flex items-center gap-sm transition-colors">
                        <span>{s.icon}</span><span>{s.label}</span>
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
                <div className="max-w-[85%] bg-primary text-on-primary px-md py-sm rounded-xl rounded-tr-none shadow-sm text-body-md">
                  {item.content}
                </div>
              ) : (item.reply_marian || item.reply_nllb) ? (
                <div className="flex gap-sm w-full max-w-[95%]">
                  <div className="flex-1 flex flex-col gap-xs">
                    <span className="text-label-sm text-primary font-semibold px-xs">MarianMT</span>
                    <div className="bg-surface-container-lowest border border-primary-container px-md py-sm rounded-xl rounded-tl-none shadow-sm text-body-md text-on-surface">
                      {item.reply_marian ? formatMessage(item.reply_marian) : "—"}
                    </div>
                  </div>
                  <div className="flex-1 flex flex-col gap-xs">
                    <span className="text-label-sm text-secondary font-semibold px-xs">NLLB-200</span>
                    <div className="bg-surface-container-lowest border border-secondary-container px-md py-sm rounded-xl rounded-tl-none shadow-sm text-body-md text-on-surface">
                      {item.reply_nllb ? formatMessage(item.reply_nllb) : "—"}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="max-w-[85%] bg-surface-container-lowest border border-outline-variant px-md py-sm rounded-xl rounded-tl-none shadow-sm text-body-md text-on-surface">
                  {formatMessage(item.content)}
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-container-lowest border border-outline-variant px-md py-sm rounded-xl rounded-tl-none">
              <div className="flex space-x-1">
                {[0,1,2].map(i => <div key={i} className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce" style={{ animationDelay: `${i*0.15}s` }} />)}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="fixed bottom-16 left-0 w-full z-40 px-margin pb-sm">
        {conversationMode && (
          <div className="flex items-center gap-sm text-xs text-secondary bg-secondary-container/30 border border-secondary-container rounded-lg px-md py-xs mb-xs">
            <span>💬</span><span>Conversation mode — type in Runyoro-Rutooro</span>
            <button onClick={() => setConversationMode(false)} className="ml-auto text-secondary hover:text-on-secondary-container">✕</button>
          </div>
        )}
        {selectedSector && (
          <div className="flex items-center gap-sm text-xs text-primary bg-primary-fixed/30 border border-primary-container rounded-lg px-md py-xs mb-xs">
            <span>{selectedSector.icon}</span><span>Sector: <strong>{selectedSector.label}</strong></span>
            <button onClick={() => setSelectedSector(null)} className="ml-auto">✕</button>
          </div>
        )}
        <div className="bg-surface-container-lowest rounded-xl shadow-[0_-8px_24px_rgba(7,2,53,0.08)] border border-outline-variant p-sm flex items-end gap-sm">
          <div className="flex-grow">
            <textarea
              className="w-full bg-surface-container-low border-none rounded-lg py-sm px-md text-on-surface text-body-md focus:ring-2 focus:ring-secondary resize-none outline-none"
              placeholder={conversationMode ? "Ngamba omu Runyoro-Rutooro..." : "Type or speak a message..."}
              rows={1}
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage())}
            />
          </div>
          <div className="flex gap-xs">
            <button className="p-sm bg-secondary-container text-on-secondary-container rounded-lg hover:bg-secondary-fixed transition-all active:scale-90">
              <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>mic</span>
            </button>
            <button onClick={() => sendMessage()} disabled={loading || !message.trim()} className="p-sm bg-primary text-on-primary rounded-lg hover:opacity-90 transition-all active:scale-90 disabled:opacity-50">
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
