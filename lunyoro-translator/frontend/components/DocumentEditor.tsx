"use client";
import { useState } from "react";
import PdfTranslator from "./PdfTranslator";
import RunyoroEditor from "./RunyoroEditor";
import BatchTranslator from "./BatchTranslator";

type SubTab = "write" | "batch" | "pdf";

const tabs: { id: SubTab; icon: string; label: string }[] = [
  { id: "write", icon: "edit_note",   label: "Write" },
  { id: "batch", icon: "list_alt",    label: "Batch" },
  { id: "pdf",   icon: "upload_file", label: "PDF Translate" },
];

export default function DocumentEditor() {
  const [subTab, setSubTab] = useState<SubTab>("write");

  return (
    <div className="w-full">
      {/* Sub-tabs */}
      <div className="flex gap-1 mb-5 bg-surface-container rounded-xl p-1">
        {tabs.map(({ id, icon, label }) => (
          <button key={id} onClick={() => setSubTab(id)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              subTab === id
                ? "bg-surface-container-lowest text-on-background shadow premium-shadow"
                : "text-on-surface-variant hover:text-on-surface"
            }`}>
            <span className="material-symbols-outlined text-[18px]">{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {subTab === "write" && <RunyoroEditor />}
      {subTab === "batch" && <BatchTranslator />}
      {subTab === "pdf"   && <PdfTranslator />}
    </div>
  );
}
