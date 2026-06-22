"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface HistoryEntry {
  input: string;
  translation: string | null;
  method: string;
  confidence: number;
  direction?: string;
  timestamp: string;
}

export default function History() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/history`)
      .then(r => r.json())
      .then(d => setHistory(d.history || []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col gap-3">
        {[1,2,3].map(i => (
          <div key={i} className="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/30 animate-pulse">
            <div className="h-3 bg-surface-container rounded w-1/3 mb-3" />
            <div className="h-4 bg-surface-container rounded w-3/4 mb-2" />
            <div className="h-4 bg-surface-container-high rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <span className="material-symbols-outlined text-[64px] text-outline/30 block mb-3">history</span>
        <p className="text-on-surface-variant font-semibold">No history yet</p>
        <p className="text-sm text-outline mt-1">Start translating and it will appear here.</p>
      </div>
    );
  }

  const methodLabel: Record<string, string> = {
    neural_mt:      "Neural MT",
    selective_rag:  "Retrieved",
    semantic_match: "Semantic",
    exact_match:    "Exact",
    dictionary_fallback: "Dictionary",
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-on-surface-variant font-semibold uppercase tracking-widest">{history.length} entries</p>
      {history.map((entry, i) => (
        <div key={i} className="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/40 premium-shadow group hover:border-primary-container transition-colors">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-outline">
              {new Date(entry.timestamp).toLocaleString([], {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"})}
            </span>
            <div className="flex gap-2 items-center">
              {entry.direction && (
                <span className="text-xs bg-primary-fixed text-on-primary-fixed px-2 py-0.5 rounded-full font-semibold">{entry.direction}</span>
              )}
              {entry.method && (
                <span className="text-xs bg-surface-container text-on-surface-variant px-2 py-0.5 rounded-full">
                  {methodLabel[entry.method] ?? entry.method.replace("_"," ")}
                </span>
              )}
            </div>
          </div>
          <p className="text-sm text-on-surface-variant">{entry.input}</p>
          {entry.translation && (
            <p className="text-base font-semibold text-on-background mt-1.5 leading-snug">{entry.translation}</p>
          )}
        </div>
      ))}
    </div>
  );
}
