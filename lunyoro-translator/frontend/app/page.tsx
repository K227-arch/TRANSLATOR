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

export type Tab = "home" | "translate" | "chat" | "editor" | "dictionary" | "history" | "voice" | "camera";

export default function Home() {
  const [tab, setTab] = useState<Tab>("home");

  const isProcessing = tab === "translate" || tab === "chat";

  // Section titles for inner pages
  const sectionTitle: Partial<Record<Tab, string>> = {
    dictionary: "Dictionary",
    history: "History",
    voice: "Voice",
    editor: "Editor",
    camera: "AI Stick Lens",
  };

  return (
    <div className="min-h-screen bg-background text-on-background">
      <TopBar processing={isProcessing} section={sectionTitle[tab]} onBack={tab !== "home" ? () => setTab("home") : undefined} />

      {/* Main content — offset by TopBar (64px) */}
      <main className={`pt-16 ${tab === "chat" ? "" : "min-h-screen"}`}>
        {tab === "home"       && <HomeDashboard onNavigate={setTab} />}
        {tab === "translate"  && <Translator />}
        {tab === "chat"       && <ChatPage />}
        {tab === "editor"     && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32">
            <DocumentEditor />
          </div>
        )}
        {tab === "dictionary" && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32">
            <Dictionary />
          </div>
        )}
        {tab === "history"    && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32">
            <History />
          </div>
        )}
        {tab === "voice"      && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32">
            <VoiceTranslator />
          </div>
        )}
        {tab === "camera"     && (
          <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32">
            <CameraTranslator />
          </div>
        )}
      </main>

      <BottomNav active={tab} onChange={setTab} />

      {/* Ambient background blobs */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 -left-20 w-80 h-80 bg-primary-container/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-primary-fixed/10 rounded-full blur-[140px]" />
      </div>
    </div>
  );
}
