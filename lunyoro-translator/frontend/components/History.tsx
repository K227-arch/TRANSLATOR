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
      .then((r) => r.json())
      .then((d) => setHistory(d.history || []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400 text-sm text-center py-8">Loading history...</p>;
  if (history.length === 0)
    return <p className="text-gray-400 text-sm text-center py-8">No translation history yet.</p>;

  return (
    <div className="space-y-3">
      {history.map((entry, i) => (
        <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-gray-400">
              {new Date(entry.timestamp).toLocaleString()}
            </span>
            <div className="flex gap-2">
              {entry.direction && (
                <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded">{entry.direction}</span>
              )}
              <span className="text-xs text-gray-400 capitalize">{entry.method?.replace("_", " ")}</span>
            </div>
          </div>
          <p className="text-sm text-gray-500">{entry.input}</p>
          {entry.translation && (
            <p className="text-sm font-medium text-gray-800 mt-1">{entry.translation}</p>
          )}
        </div>
      ))}
    </div>
  );
}
