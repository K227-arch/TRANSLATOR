"use client";
import { useState } from "react";
import TopBar from "@/components/TopBar";
import BottomNav from "@/components/BottomNav";
import HomeDashboard from "@/components/HomeDashboard";
import Translator from "@/components/Translator";
import ChatPage from "@/components/ChatPage";
import DocumentEditor from "@/components/DocumentEditor";
import Dictionary from "@/components/Dictionary";
import History from "@/components/History";
import VoiceTranslator from "@/components/VoiceTranslator";
import CameraTranslator from "@/components/CameraTranslator";
import HelpPage from "@/components/HelpPage";

export type Tab = "home" | "translate" | "chat" | "editor" | "dictionary" | "history" | "voice" | "camera" | "help";

export default function Home() {
  const [tab, setTab] = useState<Tab>("home");
  const [helpOpen, setHelpOpen] = useState(false);

  const isProcessing = tab === "translate" || tab === "chat";

  // Section titles for inner pages
  const sectionTitle: Partial<Record<Tab, string>> = {
    dictionary: "Dictionary",
    history: "History",
    voice: "Voice",
    editor: "Editor",
    camera: "Lens",
  };

  const handleHelpNavigate = (t: Tab) => {
    setHelpOpen(false);
    setTab(t);
  };

  return (
    <div className="min-h-screen bg-background text-on-background">
      <TopBar processing={isProcessing} section={sectionTitle[tab]} onBack={tab !== "home" ? () => setTab("home") : undefined} onHelp={() => setHelpOpen(!helpOpen)} />

      {/* Main content — offset by TopBar (64px) */}
      <main className={`pt-16 ${tab === "chat" ? "" : "min-h-screen"}`} key={tab}>
        {tab === "home"       && <div className="page-enter"><HomeDashboard onNavigate={setTab} /></div>}
        {tab === "translate"  && <div className="page-enter"><Translator /></div>}
        {tab === "chat"       && <div className="page-enter"><ChatPage /></div>}
        {tab === "editor"     && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 page-enter">
            <DocumentEditor />
          </div>
        )}
        {tab === "dictionary" && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 page-enter">
            <Dictionary />
          </div>
        )}
        {tab === "history"    && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 page-enter">
            <History />
          </div>
        )}
        {tab === "voice"      && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 page-enter">
            <VoiceTranslator />
          </div>
        )}
        {tab === "camera"     && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 page-enter">
            <CameraTranslator />
          </div>
        )}
      </main>

      {/* Help sidebar overlay */}
      {helpOpen && (
        <div className="fixed inset-0 z-[60]" onClick={() => setHelpOpen(false)}>
          {/* Light backdrop — only dims the left portion slightly */}
          <div className="absolute inset-0 bg-black/20" />
        </div>
      )}
      <aside
        className={`fixed top-0 right-0 h-full w-3/4 max-w-xs z-[70] bg-surface-bright border-l border-outline-variant/40 shadow-2xl transform transition-transform duration-300 ease-in-out ${
          helpOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between px-4 h-16 border-b border-outline-variant/30">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[22px]">help</span>
            <span className="font-semibold text-on-background text-lg">Help</span>
          </div>
          <button
            onClick={() => setHelpOpen(false)}
            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-surface-container transition-colors text-on-surface-variant"
            aria-label="Close help"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Sidebar content — scrollable */}
        <div className="overflow-y-auto h-[calc(100%-64px)] px-4 pt-4 pb-8">
          <HelpPage onNavigate={handleHelpNavigate} />
        </div>
      </aside>

      <BottomNav active={tab} onChange={setTab} />

      {/* Ambient background blobs */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 -left-20 w-80 h-80 bg-primary-container/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-primary-fixed/10 rounded-full blur-[140px]" />
      </div>
    </div>
  );
}
