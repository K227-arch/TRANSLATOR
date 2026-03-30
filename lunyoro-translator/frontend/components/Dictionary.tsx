"use client";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type DictDirection = "en→lun" | "lun→en";

interface DictEntry {
  word: string;
  definitionEnglish: string;
  definitionNative: string;
  exampleSentence1: string;
  exampleSentence1English: string;
  dialect: string;
  pos: string;
}

export default function Dictionary() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DictEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [direction, setDirection] = useState<DictDirection>("en→lun");

  const placeholder = direction === "en→lun"
    ? "Search an English word..."
    : "Search a Lunyoro / Rutooro word...";

  async function handleSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(`${API}/lookup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: query }),
      });
      const data = await res.json();
      setResults(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function handleDirectionChange(d: DictDirection) {
    setDirection(d);
    setQuery("");
    setResults([]);
    setSearched(false);
  }

  return (
    <div className="space-y-4">
      {/* Direction toggle */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm font-medium">
        <button
          onClick={() => handleDirectionChange("en→lun")}
          className={`flex-1 py-2 transition-colors ${
            direction === "en→lun"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-600 hover:bg-gray-50"
          }`}
        >
          English → Lunyoro / Rutooro
        </button>
        <button
          onClick={() => handleDirectionChange("lun→en")}
          className={`flex-1 py-2 transition-colors ${
            direction === "lun→en"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-600 hover:bg-gray-50"
          }`}
        >
          Lunyoro / Rutooro → English
        </button>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <input
          type="text"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Search"}
        </button>
      </div>

      {searched && results.length === 0 && !loading && (
        <p className="text-gray-500 text-sm text-center py-4">
          No results found for &quot;{query}&quot;
        </p>
      )}

      <div className="space-y-3">
        {results.map((entry, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex justify-between items-start mb-1">
              {/* heading flips based on direction */}
              {direction === "en→lun" ? (
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wide">Lunyoro / Rutooro</span>
                  <p className="text-lg font-semibold text-gray-800">{entry.word}</p>
                </div>
              ) : (
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wide">English</span>
                  <p className="text-lg font-semibold text-gray-800">
                    {entry.definitionEnglish || entry.word}
                  </p>
                </div>
              )}
              <div className="flex gap-1 mt-1">
                {entry.pos && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{entry.pos}</span>
                )}
                {entry.dialect && (
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{entry.dialect}</span>
                )}
              </div>
            </div>

            {/* definition shown in the opposite language */}
            {direction === "en→lun" ? (
              <>
                {entry.definitionEnglish && (
                  <p className="text-sm text-gray-600">{entry.definitionEnglish}</p>
                )}
                {entry.definitionNative && (
                  <p className="text-sm text-gray-500 italic">{entry.definitionNative}</p>
                )}
              </>
            ) : (
              <>
                {entry.word && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium text-gray-700">Lunyoro: </span>{entry.word}
                  </p>
                )}
                {entry.definitionNative && (
                  <p className="text-sm text-gray-500 italic">{entry.definitionNative}</p>
                )}
              </>
            )}

            {/* example sentences */}
            {(entry.exampleSentence1 || entry.exampleSentence1English) && (
              <div className="mt-2 text-xs text-gray-500 border-t border-gray-100 pt-2 space-y-0.5">
                {entry.exampleSentence1 && (
                  <p className="font-medium text-gray-600">{entry.exampleSentence1}</p>
                )}
                {entry.exampleSentence1English && (
                  <p>{entry.exampleSentence1English}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
