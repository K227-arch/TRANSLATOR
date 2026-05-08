"use client";
import { useState } from "react";
import PdfTranslator from "./PdfTranslator";
import Dictionary from "./Dictionary";
import History from "./History";

type SubTab = "pdf" | "dictionary" | "history";

export default function DocumentEditor() {
  const [subTab, setSubTab] = useState<SubTab>("pdf");

  const tabs: { id: SubTab; icon: string; label: string }[] = [
    { id: "pdf",        icon: "upload_file", label: "PDF Translate" },
    { id: "dictionary", icon: "menu_book",   label: "Dictionary"    },
    { id: "history",    icon: "history",     label: "History"       },
  ];

  return (
    <div className="w-full max-w-screen-xl mx-auto px-4 sm:px-5 pt-4 pb-32">

      {/* Toolbar — scrollable on mobile */}
      <section className="bg-white border-b border-gray-200 rounded-t-xl mb-4 overflow-x-auto">
        <div className="px-4 py-2 flex items-center gap-3 min-w-max sm:min-w-0 sm:flex-wrap">
          {/* Formatting */}
          <div className="flex items-center bg-gray-100 rounded-lg p-1 gap-0.5">
            {["format_bold","format_italic","format_underlined"].map(icon => (
              <button key={icon} className="p-1.5 hover:bg-gray-200 rounded transition-all">
                <span className="material-symbols-outlined text-gray-500 text-[20px]">{icon}</span>
              </button>
            ))}
            <div className="w-px h-5 bg-gray-300 mx-1" />
            {["format_list_bulleted","format_list_numbered"].map(icon => (
              <button key={icon} className="p-1.5 hover:bg-gray-200 rounded transition-all">
                <span className="material-symbols-outlined text-gray-500 text-[20px]">{icon}</span>
              </button>
            ))}
          </div>
          {/* Alignment */}
          <div className="flex items-center bg-gray-100 rounded-lg p-1 gap-0.5">
            {["format_align_left","format_align_center","format_align_right"].map(icon => (
              <button key={icon} className="p-1.5 hover:bg-gray-200 rounded transition-all">
                <span className="material-symbols-outlined text-gray-500 text-[20px]">{icon}</span>
              </button>
            ))}
          </div>
          {/* Actions */}
          <div className="flex items-center gap-2 sm:ml-auto">
            <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 transition-all text-xs font-semibold whitespace-nowrap">
              <span className="material-symbols-outlined text-[18px]">spellcheck</span>
              <span className="hidden sm:inline">Spellcheck</span>
            </button>
            <button className="flex items-center gap-1 bg-indigo-900 text-white px-4 py-1.5 rounded-lg text-xs font-semibold hover:opacity-90 active:scale-95 whitespace-nowrap">
              <span className="material-symbols-outlined text-[18px]">save</span> Save
            </button>
          </div>
        </div>
      </section>

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
        {subTab === "pdf"        && <PdfTranslator />}
        {subTab === "dictionary" && <Dictionary />}
        {subTab === "history"    && <History />}
      </div>
    </div>
  );
}
