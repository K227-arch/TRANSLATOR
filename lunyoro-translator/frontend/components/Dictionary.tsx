"use client";
import { useState, useMemo, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type DictDirection = "en→lun" | "lun→en";
type PosFilter = "ALL" | "N" | "V" | "ADJ" | "OTHER";

const POS_LABELS: Record<string, { label: string; bg: string; text: string }> = {
  N:    { label: "Noun",      bg: "bg-primary-fixed",     text: "text-on-primary-fixed" },
  V:    { label: "Verb",      bg: "bg-secondary-fixed",   text: "text-on-secondary-fixed" },
  ADJ:  { label: "Adjective", bg: "bg-tertiary-fixed",    text: "text-on-tertiary-fixed" },
  PART: { label: "Particle",  bg: "bg-surface-container-highest", text: "text-on-surface" },
  PRON: { label: "Pronoun",   bg: "bg-surface-container-high",    text: "text-on-surface" },
};

interface DictEntry {
  word: string;
  definitionEnglish: string;
  definitionNative: string;
  exampleSentence1: string;
  exampleSentence1English: string;
  dialect: string;
  pos: string;
  source?: "neural_mt" | "dictionary" | "corpus";
  confidence?: number;
  pos_matched?: boolean;
}

export default function Dictionary() {
  const [query, setQuery]       = useState("");
  const [results, setResults]   = useState<DictEntry[]>([]);
  const [loading, setLoading]   = useState(false);
  const [searched, setSearched] = useState(false);
  const [direction, setDirection] = useState<DictDirection>("en→lun");
  const [posFilter, setPosFilter] = useState<PosFilter>("ALL");
  const [ruleHint, setRuleHint] = useState<string | null>(null);
  const [interjections, setInterjections] = useState<Record<string, string>>({});
  const [idioms, setIdioms]     = useState<Record<string, string>>({});

  useEffect(() => {
    fetch(`${API}/language-rules/interjections`).then(r => r.json())
      .then(d => setInterjections(d.interjections || {})).catch(() => {});
    fetch(`${API}/language-rules/idioms`).then(r => r.json())
      .then(d => setIdioms(d.idioms || {})).catch(() => {});
  }, []);

  async function handleSearch() {
    if (!query.trim()) return;
    setLoading(true); setSearched(true); setPosFilter("ALL"); setRuleHint(null);
    const q = query.toLowerCase().trim();
    if (interjections[q]) setRuleHint(`Interjection: "${query}" — ${interjections[q]}`);
    else if (idioms[q]) setRuleHint(`Idiom: "${query}" — ${idioms[q]}`);
    if (direction === "lun→en" && /[lL]/.test(query))
      setRuleHint(p => (p ? p + "\n" : "") + "R/L Rule: L is only used before/after 'e' or 'i'. All other positions use R.");
    try {
      const res = await fetch(`${API}/lookup`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({word: query, direction}) });
      const data = await res.json();
      setResults(data.results || []);
    } catch { setResults([]); }
    finally { setLoading(false); }
  }

  function handleDirectionChange(d: DictDirection) {
    setDirection(d); setQuery(""); setResults([]); setSearched(false); setPosFilter("ALL"); setRuleHint(null);
  }

  const filtered = useMemo(() => {
    if (posFilter === "ALL") return results;
    if (posFilter === "OTHER") return results.filter(r => !r.pos || !["N","V","ADJ"].includes(r.pos.toUpperCase()));
    return results.filter(r => (r.pos || "").toUpperCase() === posFilter);
  }, [results, posFilter]);

  return (
    <div className="space-y-4">
      {/* Direction toggle */}
      <div className="flex rounded-xl border border-outline-variant overflow-hidden text-sm font-semibold bg-surface-container-lowest premium-shadow">
        {(["en→lun", "lun→en"] as DictDirection[]).map(d => (
          <button key={d} onClick={() => handleDirectionChange(d)}
            className={`flex-1 py-3 transition-colors ${direction === d ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container"}`}>
            {d === "en→lun" ? "English → Runyoro" : "Runyoro → English"}
          </button>
        ))}
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-outline text-[20px]">search</span>
          <input type="text"
            className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl pl-10 pr-4 py-3 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary placeholder:text-outline/60"
            placeholder={direction === "en→lun" ? "Search English word..." : "Search Runyoro / Rutooro word..."}
            value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSearch()} />
        </div>
        <button onClick={handleSearch} disabled={loading || !query.trim()}
          className="bg-primary text-on-primary px-5 rounded-xl font-semibold text-sm hover:opacity-90 disabled:opacity-40 transition-all active:scale-95">
          {loading ? "..." : "Search"}
        </button>
      </div>

      {/* Rule hint */}
      {ruleHint && (
        <div className="bg-primary-fixed/40 border border-primary-container rounded-xl px-4 py-3 text-xs text-on-primary-fixed whitespace-pre-line">
          <span className="material-symbols-outlined text-[14px] mr-1 align-middle">menu_book</span>{ruleHint}
        </div>
      )}

      {/* POS filters */}
      {results.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {(["ALL","N","V","ADJ"] as PosFilter[]).map(p => {
            const info = p !== "ALL" ? POS_LABELS[p] : null;
            const count = p === "ALL" ? results.length : results.filter(r => (r.pos||"").toUpperCase() === p).length;
            if (p !== "ALL" && count === 0) return null;
            return (
              <button key={p} onClick={() => setPosFilter(p)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all border ${posFilter===p ? "bg-primary text-on-primary border-primary shadow" : "bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:border-primary"}`}>
                {p === "ALL" ? "All" : info?.label} <span className="opacity-70">({count})</span>
              </button>
            );
          })}
        </div>
      )}

      {/* No results */}
      {searched && !loading && results.length === 0 && (
        <div className="text-center py-10 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] text-outline/40 block mb-2">search_off</span>
          <p className="text-sm">No results for &quot;{query}&quot;</p>
        </div>
      )}

      {/* Results */}
      <div className="space-y-3">
        {results.length > 0 && <p className="text-xs text-on-surface-variant font-semibold uppercase tracking-widest">Results</p>}
        {filtered.map((entry, i) => {
          const posKey = (entry.pos || "").toUpperCase();
          const posInfo = POS_LABELS[posKey];
          return (
            <div key={i} className={`bg-surface-container-lowest rounded-2xl p-4 premium-shadow border ${entry.pos_matched ? "border-primary-container" : "border-outline-variant/40"}`}>
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-xs text-on-surface-variant uppercase tracking-wide">
                    {direction === "en→lun" ? "Runyoro / Rutooro" : "English"}
                  </span>
                  <p className="text-lg font-semibold text-on-background">
                    {direction === "en→lun" ? entry.word : (entry.definitionEnglish || entry.word)}
                  </p>
                </div>
                <div className="flex gap-1.5 flex-wrap justify-end items-center mt-1">
                  {entry.source === "neural_mt" && <span className="text-xs bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded-full font-semibold">AI</span>}
                  {entry.source === "corpus"    && <span className="text-xs bg-surface-container-high text-on-surface px-2 py-0.5 rounded-full font-semibold">corpus</span>}
                  {posInfo ? (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${posInfo.bg} ${posInfo.text}`}>{posInfo.label}</span>
                  ) : entry.pos ? (
                    <span className="text-xs bg-surface-container text-on-surface px-2 py-0.5 rounded-full">{entry.pos}</span>
                  ) : null}
                  {entry.dialect && <span className="text-xs bg-surface-container text-on-surface-variant px-2 py-0.5 rounded-full">{entry.dialect}</span>}
                  {entry.confidence !== undefined && entry.confidence < 1 && (
                    <span className="text-xs text-outline">{Math.round(entry.confidence*100)}%</span>
                  )}
                </div>
              </div>
              {direction === "en→lun" ? (
                <>
                  {entry.definitionEnglish && <p className="text-sm text-on-surface-variant">{entry.definitionEnglish}</p>}
                  {entry.definitionNative  && <p className="text-sm text-on-surface-variant italic mt-0.5">{entry.definitionNative}</p>}
                </>
              ) : (
                <>
                  {entry.word && <p className="text-sm text-on-surface-variant"><span className="font-medium text-on-surface">Runyoro: </span>{entry.word}</p>}
                  {entry.definitionNative && <p className="text-sm text-on-surface-variant italic mt-0.5">{entry.definitionNative}</p>}
                </>
              )}
              {(entry.exampleSentence1 || entry.exampleSentence1English) && (
                <div className="mt-3 text-xs text-on-surface-variant border-t border-outline-variant/30 pt-2 space-y-0.5">
                  {entry.exampleSentence1        && <p className="font-medium text-on-surface">{entry.exampleSentence1}</p>}
                  {entry.exampleSentence1English && <p>{entry.exampleSentence1English}</p>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
