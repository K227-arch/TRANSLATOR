"use client";
import { useState, useRef, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Misspelled { word: string; suggestions: string[]; }
interface GrammarHint { category: string; rule: string; examples?: string[]; }

const GRAMMAR_HINTS: GrammarHint[] = [
  { category: "R/L Rule",       rule: "Use L only before/after 'e' or 'i'. All other positions use R.", examples: ["okulya (eat)", "okulima (dig)", "okurora (see)"] },
  { category: "Noun Classes",   rule: "omu-/aba- (people), en-/em- (animals), ama- (plurals), obu- (abstract), oku- (infinitives)" },
  { category: "Verb Infinitive",rule: "All verbs start with oku- (before consonant) or okw- (before vowel).", examples: ["okugenda (to go)", "okwogera (to speak)"] },
  { category: "Tense Markers",  rule: "ni- (present), ka- (past), ra-/raa- (future), -ire/-ere (perfect)", examples: ["nigenda (is going)", "nkaara (I went)", "ndaagenda (I will go)"] },
  { category: "Apostrophe",     rule: "Particles drop vowel before vowel-initial words.", examples: ["n'ente (and cow)", "z'ente (of cows)", "habw'okugonza (through love)"] },
  { category: "Long Vowels",    rule: "Double the vowel to indicate length: aa, ee, ii, oo, uu.", examples: ["abaana (children)", "okubaaga (to skin)", "omuurro (fire)"] },
];

export default function RunyoroEditor() {
  const [text, setText]               = useState("");
  const [misspelled, setMisspelled]   = useState<Misspelled[]>([]);
  const [tooltip, setTooltip]         = useState<{ word: string; suggestions: string[]; x: number; y: number } | null>(null);
  const [ignored, setIgnored]         = useState<Set<string>>(new Set());
  const [aiSuggestion, setAiSuggestion] = useState("");
  const [aiLoading, setAiLoading]     = useState(false);
  const [saved, setSaved]             = useState(false);
  const [activeHint, setActiveHint]   = useState<number | null>(null);
  const [wordCount, setWordCount]     = useState(0);

  const editorRef  = useRef<HTMLDivElement>(null);
  const isComposing = useRef(false);
  const tooltipTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const spellTimer   = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Word count ──────────────────────────────────────────────────────────────
  useEffect(() => {
    setWordCount(text.trim() ? text.trim().split(/\s+/).length : 0);
  }, [text]);

  // ── Spellcheck ──────────────────────────────────────────────────────────────
  const runSpellcheck = useCallback(async (t: string) => {
    if (!t.trim()) { setMisspelled([]); return; }
    try {
      const res = await fetch(`${API}/spellcheck`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: t }),
      });
      const data = await res.json();
      setMisspelled((data.misspelled || []).filter((m: Misspelled) => !ignored.has(m.word.toLowerCase())));
    } catch { setMisspelled([]); }
  }, [ignored]);

  // ── Build HTML with wavy underlines ─────────────────────────────────────────
  function escHtml(s: string) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function buildHtml(t: string): string {
    if (!misspelled.length) return escHtml(t);
    const bad = new Map(misspelled.map(m => [m.word.toLowerCase(), m]));
    return t.split(/(\b)/).map(chunk => {
      const entry = bad.get(chunk.toLowerCase());
      if (entry) {
        const tips = entry.suggestions.join("|");
        return `<span class="misspelled" data-word="${escHtml(chunk)}" data-tips="${escHtml(tips)}">${escHtml(chunk)}</span>`;
      }
      return escHtml(chunk);
    }).join("");
  }

  // ── Caret preservation ───────────────────────────────────────────────────────
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
    const walk = (node: Node, rem: number): { node: Node; offset: number } | null => {
      if (node.nodeType === Node.TEXT_NODE) {
        const len = (node.textContent || "").length;
        if (rem <= len) return { node, offset: rem };
        return null;
      }
      for (const child of Array.from(node.childNodes)) {
        const len = (child.textContent || "").length;
        if (rem <= len) return walk(child, rem);
        rem -= len;
      }
      return null;
    };
    const pos = walk(el, offset);
    if (!pos) return;
    const range = document.createRange();
    range.setStart(pos.node, pos.offset);
    range.collapse(true);
    const sel = window.getSelection();
    sel?.removeAllRanges();
    sel?.addRange(range);
  }

  useEffect(() => {
    if (!editorRef.current) return;
    const el = editorRef.current;
    const caret = saveCaret(el);
    el.innerHTML = buildHtml(text);
    restoreCaret(el, caret);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [misspelled]);

  function handleInput() {
    if (isComposing.current || !editorRef.current) return;
    const t = editorRef.current.innerText;
    setText(t);
    if (spellTimer.current) clearTimeout(spellTimer.current);
    spellTimer.current = setTimeout(() => runSpellcheck(t), 800);
  }

  // ── Tooltip ──────────────────────────────────────────────────────────────────
  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (target.classList.contains("misspelled")) {
      if (tooltipTimer.current) clearTimeout(tooltipTimer.current);
      const word = target.getAttribute("data-word") || "";
      const tips = (target.getAttribute("data-tips") || "").split("|").filter(Boolean);
      const rect = target.getBoundingClientRect();
      setTooltip({ word, suggestions: tips, x: rect.left, y: rect.bottom });
    } else { scheduleTooltipClose(); }
  }

  function scheduleTooltipClose() {
    if (tooltipTimer.current) clearTimeout(tooltipTimer.current);
    tooltipTimer.current = setTimeout(() => setTooltip(null), 120);
  }

  function applySuggestion(original: string, suggestion: string) {
    if (!editorRef.current) return;
    const newText = text.replace(new RegExp(`\\b${original}\\b`, "i"), suggestion);
    setText(newText);
    editorRef.current.innerText = newText;
    setTooltip(null);
    runSpellcheck(newText);
  }

  function ignoreWord(word: string) {
    const lower = word.toLowerCase();
    setIgnored(prev => new Set([...prev, lower]));
    setMisspelled(prev => prev.filter(m => m.word.toLowerCase() !== lower));
    setTooltip(null);
  }

  // ── Formatting commands ───────────────────────────────────────────────────────
  function execFormat(cmd: string) {
    document.execCommand(cmd, false);
    editorRef.current?.focus();
  }

  // ── AI grammar suggestion ─────────────────────────────────────────────────────
  async function getAiSuggestion() {
    if (!text.trim()) return;
    setAiLoading(true);
    setAiSuggestion("");
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Review this Runyoro-Rutooro text for grammar errors and suggest corrections. Text: "${text.trim()}"`,
          history: [],
        }),
      });
      const data = await res.json();
      setAiSuggestion(data.reply || "No suggestions.");
    } catch { setAiSuggestion("Could not get AI suggestions. Make sure the backend is running."); }
    finally { setAiLoading(false); }
  }

  // ── Save ──────────────────────────────────────────────────────────────────────
  function handleSave() {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `runyoro_document_${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="space-y-4">

      {/* Grammar hints panel */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
        <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-3">
          Runyoro-Rutooro Writing Guide
        </p>
        <div className="flex flex-wrap gap-2">
          {GRAMMAR_HINTS.map((hint, i) => (
            <button
              key={i}
              onClick={() => setActiveHint(activeHint === i ? null : i)}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${
                activeHint === i
                  ? "bg-indigo-700 text-white border-indigo-700"
                  : "bg-white text-indigo-700 border-indigo-200 hover:bg-indigo-100"
              }`}
            >
              {hint.category}
            </button>
          ))}
        </div>
        {activeHint !== null && (
          <div className="mt-3 bg-white rounded-lg p-3 border border-indigo-100">
            <p className="text-sm text-gray-700">{GRAMMAR_HINTS[activeHint].rule}</p>
            {GRAMMAR_HINTS[activeHint].examples && (
              <div className="flex flex-wrap gap-2 mt-2">
                {GRAMMAR_HINTS[activeHint].examples!.map((ex, j) => (
                  <span key={j} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono">{ex}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Toolbar — matches the image */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl">
        <div className="px-4 py-2 flex flex-wrap items-center gap-3">
          {/* Formatting */}
          <div className="flex items-center bg-white border border-gray-200 rounded-lg p-1 gap-0.5">
            {[
              { cmd: "bold",          icon: "B",  cls: "font-bold" },
              { cmd: "italic",        icon: "I",  cls: "italic" },
              { cmd: "underline",     icon: "U",  cls: "underline" },
            ].map(({ cmd, icon, cls }) => (
              <button key={cmd} onMouseDown={e => { e.preventDefault(); execFormat(cmd); }}
                className={`w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 text-gray-600 text-sm ${cls}`}>
                {icon}
              </button>
            ))}
            <div className="w-px h-5 bg-gray-200 mx-1" />
            {[
              { cmd: "insertUnorderedList", icon: "≡" },
              { cmd: "insertOrderedList",   icon: "1≡" },
            ].map(({ cmd, icon }) => (
              <button key={cmd} onMouseDown={e => { e.preventDefault(); execFormat(cmd); }}
                className="w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 text-gray-600 text-sm">
                {icon}
              </button>
            ))}
          </div>

          {/* Alignment */}
          <div className="flex items-center bg-white border border-gray-200 rounded-lg p-1 gap-0.5">
            {[
              { cmd: "justifyLeft",   icon: "⬛⬜⬜" },
              { cmd: "justifyCenter", icon: "⬜⬛⬜" },
              { cmd: "justifyRight",  icon: "⬜⬜⬛" },
            ].map(({ cmd, icon }) => (
              <button key={cmd} onMouseDown={e => { e.preventDefault(); execFormat(cmd); }}
                className="w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 text-gray-500 text-xs">
                <span className="material-symbols-outlined text-[18px]">
                  {cmd === "justifyLeft" ? "format_align_left" : cmd === "justifyCenter" ? "format_align_center" : "format_align_right"}
                </span>
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => runSpellcheck(text)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 text-xs font-semibold transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">spellcheck</span>
              Spellcheck
              {misspelled.length > 0 && (
                <span className="bg-red-500 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{misspelled.length}</span>
              )}
            </button>
            <button
              onClick={getAiSuggestion}
              disabled={aiLoading || !text.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-indigo-300 text-indigo-700 hover:bg-indigo-50 text-xs font-semibold transition-colors disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
              {aiLoading ? "Checking..." : "AI Review"}
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-1.5 bg-indigo-900 text-white px-4 py-1.5 rounded-lg text-xs font-semibold hover:opacity-90 active:scale-95 transition-all"
            >
              <span className="material-symbols-outlined text-[16px]">save</span>
              {saved ? "Saved!" : "Save"}
            </button>
          </div>
        </div>
      </div>

      {/* Editor canvas */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={handleInput}
          onMouseMove={handleMouseMove}
          onMouseLeave={scheduleTooltipClose}
          onCompositionStart={() => { isComposing.current = true; }}
          onCompositionEnd={() => { isComposing.current = false; handleInput(); }}
          className="min-h-[400px] p-6 text-gray-800 text-base leading-relaxed outline-none focus:ring-0 whitespace-pre-wrap break-words"
          style={{ fontFamily: "inherit" }}
          data-placeholder="Start writing in Runyoro-Rutooro..."
        />
        <div className="px-6 py-2 border-t border-gray-100 flex justify-between items-center">
          <span className="text-xs text-gray-400">{wordCount} word{wordCount !== 1 ? "s" : ""}</span>
          {misspelled.length > 0 && (
            <span className="text-xs text-red-500">{misspelled.length} possible spelling issue{misspelled.length > 1 ? "s" : ""} — hover to fix</span>
          )}
        </div>
      </div>

      {/* AI suggestion panel */}
      {aiSuggestion && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-indigo-600 text-[18px]">auto_awesome</span>
            <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">AI Grammar Review</p>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{aiSuggestion}</p>
        </div>
      )}

      {/* Spellcheck tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 bg-gray-900 text-white rounded-xl p-3 shadow-xl min-w-[160px]"
          style={{ top: tooltip.y + 6, left: tooltip.x }}
          onMouseEnter={() => { if (tooltipTimer.current) clearTimeout(tooltipTimer.current); }}
          onMouseLeave={scheduleTooltipClose}
        >
          <p className="text-xs opacity-60 mb-1">Did you mean?</p>
          {tooltip.suggestions.length > 0 ? tooltip.suggestions.map(s => (
            <button key={s} className="block w-full text-left text-teal-300 hover:bg-white/10 px-2 py-1.5 rounded text-sm"
              onMouseDown={e => { e.preventDefault(); applySuggestion(tooltip.word, s); }}>
              {s}
            </button>
          )) : <p className="text-xs opacity-50 italic">No suggestions</p>}
          <div className="border-t border-white/10 mt-1 pt-1">
            <button className="text-xs opacity-50 hover:opacity-100 px-2 py-1"
              onMouseDown={e => { e.preventDefault(); ignoreWord(tooltip.word); }}>
              Ignore
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
