"use client";
import { useEffect, useState } from "react";
import type { Tab } from "@/app/page";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface HistoryEntry { input: string; translation: string | null; direction?: string; timestamp: string; }
interface SystemInfo { marian_en2lun: boolean; marian_lun2en: boolean; nllb_en2lun: boolean; nllb_lun2en: boolean; gpu_available: boolean; marian_onnx: boolean; }

export default function HomeDashboard({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  const [history, setHistory]     = useState<HistoryEntry[]>([]);
  const [sysInfo, setSysInfo]     = useState<SystemInfo | null>(null);

  useEffect(() => {
    fetch(`${API}/history`).then(r => r.json())
      .then(d => setHistory((d.history || []).slice(0, 3))).catch(() => {});
    fetch(`${API}/system-info`).then(r => r.json())
      .then(d => setSysInfo(d)).catch(() => {});
  }, []);

  const tools: { id: Tab; icon: string; title: string; desc: string; span?: boolean; iconBg: string; iconColor: string; size?: "lg" | "sm" }[] = [
    { id: "translate",  icon: "g_translate", title: "Translator",      desc: "Neural translation: English ↔ Runyoro-Rutooro.",     span: true, iconBg: "bg-secondary-container",  iconColor: "text-on-secondary-container", size: "lg" },
    { id: "editor",     icon: "edit_note",   title: "Word Editor",     desc: "Write & refine in Runyoro-Rutooro.",                 iconBg: "bg-surface-container-highest", iconColor: "text-primary",             size: "sm" },
    { id: "chat",       icon: "chat_bubble", title: "AI Chat",         desc: "Ask about grammar or culture.",                      iconBg: "bg-primary-container/20",      iconColor: "text-primary",             size: "sm" },
    { id: "voice",      icon: "mic",         title: "Voice",           desc: "Speak and translate in real time.",     span: true,  iconBg: "bg-tertiary-container/40",     iconColor: "text-tertiary" },
    { id: "camera",     icon: "photo_camera", title: "Camera",         desc: "Point & translate like Google Lens.", span: true,  iconBg: "bg-primary-container/30",      iconColor: "text-primary" },
    { id: "dictionary", icon: "menu_book",   title: "Dictionary",      desc: "Explore word roots and definitions.",   span: true,  iconBg: "bg-secondary-fixed",           iconColor: "text-on-secondary-fixed" },
    { id: "history",    icon: "history",     title: "History",         desc: "Browse your recent translations.",      span: true,  iconBg: "bg-surface-container-high",    iconColor: "text-on-surface" },
  ];

  return (
    <div className="max-w-screen-xl mx-auto px-5 pb-32">

      {/* Hero */}
      <section className="pt-6 pb-8">
        <div className="relative overflow-hidden rounded-3xl bg-surface-container-lowest p-6 premium-shadow border border-outline-variant/30">
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary-fixed text-on-primary-fixed rounded-full text-xs font-semibold mb-4">
              <span className="material-symbols-outlined text-[14px]" style={{fontVariationSettings:"'FILL' 1"}}>security</span>
              RUNYORO-RUTOORO AI
            </span>
            <h1 className="text-3xl font-bold text-on-background mb-2 leading-tight">
              Translate with<br /><span className="text-primary">Precision.</span>
            </h1>
            <p className="text-base text-on-surface-variant mb-6 max-w-[80%]">
              Fine-tuned MarianMT + NLLB-200 models for the Runyoro-Rutooro language.
            </p>
            <button onClick={() => onNavigate("translate")}
              className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold flex items-center gap-2 active:scale-95 transition-all shadow-md hover:opacity-90">
              START TRANSLATING
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>
          </div>
          <div className="absolute -right-12 -top-12 w-48 h-48 bg-primary-container/20 rounded-full blur-3xl" />
          <div className="absolute -right-4 bottom-0 opacity-8">
            <span className="material-symbols-outlined text-[120px] text-primary" style={{fontVariationSettings:"'wght' 200"}}>g_translate</span>
          </div>
        </div>
      </section>

      {/* Bento tools */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-on-background mb-4">Tools</h2>
        <div className="grid grid-cols-2 gap-4">
          {tools.map(({ id, icon, title, desc, span, iconBg, iconColor, size }) => (
            <div key={id} onClick={() => onNavigate(id)}
              className={`glass-card rounded-2xl p-4 flex flex-col gap-3 hover:border-primary transition-all cursor-pointer group premium-shadow active:scale-98 ${span ? "col-span-2 flex-row items-center" : ""}`}>
              <div className={`${size === "lg" ? "w-12 h-12" : "w-10 h-10"} rounded-xl ${iconBg} flex items-center justify-center ${iconColor} group-hover:scale-110 transition-transform flex-shrink-0`}>
                <span className={`material-symbols-outlined ${size === "lg" ? "text-[28px]" : "text-[22px]"}`}>{icon}</span>
              </div>
              <div className="flex-grow min-w-0">
                <h3 className={`font-semibold text-on-background ${size === "lg" ? "text-base" : "text-sm"}`}>{title}</h3>
                <p className="text-xs text-on-surface-variant leading-tight mt-0.5 truncate">{desc}</p>
              </div>
              {span && <span className="material-symbols-outlined text-outline flex-shrink-0">chevron_right</span>}
            </div>
          ))}
        </div>
      </section>

      {/* System status */}
      <section className="mb-8">
        <div className="bg-surface-container-low rounded-2xl p-4 border border-outline-variant/50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-xs font-semibold text-on-surface uppercase tracking-widest">Model Status</h3>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${sysInfo ? "bg-green-500 animate-pulse" : "bg-outline"}`} />
              <span className="text-xs font-medium text-on-surface-variant">{sysInfo ? "Ready" : "Loading..."}</span>
            </div>
          </div>
          {sysInfo ? (
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
              {[
                { label: "MarianMT en→lun", ok: sysInfo.marian_en2lun },
                { label: "MarianMT lun→en", ok: sysInfo.marian_lun2en },
                { label: "NLLB-200 en→lun", ok: sysInfo.nllb_en2lun },
                { label: "NLLB-200 lun→en", ok: sysInfo.nllb_lun2en },
              ].map(({ label, ok }) => (
                <div key={label} className="flex items-center justify-between text-on-surface-variant">
                  <span className="text-xs">{label}</span>
                  <span className={`text-xs font-semibold ${ok ? "text-green-600" : "text-outline"}`}>
                    {ok ? "✓" : "—"}
                  </span>
                </div>
              ))}
              <div className="flex items-center justify-between text-on-surface-variant col-span-2 border-t border-outline-variant/30 pt-1.5 mt-0.5">
                <span className="text-xs">Inference</span>
                <span className="text-xs font-semibold text-on-surface">
                  {sysInfo.gpu_available ? "GPU" : sysInfo.marian_onnx ? "ONNX CPU" : "CPU"}
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="h-3 bg-surface-container rounded animate-pulse" />)}
            </div>
          )}
        </div>
      </section>

      {/* Recent activity */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-on-background">Recent</h3>
          <button onClick={() => onNavigate("history")} className="text-xs font-semibold text-secondary flex items-center gap-1 hover:text-primary transition-colors">
            VIEW ALL <span className="material-symbols-outlined text-[16px]">chevron_right</span>
          </button>
        </div>
        <div className="bg-surface-container-lowest rounded-2xl premium-shadow overflow-hidden border border-outline-variant/30">
          {history.length === 0 ? (
            <div className="p-6 text-center text-on-surface-variant text-sm">
              No recent activity yet. Start translating!
            </div>
          ) : history.map((entry, i) => (
            <div key={i} onClick={() => onNavigate("translate")}
              className={`p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors cursor-pointer group ${i < history.length-1 ? "border-b border-outline-variant/30" : ""}`}>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-primary-fixed/40 rounded-xl flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary text-[20px]">translate</span>
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-on-surface text-sm truncate max-w-[200px]">{entry.input}</p>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    {entry.direction || "en→lun"} · {new Date(entry.timestamp).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}
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
