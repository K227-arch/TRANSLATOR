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

const CARDS = [
  { tab: "translate" as Tab, icon: "translate",   bg: "bg-secondary-container",  fg: "text-on-secondary-container", title: "Translate",    desc: "Quick English to Runyoro text conversion." },
  { tab: "chat"      as Tab, icon: "chat_bubble", bg: "bg-primary-container",    fg: "text-on-primary-container",   title: "AI Chat",      desc: "Conversational assistance & insights." },
  { tab: "editor"    as Tab, icon: "description", bg: "bg-secondary-fixed",      fg: "text-on-secondary-fixed-variant", title: "Editor",   desc: "Full document localization & layout." },
];

export default function HomeDashboard({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/history`)
      .then(r => r.json())
      .then(d => setHistory((d.history || []).slice(0, 3)))
      .catch(() => {});
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";

  return (
    <div className="max-w-screen-xl mx-auto px-margin py-lg pb-32">
      {/* Welcome */}
      <section className="mb-xl">
        <h2 className="text-h2 text-primary">{ greeting }, Linguist</h2>
        <p className="text-body-md text-on-surface-variant mt-xs">What would you like to build today?</p>
      </section>

      {/* Bento Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-md mb-xl">
        {CARDS.map(({ tab, icon, bg, fg, title, desc }) => (
          <div
            key={tab}
            onClick={() => onNavigate(tab)}
            className="bg-surface-container-lowest rounded-xl p-lg shadow-sm hover:shadow-md transition-all active:scale-95 cursor-pointer flex flex-col gap-md border border-outline-variant/10"
          >
            <div className={`${bg} ${fg} h-12 w-12 rounded-lg flex items-center justify-center`}>
              <span className="material-symbols-outlined text-2xl">{icon}</span>
            </div>
            <div>
              <h3 className="font-semibold text-[20px] text-primary">{title}</h3>
              <p className="text-body-md text-on-surface-variant text-[14px]">{desc}</p>
            </div>
            <div className="mt-auto flex justify-end">
              <span className="material-symbols-outlined text-secondary">arrow_forward</span>
            </div>
          </div>
        ))}
      </section>

      {/* AI Processing Bar */}
      <div className="w-full h-1 bg-surface-container rounded-full overflow-hidden mb-xl">
        <div className="h-full bg-secondary w-1/3 animate-pulse" />
      </div>

      {/* Recent Activity */}
      <section>
        <div className="flex justify-between items-center mb-md">
          <h3 className="text-h2 text-primary">Recent Activity</h3>
          <button
            onClick={() => onNavigate("translate")}
            className="text-secondary text-label-sm font-semibold flex items-center gap-xs"
          >
            VIEW ALL <span className="material-symbols-outlined text-[16px]">chevron_right</span>
          </button>
        </div>

        <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden border border-outline-variant/10">
          {history.length === 0 ? (
            <div className="p-lg text-center text-on-surface-variant text-body-md">
              No recent activity yet. Start translating!
            </div>
          ) : (
            history.map((entry, i) => (
              <div
                key={i}
                onClick={() => onNavigate("translate")}
                className={`p-md flex items-center justify-between hover:bg-surface-container-low transition-colors cursor-pointer group ${
                  i < history.length - 1 ? "border-b border-outline-variant/10" : ""
                }`}
              >
                <div className="flex items-center gap-md">
                  <div className="h-10 w-10 bg-surface-container-high rounded-lg flex items-center justify-center">
                    <span className="material-symbols-outlined text-secondary">translate</span>
                  </div>
                  <div>
                    <p className="font-semibold text-primary text-body-md truncate max-w-[200px]">{entry.input}</p>
                    <p className="text-label-sm text-on-surface-variant">
                      {entry.direction || "en→lun"} • {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
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
