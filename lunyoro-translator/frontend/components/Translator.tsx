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
  translation_nllb?: string | null;
  translation_marian?: string | null;
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
  const [showComparison, setShowComparison] = useState(false);
  const [ignored, setIgnored] = useState<Set<string>>(new Set());
  // Feedback state
  const [feedbackRating, setFeedbackRating] = useState<1 | -1 | null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correction, setCorrection] = useState("");
  const [errorTypes, setErrorTypes] = useState<string[]>([]);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [selectedModel, setSelectedModel] = useState<"marian" | "nllb" | "none" | null>(null);
  const [modelFeedbackSent, setModelFeedbackSent] = useState(false);

  const spellTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposing = useRef(false);

  const fromLabel = direction === "en→lun" ? "English" : "Runyoro / Rutooro";
  const toLabel   = direction === "en→lun" ? "Runyoro / Rutooro" : "English";
  const endpoint  = direction === "en→lun" ? "/translate" : "/translate-reverse";

  // Clear stale result when input changes
  function handleInputChange(val: string) {
    setInput(val);
    if (result) {
      setResult(null);
      setFeedbackRating(null);
      setFeedbackSent(false);
      setModelFeedbackSent(false);
      setShowCorrection(false);
      setCorrection("");
      setErrorTypes([]);
      setSelectedModel(null);
    }
  }

  function swapDirection() {
    setDirection((d) => (d === "en→lun" ? "lun→en" : "en→lun"));
    setInput("");
    setResult(null);
    setError("");
    setMisspelled([]);
    setTooltip(null);
    setShowComparison(false);
    setIgnored(new Set());
    setFeedbackRating(null);
    setFeedbackSent(false);
    setModelFeedbackSent(false);
    setShowCorrection(false);
    setCorrection("");
    setErrorTypes([]);
    setSelectedModel(null);
  }

  async function submitFeedback(rating: 1 | -1, modelChoice?: "marian" | "nllb" | "none") {
    if (!result?.translation || !input.trim()) return;
    
    // For primary feedback (not model choice)
    if (!modelChoice) {
      // If rating is negative, require either error_types or correction
      if (rating === -1 && errorTypes.length === 0 && !correction.trim()) {
        return; // Don't submit without any feedback details
      }
    }
    
    if (modelChoice) {
      setModelFeedbackSent(true);
    } else {
      setFeedbackRating(rating);
      setFeedbackSent(true);
    }
    
    // Determine which translation to send based on model choice
    let translationToSend = result.translation;
    if (modelChoice === "marian" && result.translation_marian) {
      translationToSend = result.translation_marian;
    } else if (modelChoice === "nllb" && result.translation_nllb) {
      translationToSend = result.translation_nllb;
    }
    
    try {
      await fetch(`${API}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_text: input.trim(),
          translation: translationToSend,
          direction,
          rating,
          correction: correction.trim(),
          error_type: modelChoice === "none" ? "both_models_wrong" : errorTypes.join(", "),
        }),
      });
      if (!modelChoice) {
        setShowCorrection(false);
      }
    } catch {
      // silently fail — feedback is non-critical
    }
  }

  // ── spellcheck ───────────────────────────────────────────────────────────────
  const runSpellcheck = useCallback(async (text: string) => {
    if (!text.trim()) { setMisspelled([]); return; }
    try {
      const res = await fetch(`${API}/spellcheck`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      setMisspelled((data.misspelled || []).filter((m: Misspelled) => !ignored.has(m.word.toLowerCase())));
    } catch {
      setMisspelled([]);
    }
  }, [ignored]);

  function ignoreWord(word: string) {
    const lower = word.toLowerCase();
    setIgnored((prev) => new Set([...prev, lower]));
    setMisspelled((prev) => prev.filter((m) => m.word.toLowerCase() !== lower));
    if (editorRef.current) {
      editorRef.current.innerHTML = buildHtml(input);
    }
    setTooltip(null);
  }

  useEffect(() => {
    // Spellcheck disabled for lun→en — Lunyoro grammar is always accepted as-is
    setMisspelled([]);
  }, [input, direction]);

  // ── build HTML with red wavy underlines ──────────────────────────────────────
  function escHtml(s: string) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function buildHtml(text: string): string {
    if (!misspelled.length) return escHtml(text);
    const badWords = new Map(misspelled.map((m) => [m.word.toLowerCase(), m]));
    return text.split(/(\b)/).map((chunk) => {
      const entry = badWords.get(chunk.toLowerCase());
      if (entry) {
        const tips = entry.suggestions.join("|");
        return `<span class="misspelled" data-word="${escHtml(chunk)}" data-tips="${escHtml(tips)}" style="text-decoration:underline;text-decoration-style:wavy;text-decoration-color:#ef4444;cursor:pointer;">${escHtml(chunk)}</span>`;
      }
      return escHtml(chunk);
    }).join("");
  }

  // ── caret preservation ───────────────────────────────────────────────────────
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
    if (direction !== "lun→en" || !editorRef.current) return;
    const el = editorRef.current;
    const caretPos = saveCaret(el);
    el.innerHTML = buildHtml(input);
    restoreCaret(el, caretPos);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [misspelled]);

  function handleEditorInput() {
    if (isComposing.current || !editorRef.current) return;
    setInput(editorRef.current.innerText);
    setResult(null);
  }

  // ── hover tooltip ────────────────────────────────────────────────────────────
  const tooltipLeaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleEditorMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (target.classList.contains("misspelled")) {
      if (tooltipLeaveTimer.current) clearTimeout(tooltipLeaveTimer.current);
      const word = target.getAttribute("data-word") || "";
      const tips = (target.getAttribute("data-tips") || "").split("|").filter(Boolean);
      const rect = target.getBoundingClientRect();
      setTooltip({ word, suggestions: tips, x: rect.left, y: rect.bottom });
    } else {
      scheduleTooltipClose();
    }
  }

  function scheduleTooltipClose() {
    if (tooltipLeaveTimer.current) clearTimeout(tooltipLeaveTimer.current);
    tooltipLeaveTimer.current = setTimeout(() => setTooltip(null), 120);
  }

  function cancelTooltipClose() {
    if (tooltipLeaveTimer.current) clearTimeout(tooltipLeaveTimer.current);
  }

  function applySuggestion(original: string, suggestion: string) {
    if (!editorRef.current) return;
    const newText = input.replace(new RegExp(`\\b${original}\\b`, "i"), suggestion);
    setInput(newText);
    setResult(null);
    setTooltip(null);
  }

  // ── translate ────────────────────────────────────────────────────────────────
  async function handleTranslate() {
    const text = direction === "lun→en" ? (editorRef.current?.innerText || input) : input;
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    // Build context from the last translation result for context-aware translation
    const context = "";

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, context }),
      });
      if (!res.ok) throw new Error();
      setResult(await res.json());
      setFeedbackRating(null);
      setFeedbackSent(false);
      setModelFeedbackSent(false);
      setShowCorrection(false);
      setCorrection("");
      setErrorTypes([]);
      setSelectedModel(null);
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
            <span className="text-xs text-red-500">
              {misspelled.length} possible misspelling{misspelled.length > 1 ? "s" : ""} — hover to fix
            </span>
          )}
        </div>

        {direction === "lun→en" ? (
          <div
            ref={editorRef}
            contentEditable
            suppressContentEditableWarning
            onInput={handleEditorInput}
            onMouseMove={handleEditorMouseMove}
            onMouseLeave={scheduleTooltipClose}
            onCompositionStart={() => { isComposing.current = true; }}
            onCompositionEnd={() => { isComposing.current = false; handleEditorInput(); }}
            onKeyDown={(e) => e.key === "Enter" && e.ctrlKey && misspelled.length === 0 && handleTranslate()}
            className={`w-full border rounded-lg p-3 text-sm min-h-[96px] focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed text-gray-900 whitespace-pre-wrap break-words ${
              misspelled.length > 0 ? "border-red-300" : "border-gray-300"
            }`}
            style={{ fontFamily: "inherit" }}
          />
        ) : (
          <textarea
            ref={textareaRef}
            className="w-full border border-gray-300 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed text-gray-900"
            rows={4}
            placeholder={`Enter ${fromLabel} text to translate...`}
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && e.ctrlKey && handleTranslate()}
          />
        )}
        <p className="text-xs text-gray-400 mt-1">Ctrl+Enter to translate</p>
      </div>

      {/* Hover tooltip for misspelled words */}
      {tooltip && (
        <div
          className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm min-w-[140px]"
          style={{ top: tooltip.y + 6, left: tooltip.x }}
          onMouseEnter={cancelTooltipClose}
          onMouseLeave={scheduleTooltipClose}
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-xs text-gray-400 mb-1.5">Did you mean?</p>
          {tooltip.suggestions.length > 0 ? (
            tooltip.suggestions.map((s) => (
              <button
                key={s}
                className="block w-full text-left text-blue-600 hover:bg-blue-50 active:bg-blue-100 px-2 py-1.5 rounded text-sm cursor-pointer"
                onMouseDown={(e) => {
                  e.preventDefault();
                  applySuggestion(tooltip.word, s);
                }}
              >
                {s}
              </button>
            ))
          ) : (
            <p className="text-gray-400 italic text-xs">No suggestions</p>
          )}
          <div className="border-t border-gray-100 mt-1.5 pt-1.5">
            <button
              className="block w-full text-left text-gray-400 hover:bg-gray-50 active:bg-gray-100 px-2 py-1.5 rounded text-xs cursor-pointer"
              onMouseDown={(e) => {
                e.preventDefault();
                ignoreWord(tooltip.word);
              }}
            >
              Ignore
            </button>
          </div>
        </div>
      )}

      <button
        onClick={handleTranslate}
        disabled={loading || !input.trim() || (direction === "lun→en" && misspelled.length > 0)}
        title={direction === "lun→en" && misspelled.length > 0 ? "Fix spelling errors before translating" : undefined}
        className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Translating..." : direction === "lun→en" && misspelled.length > 0 ? `Fix ${misspelled.length} spelling error${misspelled.length > 1 ? "s" : ""} to translate` : `Translate to ${toLabel}`}
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

            {/* Feedback Section */}
            {result.translation && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="space-y-3">
                  {/* Primary Feedback: Is this the right translation? */}
                  {!feedbackSent && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-gray-600 font-medium">Is this the right translation?</span>
                        <button
                          onClick={() => submitFeedback(1)}
                          className={`text-xs px-3 py-1.5 rounded font-medium transition-colors ${
                            feedbackRating === 1
                              ? "bg-green-500 text-white"
                              : "bg-gray-100 hover:bg-green-50 text-gray-700 hover:text-green-600 border border-gray-200"
                          }`}
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => { setFeedbackRating(-1); setShowCorrection(true); }}
                          className={`text-xs px-3 py-1.5 rounded font-medium transition-colors ${
                            feedbackRating === -1
                              ? "bg-red-500 text-white"
                              : "bg-gray-100 hover:bg-red-50 text-gray-700 hover:text-red-600 border border-gray-200"
                          }`}
                        >
                          No
                        </button>
                      </div>

                      {/* Error categorization when user clicks No */}
                      {showCorrection && feedbackRating === -1 && (
                        <div className="mt-2 space-y-2 bg-gray-50 p-3 rounded border border-gray-200">
                          <p className="text-xs text-gray-600 font-medium">What's wrong with this translation? (Select all that apply)</p>
                          <div className="space-y-1">
                            {["grammar", "spelling", "context", "vocabulary", "other"].map((type) => (
                              <label key={type} className="flex items-center gap-2 text-xs cursor-pointer">
                                <input
                                  type="checkbox"
                                  value={type}
                                  checked={errorTypes.includes(type)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setErrorTypes([...errorTypes, type]);
                                    } else {
                                      setErrorTypes(errorTypes.filter(t => t !== type));
                                    }
                                  }}
                                  className="cursor-pointer"
                                />
                                <span className="text-gray-700 capitalize">{type === "context" ? "Context awareness" : type === "vocabulary" ? "Word doesn't exist in vocabulary" : type}</span>
                              </label>
                            ))}
                          </div>
                          <div className="mt-2">
                            <textarea
                              className="w-full border border-gray-300 rounded p-2 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-blue-400"
                              rows={2}
                              placeholder="Enter the correct translation (optional)..."
                              value={correction}
                              onChange={(e) => setCorrection(e.target.value)}
                            />
                          </div>
                          <div className="flex gap-2 mt-2">
                            <button
                              onClick={() => submitFeedback(-1)}
                              disabled={errorTypes.length === 0 && !correction.trim()}
                              className="text-xs bg-red-500 text-white px-3 py-1.5 rounded hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                              title={errorTypes.length === 0 && !correction.trim() ? "Please select at least one error type or provide a correction" : ""}
                            >
                              Submit Feedback
                            </button>
                            <button
                              onClick={() => { 
                                setShowCorrection(false); 
                                setFeedbackRating(null); 
                                setErrorTypes([]); 
                                setCorrection(""); 
                              }}
                              className="text-xs text-gray-500 hover:text-gray-700 px-2"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {feedbackSent && !modelFeedbackSent && (
                    <p className="text-xs text-green-600">Thanks for the feedback!</p>
                  )}

                  {/* Model Comparison (only if both models available) */}
                  {result.translation_marian && result.translation_nllb && !modelFeedbackSent && (
                    <div className="pt-3 border-t border-gray-100 space-y-2">
                      <p className="text-xs text-gray-600 font-medium">Or choose which model translation is better or close to better:</p>
                      
                      {/* MarianMT Option */}
                      <div 
                        onClick={() => setSelectedModel("marian")}
                        className={`border rounded-lg p-3 cursor-pointer transition-all ${
                          selectedModel === "marian" 
                            ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200" 
                            : "border-gray-200 hover:border-blue-300 hover:bg-gray-50"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <input
                            type="radio"
                            name="model_choice"
                            checked={selectedModel === "marian"}
                            onChange={() => setSelectedModel("marian")}
                            className="mt-0.5 cursor-pointer"
                          />
                          <div className="flex-1">
                            <p className="text-xs font-medium text-gray-700 mb-1">MarianMT</p>
                            <p className="text-sm text-gray-800">{result.translation_marian}</p>
                          </div>
                        </div>
                      </div>

                      {/* NLLB Option */}
                      <div 
                        onClick={() => setSelectedModel("nllb")}
                        className={`border rounded-lg p-3 cursor-pointer transition-all ${
                          selectedModel === "nllb" 
                            ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200" 
                            : "border-gray-200 hover:border-blue-300 hover:bg-gray-50"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <input
                            type="radio"
                            name="model_choice"
                            checked={selectedModel === "nllb"}
                            onChange={() => setSelectedModel("nllb")}
                            className="mt-0.5 cursor-pointer"
                          />
                          <div className="flex-1">
                            <p className="text-xs font-medium text-gray-700 mb-1">NLLB-200</p>
                            <p className="text-sm text-gray-800">{result.translation_nllb}</p>
                          </div>
                        </div>
                      </div>

                      {/* None Option */}
                      <div 
                        onClick={() => setSelectedModel("none")}
                        className={`border rounded-lg p-3 cursor-pointer transition-all ${
                          selectedModel === "none" 
                            ? "border-red-500 bg-red-50 ring-2 ring-red-200" 
                            : "border-gray-200 hover:border-red-300 hover:bg-gray-50"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <input
                            type="radio"
                            name="model_choice"
                            checked={selectedModel === "none"}
                            onChange={() => setSelectedModel("none")}
                            className="mt-0.5 cursor-pointer"
                          />
                          <div className="flex-1">
                            <p className="text-xs font-medium text-red-700">None - Both are wrong</p>
                            <p className="text-xs text-gray-600">Neither translation is correct</p>
                          </div>
                        </div>
                      </div>

                      {/* Submit Button for Model Selection */}
                      {selectedModel && (
                        <div className="space-y-2">
                          {selectedModel === "none" && (
                            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 space-y-2">
                              <p className="text-xs text-gray-600 font-medium">Please provide the correct translation:</p>
                              <textarea
                                className="w-full border border-gray-300 rounded p-2 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-blue-400"
                                rows={2}
                                placeholder="Enter the correct translation..."
                                value={correction}
                                onChange={(e) => setCorrection(e.target.value)}
                              />
                            </div>
                          )}
                          <button
                            onClick={() => submitFeedback(selectedModel === "none" ? -1 : 1, selectedModel)}
                            disabled={selectedModel === "none" && !correction.trim()}
                            className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                          >
                            Submit Model Feedback
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {modelFeedbackSent && (
                    <p className="text-xs text-green-600">Thanks for the model feedback!</p>
                  )}
                </div>
              </div>
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
