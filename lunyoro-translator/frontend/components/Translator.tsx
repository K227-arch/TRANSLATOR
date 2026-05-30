"use client";
import { useState, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Direction = "en->lun" | "lun->en";
type DimKey = "score_mng"|"score_grm"|"score_tns"|"score_vcb"|"score_ort"|"score_ctx"|"score_flu"|"score_cul";

interface Misspelled { word: string; suggestions: string[]; }
interface TranslationResult {
  translation: string | null;
  translation_nllb?: string | null;
  translation_marian?: string | null;
  translation_refined?: string | null;
  method: string;
  confidence: number;
  matched_english?: string;
  matched_lunyoro?: string;
  message?: string;
}

const DIMS: { key: DimKey; code: string; label: string; weight: number; tooltip: string }[] = [
  { key:"score_mng", code:"MNG", label:"Meaning",    weight:25, tooltip:"Does the translation preserve the full meaning?" },
  { key:"score_grm", code:"GRM", label:"Grammar",    weight:15, tooltip:"Noun class concord, word order, subject-verb agreement" },
  { key:"score_tns", code:"TNS", label:"Tense",      weight:12, tooltip:"Correct tense & aspect markers (past, present, future, habitual)" },
  { key:"score_vcb", code:"VCB", label:"Vocabulary", weight:12, tooltip:"Right word choice, register, no unnecessary loanwords" },
  { key:"score_ort", code:"ORT", label:"Spelling",   weight: 8, tooltip:"Correct orthography, double vowels, prenasalised consonants" },
  { key:"score_ctx", code:"CTX", label:"Context",    weight:10, tooltip:"Pronouns, deixis, cultural references handled correctly" },
  { key:"score_flu", code:"FLU", label:"Fluency",    weight:10, tooltip:"Reads naturally — not stilted or mechanical" },
  { key:"score_cul", code:"CUL", label:"Cultural",   weight: 8, tooltip:"Proverbs, honorifics, kinship terms culturally appropriate" },
];

const EMPTY_DIMS: Record<DimKey, number|null> = {
  score_mng:null, score_grm:null, score_tns:null, score_vcb:null,
  score_ort:null, score_ctx:null, score_flu:null, score_cul:null,
};

const DOMAINS = [
  { value: "",                      label: "— Domain (optional) —" },
  { value: "everyday_conversation", label: "Everyday Conversation" },
  { value: "news_formal",           label: "News / Formal Prose" },
  { value: "religious_cultural",    label: "Religious / Cultural" },
  { value: "health_medical",        label: "Health / Medical" },
  { value: "education",             label: "Education" },
  { value: "agriculture",           label: "Agriculture" },
  { value: "government_legal",      label: "Government / Legal" },
  { value: "technical_digital",     label: "Technical / Digital" },
  { value: "idioms_proverbs",       label: "Idioms & Proverbs" },
  { value: "songs_poetry",          label: "Songs / Poetry" },
  { value: "other",                 label: "Other" },
];

const ERROR_TYPES = ["grammar","spelling","context","vocabulary","different meaning","other"];

function computeSqs(scores: Record<DimKey, number|null>): number|null {
  const scored = DIMS.filter(d => scores[d.key] !== null);
  if (!scored.length) return null;
  const totalW   = scored.reduce((s, d) => s + d.weight, 0);
  const weighted = scored.reduce((s, d) => s + (scores[d.key]! * d.weight), 0);
  return Math.round((weighted / (totalW * 5)) * 1000) / 10;
}

function sqsBand(sqs: number) {
  if (sqs >= 90) return { label: "Excellent", color: "text-emerald-600" };
  if (sqs >= 75) return { label: "Good",      color: "text-teal-600" };
  if (sqs >= 60) return { label: "Usable",    color: "text-yellow-600" };
  if (sqs >= 40) return { label: "Poor",      color: "text-orange-500" };
  return              { label: "Unusable",    color: "text-red-600" };
}

export default function Translator() {
  const [input, setInput]           = useState("");
  const [result, setResult]         = useState<TranslationResult | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [direction, setDirection]   = useState<Direction>("en->lun");
  const [misspelled, setMisspelled] = useState<Misspelled[]>([]);
  const [tooltip, setTooltip]       = useState<{ word: string; suggestions: string[]; x: number; y: number } | null>(null);
  const [ignored, setIgnored]       = useState<Set<string>>(new Set());
  const [feedbackRating, setFeedbackRating]       = useState<1 | -1 | null>(null);
  const [showCorrection, setShowCorrection]       = useState(false);
  const [correction, setCorrection]               = useState("");
  const [errorTypes, setErrorTypes]               = useState<string[]>([]);
  const [otherNote, setOtherNote]                 = useState("");
  const [feedbackSent, setFeedbackSent]           = useState(false);
  const [selectedModel, setSelectedModel]         = useState<"marian" | "nllb" | "none" | "both" | null>(null);
  const [modelFeedbackSent, setModelFeedbackSent] = useState(false);
  const [preferredModel, setPreferredModel]       = useState<"marian" | "nllb" | null>(null);
  const [refine, setRefine]                       = useState(true);
  const [refining, setRefining]                   = useState(false);
  const [domain, setDomain]                       = useState("");
  const [showBenchmark, setShowBenchmark]         = useState(false);
  const [dimScores, setDimScores]                 = useState<Record<DimKey, number | null>>({ ...EMPTY_DIMS });
  const [benchmarkSent, setBenchmarkSent]         = useState(false);
  const [sqsResult, setSqsResult]                 = useState<number | null>(null);

  const editorRef   = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposing = useRef(false);
  const tooltipLeaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fromLabel = direction === "en->lun" ? "English" : "Runyoro / Rutooro";
  const toLabel   = direction === "en->lun" ? "Runyoro / Rutooro" : "English";
  const endpoint  = direction === "en->lun" ? "/translate" : "/translate-reverse";

  function resetFeedback() {
    setFeedbackRating(null); setFeedbackSent(false); setModelFeedbackSent(false);
    setShowCorrection(false); setCorrection(""); setErrorTypes([]); setOtherNote("");
    setSelectedModel(null); setShowBenchmark(false); setBenchmarkSent(false);
    setSqsResult(null); setDimScores({ ...EMPTY_DIMS });
  }

  function handleInputChange(val: string) {
    setInput(val);
    if (result) { setResult(null); resetFeedback(); }
  }

  function swapDirection() {
    setDirection(d => d === "en->lun" ? "lun->en" : "en->lun");
    setInput(""); setResult(null); setError(""); setMisspelled([]);
    setTooltip(null); setIgnored(new Set()); resetFeedback();
  }

  async function submitFeedback(rating: 1 | -1, modelChoice?: "marian" | "nllb" | "none" | "both") {
    if (!result?.translation || !input.trim()) return;
    if (!modelChoice && rating === -1 && errorTypes.length === 0 && !correction.trim()) return;
    if (modelChoice) {
      setModelFeedbackSent(true);
      if (modelChoice === "marian" || modelChoice === "nllb") {
        setPreferredModel(modelChoice);
        if (modelChoice === "marian" && result.translation_marian) setResult({ ...result, translation: result.translation_marian });
        else if (modelChoice === "nllb" && result.translation_nllb) setResult({ ...result, translation: result.translation_nllb });
      }
    } else { setFeedbackRating(rating); setFeedbackSent(true); }
    let translationToSend = result.translation;
    let modelUsed = preferredModel || "";
    if (modelChoice === "marian" && result.translation_marian) { translationToSend = result.translation_marian; modelUsed = "marian"; }
    else if (modelChoice === "nllb" && result.translation_nllb) { translationToSend = result.translation_nllb; modelUsed = "nllb"; }
    else if (modelChoice === "both") { modelUsed = "both"; }
    else if (modelChoice === "none") { modelUsed = "none"; }
    const errorTypeStr = modelChoice === "none" ? "both_models_wrong"
      : modelChoice === "both" ? "both_models_correct"
      : errorTypes.map(t => t === "other" && otherNote.trim() ? `other: ${otherNote.trim()}` : t).join(", ");
    try {
      await fetch(`${API}/feedback`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_text: input.trim(), translation: translationToSend, direction, rating, correction: correction.trim(), error_type: errorTypeStr, model_used: modelUsed, refined: refine, domain }),
      });
      if (!modelChoice) setShowCorrection(false);
    } catch { /* non-critical */ }
  }

  async function submitBenchmark() {
    if (!result?.translation || !input.trim()) return;
    const sqs = computeSqs(dimScores);
    setSqsResult(sqs);
    setBenchmarkSent(true);
    try {
      await fetch(`${API}/feedback`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_text: input.trim(),
          translation: result.translation,
          direction,
          rating: sqs !== null ? (sqs >= 60 ? 1 : -1) : 0,
          correction: correction.trim(),
          error_type: errorTypes.join(", "),
          model_used: preferredModel || "",
          refined: refine,
          domain,
          ...Object.fromEntries(DIMS.map(d => [d.key, dimScores[d.key]])),
          sqs,
        }),
      });
    } catch { /* non-critical */ }
  }

  const runSpellcheck = useCallback(async (text: string) => {
    if (!text.trim()) { setMisspelled([]); return; }
    try {
      const res = await fetch(`${API}/spellcheck`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      const data = await res.json();
      setMisspelled((data.misspelled || []).filter((m: Misspelled) => !ignored.has(m.word.toLowerCase())));
    } catch { setMisspelled([]); }
  }, [ignored]);

  function ignoreWord(word: string) {
    const lower = word.toLowerCase();
    setIgnored(prev => new Set([...prev, lower]));
    setMisspelled(prev => prev.filter(m => m.word.toLowerCase() !== lower));
    setTooltip(null);
  }

  function handleEditorInput() {
    if (isComposing.current || !editorRef.current) return;
    setInput(editorRef.current.innerText); setResult(null);
  }

  function handleEditorMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (target.classList.contains("misspelled")) {
      if (tooltipLeaveTimer.current) clearTimeout(tooltipLeaveTimer.current);
      const word = target.getAttribute("data-word") || "";
      const tips = (target.getAttribute("data-tips") || "").split("|").filter(Boolean);
      const rect = target.getBoundingClientRect();
      setTooltip({ word, suggestions: tips, x: rect.left, y: rect.bottom });
    } else { scheduleTooltipClose(); }
  }

  function scheduleTooltipClose() {
    if (tooltipLeaveTimer.current) clearTimeout(tooltipLeaveTimer.current);
    tooltipLeaveTimer.current = setTimeout(() => setTooltip(null), 120);
  }

  function applySuggestion(original: string, suggestion: string) {
    setInput(input.replace(new RegExp(`\\b${original}\\b`, "i"), suggestion));
    setResult(null); setTooltip(null);
  }

  async function handleTranslate() {
    const text = direction === "lun->en" ? (editorRef.current?.innerText || input) : input;
    if (!text.trim()) return;
    setLoading(true); setError(""); setResult(null);
    if (refine) setRefining(true);
    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, context: "", refine }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (preferredModel && data.translation_marian && data.translation_nllb)
        data.translation = preferredModel === "marian" ? data.translation_marian : data.translation_nllb;
      // If NLLB returned the source text unchanged (passthrough), fall back to MarianMT
      if (data.translation_nllb && data.translation_nllb.trim().toLowerCase() === text.trim().toLowerCase()) {
        data.translation_nllb = data.translation_marian;
        if (!preferredModel || preferredModel === "nllb") data.translation = data.translation_marian;
      }
      setResult(data); resetFeedback();
    } catch { setError("Could not connect to the translation server."); }
    finally { setLoading(false); setRefining(false); }
  }

  const ERROR_TYPES = ["grammar", "spelling", "context", "vocabulary", "different meaning", "other"];

  return (
    <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 w-full flex flex-col gap-4">
      <div className="flex items-center bg-white rounded-xl p-3 shadow-sm border border-gray-100 gap-3 flex-wrap">
        <button className="px-4 py-1 rounded-full bg-teal-100 text-teal-800 text-sm font-semibold flex items-center gap-1">
          {fromLabel} <span className="material-symbols-outlined text-[16px]">expand_more</span>
        </button>
        <button onClick={swapDirection} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 transition-all active:scale-90">
          <span className="material-symbols-outlined text-teal-600">swap_horiz</span>
        </button>
        <button className="px-4 py-1 rounded-full bg-gray-100 text-gray-600 text-sm font-semibold flex items-center gap-1">
          {toLabel} <span className="material-symbols-outlined text-[16px]">expand_more</span>
        </button>
        {/* Domain selector */}
        <div className="ml-auto">
          <select
            value={domain}
            onChange={e => setDomain(e.target.value)}
            className="text-xs border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 bg-white focus:outline-none focus:ring-1 focus:ring-teal-400 cursor-pointer"
          >
            {DOMAINS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4 min-h-[400px]">
        <div className="flex-1 bg-white border border-gray-200 rounded-xl shadow-lg p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <span className="text-xs text-gray-400 uppercase tracking-widest font-semibold">Source</span>
            {input && <button onClick={() => { setInput(""); setResult(null); resetFeedback(); }} className="text-gray-400 hover:text-red-500 transition-colors"><span className="material-symbols-outlined">close</span></button>}
          </div>
          {direction === "lun->en" ? (
            <div ref={editorRef} contentEditable suppressContentEditableWarning onInput={handleEditorInput} onMouseMove={handleEditorMouseMove} onMouseLeave={scheduleTooltipClose} onCompositionStart={() => { isComposing.current = true; }} onCompositionEnd={() => { isComposing.current = false; handleEditorInput(); }} onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleTranslate()} className="flex-grow outline-none text-lg text-gray-800 min-h-[160px] whitespace-pre-wrap break-words" style={{ fontFamily: "inherit" }} />
          ) : (
            <textarea ref={textareaRef} className="flex-grow outline-none text-lg text-gray-800 resize-none placeholder:text-gray-300 min-h-[160px]" placeholder="Enter text here to translate..." value={input} onChange={e => handleInputChange(e.target.value)} onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleTranslate()} />
          )}
          <div className="mt-4 flex justify-between items-center border-t border-gray-100 pt-4">
            <span className="text-xs text-gray-400">{input.length} / 5000</span>
            <button className="p-1 text-gray-400 hover:text-indigo-900 transition-colors"><span className="material-symbols-outlined">mic</span></button>
          </div>
        </div>

        <div className="flex flex-row md:flex-col justify-center items-center gap-3">
          <button onClick={handleTranslate} disabled={loading || !input.trim()} className="bg-teal-600 text-white w-16 h-16 md:w-20 md:h-20 rounded-full shadow-xl flex items-center justify-center active:scale-90 transition-all hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed">
            <span className="material-symbols-outlined text-[32px] md:text-[40px]">{loading ? "hourglass_empty" : "translate"}</span>
          </button>
          {
            <button
              onClick={() => setRefine(r => !r)}
              title={refine ? "AI Refine ON" : "Enable AI refinement"}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${refine ? "bg-indigo-700 text-white border-indigo-700 shadow" : "bg-white text-gray-500 border-gray-200 hover:border-indigo-300 hover:text-indigo-700"}`}
            >
              <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
              <span>{refining ? "Refining..." : refine ? "Refine ON" : "Refine"}</span>
            </button>
          }
        </div>

        <div className="flex-1 bg-white border-2 border-teal-100 rounded-xl shadow-lg p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <span className="text-xs text-teal-600 uppercase tracking-widest font-semibold">{toLabel}</span>
            {result?.translation && (
              <button onClick={() => navigator.clipboard.writeText(result.translation || "")} className="p-1 text-gray-400 hover:text-indigo-900 transition-colors">
                <span className="material-symbols-outlined">content_copy</span>
              </button>
            )}
          </div>
          <div className="flex-grow text-lg text-gray-800 flex flex-col justify-start">
            {loading ? (
              <div className="flex items-center gap-2 text-gray-400">
                <div className="flex space-x-1">{[0,1,2].map(i => <div key={i} className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: `${i*0.15}s` }} />)}</div>
                <span className="text-sm">{refining ? "Translating + refining..." : "Translating..."}</span>
              </div>
            ) : result?.translation ? (
              <p className="leading-relaxed">{result.translation}</p>
            ) : error ? (
              <p className="text-red-500 text-base">{error}</p>
            ) : (
              <p className="text-gray-300 italic">Translation will appear here...</p>
            )}
          </div>
          {result && (
            <div className="mt-2 flex gap-2 flex-wrap">
              {preferredModel && <span className="text-xs bg-teal-100 text-teal-700 px-2 py-0.5 rounded-full font-semibold">Using {preferredModel === "marian" ? "MarianMT" : "NLLB-200"}</span>}
              {result.translation_refined && <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-semibold flex items-center gap-1"><span className="material-symbols-outlined text-[12px]">auto_awesome</span>AI Refined</span>}
              {domain && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-semibold">{DOMAINS.find(d => d.value === domain)?.label ?? domain}</span>}
            </div>
          )}
          {result?.translation && (
            <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
              {!feedbackSent && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-500 font-semibold">Is this the right translation?</span>
                    <button onClick={() => submitFeedback(1)} className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors ${feedbackRating === 1 ? "bg-teal-600 text-white" : "bg-gray-100 hover:bg-teal-50 text-gray-600 border border-gray-200"}`}>Yes</button>
                    <button onClick={() => { setFeedbackRating(-1); setShowCorrection(true); }} className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors ${feedbackRating === -1 ? "bg-red-500 text-white" : "bg-gray-100 hover:bg-red-50 text-gray-600 border border-gray-200"}`}>No</button>
                  </div>
                  {showCorrection && feedbackRating === -1 && (
                    <div className="bg-gray-50 p-3 rounded-xl border border-gray-200 space-y-2">
                      <p className="text-xs text-gray-500 font-semibold">What is wrong?</p>
                      <div className="space-y-1">
                        {ERROR_TYPES.map(type => (
                          <div key={type}>
                            <label className="flex items-center gap-2 text-xs cursor-pointer">
                              <input type="checkbox" checked={errorTypes.includes(type)} onChange={e => setErrorTypes(e.target.checked ? [...errorTypes, type] : errorTypes.filter(t => t !== type))} />
                              <span className="text-gray-600 capitalize">{type === "context" ? "Lack of context awareness" : type === "vocabulary" ? "Word does not exist in vocabulary" : type}</span>
                            </label>
                            {type === "other" && errorTypes.includes("other") && (
                              <input type="text" autoFocus className="mt-1 ml-5 w-[calc(100%-1.25rem)] border border-gray-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-teal-400" placeholder="Describe the problem..." value={otherNote} onChange={e => setOtherNote(e.target.value)} />
                            )}
                          </div>
                        ))}
                      </div>
                      <textarea className="w-full border border-gray-200 rounded-lg p-2 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-teal-400" rows={2} placeholder="Enter the correct translation (optional)..." value={correction} onChange={e => setCorrection(e.target.value)} />
                      <div className="flex gap-2">
                        <button onClick={() => submitFeedback(-1)} disabled={errorTypes.length === 0 && !correction.trim()} className="text-xs bg-red-500 text-white px-3 py-1.5 rounded-full hover:bg-red-600 disabled:opacity-50 font-semibold">Submit Feedback</button>
                        <button onClick={() => { setShowCorrection(false); setFeedbackRating(null); setErrorTypes([]); setCorrection(""); setOtherNote(""); }} className="text-xs text-gray-400 hover:text-gray-600 px-2">Cancel</button>
                      </div>
                    </div>
                  )}
                </div>
              )}
              {feedbackSent && !modelFeedbackSent && <p className="text-xs text-teal-600 font-semibold">Thanks for the feedback!</p>}
              {result.translation_marian && result.translation_nllb && !modelFeedbackSent && (
                <div className="pt-2 border-t border-gray-100 space-y-2">
                  <p className="text-xs text-gray-500 font-semibold">Which model translation is better?</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {([
                      { id: "marian" as const, label: "MarianMT", text: result.translation_marian },
                      { id: "nllb" as const, label: "NLLB-200", text: result.translation_nllb },
                      { id: "both" as const, label: "Both are correct", text: "Both translations are accurate" },
                      { id: "none" as const, label: "Both are wrong", text: "Neither is accurate" },
                    ]).map(({ id, label, text }) => (
                      <div key={id} onClick={() => setSelectedModel(id)} className={`border-2 rounded-xl p-2 cursor-pointer transition-all ${selectedModel === id ? "border-teal-500 bg-teal-50" : "border-gray-200 hover:border-gray-300"}`}>
                        <div className="flex items-start gap-2">
                          <input type="radio" name="model_choice" checked={selectedModel === id} onChange={() => setSelectedModel(id)} className="mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-indigo-900 mb-0.5">{label}</p>
                            <p className="text-xs text-gray-500 break-words">{text}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {selectedModel && <button onClick={() => submitFeedback(selectedModel === "none" ? -1 : 1, selectedModel)} className="w-full bg-teal-600 text-white py-2 rounded-full text-xs font-semibold hover:bg-teal-700 transition-all">Confirm Selection</button>}
                </div>
              )}
              {modelFeedbackSent && <p className="text-xs text-teal-600 font-semibold">Model preference saved!</p>}

              {/* ── Benchmark Scoring Panel ─────────────────────────────── */}
              {!benchmarkSent && (
                <div className="pt-2 border-t border-gray-100">
                  <button
                    onClick={() => setShowBenchmark(b => !b)}
                    className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
                  >
                    <span className="material-symbols-outlined text-[14px]">
                      {showBenchmark ? "expand_less" : "expand_more"}
                    </span>
                    {showBenchmark ? "Hide" : "Rate this translation in detail (8 dimensions)"}
                  </button>

                  {showBenchmark && (
                    <div className="mt-3 bg-indigo-50 rounded-xl border border-indigo-100 p-3 space-y-3">
                      <p className="text-xs text-indigo-700 font-semibold">
                        Runyoro-Rutooro LLM Benchmark
                      </p>
                      <div className="space-y-2">
                        {DIMS.map(dim => (
                          <div key={dim.key} className="flex items-center gap-2">
                            <div className="w-20 flex-shrink-0">
                              <span
                                className="text-[10px] font-bold text-indigo-800 uppercase tracking-wide cursor-help"
                                title={dim.tooltip}
                              >
                                {dim.code}
                              </span>
                              <span className="text-[10px] text-gray-500 block leading-tight">{dim.label}</span>
                            </div>
                            <div className="flex gap-1">
                              {[0,1,2,3,4,5].map(n => (
                                <button
                                  key={n}
                                  onClick={() => setDimScores(s => ({ ...s, [dim.key]: s[dim.key] === n ? null : n }))}
                                  className={`w-7 h-7 rounded-full text-xs font-bold border transition-all ${
                                    dimScores[dim.key] === n
                                      ? "bg-indigo-600 text-white border-indigo-600 shadow"
                                      : "bg-white text-gray-500 border-gray-200 hover:border-indigo-300 hover:text-indigo-600"
                                  }`}
                                >
                                  {n}
                                </button>
                              ))}
                            </div>
                            <span className="text-[10px] text-gray-400 ml-1">{dim.weight}%</span>
                          </div>
                        ))}
                      </div>

                      {/* Live SQS preview */}
                      {(() => {
                        const sqs = computeSqs(dimScores);
                        if (sqs === null) return null;
                        const band = sqsBand(sqs);
                        return (
                          <div className="flex items-center gap-2 pt-1 border-t border-indigo-100">
                            <span className="text-xs text-gray-500">SQS:</span>
                            <span className={`text-sm font-bold ${band.color}`}>{sqs}/100</span>
                            <span className={`text-xs font-semibold ${band.color}`}>— {band.label}</span>
                          </div>
                        );
                      })()}

                      <button
                        onClick={submitBenchmark}
                        disabled={DIMS.every(d => dimScores[d.key] === null)}
                        className="w-full bg-indigo-600 text-white py-2 rounded-full text-xs font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-all"
                      >
                        Submit Benchmark Score
                      </button>
                    </div>
                  )}
                </div>
              )}

              {benchmarkSent && sqsResult !== null && (
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs font-semibold text-indigo-700 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                    Benchmark saved &nbsp;·&nbsp;
                    <span className={sqsBand(sqsResult).color}>SQS {sqsResult}/100 — {sqsBand(sqsResult).label}</span>
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {tooltip && (
        <div className="fixed z-50 bg-gray-900 text-white rounded-xl p-3 shadow-xl min-w-[140px]" style={{ top: tooltip.y + 6, left: tooltip.x }} onMouseEnter={() => { if (tooltipLeaveTimer.current) clearTimeout(tooltipLeaveTimer.current); }} onMouseLeave={scheduleTooltipClose}>
          <p className="text-xs opacity-70 mb-1">Did you mean?</p>
          {tooltip.suggestions.length > 0 ? tooltip.suggestions.map(s => (
            <button key={s} className="block w-full text-left text-teal-300 hover:bg-white/10 px-2 py-1.5 rounded text-sm" onMouseDown={e => { e.preventDefault(); applySuggestion(tooltip.word, s); }}>{s}</button>
          )) : <p className="text-xs opacity-60 italic">No suggestions</p>}
          <div className="border-t border-white/10 mt-1 pt-1">
            <button className="text-xs opacity-60 hover:opacity-100 px-2 py-1" onMouseDown={e => { e.preventDefault(); ignoreWord(tooltip.word); }}>Ignore</button>
          </div>
        </div>
      )}

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        {[
          { icon: "menu_book", title: "Dictionary", desc: "Explore Runyoro word roots and etymology." },
          { icon: "construction", title: "Linguistic Tools", desc: "Analyze grammar structure and tonal markers." },
          { icon: "star", title: "Saved Phrases", desc: "Quick access to your most used bilingual cards." },
        ].map(({ icon, title, desc }) => (
          <div key={title} className="bg-gray-50 p-4 rounded-xl border border-gray-200 hover:bg-gray-100 transition-colors cursor-pointer">
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-gray-500">{icon}</span>
              <h3 className="font-semibold text-indigo-900">{title}</h3>
            </div>
            <p className="text-gray-500 text-sm">{desc}</p>
          </div>
        ))}
      </section>
    </div>
  );
}


