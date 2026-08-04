"use client";
import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Direction = "en->lun" | "lun->en";

interface BatchResult {
  source: string;
  translation: string;
  method: string;
  confidence?: number;
  error?: string;
}

export default function BatchTranslator() {
  const [text, setText] = useState("");
  const [direction, setDirection] = useState<Direction>("en->lun");
  const [results, setResults] = useState<BatchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Translate pasted/typed sentences
  const handleTranslate = async () => {
    const sentences = text.split("\n").filter((l) => l.trim());
    if (!sentences.length) return;

    setLoading(true);
    setError("");
    setResults([]);

    try {
      const res = await fetch(`${API}/translate-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sentences, direction }),
      });
      const data = await res.json();
      if (data.detail) {
        setError(data.detail);
      } else {
        setResults(data.results || []);
      }
    } catch {
      setError("Could not connect to translation server.");
    } finally {
      setLoading(false);
    }
  };

  // Upload file for batch translation
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError("");
    setResults([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/translate-batch-file?direction=${direction}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.detail) {
        setError(data.detail);
      } else {
        setResults(data.results || []);
      }
    } catch {
      setError("Could not connect to translation server.");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  // Export results as CSV
  const handleExport = () => {
    if (!results.length) return;
    const header = "source,translation,method\n";
    const rows = results
      .map((r) => `"${r.source.replace(/"/g, '""')}","${r.translation.replace(/"/g, '""')}","${r.method}"`)
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `batch_translations_${direction}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Direction toggle */}
      <div className="flex items-center bg-surface-container rounded-xl p-1">
        <button
          onClick={() => setDirection("en->lun")}
          className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${
            direction === "en->lun"
              ? "bg-surface-container-lowest text-on-background shadow"
              : "text-on-surface-variant"
          }`}
        >
          English → Runyoro
        </button>
        <button
          onClick={() => setDirection("lun->en")}
          className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${
            direction === "lun->en"
              ? "bg-surface-container-lowest text-on-background shadow"
              : "text-on-surface-variant"
          }`}
        >
          Runyoro → English
        </button>
      </div>

      {/* Input area */}
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter sentences (one per line) or upload a file below..."
          className="w-full h-40 p-4 bg-surface-container-lowest border border-outline-variant/40 rounded-2xl text-on-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all placeholder:text-on-surface-variant/50"
        />
        <div className="absolute bottom-3 right-3 text-xs text-on-surface-variant/50">
          {text.split("\n").filter((l) => l.trim()).length} lines
        </div>
      </div>

      {/* Action row */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleTranslate}
          disabled={loading || !text.trim()}
          className="flex-1 bg-primary text-on-primary py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 active:scale-95 transition-all disabled:opacity-50 shadow-md"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Translating...
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[18px]">translate</span>
              Translate All
            </>
          )}
        </button>

        <label className="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant/40 rounded-xl cursor-pointer active:scale-95 transition-all hover:border-primary/50">
          <span className="material-symbols-outlined text-primary text-[20px]">upload_file</span>
          <span className="text-sm font-medium text-on-surface">Upload</span>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.txt"
            className="hidden"
            onChange={handleFileUpload}
          />
        </label>
      </div>

      {/* Help text */}
      <p className="text-xs text-on-surface-variant/70 -mt-2">
        Supports .csv (first column) and .txt (one sentence per line). Max 200 sentences per file.
      </p>

      {/* Error */}
      {error && (
        <div className="bg-error-container/30 border border-error/30 rounded-xl px-4 py-3 text-sm text-error text-center">
          <span className="material-symbols-outlined text-[16px] align-middle mr-1">error</span>
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center justify-between bg-surface-container/30">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">checklist</span>
              <h3 className="text-sm font-semibold text-on-background">
                {results.length} Translation{results.length > 1 ? "s" : ""}
              </h3>
            </div>
            <button
              onClick={handleExport}
              className="flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              Export CSV
            </button>
          </div>
          <div className="max-h-80 overflow-y-auto divide-y divide-outline-variant/20">
            {results.map((r, i) => (
              <div key={i} className="px-4 py-3 flex items-start gap-3">
                <span className="text-xs text-on-surface-variant/50 mt-0.5 w-6 text-right shrink-0">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-on-surface-variant truncate">{r.source}</p>
                  <p className="text-sm font-medium text-on-background mt-0.5">
                    {r.translation || <span className="text-error italic">No translation</span>}
                  </p>
                </div>
                <span className="text-[10px] text-on-surface-variant/50 bg-surface-container rounded px-1.5 py-0.5 shrink-0">
                  {r.method}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
