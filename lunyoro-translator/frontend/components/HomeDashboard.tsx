"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Tab = "home" | "translate" | "chat" | "editor";

interface HistoryEntry {
  input: string;
  translation: string | null;
  direction?: string;
  timestamp: string;
}

export default function HomeDashboard({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/history`)
      .then(r => r.json())
      .then(d => setHistory((d.history || []).slice(0, 3)))
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-screen-xl mx-auto px-5 pb-32">
      {/* Hero Section */}
      <section className="pt-6 pb-8">
        <div className="relative overflow-hidden rounded-2xl bg-surface-container-lowest p-6 premium-shadow border border-outline-variant/30">
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary-fixed text-on-primary-fixed rounded-full text-xs font-semibold mb-4">
              <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>security</span>
              100% OFFLINE ENCRYPTION
            </span>
            <h1 className="text-3xl font-bold text-on-background mb-2 leading-tight">
              Uncompromised Power, <br /><span className="text-primary">Fully Offline.</span>
            </h1>
            <p className="text-base text-on-surface-variant max-w-[80%] mb-6">
              Premium AI processing for global professionals. No cloud. No limits. Just performance.
            </p>
            <button
              onClick={() => onNavigate("translate")}
              className="bg-primary text-on-primary px-6 py-3 rounded-xl text-xs font-semibold flex items-center gap-2 active:scale-95 transition-all shadow-md"
            >
              START NEW PROJECT
              <span className="material-symbols-outlined">arrow_forward</span>
            </button>
          </div>
          <div className="absolute -right-12 -top-12 w-48 h-48 bg-primary-container/20 rounded-full blur-3xl" />
          <div className="absolute -right-4 bottom-0 opacity-10">
            <span className="material-symbols-outlined text-[120px] text-primary" style={{ fontVariationSettings: "'wght' 200" }}>memory</span>
          </div>
        </div>
      </section>

      {/* Bento Grid */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-on-background mb-6">Primary Tools</h2>
        <div className="grid grid-cols-2 gap-4">
          {/* Translator - Large */}
          <div
            onClick={() => onNavigate("translate")}
            className="col-span-2 glass-card rounded-2xl p-5 flex flex-col gap-3 hover:border-primary transition-colors cursor-pointer group premium-shadow"
          >
            <div className="w-12 h-12 rounded-xl bg-secondary-container flex items-center justify-center text-on-secondary-container group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[28px]">g_translate</span>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-on-background">Translator</h3>
              <p className="text-sm text-on-surface-variant">Instant neural translation across 64 languages without internet.</p>
            </div>
          </div>

          {/* Word Editor */}
          <div
            onClick={() => onNavigate("editor")}
            className="glass-card rounded-2xl p-4 flex flex-col gap-2 hover:border-primary transition-colors cursor-pointer group premium-shadow"
          >
            <div className="w-10 h-10 rounded-xl bg-surface-container-highest flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[24px]">edit_note</span>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-on-background">Word Editor</h4>
              <p className="text-[10px] text-on-surface-variant leading-tight">Advanced syntax &amp; grammar refining.</p>
            </div>
          </div>

          {/* AI Chatbot */}
          <div
            onClick={() => onNavigate("chat")}
            className="glass-card rounded-2xl p-4 flex flex-col gap-2 hover:border-primary transition-colors cursor-pointer group premium-shadow"
          >
            <div className="w-10 h-10 rounded-xl bg-primary-container/20 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[24px]">chat_bubble</span>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-on-background">AI Chatbot</h4>
              <p className="text-[10px] text-on-surface-variant leading-tight">Conversational intelligence on-device.</p>
            </div>
          </div>

          {/* Document & Audio */}
          <div
            onClick={() => onNavigate("editor")}
            className="col-span-2 glass-card rounded-2xl p-4 flex items-center gap-4 hover:border-primary transition-colors cursor-pointer group premium-shadow"
          >
            <div className="w-12 h-12 rounded-xl bg-tertiary-container/30 flex items-center justify-center text-tertiary group-hover:scale-110 transition-transform flex-shrink-0">
              <span className="material-symbols-outlined text-[28px]">description</span>
            </div>
            <div className="flex-grow">
              <h4 className="text-xs font-semibold text-on-background">Document &amp; Audio</h4>
              <p className="text-[11px] text-on-surface-variant">Batch process large files and voice recordings locally.</p>
            </div>
            <span className="material-symbols-outlined text-outline">chevron_right</span>
          </div>

          {/* Dictionary */}
          <div
            onClick={() => onNavigate("editor")}
            className="col-span-2 glass-card rounded-2xl p-4 flex items-center gap-4 hover:border-primary transition-colors cursor-pointer group premium-shadow"
          >
            <div className="w-12 h-12 rounded-xl bg-secondary-fixed flex items-center justify-center text-on-secondary-fixed group-hover:scale-110 transition-transform flex-shrink-0">
              <span className="material-symbols-outlined text-[28px]">menu_book</span>
            </div>
            <div className="flex-grow">
              <h4 className="text-xs font-semibold text-on-background">Dictionary</h4>
              <p className="text-[11px] text-on-surface-variant">Offline etymology and comprehensive definitions.</p>
            </div>
            <span className="material-symbols-outlined text-outline">chevron_right</span>
          </div>
        </div>
      </section>

      {/* System Status */}
      <section className="mb-8">
        <div className="bg-surface-container-low rounded-2xl p-4 border border-outline-variant/50">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-semibold text-on-surface tracking-wide">SYSTEM STATUS</h3>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[11px] font-medium text-on-surface-variant">Optimized</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-on-surface-variant">
              <span className="text-sm">Neural Engine</span>
              <span className="text-xs font-semibold">Ready</span>
            </div>
            <div className="flex items-center justify-between text-on-surface-variant">
              <span className="text-sm">Local Models</span>
              <span className="text-xs font-semibold">64 Installed</span>
            </div>
          </div>
        </div>
      </section>

      {/* Recent Activity */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-on-background">Recent Activity</h3>
          <button
            onClick={() => onNavigate("translate")}
            className="text-xs font-semibold text-secondary flex items-center gap-1"
          >
            VIEW ALL <span className="material-symbols-outlined text-[16px]">chevron_right</span>
          </button>
        </div>

        <div className="bg-surface-container-lowest rounded-xl premium-shadow overflow-hidden border border-outline-variant/30">
          {history.length === 0 ? (
            <div className="p-5 text-center text-on-surface-variant text-sm">
              No recent activity yet. Start translating!
            </div>
          ) : (
            history.map((entry, i) => (
              <div
                key={i}
                onClick={() => onNavigate("translate")}
                className={`p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors cursor-pointer group ${
                  i < history.length - 1 ? "border-b border-outline-variant/30" : ""
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 bg-surface-container-high rounded-lg flex items-center justify-center">
                    <span className="material-symbols-outlined text-secondary">translate</span>
                  </div>
                  <div>
                    <p className="font-semibold text-on-surface text-sm truncate max-w-[200px]">{entry.input}</p>
                    <p className="text-xs text-on-surface-variant">
                      {entry.direction || "en->lun"} &bull; {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">chevron_right</span>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
