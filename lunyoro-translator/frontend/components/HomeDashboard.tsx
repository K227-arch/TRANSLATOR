"use client";
import { useEffect, useState } from "react";
import type { Tab } from "@/app/page";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface HistoryEntry { input: string; translation: string | null; direction?: string; timestamp: string; }

export default function HomeDashboard({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/history`).then(r => r.json())
      .then(d => setHistory((d.history || []).slice(0, 3))).catch(() => {});
  }, []);

  const tools: { id: Tab; icon: string; title: string; desc: string; span?: boolean; accent: string }[] = [
    { id: "translate",  icon: "g_translate",  title: "Translator",  desc: "English ↔ Runyoro-Rutooro",     span: true,  accent: "text-primary" },
    { id: "editor",     icon: "edit_note",    title: "Word Editor", desc: "Write & refine in Runyoro",                  accent: "text-secondary" },
    { id: "chat",       icon: "chat_bubble",  title: "AI Chat",     desc: "Grammar & culture assistant",                accent: "text-tertiary" },
    { id: "voice",      icon: "mic",          title: "Voice",       desc: "Speak and translate",           span: true,  accent: "text-primary" },
    { id: "camera",     icon: "photo_camera", title: "Lens",        desc: "Point camera & translate",      span: true,  accent: "text-secondary" },
    { id: "dictionary", icon: "menu_book",    title: "Dictionary",  desc: "Word roots and definitions",    span: true,  accent: "text-tertiary" },
    { id: "history",    icon: "history",      title: "History",     desc: "Recent translations",           span: true,  accent: "text-on-surface-variant" },
  ];

  return (
    <div className="max-w-screen-xl mx-auto px-5 pb-32">

      {/* Hero */}
      <section className="pt-8 pb-6">
        <div className="relative overflow-hidden rounded-3xl border border-primary/20 premium-shadow p-7"
          style={{ background: "linear-gradient(135deg, #1a1200 0%, #0e0e0e 60%, #1a0d00 100%)" }}>

          {/* Top badge */}
          <div className="flex items-center gap-2 mb-5">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase"
              style={{ background: "rgba(233,195,73,0.12)", color: "#e9c349", border: "1px solid rgba(233,195,73,0.25)" }}>
              <span className="material-symbols-outlined text-[13px]" style={{ fontVariationSettings: "'FILL' 1" }}>security</span>
              100% OFFLINE CAPABLE
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl font-black text-on-background mb-1 leading-none tracking-tight">
            Uncompromised
          </h1>
          <h1 className="text-4xl font-black leading-none tracking-tight mb-4" style={{ color: "#e9c349" }}>
            Translation.
          </h1>
          <p className="text-sm text-on-surface-variant mb-7 max-w-[75%] leading-relaxed">
            Premium AI for the Runyoro-Rutooro language. No cloud required.
          </p>

          <button
            onClick={() => onNavigate("translate")}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold tracking-wide uppercase active:scale-95 transition-all animate-gold-pulse"
            style={{ background: "#e9c349", color: "#1a1200" }}
          >
            START TRANSLATING
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>

          {/* Decorative icon */}
          <div className="absolute -right-8 -top-8 opacity-5">
            <span className="material-symbols-outlined text-[180px] text-primary animate-float"
              style={{ fontVariationSettings: "'wght' 100" }}>g_translate</span>
          </div>

          {/* Stat pills */}
          <div className="flex gap-2 mt-6 flex-wrap">
            {[
              { label: "2 AI Models", icon: "smart_toy" },
              { label: "NLLB-200", icon: "language" },
              { label: "MarianMT", icon: "translate" },
            ].map(s => (
              <span key={s.label}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold text-on-surface-variant"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
                <span className="material-symbols-outlined text-[13px] text-primary">{s.icon}</span>
                {s.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Tools grid */}
      <section className="mb-8">
        <h2 className="text-base font-bold text-on-surface-variant uppercase tracking-widest mb-4">Tools</h2>
        <div className="grid grid-cols-2 gap-3 stagger-children">
          {tools.map(({ id, icon, title, desc, span, accent }) => (
            <div
              key={id}
              onClick={() => onNavigate(id)}
              className={`glass-card rounded-2xl p-4 flex flex-col gap-3 cursor-pointer group active:scale-95 transition-all animate-fade-in-up hover:border-primary/30 premium-shadow ${span ? "col-span-2 flex-row items-center" : ""}`}
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform ${accent}`}
                style={{ background: "rgba(255,255,255,0.06)" }}>
                <span className="material-symbols-outlined text-[22px]">{icon}</span>
              </div>
              <div className="flex-grow min-w-0">
                <h3 className="font-bold text-on-background text-sm">{title}</h3>
                <p className="text-xs text-on-surface-variant leading-tight mt-0.5 truncate">{desc}</p>
              </div>
              {span && (
                <span className="material-symbols-outlined text-on-surface-variant/40 flex-shrink-0 group-hover:text-primary transition-colors">
                  chevron_right
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Recent */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-base font-bold text-on-surface-variant uppercase tracking-widest">Recent</h2>
          <button
            onClick={() => onNavigate("history")}
            className="text-xs font-bold text-primary flex items-center gap-0.5 hover:opacity-80 transition-opacity"
          >
            VIEW ALL <span className="material-symbols-outlined text-[15px]">chevron_right</span>
          </button>
        </div>
        <div className="rounded-2xl overflow-hidden border border-outline-variant/30 premium-shadow"
          style={{ background: "#121212" }}>
          {history.length === 0 ? (
            <div className="p-8 text-center text-on-surface-variant text-sm">
              No recent activity. Start translating!
            </div>
          ) : history.map((entry, i) => (
            <div
              key={i}
              onClick={() => onNavigate("translate")}
              className={`p-4 flex items-center justify-between cursor-pointer group hover:bg-surface-container transition-colors ${i < history.length - 1 ? "border-b border-outline-variant/20" : ""}`}
            >
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: "rgba(233,195,73,0.1)" }}>
                  <span className="material-symbols-outlined text-primary text-[18px]">translate</span>
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-on-surface text-sm truncate max-w-[200px]">{entry.input}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    {entry.direction || "en→lun"} · {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">chevron_right</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
