"use client";
import { useState, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Direction = "en->lun" | "lun->en";
type DimKey = "score_mng"|"score_grm"|"score_tns"|"score_vcb"|"score_ort"|"score_ctx"|"score_flu"|"score_cul";
interface Misspelled { word: string; suggestions: string[]; }
interface TranslationResult {
  translation: string | null;
  translation_nllb?: string | null;
  translation_marian?: string | null;
  method: string;
  confidence: number;
  message?: string;
}

const DIMS: { key: DimKey; code: string; label: string; weight: number; tooltip: string }[] = [
  { key:"score_mng", code:"MNG", label:"Meaning",    weight:25, tooltip:"Does the translation preserve the full meaning?" },
  { key:"score_grm", code:"GRM", label:"Grammar",    weight:15, tooltip:"Noun class concord, word order, subject-verb agreement" },
  { key:"score_tns", code:"TNS", label:"Tense",      weight:12, tooltip:"Correct tense & aspect markers" },
  { key:"score_vcb", code:"VCB", label:"Vocabulary", weight:12, tooltip:"Right word choice, register" },
  { key:"score_ort", code:"ORT", label:"Spelling",   weight: 8, tooltip:"Correct orthography, double vowels" },
  { key:"score_ctx", code:"CTX", label:"Context",    weight:10, tooltip:"Pronouns, deixis, cultural references" },
  { key:"score_flu", code:"FLU", label:"Fluency",    weight:10, tooltip:"Reads naturally — not stilted" },
  { key:"score_cul", code:"CUL", label:"Cultural",   weight: 8, tooltip:"Proverbs, honorifics, kinship terms" },
];

const EMPTY_DIMS: Record<DimKey, number|null> = {
  score_mng:null, score_grm:null, score_tns:null, score_vcb:null,
  score_ort:null, score_ctx:null, score_flu:null, score_cul:null,
};

const DOMAINS = [
  { value: "",                      label: "Domain" },
  { value: "everyday_conversation", label: "Daily Life" },
  { value: "news_formal",           label: "News / Formal" },
  { value: "religious_cultural",    label: "Religious" },
  { value: "health_medical",        label: "Health" },
  { value: "education",             label: "Education" },
  { value: "agriculture",           label: "Agriculture" },
  { value: "government_legal",      label: "Government" },
  { value: "technical_digital",     label: "Technical" },
  { value: "idioms_proverbs",       label: "Idioms" },
  { value: "songs_poetry",          label: "Songs / Poetry" },
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
  if (sqs >= 90) return { label: "Excellent", color: "text-green-700" };
  if (sqs >= 75) return { label: "Good",      color: "text-primary" };
  if (sqs >= 60) return { label: "Usable",    color: "text-on-surface-variant" };
  if (sqs >= 40) return { label: "Poor",      color: "text-secondary" };
  return              { label: "Unusable",    color: "text-error" };
}

export default function Translator() {
  const [input, setInput]         = useState("");
  const [result, setResult]       = useState<TranslationResult | null>(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [direction, setDirection] = useState<Direction>("en->lun");
  const [misspelled, setMisspelled] = useState<Misspelled[]>([]);
  const [tooltip, setTooltip]     = useState<{word:string;suggestions:string[];x:number;y:number}|null>(null);
  const [ignored, setIgnored]     = useState<Set<string>>(new Set());
  const [feedbackRating, setFeedbackRating] = useState<1|-1|null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correction, setCorrection]         = useState("");
  const [errorTypes, setErrorTypes]         = useState<string[]>([]);
  const [otherNote, setOtherNote]           = useState("");
  const [feedbackSent, setFeedbackSent]     = useState(false);
  const [selectedModel, setSelectedModel]   = useState<"marian"|"nllb"|"none"|"both"|null>(null);
  const [modelFeedbackSent, setModelFeedbackSent] = useState(false);
  const [preferredModel, setPreferredModel] = useState<"marian"|"nllb"|null>(null);
  const [domain, setDomain]               = useState("");
  const [showBenchmark, setShowBenchmark] = useState(false);
  const [dimScores, setDimScores]         = useState<Record<DimKey,number|null>>({...EMPTY_DIMS});
  const [benchmarkSent, setBenchmarkSent] = useState(false);
  const [sqsResult, setSqsResult]         = useState<number|null>(null);

  const editorRef   = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposing = useRef(false);
  const tooltipTimer = useRef<ReturnType<typeof setTimeout>|null>(null);

  const fromLabel = direction === "en->lun" ? "English" : "Runyoro / Rutooro";
  const toLabel   = direction === "en->lun" ? "Runyoro / Rutooro" : "English";
  const endpoint  = direction === "en->lun" ? "/translate" : "/translate-reverse";

  function resetFeedback() {
    setFeedbackRating(null); setFeedbackSent(false); setModelFeedbackSent(false);
    setShowCorrection(false); setCorrection(""); setErrorTypes([]); setOtherNote("");
    setSelectedModel(null); setShowBenchmark(false); setBenchmarkSent(false);
    setSqsResult(null); setDimScores({...EMPTY_DIMS});
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
  async function submitFeedback(rating: 1|-1, modelChoice?: "marian"|"nllb"|"none"|"both") {
    if (!result?.translation || !input.trim()) return;
    if (!modelChoice && rating === -1 && errorTypes.length === 0 && !correction.trim()) return;
    if (modelChoice) {
      setModelFeedbackSent(true);
      if (modelChoice === "marian" || modelChoice === "nllb") {
        setPreferredModel(modelChoice);
        if (modelChoice === "marian" && result.translation_marian) setResult({...result, translation: result.translation_marian});
        else if (modelChoice === "nllb" && result.translation_nllb) setResult({...result, translation: result.translation_nllb});
      }
    } else { setFeedbackRating(rating); setFeedbackSent(true); }
    let translationToSend = result.translation;
    let modelUsed = preferredModel || "";
    if (modelChoice === "marian" && result.translation_marian) { translationToSend = result.translation_marian; modelUsed = "marian"; }
    else if (modelChoice === "nllb" && result.translation_nllb) { translationToSend = result.translation_nllb; modelUsed = "nllb"; }
    else if (modelChoice === "both") modelUsed = "both";
    else if (modelChoice === "none") modelUsed = "none";
    const errorTypeStr = modelChoice === "none" ? "both_models_wrong"
      : modelChoice === "both" ? "both_models_correct"
      : errorTypes.map(t => t === "other" && otherNote.trim() ? `other: ${otherNote.trim()}` : t).join(", ");
    try {
      await fetch(`${API}/feedback`, {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({source_text:input.trim(), translation:translationToSend, direction, rating, correction:correction.trim(), error_type:errorTypeStr, model_used:modelUsed, domain}),
      });
      if (!modelChoice) setShowCorrection(false);
    } catch { /* non-critical */ }
  }
  async function submitBenchmark() {
    if (!result?.translation || !input.trim()) return;
    const sqs = computeSqs(dimScores);
    setSqsResult(sqs); setBenchmarkSent(true);
    try {
      await fetch(`${API}/feedback`, {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({source_text:input.trim(), translation:result.translation, direction,
          rating: sqs !== null ? (sqs >= 60 ? 1 : -1) : 0,
          correction:correction.trim(), error_type:errorTypes.join(", "), model_used:preferredModel||"", domain,
          ...Object.fromEntries(DIMS.map(d => [d.key, dimScores[d.key]])), sqs}),
      });
    } catch { /* non-critical */ }
  }
  const runSpellcheck = useCallback(async (text: string) => {
    if (!text.trim()) { setMisspelled([]); return; }
    try {
      const res = await fetch(`${API}/spellcheck`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
      const data = await res.json();
      setMisspelled((data.misspelled||[]).filter((m: Misspelled) => !ignored.has(m.word.toLowerCase())));
    } catch { setMisspelled([]); }
  }, [ignored]);
  function ignoreWord(word: string) {
    setIgnored(prev => new Set([...prev, word.toLowerCase()]));
    setMisspelled(prev => prev.filter(m => m.word.toLowerCase() !== word.toLowerCase()));
    setTooltip(null);
  }
  function handleEditorInput() {
    if (isComposing.current || !editorRef.current) return;
    setInput(editorRef.current.innerText); setResult(null);
  }
  function handleEditorMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (target.classList.contains("misspelled")) {
      if (tooltipTimer.current) clearTimeout(tooltipTimer.current);
      const word = target.getAttribute("data-word") || "";
      const tips = (target.getAttribute("data-tips")||"").split("|").filter(Boolean);
      const rect = target.getBoundingClientRect();
      setTooltip({word, suggestions:tips, x:rect.left, y:rect.bottom});
    } else { scheduleTooltipClose(); }
  }
  function scheduleTooltipClose() {
    if (tooltipTimer.current) clearTimeout(tooltipTimer.current);
    tooltipTimer.current = setTimeout(() => setTooltip(null), 120);
  }
  function applySuggestion(original: string, suggestion: string) {
    setInput(input.replace(new RegExp(`\\b${original}\\b`, "i"), suggestion));
    setResult(null); setTooltip(null);
  }
  async function handleTranslate() {
    const text = direction === "lun->en" ? (editorRef.current?.innerText || input) : input;
    if (!text.trim()) return;
    setLoading(true); setError(""); setResult(null);

    // ── Offline cache key ────────────────────────────────────────────────────
    const cacheKey = `tx:${direction}:${text.trim().toLowerCase()}`;

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({text, context:""}),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (preferredModel && data.translation_marian && data.translation_nllb)
        data.translation = preferredModel === "marian" ? data.translation_marian : data.translation_nllb;
      // Save to localStorage for offline use
      try { localStorage.setItem(cacheKey, JSON.stringify(data)); } catch { /* storage full */ }
      setResult(data); resetFeedback();
    } catch {
      // ── Offline fallback: check localStorage cache ───────────────────────
      try {
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
          const data = JSON.parse(cached);
          setResult({ ...data, method: "cached_offline" });
          setError("Offline — showing cached translation");
          resetFeedback();
          return;
        }
      } catch { /* ignore */ }
      setError(!navigator.onLine
        ? "You're offline and this translation isn't cached yet."
        : "Could not connect to the translation server.");
    }
    finally { setLoading(false); }
  }

  return (
    <div className="max-w-screen-xl mx-auto px-5 pt-6 pb-32 flex flex-col gap-4">

      {/* Language direction bar */}
      <div className="flex items-center bg-surface-container-lowest rounded-2xl p-3 premium-shadow border border-outline-variant/40 gap-3 flex-wrap">
        <button className="px-4 py-1.5 rounded-full bg-primary-fixed text-on-primary-fixed text-sm font-semibold flex items-center gap-1">
          {fromLabel}
        </button>
        <button onClick={swapDirection} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container transition-all active:scale-90 text-primary">
          <span className="material-symbols-outlined">swap_horiz</span>
        </button>
        <button className="px-4 py-1.5 rounded-full bg-surface-container text-on-surface-variant text-sm font-semibold flex items-center gap-1">
          {toLabel}
        </button>
        <div className="ml-auto">
          <select value={domain} onChange={e => setDomain(e.target.value)}
            className="text-xs border border-outline-variant rounded-full px-3 py-1.5 text-on-surface-variant bg-surface-container-low focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer">
            {DOMAINS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </div>
      </div>

      {/* Translation panels */}
      <div className="flex flex-col md:flex-row gap-4 min-h-[360px]">
        {/* Source panel */}
        <div className="flex-1 bg-surface-container-lowest border border-outline-variant/40 rounded-2xl premium-shadow p-5 flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs text-on-surface-variant uppercase tracking-widest font-semibold">{fromLabel}</span>
            {input && <button onClick={() => { setInput(""); setResult(null); resetFeedback(); }} className="text-outline hover:text-error transition-colors"><span className="material-symbols-outlined text-[20px]">close</span></button>}
          </div>
          {direction === "lun->en" ? (
            <div ref={editorRef} contentEditable suppressContentEditableWarning
              onInput={handleEditorInput} onMouseMove={handleEditorMouseMove} onMouseLeave={scheduleTooltipClose}
              onCompositionStart={() => { isComposing.current = true; }}
              onCompositionEnd={() => { isComposing.current = false; handleEditorInput(); }}
              onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleTranslate()}
              className="flex-grow outline-none text-lg text-on-surface min-h-[160px] whitespace-pre-wrap break-words"
              style={{fontFamily:"inherit"}} />
          ) : (
            <textarea ref={textareaRef}
              className="flex-grow outline-none text-lg text-on-surface resize-none placeholder:text-outline/50 min-h-[160px] bg-transparent"
              placeholder="Enter text to translate..."
              value={input} onChange={e => handleInputChange(e.target.value)}
              onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleTranslate()} />
          )}
          <div className="mt-3 flex justify-between items-center border-t border-outline-variant/30 pt-3">
            <span className="text-xs text-outline">{input.length} / 5000</span>
            <button onClick={() => runSpellcheck(input)} className="p-1 text-outline hover:text-primary transition-colors" title="Spellcheck">
              <span className="material-symbols-outlined text-[20px]">spellcheck</span>
            </button>
          </div>
        </div>

        {/* Translate action */}
        <div className="flex flex-row md:flex-col justify-center items-center gap-3">
          <button onClick={handleTranslate} disabled={loading || !input.trim()}
            className="bg-primary text-on-primary w-16 h-16 md:w-20 md:h-20 rounded-full shadow-xl flex items-center justify-center active:scale-90 transition-all hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed">
            <span className="material-symbols-outlined text-[32px] md:text-[40px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              {loading ? "hourglass_empty" : "translate"}
            </span>
          </button>
        </div>

        {/* Output panel */}
        <div className="flex-1 bg-surface-container-lowest border-2 border-primary-container/50 rounded-2xl premium-shadow p-5 flex flex-col overflow-y-auto">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs text-primary uppercase tracking-widest font-semibold">{toLabel}</span>
            <div className="flex items-center gap-1">
              {result?.translation && !feedbackSent && (
                <>
                  <button onClick={() => submitFeedback(1)} className={`p-1.5 rounded-full transition-colors ${feedbackRating===1 ? "text-primary bg-primary/10" : "text-outline hover:text-primary"}`} title="Good translation">
                    <span className="material-symbols-outlined text-[20px]" style={feedbackRating===1 ? {fontVariationSettings:"'FILL' 1"} : undefined}>thumb_up</span>
                  </button>
                  <button onClick={() => {setFeedbackRating(-1); setShowCorrection(true);}} className={`p-1.5 rounded-full transition-colors ${feedbackRating===-1 ? "text-error bg-error/10" : "text-outline hover:text-error"}`} title="Bad translation">
                    <span className="material-symbols-outlined text-[20px]" style={feedbackRating===-1 ? {fontVariationSettings:"'FILL' 1"} : undefined}>thumb_down</span>
                  </button>
                </>
              )}
              {feedbackSent && (
                <span className="text-xs text-primary font-medium">Thanks!</span>
              )}
              {result?.translation && (
                <button onClick={() => navigator.clipboard.writeText(result.translation||"")} className="p-1.5 rounded-full text-outline hover:text-primary transition-colors" title="Copy">
                  <span className="material-symbols-outlined text-[20px]">content_copy</span>
                </button>
              )}
            </div>
          </div>
          <div className="text-lg text-on-surface flex flex-col justify-start mb-3">
            {loading ? (
              <div className="flex items-center gap-2 text-outline">
                <div className="flex space-x-1">{[0,1,2].map(i => <div key={i} className="w-2 h-2 bg-primary-container rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}} />)}</div>
                <span className="text-sm">Translating...</span>
              </div>
            ) : result?.translation ? (
              <p className="leading-relaxed">{result.translation}</p>
            ) : error ? (
              <p className={`text-base ${error.startsWith("Offline") ? "text-tertiary" : "text-error"}`}>{error}</p>
            ) : (
              <p className="text-outline/60 italic text-base">Translation will appear here...</p>
            )}
          </div>

          {/* ── Dual model output panel — only shown when outputs meaningfully differ ── */}
          {(() => {
            const nllb = result?.translation_nllb;
            const marian = result?.translation_marian;
            if (!nllb || !marian) return null;
            // Normalise for comparison — lowercase, strip punctuation/spaces
            const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9\u0080-\uFFFF]/g, "").trim();
            const same = norm(nllb) === norm(marian);
            if (same) return null; // identical — no need to show both
            return (
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                {/* NLLB card — primary */}
                <div className="rounded-xl p-3 border border-secondary-container bg-secondary-container/20 transition-all">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container">NLLB-200</span>
                    <span className="text-[10px] text-secondary font-semibold">Primary ✓</span>
                  </div>
                  <p className="text-sm text-on-surface leading-relaxed break-words">{nllb}</p>
                </div>
                {/* MarianMT card */}
                <div className="rounded-xl p-3 border border-outline-variant/30 bg-surface-container/40 transition-all">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant">MarianMT</span>
                  </div>
                  <p className="text-sm text-on-surface leading-relaxed break-words">{marian}</p>
                </div>
              </div>
            );
          })()}

          {/* Model badges */}
          {result && (
            <div className="mt-2 flex gap-2 flex-wrap">
              {result.method === "neural_mt" && result.translation === result.translation_nllb && result.translation_nllb && !preferredModel && (
                <span className="text-xs bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded-full font-semibold">NLLB</span>
              )}
              {result.method === "neural_mt" && result.translation === result.translation_marian && !preferredModel && (
                <span className="text-xs bg-primary-fixed text-on-primary-fixed px-2 py-0.5 rounded-full font-semibold">MarianMT</span>
              )}
              {preferredModel && (
                <span className="text-xs bg-primary-fixed text-on-primary-fixed px-2 py-0.5 rounded-full font-semibold">
                  {preferredModel === "marian" ? "MarianMT" : "NLLB"} ✓
                </span>
              )}
              {result.method === "selective_rag" && (
                <span className="text-xs bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded-full font-semibold">Retrieved</span>
              )}
              {domain && (
                <span className="text-xs bg-secondary-fixed text-on-secondary-fixed px-2 py-0.5 rounded-full font-semibold">
                  {DOMAINS.find(d => d.value === domain)?.label ?? domain}
                </span>
              )}
            </div>
          )}

          {/* Feedback correction form (shows after thumbs down) */}
          {result?.translation && (
            <div className="mt-4 pt-4 border-t border-outline-variant/30 space-y-3">
              {showCorrection && feedbackRating === -1 && (
                    <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant space-y-2">
                      <p className="text-xs text-on-surface-variant font-semibold">What is wrong?</p>
                      <div className="space-y-1">
                        {ERROR_TYPES.map(type => (
                          <div key={type}>
                            <label className="flex items-center gap-2 text-xs cursor-pointer">
                              <input type="checkbox" checked={errorTypes.includes(type)} onChange={e => setErrorTypes(e.target.checked ? [...errorTypes,type] : errorTypes.filter(t=>t!==type))} className="accent-primary" />
                              <span className="text-on-surface-variant capitalize">{type === "context" ? "Lack of context" : type === "vocabulary" ? "Word missing from vocab" : type}</span>
                            </label>
                            {type === "other" && errorTypes.includes("other") && (
                              <input type="text" autoFocus className="mt-1 ml-5 w-[calc(100%-1.25rem)] border border-outline-variant rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-primary bg-surface-container-lowest" placeholder="Describe the problem..." value={otherNote} onChange={e => setOtherNote(e.target.value)} />
                            )}
                          </div>
                        ))}
                      </div>
                      <textarea className="w-full border border-outline-variant rounded-xl p-2 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-primary bg-surface-container-lowest" rows={2} placeholder="Correct translation (optional)..." value={correction} onChange={e => setCorrection(e.target.value)} />
                      <div className="flex gap-2">
                        <button onClick={() => submitFeedback(-1)} disabled={errorTypes.length===0 && !correction.trim()} className="text-xs bg-error text-on-error px-3 py-1.5 rounded-full hover:opacity-90 disabled:opacity-40 font-semibold">Submit</button>
                        <button onClick={() => {setShowCorrection(false); setFeedbackRating(null); setErrorTypes([]); setCorrection(""); setOtherNote("");}} className="text-xs text-outline hover:text-on-surface px-2">Cancel</button>
                      </div>
                    </div>
                  )}
              {feedbackSent && !modelFeedbackSent && <p className="text-xs text-primary font-semibold">Thanks for the feedback!</p>}

              {/* Model comparison — always visible when both models return output */}
              {result.translation_marian && result.translation_nllb && !modelFeedbackSent && (
                <div className="pt-2 border-t border-outline-variant/30 space-y-2">
                  <p className="text-xs text-on-surface-variant font-semibold">Which model is better?</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {([
                      ...(result.translation_marian ? [{id:"marian" as const, label:"MarianMT", text:result.translation_marian}] : []),
                      ...(result.translation_nllb   ? [{id:"nllb"   as const, label:"NLLB", text:result.translation_nllb}]   : []),
                      {id:"both" as const, label:"Both correct", text:"Both translations are accurate"},
                      {id:"none" as const, label:"Both wrong",   text:"Neither is accurate"},
                    ]).map(({id, label, text}) => (
                      <div key={id} onClick={() => setSelectedModel(id)} className={`border-2 rounded-xl p-2 cursor-pointer transition-all ${selectedModel===id?"border-primary bg-primary-fixed/30":"border-outline-variant hover:border-primary-container"}`}>
                        <div className="flex items-start gap-2">
                          <input type="radio" name="model_choice" checked={selectedModel===id} onChange={() => setSelectedModel(id)} className="mt-0.5 flex-shrink-0 accent-primary" />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-on-background mb-0.5">{label}</p>
                            <p className="text-xs text-on-surface-variant break-words">{text}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {selectedModel && <button onClick={() => submitFeedback(selectedModel==="none"?-1:1, selectedModel)} className="w-full bg-primary text-on-primary py-2 rounded-full text-xs font-semibold hover:opacity-90 transition-all">Confirm</button>}
                </div>
              )}
              {modelFeedbackSent && <p className="text-xs text-primary font-semibold">Model preference saved!</p>}

              {/* Benchmark */}
              {!benchmarkSent && (
                <div className="pt-2 border-t border-outline-variant/30">
                  <button onClick={() => setShowBenchmark(b => !b)} className="flex items-center gap-1 text-xs text-on-surface-variant hover:text-on-background font-semibold transition-colors">
                    <span className="material-symbols-outlined text-[14px]">{showBenchmark?"expand_less":"expand_more"}</span>
                    {showBenchmark ? "Hide benchmark" : "Rate translation (8 dimensions)"}
                  </button>
                  {showBenchmark && (
                    <div className="mt-3 bg-surface-container-low rounded-xl border border-outline-variant p-3 space-y-3">
                      <p className="text-xs text-on-surface font-semibold">Runyoro-Rutooro LLM Benchmark</p>
                      <div className="space-y-2">
                        {DIMS.map(dim => (
                          <div key={dim.key} className="flex items-center gap-2">
                            <div className="w-20 flex-shrink-0">
                              <span className="text-[10px] font-bold text-on-background uppercase tracking-wide cursor-help" title={dim.tooltip}>{dim.code}</span>
                              <span className="text-[10px] text-on-surface-variant block leading-tight">{dim.label}</span>
                            </div>
                            <div className="flex gap-1">
                              {[0,1,2,3,4,5].map(n => (
                                <button key={n} onClick={() => setDimScores(s => ({...s, [dim.key]: s[dim.key]===n?null:n}))}
                                  className={`w-7 h-7 rounded-full text-xs font-bold border transition-all ${dimScores[dim.key]===n?"bg-primary text-on-primary border-primary shadow":"bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:border-primary hover:text-primary"}`}>
                                  {n}
                                </button>
                              ))}
                            </div>
                            <span className="text-[10px] text-outline ml-1">{dim.weight}%</span>
                          </div>
                        ))}
                      </div>
                      {(() => { const sqs=computeSqs(dimScores); if(!sqs) return null; const band=sqsBand(sqs); return (
                        <div className="flex items-center gap-2 pt-1 border-t border-outline-variant/30">
                          <span className="text-xs text-on-surface-variant">SQS:</span>
                          <span className={`text-sm font-bold ${band.color}`}>{sqs}/100</span>
                          <span className={`text-xs font-semibold ${band.color}`}>— {band.label}</span>
                        </div>
                      );})()}
                      <button onClick={submitBenchmark} disabled={DIMS.every(d=>dimScores[d.key]===null)} className="w-full bg-primary text-on-primary py-2 rounded-full text-xs font-semibold hover:opacity-90 disabled:opacity-40 transition-all">Submit Benchmark</button>
                    </div>
                  )}
                </div>
              )}
              {benchmarkSent && sqsResult !== null && (
                <div className="pt-2 border-t border-outline-variant/30">
                  <p className={`text-xs font-semibold flex items-center gap-1 ${sqsBand(sqsResult).color}`}>
                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                    Benchmark saved · SQS {sqsResult}/100 — {sqsBand(sqsResult).label}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Spellcheck tooltip */}
      {tooltip && (
        <div className="fixed z-50 bg-inverse-surface text-inverse-on-surface rounded-xl p-3 shadow-xl min-w-[140px]"
          style={{top: tooltip.y+6, left: tooltip.x}}
          onMouseEnter={() => { if(tooltipTimer.current) clearTimeout(tooltipTimer.current); }}
          onMouseLeave={scheduleTooltipClose}>
          <p className="text-xs opacity-60 mb-1">Did you mean?</p>
          {tooltip.suggestions.length > 0 ? tooltip.suggestions.map(s => (
            <button key={s} className="block w-full text-left text-primary-fixed hover:bg-white/10 px-2 py-1.5 rounded text-sm"
              onMouseDown={e => { e.preventDefault(); applySuggestion(tooltip.word, s); }}>{s}</button>
          )) : <p className="text-xs opacity-50 italic">No suggestions</p>}
          <div className="border-t border-white/10 mt-1 pt-1">
            <button className="text-xs opacity-50 hover:opacity-100 px-2 py-1" onMouseDown={e => { e.preventDefault(); ignoreWord(tooltip.word); }}>Ignore</button>
          </div>
        </div>
      )}
    </div>
  );
}
