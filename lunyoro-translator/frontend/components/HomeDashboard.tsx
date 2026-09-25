"use client";
import { useEffect, useState } from "react";
import { useTheme } from "@/components/ThemeProvider";
import type { Tab } from "@/app/page";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SystemInfo {
  marian_en2lun: boolean;
  marian_lun2en: boolean;
  nllb_en2lun: boolean;
  nllb_lun2en: boolean;
  gpu_available: boolean;
}

interface HistoryEntry {
  input: string;
  translation: string | null;
  direction?: string;
  timestamp: string;
}

const TOOLS: { id: Tab; icon: string; title: string; desc: string }[] = [
  { id: "translate",  icon: "g_translate",  title: "Translator",      desc: "Instant neural translation — English ↔ Runyoro-Rutooro." },
  { id: "editor",     icon: "edit_note",    title: "Word Editor",     desc: "Advanced syntax & grammar refining in Runyoro." },
  { id: "chat",       icon: "chat_bubble",  title: "AI Chatbot",      desc: "Conversational grammar and culture assistant." },
  { id: "camera",     icon: "description",  title: "Document & Audio","desc": "Batch process documents and voice recordings." },
  { id: "dictionary", icon: "menu_book",    title: "Dictionary",      desc: "Offline etymology and comprehensive definitions." },
];

export default function HomeDashboard({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const { theme } = useTheme();
  const isLight = theme === "light";

  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/system-info`)
      .then(r => r.json())
      .then(d => setSysInfo(d))
      .catch(() => {});
    fetch(`${API}/history`)
      .then(r => r.json())
      .then(d => setHistory((d.history || []).slice(0, 3)))
      .catch(() => {});
  }, []);

  const nllbReady   = sysInfo ? (sysInfo.nllb_en2lun && sysInfo.nllb_lun2en) : null;
  const marianReady = sysInfo ? (sysInfo.marian_en2lun && sysInfo.marian_lun2en) : null;
  const gpuReady    = sysInfo ? sysInfo.gpu_available : null;

  // ── Colour tokens resolved for the two themes ──────────────────────
  const heroBg        = isLight
    ? "linear-gradient(135deg, #fffbe6 0%, #fff9f0 60%, #fffbea 100%)"
    : "linear-gradient(135deg, #1a1200 0%, #0e0e0e 60%, #1a0d00 100%)";
  const heroBorder    = isLight ? "rgba(154,124,0,0.25)" : "rgba(233,195,73,0.20)";
  const badgeBg       = isLight ? "rgba(154,124,0,0.10)" : "rgba(233,195,73,0.12)";
  const badgeColor    = isLight ? "#7a5e00" : "#e9c349";
  const badgeBorder   = isLight ? "rgba(154,124,0,0.30)" : "rgba(233,195,73,0.25)";
  const ctaBg         = isLight ? "#9a7c00" : "#e9c349";
  const ctaColor      = isLight ? "#ffffff" : "#1a1200";
  const statPillBg    = isLight ? "rgba(0,0,0,0.04)" : "rgba(255,255,255,0.05)";
  const statPillBdr   = isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
  const toolCardBg    = isLight ? "#ffffff"           : "rgba(255,255,255,0.04)";
  const toolCardBdr   = isLight ? "rgba(0,0,0,0.07)"  : "rgba(233,195,73,0.10)";
  const toolIconBg    = isLight ? "rgba(154,124,0,0.08)" : "rgba(255,255,255,0.06)";
  const recentBg      = isLight ? "#ffffff"           : "#121212";
  const recentBdr     = isLight ? "rgba(0,0,0,0.07)"  : "rgba(255,255,255,0.07)";
  const statusCardBg  = isLight ? "#f4f3ef"           : "rgba(255,255,255,0.03)";
  const statusCardBdr = isLight ? "rgba(0,0,0,0.07)"  : "rgba(255,255,255,0.07)";

  // ── Status pills helper ────────────────────────────────────────────
  type StatusState = "ok" | "warn" | "off" | "loading";
  const statusStyle: Record<StatusState, { bg: string; color: string; dot: string }> = {
    ok:      { bg: isLight ? "rgba(0,120,60,0.08)"  : "rgba(0,200,80,0.10)",  color: isLight ? "#006630" : "#4cde88",  dot: isLight ? "#006630" : "#4cde88" },
    warn:    { bg: isLight ? "rgba(200,120,0,0.10)" : "rgba(233,195,73,0.12)", color: isLight ? "#7a5e00" : "#e9c349",  dot: isLight ? "#7a5e00" : "#e9c349" },
    off:     { bg: isLight ? "rgba(180,0,0,0.08)"   : "rgba(255,100,80,0.10)", color: isLight ? "#900"    : "#ff8070",  dot: isLight ? "#900"    : "#ff8070" },
    loading: { bg: isLight ? "rgba(0,0,0,0.05)"     : "rgba(255,255,255,0.05)", color: isLight ? "#888"   : "#888",    dot: isLight ? "#bbb"    : "#555" },
  };

  function pillState(ready: boolean | null): StatusState {
    if (ready === null) return "loading";
    return ready ? "ok" : "off";
  }

  function StatusPill({ label, state }: { label: string; state: StatusState }) {
    const s = statusStyle[state];
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
        style={{ background: s.bg, color: s.color, border: `1px solid ${s.dot}30` }}>
        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: s.dot }} />
        {label}
      </span>
    );
  }

  return (
    <div className="max-w-screen-xl mx-auto px-5 pb-32">

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="pt-8 pb-6">
        <div
          className="relative overflow-hidden rounded-3xl p-7 premium-shadow"
          style={{ background: heroBg, border: `1px solid ${heroBorder}` }}
        >
          {/* Security badge */}
          <div className="flex items-center gap-2 mb-5">
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase"
              style={{ background: badgeBg, color: badgeColor, border: `1px solid ${badgeBorder}` }}
            >
              <span className="material-symbols-outlined text-[13px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                security
              </span>
              100% OFFLINE ENCRYPTION
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-3xl sm:text-4xl font-black leading-tight tracking-tight mb-1"
            style={{ color: isLight ? "#1a1a1a" : "#f0ede6" }}>
            Uncompromised Power,
          </h1>
          <h1 className="text-3xl sm:text-4xl font-black leading-tight tracking-tight mb-4"
            style={{ color: badgeColor }}>
            Fully Offline.
          </h1>
          <p className="text-sm mb-7 max-w-[78%] leading-relaxed"
            style={{ color: isLight ? "#5a5348" : "#a89e88" }}>
            Premium AI processing for global professionals. No cloud. No limits. Just performance.
          </p>

          {/* CTA */}
          <button
            onClick={() => onNavigate("translate")}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold tracking-wide uppercase active:scale-95 transition-transform"
            style={{ background: ctaBg, color: ctaColor }}
          >
            START TRANSLATING
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>

          {/* Stat pills */}
          <div className="flex gap-2 mt-6 flex-wrap">
            {[
              { label: "2 AI Models", icon: "smart_toy" },
              { label: "NLLB-200",   icon: "language" },
              { label: "MarianMT",   icon: "translate" },
            ].map(s => (
              <span key={s.label}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold"
                style={{ background: statPillBg, border: `1px solid ${statPillBdr}`,
                         color: isLight ? "#5a5348" : "#a89e88" }}>
                <span className="material-symbols-outlined text-[13px]"
                  style={{ color: badgeColor }}>{s.icon}</span>
                {s.label}
              </span>
            ))}
          </div>

          {/* Decorative chip icon */}
          <div className="absolute -right-6 top-1/2 -translate-y-1/2 pointer-events-none"
            style={{ opacity: isLight ? 0.06 : 0.04 }}>
            <span className="material-symbols-outlined text-[200px]"
              style={{ color: badgeColor, fontVariationSettings: "'wght' 100" }}>
              memory
            </span>
          </div>
        </div>
      </section>

      {/* ── Primary Tools ─────────────────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="text-xs font-bold tracking-widest uppercase mb-4"
          style={{ color: isLight ? "#a09880" : "#a89e88" }}>
          Primary Tools
        </h2>

        <div className="rounded-2xl overflow-hidden premium-shadow stagger-children"
          style={{ border: `1px solid ${toolCardBdr}` }}>
          {TOOLS.map(({ id, icon, title, desc }, idx) => (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className="w-full flex items-center gap-4 px-5 py-4 text-left group active:scale-[0.99] transition-all"
              style={{
                background: toolCardBg,
                borderBottom: idx < TOOLS.length - 1 ? `1px solid ${toolCardBdr}` : "none",
              }}
            >
              {/* Icon */}
              <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110"
                style={{ background: toolIconBg }}>
                <span className="material-symbols-outlined text-[22px]"
                  style={{ color: badgeColor }}>
                  {icon}
                </span>
              </div>

              {/* Text */}
              <div className="flex-grow min-w-0">
                <p className="font-bold text-sm" style={{ color: isLight ? "#1a1a1a" : "#f0ede6" }}>
                  {title}
                </p>
                <p className="text-xs mt-0.5 truncate" style={{ color: isLight ? "#5a5348" : "#a89e88" }}>
                  {desc}
                </p>
              </div>

              {/* Arrow */}
              <span className="material-symbols-outlined flex-shrink-0 transition-colors group-hover:translate-x-0.5 transition-transform"
                style={{ color: isLight ? "#c0b898" : "#5a5240" }}>
                chevron_right
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* ── System Status ─────────────────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="text-xs font-bold tracking-widest uppercase mb-4"
          style={{ color: isLight ? "#a09880" : "#a89e88" }}>
          System Status
        </h2>
        <div className="rounded-2xl p-5 premium-shadow"
          style={{ background: statusCardBg, border: `1px solid ${statusCardBdr}` }}>
          <div className="flex flex-wrap gap-2.5">
            <StatusPill
              label={gpuReady === null ? "Checking GPU…" : gpuReady ? "GPU Accelerated" : "CPU Mode"}
              state={gpuReady === null ? "loading" : gpuReady ? "ok" : "warn"}
            />
            <StatusPill
              label={
                nllbReady === null ? "Neural Engine…"
                : nllbReady ? "Neural Engine Ready"
                : marianReady ? "Translation Engine Ready"
                : "Neural Engine Offline"
              }
              state={
                nllbReady === null ? "loading"
                : nllbReady ? "ok"
                : marianReady ? "warn"
                : "off"
              }
            />
            <StatusPill
              label={marianReady === null ? "Local Models…" : marianReady ? "Local Models Installed" : "Models Missing"}
              state={pillState(marianReady)}
            />
          </div>
        </div>
      </section>

      {/* ── Recent Translations ────────────────────────────────────────── */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xs font-bold tracking-widest uppercase"
            style={{ color: isLight ? "#a09880" : "#a89e88" }}>
            Recent
          </h2>
          <button
            onClick={() => onNavigate("history")}
            className="text-xs font-bold flex items-center gap-0.5 hover:opacity-70 transition-opacity"
            style={{ color: badgeColor }}
          >
            VIEW ALL
            <span className="material-symbols-outlined text-[15px]">chevron_right</span>
          </button>
        </div>

        <div className="rounded-2xl overflow-hidden premium-shadow"
          style={{ background: recentBg, border: `1px solid ${recentBdr}` }}>
          {history.length === 0 ? (
            <div className="p-8 flex flex-col items-center gap-3">
              <span className="material-symbols-outlined text-[40px]"
                style={{ color: isLight ? "#d4cfbf" : "#302c22" }}>
                history
              </span>
              <p className="text-sm" style={{ color: isLight ? "#a09880" : "#a89e88" }}>
                No recent activity. Start translating!
              </p>
            </div>
          ) : history.map((entry, i) => (
            <div
              key={i}
              onClick={() => onNavigate("translate")}
              className="px-4 py-3.5 flex items-center justify-between cursor-pointer group"
              style={{
                borderBottom: i < history.length - 1 ? `1px solid ${recentBdr}` : "none",
              }}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: isLight ? "rgba(154,124,0,0.08)" : "rgba(233,195,73,0.10)" }}>
                  <span className="material-symbols-outlined text-[18px]"
                    style={{ color: badgeColor }}>
                    translate
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-sm truncate max-w-[200px]"
                    style={{ color: isLight ? "#1a1a1a" : "#f0ede6" }}>
                    {entry.input}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: isLight ? "#a09880" : "#a89e88" }}>
                    {entry.direction || "en→lun"} ·{" "}
                    {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
              <span className="material-symbols-outlined flex-shrink-0 group-hover:translate-x-0.5 transition-transform"
                style={{ color: isLight ? "#c0b898" : "#5a5240" }}>
                chevron_right
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
