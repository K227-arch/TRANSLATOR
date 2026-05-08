"use client";
import { useState } from "react";
import TopBar from "@/components/TopBar";
import BottomNav from "@/components/BottomNav";
import HomeDashboard from "@/components/HomeDashboard";
import Translator from "@/components/Translator";
import ChatPage from "@/components/ChatPage";
import DocumentEditor from "@/components/DocumentEditor";

type Tab = "home" | "translate" | "chat" | "editor";

export default function Home() {
  const [tab, setTab] = useState<Tab>("home");

  return (
    <div className="min-h-screen bg-background text-on-background">
      <TopBar processing={tab === "translate" || tab === "chat"} />

      <main>
        {tab === "home"      && <HomeDashboard onNavigate={setTab} />}
        {tab === "translate" && <Translator />}
        {tab === "chat"      && <ChatPage />}
        {tab === "editor"    && <DocumentEditor />}
      </main>

      <BottomNav active={tab} onChange={setTab} />

      {/* Background decoration */}
      <div className="fixed inset-0 -z-10 opacity-20 pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-80 h-80 bg-secondary-fixed-dim rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-primary-fixed rounded-full blur-[140px]" />
      </div>
    </div>
  );
}
