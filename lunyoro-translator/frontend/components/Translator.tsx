"use client";
import { useState, useEffect, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Direction = "en→lun" | "lun→en";

interface Misspelled {
  word: string;
  suggestions: string[];
}

interface TranslationResult {
  translation: string | null;
  method: string;
  confidence: number;
  matched_english?: string;
  matched_lunyoro?: string;
  alternatives?: { english: string; lunyoro: string; score: number }[];
  dictionary_matches?: {
    english_word?: string;
    lunyoro_word?: string;
    definition?: string;
    english_definition?: string;
  }[];
  message?: string;
}

export default function Translator() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [direction, setDirection] = useState<Direction>("en→lun");
  const [misspelled, setMisspelled] = useState<Misspelled[]>([]);
  const [tooltip, setTooltip] = useState<{ word: string; suggestions: string[]; x: number; y: number } | null>(null);

  const spellTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // track if we're composing (IME) to avoid caret jumps
  const isComposing = useRef(false);

  const fromLabel = direction === "en→lun" ? "English" : "Lunyoro / Rutooro";
  const toLabel = direction === "en→lun" ? "Lunyoro / Rutooro" : "English";
  const endpoint = direction === "en→lun" ? "/translate" : "/translate-reverse";

  function swapDirection() {
    setDirection((d) => (d === "en→lun" ? "lun→en" : "en→lun"));
    setInput("");
    setResult(null);
    setError("");
    setMisspelled([]);
  }

  // ── spellcheck ──────────────────────────────────────────────────────────────
  const runSpellcheck = useCallback(async (text: string) => {
    if (!text.trim()) { setMisspelled([]); return; }
    try {
      const res = await fetch(`${API}/spellcheck`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      setMisspelled(data.misspelled || []);
    } catch {
      setMisspelled([]);
    }
  }, []);

  useEffect(() => {
    if (direction !== "lun→en") { setMisspelled([]); return; }
    if (spellTimer.current) clearTimeout(spellTimer.current);
    spellTimer.current = setTimeout(() => runSpellcheck(input), 700);
    return () => { if (spellTimer.current) clearTimeout(spellTimer.current); };
  }, [input, direction, runSpellcheck]);

  // ── build HTML with red wavy underlines ─────────────────────────────────────
  function buildHtml(text: string): string {
    if (!misspelled.length) return escHtml(text);
    const badWords = new Map(misspelled.map((m) => [m.word.toLowerCase(), m]));
    // split on word boundaries keeping delimiters
    return text.split(/(\b)/).map((chunk) => {
      const entry = badWords.get(chunk.toLowerCase());
      if (entry) {
        const tips = entry.suggestions.join("|");
        return `<span class="misspelled" data-word="${escHtml(chunk)}" data-tips="${escHtml(tips)}" style="text-decoration:underline;text-decoration-style:wavy;text-decoration-color:#ef4444;cursor:pointer;">${escHtml(chunk)}</span>`;
      }
      return escHtml(chunk);
    }).join("");
  }

  function escHtml(s: string) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ── sync contentEditable → state (preserve caret) ───────────────────────────
  function saveCaret(el: HTMLDivElement): number {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return 0;
    const range = sel.getRangeAt(0);
    const pre = range.cloneRange();
    pre.selectNodeContents(el);
    pre.setEnd(range.endContainer, range.endOffset);
    return pre.toString().length;
  }

  function restoreCaret(el: HTMLDivElement, offset: number) {
    const walk = (node: Node, remaining: number): { node: Node; offset: number } | null => {
      if (node.nodeType === Node.TEXT_NODE) {
        const len = (node.textContent || "").length;
        if (remaining <= len) return { node, offset: remaining };
        return null;
      }
      for (const child of Array.from(node.childNodes)) {
        const len = (child.textContent || "").length;
        if (remaining <= len) return walk(child, remaining);
        remaining -= len;
      }
      return null;
    };
    const result = walk(el, offset);
    if (!result) return;
    const range = document.createRange();
    range.setStart(result.node, result.offset);
    range.collapse(true);
    const sel = window.getSelection();
    sel?.removeAllRanges();
    sel?.addRange(range);
  }

  // re-render highlighted HTML whenever misspelled list changes
  useEffect(() => {
    if (direction !== "lun→en" || !editorRef.current) return;
    const el = editorRef.current;
    const caretPos = saveCaret(el);
    el.innerHTML = buildHtml(input);
    restoreCaret(el, caretPos);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [misspelled]);

  function handleEditorInput() {
    if (isComposing.current || !editorRef.current) return;
    const text = editorRef.current.innerText;
    setInput(text);
  }

  // ── tooltip on misspelled word click ────────────────────────────────────────
  function handleEditorClick(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (!target.classList.contains("misspelled")) setTooltip(null);
  }

  function handleEditorMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (target.classList.contains("misspelled")) {
      const word = target.getAttribute("data-word") || "";
      const tips = (target.getAttribute("data-tips") || "").split("|").filter(Boolean);
      const rect = target.getBoundingClientRect();
      setTooltip({ word, suggestions: tips, x: rect.left, y: rect.bottom });
    } else {
      setTooltip(null);
    }
  }

  function applySuggestion(original: string, suggestion: string) {
    if (!editorRef.current) return;
    const newText = input.replace(new RegExp(`\\b${original}\\b`, "i"), suggestion);
    setInput(newText);
    editorRef.current.innerHTML = buildHtml(newText);
    setTooltip(null);
  }

  // ── translate ────────────────────────────────────────────────────────────────
  async function handleTranslate() {
    const text = direction === "lun→en" ? (editorRef.current?.innerText || input) : input;
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error();
      setResult(await res.json());
    } catch {
      setError("Could not connect to the translation server. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  const confidenceColor =
    result?.confidence && result.confidence > 0.8 ? "text-green-600"
    : result?.confidence && result.confidence > 0.5 ? "text-yellow-600"
    : "text-red-500";

  const matchedValue = result?.matched_english || result?.matched_lunyoro;
  const matchedLabel = direction === "en→lun" ? "Closest match found" : "Closest Lunyoro match found";

  return (
    <div className="space-y-4">
      {/* Direction selector */}
      <div className="flex items-center justify-center gap-3">
        <span className="text-sm font-medium text-gray-700 w-36 text-right">{fromLabel}</span>
        <button onClick={swapDirection} className="bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full px-3 py-1 text-sm transition-colors">
          ⇄ Swap
        </button>
        <span className="text-sm font-medium text-gray-700 w-36">{toLabel}</span>
      </div>

      {/* Input */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-sm font-medium text-gray-700">{fromLabel}</label>
          {direction === "lun→en" && misspelled.length > 0 && (
            <span className="text-xs text-red-500">{misspelled.length} possible misspelling{misspelled.length > 1 ? "s" : ""} — click to fix</span>
          )}
        </div>

        {direction === "lun→en" ? (
          /* contentEditable for Lunyoro — supports inline red underlines */
          <div
            ref={editorRef}
            contentEditable
            suppressContentEditableWarning
            onInput={handleEditorInput}
            onClick={handleEditorClick}
            onMouseMove={handleEditorMouseMove}
            onMouseLeave={() => setTooltip(null)}
            onCompositionStart={() => { isComposing.current = true; }}
            onCompositionEnd={() => { isComposing.current = false; handleEditorInput(); }}
            onKeyDown={(e) => e.key === "Enter" && e.ctrlKey && handleTranslate()}
            className={`w-full border rounded-lg p-3 text-sm min-h-[96px] focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed text-gray-900 whitespace-pre-wrap break-words ${
              misspelled.length > 0 ? "border-red-300" : "border-gray-300"
            }`}
            data-placeholder={`Enter ${fromLabel} text to translate...`}
            style={{ fontFamily: "inherit" }}
          />
        ) : (
          <textarea
            ref={textareaRef}
            className="w-full border border-gray-300 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed text-gray-900"
            rows={4}
            placeholder={`Enter ${fromLabel} text to translate...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && e.ctrlKey && handleTranslate()}
          />
        )}
        <p className="text-xs text-gray-400 mt-1">Ctrl+Enter to translate</p>
      </div>

      {/* Tooltip for suggestions */}
      {tooltip && (
        <div
          className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm"
          style={{ top: tooltip.y + 6, left: tooltip.x }}
          onMouseEnter={() => {/* keep open */}}
          onMouseLeave={() => setTooltip(null)}
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-xs text-gray-400 mb-1">Did you mean?</p>
          {tooltip.suggestions.length > 0 ? (
            tooltip.suggestions.map((s) => (
              <button
                key={s}
                className="block w-full text-left text-blue-600 hover:bg-blue-50 px-2 py-0.5 rounded"
                onClick={() => applySuggestion(tooltip.word, s)}
              >
                {s}
              </button>
            ))
          ) : (
            <p className="text-gray-400 italic">No suggestions</p>
          )}
        </div>
      )}

      <button
        onClick={handleTranslate}
        disabled={loading || !input.trim()}
        className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Translating..." : `Translate to ${toLabel}`}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">{toLabel}</span>
              <span className={`text-xs font-medium ${confidenceColor}`}>
                {result.method === "exact_match" ? "Exact match" : `${Math.round((result.confidence || 0) * 100)}% confidence`}
              </span>
            </div>
            {result.translation
              ? <p className="text-gray-800 text-base leading-relaxed">{result.translation}</p>
              : <p className="text-gray-400 italic text-sm">{result.message}</p>
            }
            {matchedValue && result.method !== "exact_match" && (
              <p className="text-xs text-gray-400 mt-2">{matchedLabel}: &quot;{matchedValue}&quot;</p>
            )}
          </div>

          {result.dictionary_matches && result.dictionary_matches.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm font-medium text-yellow-800 mb-2">Word matches found:</p>
              <ul className="space-y-1">
                {result.dictionary_matches.map((m, i) => (
                  <li key={i} className="text-sm text-yellow-700">
                    {direction === "en→lun" ? (
                      <><span className="font-medium">{m.english_word}</span> → {m.lunyoro_word}{m.definition && <span className="text-yellow-600"> ({m.definition})</span>}</>
                    ) : (
                      <><span className="font-medium">{m.lunyoro_word}</span> → {m.english_definition}</>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.alternatives && result.alternatives.length > 0 && (
            <details className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <summary className="text-sm font-medium text-gray-600 cursor-pointer">Other close matches</summary>
              <ul className="mt-2 space-y-2">
                {result.alternatives.map((alt, i) => (
                  <li key={i} className="text-sm border-t border-gray-100 pt-2">
                    <p className="text-gray-500 text-xs">{direction === "en→lun" ? alt.english : alt.lunyoro}</p>
                    <p className="text-gray-700">{direction === "en→lun" ? alt.lunyoro : alt.english}</p>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
