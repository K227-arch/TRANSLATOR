"use client";
import { useState } from "react";
import PdfTranslator from "./PdfTranslator";
import Dictionary from "./Dictionary";
import History from "./History";
import RunyoroEditor from "./RunyoroEditor";

type SubTab = "write" | "pdf" | "dictionary" | "history";

export default function DocumentEditor() {
  const [subTab, setSubTab] = useState<SubTab>("write");

  const tabs: { id: SubTab; icon: string; label: string }[] = [
    { id: "write",      icon: "edit_note",   label: "Write"       },
    { id: "pdf",        icon: "upload_file", label: "PDF Translate" },
    { id: "dictionary", icon: "menu_book",   label: "Dictionary"    },
    { id: "history",    icon: "history",     label: "History"       },
  ];

  return (
    <div className="w-full max-w-screen-xl mx-auto px-4 sm:px-5 pt-4 pb-32">

      {/* Sub-tabs — scrollable on mobile */}
      <div className="flex gap-1 mb-4 border-b border-gray-200 overflow-x-auto">
        {tabs.map(({ id, icon, label }) => (
          <button
            key={id}
            onClick={() => setSubTab(id)}
            className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold transition-colors whitespace-nowrap flex-shrink-0 ${
              subTab === id
                ? "border-b-2 border-teal-600 text-teal-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 min-h-[400px]">
        {subTab === "write"      && <RunyoroEditor />}
        {subTab === "pdf"        && <PdfTranslator />}
        {subTab === "dictionary" && <Dictionary />}
        {subTab === "history"    && <History />}
      </div>
    </div>
  );
}
