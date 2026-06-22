"use client";
import { useState, useRef, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Lang = "English" | "Lunyoro" | "Rutooro";

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}
interface SpeechRecognition extends EventTarget {
  lang: string; continuous: boolean; interimResults: boolean;
  start(): void; stop(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}
interface SpeechRecognitionEvent extends Event { results: SpeechRecognitionResultList; }
interface SpeechRecognitionErrorEvent extends Event { error: string; }
interface SpeechRecognitionResultList { readonly length: number; [index: number]: SpeechRecognitionResult; }
interface SpeechRecognitionResult { readonly length: number; [index: number]: SpeechRecognitionAlternative; }
interface SpeechRecognitionAlternative { transcript: string; }

export default function VoiceTranslator() {
  const [lang, setLang]           = useState<Lang>("English");
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [translation, setTranslation] = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [pulse, setPulse]         = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const transcriptRef  = useRef("");

  useEffect(() => { transcriptRef.current = transcript; }, [transcript]);

  function getSpeechLang(l: Lang) { return l === "English" ? "en-US" : "en-UG"; }

  function startRecording() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setError("Speech recognition is not supported. Try Chrome."); return; }
    setError(""); setTranscript(""); setTranslation("");
    const rec = new SR();
    rec.lang = getSpeechLang(lang); rec.continuous = false; rec.interimResults = true;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const text = Array.from({length: e.results.length}, (_,i) => e.results[i][0].transcript).join("");
      setTranscript(text); transcriptRef.current = text; setPulse(true);
    };
    rec.onerror = (e: SpeechRecognitionErrorEvent) => { setError(`Microphone error: ${e.error}`); setRecording(false); };
    rec.onend = () => { setRecording(false); if (transcriptRef.current.trim()) translateVoice(transcriptRef.current); };
    recognitionRef.current = rec;
    rec.start(); setRecording(true);
  }
  function stopRecording() { recognitionRef.current?.stop(); setRecording(false); }

  async function translateVoice(text: string) {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const endpoint = lang === "English" ? "/translate" : "/translate-reverse";
      const res = await fetch(`${API}${endpoint}`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
      const data = await res.json();
      setTranslation(data.translation || "No translation found.");
      if (data.translation) {
        const utter = new SpeechSynthesisUtterance(data.translation);
        utter.lang = lang === "English" ? "en-UG" : "en-US";
        window.speechSynthesis.speak(utter);
      }
    } catch { setError("Could not connect to the translation server."); }
    finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col items-center gap-8 py-4">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-on-background">Voice Translation</h2>
        <p className="text-on-surface-variant mt-1 text-sm max-w-xs mx-auto leading-relaxed">
          Speak in your chosen language for instant Runyoro-Rutooro or English translation.
        </p>
      </div>

      {/* Mic button */}
      <div className="relative flex items-center justify-center">
        {recording && (
          <>
            <span className="absolute w-44 h-44 rounded-full bg-primary-container/30 animate-ping" />
            <span className="absolute w-36 h-36 rounded-full bg-primary-container/20 animate-ping" style={{animationDelay:"0.2s"}} />
          </>
        )}
        <button onClick={recording ? stopRecording : startRecording}
          className={`relative z-10 w-32 h-32 rounded-full flex items-center justify-center shadow-xl transition-all duration-200 active:scale-95 ${recording ? "bg-primary text-on-primary scale-105" : "bg-surface-container-lowest text-primary border-2 border-primary-container hover:bg-primary-fixed/20"}`}>
          <span className="material-symbols-outlined text-[52px]" style={{fontVariationSettings: recording ? "'FILL' 1" : "'FILL' 0"}}>mic</span>
        </button>
      </div>

      {/* Start/Stop button */}
      <button onClick={recording ? stopRecording : startRecording}
        className={`flex items-center gap-2 px-8 py-3 rounded-xl font-semibold text-sm transition-all active:scale-95 shadow-md ${recording ? "bg-error text-on-error" : "bg-primary text-on-primary hover:opacity-90"}`}>
        <span className="material-symbols-outlined text-[18px]" style={{fontVariationSettings:"'FILL' 1"}}>{recording ? "stop_circle" : "mic"}</span>
        {recording ? "Stop Recording" : "Start Speaking"}
      </button>

      {/* Language selector */}
      <div className="flex gap-2 flex-wrap justify-center">
        {(["English","Lunyoro","Rutooro"] as Lang[]).map(l => (
          <button key={l} onClick={() => {setLang(l); setTranscript(""); setTranslation("");}}
            className={`px-5 py-2 rounded-full text-sm font-semibold border transition-all ${lang===l ? "bg-primary text-on-primary border-primary shadow" : "bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:border-primary hover:text-primary"}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Transcript + translation */}
      {(transcript || loading || translation) && (
        <div className="w-full max-w-md space-y-3">
          {transcript && (
            <div className="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/40 premium-shadow">
              <p className="text-xs text-on-surface-variant uppercase tracking-widest font-semibold mb-1">You said</p>
              <p className={`text-sm text-on-surface transition-opacity ${pulse ? "opacity-60" : "opacity-100"}`}>{transcript}</p>
            </div>
          )}
          {loading && (
            <div className="flex items-center justify-center gap-2 text-on-surface-variant">
              <div className="flex space-x-1">{[0,1,2].map(i => <div key={i} className="w-2 h-2 bg-primary-container rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}} />)}</div>
              <span className="text-sm">Translating...</span>
            </div>
          )}
          {translation && (
            <div className="bg-primary-fixed/30 rounded-2xl p-4 border border-primary-container/50 premium-shadow">
              <p className="text-xs text-on-primary-fixed-variant uppercase tracking-widest font-semibold mb-1">
                {lang === "English" ? "Runyoro / Rutooro" : "English"}
              </p>
              <p className="text-base font-semibold text-on-background">{translation}</p>
              <button onClick={() => { const u = new SpeechSynthesisUtterance(translation); u.lang = lang==="English"?"en-UG":"en-US"; window.speechSynthesis.speak(u); }}
                className="mt-2 flex items-center gap-1 text-xs text-on-surface-variant hover:text-primary transition-colors">
                <span className="material-symbols-outlined text-[16px]">volume_up</span> Play again
              </button>
            </div>
          )}
        </div>
      )}

      {error && <p className="text-sm text-error text-center max-w-xs">{error}</p>}
    </div>
  );
}
