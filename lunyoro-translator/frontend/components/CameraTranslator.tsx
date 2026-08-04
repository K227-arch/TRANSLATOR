"use client";
import { useState, useRef, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TranslatedRegion {
  original: string;
  translated: string;
  confidence: number;
  bbox_norm: { x: number; y: number; width: number; height: number };
}
interface ClassificationResult {
  label_en: string;
  label_lun: string;
  confidence: number;
  method: string;
}
type Direction = "en->lun" | "lun->en";
type Mode = "ocr" | "classify";

export default function CameraTranslator() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [cameraActive, setCameraActive] = useState(false);
  const [regions, setRegions] = useState<TranslatedRegion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [direction, setDirection] = useState<Direction>("en->lun");
  const [paused, setPaused] = useState(false);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [showOverlay, setShowOverlay] = useState(true);
  const [showResults, setShowResults] = useState(false);
  const [scanCount, setScanCount] = useState(0);
  const [mode, setMode] = useState<Mode>("ocr");
  const [classifications, setClassifications] = useState<ClassificationResult[]>([]);
  const [classifyLoading, setClassifyLoading] = useState(false);

  const attachStream = useCallback((stream: MediaStream) => {
    const video = videoRef.current;
    if (!video) return;
    if (video.srcObject === stream) return;
    video.srcObject = stream;
    video.onloadedmetadata = () => { video.play().catch(() => {}); };
    setTimeout(() => { if (video.paused) video.play().catch(() => {}); }, 200);
  }, []);

  useEffect(() => {
    if (cameraActive && streamRef.current) attachStream(streamRef.current);
  }, [cameraActive, attachStream]);

  const startCamera = useCallback(async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera not supported (requires HTTPS or localhost).");
      return;
    }
    const tryStart = async (c: MediaStreamConstraints) => {
      const stream = await navigator.mediaDevices.getUserMedia(c);
      streamRef.current = stream;
      setCapturedImage(null); setRegions([]); setScanCount(0);
      setCameraActive(true);
    };
    try {
      await tryStart({ video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } } });
    } catch {
      try { await tryStart({ video: true }); }
      catch (e) {
        const msg = e instanceof Error ? e.message : "Unknown error";
        setError(msg.includes("denied") ? "Camera permission denied." : `Camera error: ${msg}`);
      }
    }
  }, [facingMode]);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraActive(false);
  }, []);

  const captureAndTranslate = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || loading) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video.videoWidth) return;
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    setLoading(true);
    try {
      const res = await fetch(`${API}/ocr-translate-base64`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: canvas.toDataURL("image/jpeg", 0.92), direction }),
      });
      const data = await res.json();
      if (data.error) setError(data.error);
      else { setRegions(data.regions || []); setScanCount(c => c + 1); setError(""); }
    } catch { setError("Could not connect to translation server."); }
    finally { setLoading(false); }
  }, [direction, loading]);

  useEffect(() => {
    if (cameraActive && !paused) intervalRef.current = setInterval(captureAndTranslate, 3000);
    else { if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; } }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [cameraActive, paused, captureAndTranslate]);

  useEffect(() => () => { stopCamera(); }, [stopCamera]);

  const switchCamera = () => { stopCamera(); setFacingMode(p => p === "environment" ? "user" : "environment"); };
  useEffect(() => { if (cameraActive) startCamera(); }, [facingMode]); // eslint-disable-line

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setLoading(true); setError(""); setCapturedImage(URL.createObjectURL(file)); stopCamera();
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch(`${API}/ocr-translate?direction=${direction}`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.error) setError(data.error); else setRegions(data.regions || []);
    } catch { setError("Could not connect to translation server."); }
    finally { setLoading(false); }
  };

  const handleClassifyUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setClassifyLoading(true); setError(""); setCapturedImage(URL.createObjectURL(file)); setClassifications([]); stopCamera();
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch(`${API}/classify-image?top_k=5`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.detail) setError(data.detail); else setClassifications(data.predictions || []);
    } catch { setError("Could not connect to translation server."); }
    finally { setClassifyLoading(false); }
  };

  return (
    <div className="w-full">
      <canvas ref={canvasRef} className="hidden" />

      {/* Always-in-DOM video element */}
      <video ref={videoRef} playsInline muted autoPlay
        onLoadedMetadata={e => { (e.target as HTMLVideoElement).play().catch(() => {}); }}
        style={{
          position: "fixed", top: 0, left: 0,
          width: "100vw", height: "calc(100vh - 80px)",
          objectFit: "cover", background: "#000", display: "block",
          zIndex: cameraActive ? 39 : -999, opacity: cameraActive ? 1 : 0, pointerEvents: "none",
        }}
      />

      {/* ── CAMERA ACTIVE OVERLAY ── */}
      {cameraActive && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "calc(100vh - 80px)", zIndex: 40 }}>
          <div style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden" }}>

            {/* Viewfinder corners */}
            <div className="absolute inset-8 pointer-events-none">
              {(["top-0 left-0 border-t-2 border-l-2 rounded-tl-lg",
                "top-0 right-0 border-t-2 border-r-2 rounded-tr-lg",
                "bottom-0 left-0 border-b-2 border-l-2 rounded-bl-lg",
                "bottom-0 right-0 border-b-2 border-r-2 rounded-br-lg"] as const).map((pos, i) => (
                <div key={i} className={`absolute w-8 h-8 border-white/60 ${pos}`} />
              ))}
            </div>

            {/* Scanline */}
            {!paused && (
              <div className="absolute inset-x-8 top-8 bottom-8 pointer-events-none overflow-hidden">
                <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary to-transparent opacity-80"
                  style={{ animation: "scanline 2.5s ease-in-out infinite" }} />
              </div>
            )}

            {/* Translation overlays on video */}
            {showOverlay && regions.length > 0 && (
              <div className="absolute inset-0 pointer-events-none">
                {regions.map((r, i) => (
                  <div key={i} className="absolute flex items-center justify-center"
                    style={{ left: `${r.bbox_norm.x * 100}%`, top: `${r.bbox_norm.y * 100}%`, width: `${r.bbox_norm.width * 100}%`, height: `${r.bbox_norm.height * 100}%` }}>
                    <div className="absolute inset-0 bg-black/75 backdrop-blur-[2px] rounded" />
                    <span className="relative text-green-300 font-bold text-center px-1 leading-tight drop-shadow-lg"
                      style={{ fontSize: `clamp(9px, ${Math.max(r.bbox_norm.height * 50, 2)}vw, 20px)` }}>
                      {r.translated}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Top bar */}
            <div className="absolute top-0 inset-x-0 bg-gradient-to-b from-black/60 to-transparent p-4 pt-5">
              <div className="flex items-center justify-between">
                <button onClick={stopCamera} className="w-9 h-9 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center active:scale-90 transition-all">
                  <span className="material-symbols-outlined text-white text-[20px]">close</span>
                </button>
                <button onClick={() => setDirection(d => d === "en->lun" ? "lun->en" : "en->lun")}
                  className="bg-white/15 backdrop-blur-md rounded-full px-3 py-1.5 flex items-center gap-1.5 active:scale-95 transition-all">
                  <span className="text-white text-xs font-medium">{direction === "en->lun" ? "EN" : "LUN"}</span>
                  <span className="material-symbols-outlined text-white/80 text-[14px]">swap_horiz</span>
                  <span className="text-white text-xs font-medium">{direction === "en->lun" ? "LUN" : "EN"}</span>
                </button>
                <div className="flex items-center gap-2">
                  {loading && <div className="w-9 h-9 bg-primary/80 backdrop-blur-md rounded-full flex items-center justify-center">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /></div>}
                  {!loading && regions.length > 0 && <div className="bg-green-500/80 backdrop-blur-md rounded-full px-2.5 py-1 text-white text-[10px] font-bold">{regions.length} found</div>}
                  {!loading && regions.length === 0 && scanCount > 0 && <div className="bg-yellow-500/80 backdrop-blur-md rounded-full px-2.5 py-1 text-white text-[10px] font-bold">No text</div>}
                </div>
              </div>
            </div>

            {/* Bottom controls */}
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/70 to-transparent p-6 pb-8">
              <div className="flex items-center justify-center gap-5">
                <label className="w-12 h-12 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center cursor-pointer active:scale-90 transition-all">
                  <span className="material-symbols-outlined text-white text-[22px]">photo_library</span>
                  <input type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
                </label>
                <button onClick={captureAndTranslate} disabled={loading}
                  className="w-[72px] h-[72px] rounded-full border-[4px] border-white/80 flex items-center justify-center active:scale-90 transition-all disabled:opacity-50">
                  <div className={`w-[58px] h-[58px] rounded-full flex items-center justify-center transition-all ${loading ? "bg-primary/80" : "bg-white"}`}>
                    <span className={`material-symbols-outlined text-[30px] ${loading ? "text-white animate-pulse" : "text-black"}`}>
                      {loading ? "hourglass_top" : "center_focus_strong"}
                    </span>
                  </div>
                </button>
                <button onClick={switchCamera} className="w-12 h-12 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center active:scale-90 transition-all">
                  <span className="material-symbols-outlined text-white text-[22px]">flip_camera_ios</span>
                </button>
              </div>
              <div className="flex items-center justify-center gap-3 mt-4 flex-wrap">
                <button onClick={() => setPaused(p => !p)}
                  className={`px-3 py-1.5 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${paused ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40" : "bg-white/10 text-white/70 border border-white/20"}`}>
                  <span className="material-symbols-outlined text-[14px]">{paused ? "play_arrow" : "pause"}</span>
                  {paused ? "Resume" : "Auto-scan"}
                </button>
                <button onClick={() => setShowOverlay(s => !s)}
                  className={`px-3 py-1.5 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${showOverlay ? "bg-green-500/20 text-green-300 border border-green-500/40" : "bg-white/10 text-white/70 border border-white/20"}`}>
                  <span className="material-symbols-outlined text-[14px]">{showOverlay ? "visibility" : "visibility_off"}</span>
                  Overlay
                </button>
                {regions.length > 0 && (
                  <button onClick={() => setShowResults(s => !s)} className="px-3 py-1.5 rounded-full text-[11px] font-semibold flex items-center gap-1 bg-white/10 text-white/70 border border-white/20 transition-all">
                    <span className="material-symbols-outlined text-[14px]">list</span>Results
                  </button>
                )}
              </div>
            </div>

            {/* Results panel */}
            {showResults && regions.length > 0 && (
              <div className="absolute bottom-36 inset-x-4 max-h-[40vh] bg-black/85 backdrop-blur-lg rounded-2xl overflow-hidden border border-white/10">
                <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between">
                  <span className="text-white/80 text-xs font-semibold">{regions.length} translations</span>
                  <button onClick={() => setShowResults(false)} className="text-white/50 active:text-white">
                    <span className="material-symbols-outlined text-[18px]">close</span>
                  </button>
                </div>
                <div className="overflow-y-auto max-h-[30vh] px-4 py-3 space-y-2">
                  {regions.map((r, i) => (
                    <p key={i} className="text-sm leading-relaxed">
                      <span className="text-white/50">{r.original}</span>{" → "}
                      <span className="text-green-300 font-medium">{r.translated}</span>
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
          <style jsx>{`@keyframes scanline { 0%, 100% { top: 0; } 50% { top: 100%; } }`}</style>
        </div>
      )}

      {/* ── INACTIVE / UPLOAD STATE ── */}
      {!cameraActive && (
        <div className="w-full">
          {/* Scrollable content, centered, responsive max-width */}
          <div className="w-full px-4 sm:px-6 pt-4 pb-8 mx-auto"
            style={{ maxWidth: "480px" }}>
            <div className="flex flex-col gap-4">

              {/* Captured image preview */}
              {capturedImage && (
                <div className="relative w-full rounded-2xl overflow-hidden shadow-xl border border-outline-variant/30"
                  style={{ aspectRatio: "4/3" }}>
                  <img src={capturedImage} alt="Captured" className="w-full h-full object-cover" />
                  {showOverlay && regions.length > 0 && (
                    <div className="absolute inset-0 pointer-events-none">
                      {regions.map((r, i) => (
                        <div key={i} className="absolute flex items-center justify-center"
                          style={{ left: `${r.bbox_norm.x * 100}%`, top: `${r.bbox_norm.y * 100}%`, width: `${r.bbox_norm.width * 100}%`, height: `${r.bbox_norm.height * 100}%` }}>
                          <div className="absolute inset-0 bg-black/75 backdrop-blur-[2px] rounded" />
                          <span className="relative text-green-300 font-bold text-center px-1 leading-tight"
                            style={{ fontSize: `clamp(8px, ${r.bbox_norm.height * 50}vw, 18px)` }}>{r.translated}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {(loading || classifyLoading) && (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                      <div className="bg-black/70 backdrop-blur-md rounded-2xl px-5 py-3 flex items-center gap-2">
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span className="text-white text-sm font-medium">{classifyLoading ? "Identifying..." : "Scanning..."}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Mode toggle */}
              <div className="w-full flex bg-surface-container rounded-xl p-1">
                {(["ocr", "classify"] as const).map(m => (
                  <button key={m} onClick={() => { setMode(m); if (m === "ocr") setClassifications([]); else setRegions([]); }}
                    className={`flex-1 py-2.5 rounded-lg text-sm font-semibold flex items-center justify-center gap-1.5 transition-all min-w-0 ${mode === m ? "bg-surface-container-lowest text-on-background shadow" : "text-on-surface-variant"}`}>
                    <span className="material-symbols-outlined text-[16px] shrink-0">{m === "ocr" ? "text_fields" : "image_search"}</span>
                    <span className="truncate">{m === "ocr" ? "Text OCR" : "Identify"}</span>
                  </button>
                ))}
              </div>

              {/* Direction toggle — OCR only */}
              {mode === "ocr" && (
                <div className="w-full flex bg-surface-container-lowest border border-outline-variant/40 rounded-full p-1">
                  {([["en->lun", "English → Runyoro"], ["lun->en", "Runyoro → English"]] as const).map(([val, label]) => (
                    <button key={val} onClick={() => setDirection(val as Direction)}
                      className={`flex-1 py-2 rounded-full text-sm font-medium text-center transition-all min-w-0 ${direction === val ? "bg-primary text-on-primary shadow-sm" : "text-on-surface-variant"}`}>
                      <span className="block truncate px-1">{label}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Action buttons */}
              {mode === "ocr" ? (
                <div className="w-full grid grid-cols-2 gap-3">
                  <button onClick={startCamera}
                    className="flex flex-col items-center justify-center gap-2 bg-primary text-on-primary py-6 rounded-2xl shadow-lg active:scale-95 transition-all">
                    <span className="material-symbols-outlined text-[30px]">photo_camera</span>
                    <span className="text-xs font-semibold">Open Camera</span>
                  </button>
                  <label className="flex flex-col items-center justify-center gap-2 bg-surface-container-lowest border border-outline-variant/40 text-on-surface py-6 rounded-2xl cursor-pointer active:scale-95 transition-all shadow-sm">
                    <span className="material-symbols-outlined text-[30px] text-primary">photo_library</span>
                    <span className="text-xs font-medium">Upload Image</span>
                    <input type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
                  </label>
                </div>
              ) : (
                <label className="w-full flex flex-col items-center justify-center gap-2 bg-primary text-on-primary py-6 rounded-2xl shadow-lg cursor-pointer active:scale-95 transition-all">
                  <span className="material-symbols-outlined text-[30px]">image_search</span>
                  <span className="text-xs font-semibold">Upload Photo to Identify</span>
                  <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleClassifyUpload} />
                </label>
              )}

              {/* Error */}
              {error && (
                <div className="w-full bg-error-container/30 border border-error/30 rounded-xl px-4 py-3 text-sm text-error text-center break-words">
                  <span className="material-symbols-outlined text-[16px] align-middle mr-1">error</span>{error}
                </div>
              )}

              {/* Classification results */}
              {classifications.length > 0 && (
                <div className="w-full bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
                  <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center gap-2 bg-surface-container/30">
                    <span className="material-symbols-outlined text-primary text-[18px]">image_search</span>
                    <h3 className="text-sm font-semibold text-on-background">Objects Identified</h3>
                  </div>
                  <div className="px-4 py-3 space-y-3">
                    {classifications.map((item, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-on-surface-variant truncate">{item.label_en}</p>
                          <p className="text-base font-semibold text-primary truncate">{item.label_lun}</p>
                        </div>
                        <span className="text-xs text-on-surface-variant/60 bg-surface-container rounded-full px-2 py-0.5 shrink-0">
                          {(item.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* OCR results */}
              {regions.length > 0 && (
                <div className="w-full bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
                  <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center justify-between bg-surface-container/30">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="material-symbols-outlined text-primary text-[18px] shrink-0">translate</span>
                      <h3 className="text-sm font-semibold text-on-background truncate">{regions.length} Translation{regions.length > 1 ? "s" : ""}</h3>
                    </div>
                    <button onClick={() => setShowOverlay(s => !s)} className="text-xs text-primary font-medium shrink-0 ml-2">
                      {showOverlay ? "Hide" : "Show"} overlay
                    </button>
                  </div>
                  <div className="px-4 py-3 max-h-60 overflow-y-auto space-y-2">
                    {regions.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm leading-relaxed">
                        <span className="text-on-surface-variant min-w-0 break-words" style={{ flex: "1 1 0" }}>{r.original}</span>
                        <span className="text-on-surface-variant/40 shrink-0 pt-0.5">→</span>
                        <span className="font-semibold text-primary min-w-0 break-words" style={{ flex: "1 1 0" }}>{r.translated}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty state */}
              {!capturedImage && regions.length === 0 && classifications.length === 0 && (
                <div className="w-full text-center py-6 px-2">
                  <div className="flex justify-center items-center gap-1 mb-3">
                    {(mode === "ocr"
                      ? ["photo_camera", "arrow_forward", "text_fields", "arrow_forward", "g_translate"]
                      : ["image_search", "arrow_forward", "label", "arrow_forward", "g_translate"]
                    ).map((icon, i) => (
                      <span key={i} className={`material-symbols-outlined ${i % 2 === 0 ? "text-primary text-[26px]" : "text-on-surface-variant/30 text-[16px]"}`}>{icon}</span>
                    ))}
                  </div>
                  <p className="text-sm leading-relaxed text-on-surface-variant">
                    {mode === "ocr"
                      ? "Point your camera at signs, documents, or menus to instantly translate text into Runyoro/Rutooro."
                      : "Upload a photo of any object to identify it and get its Runyoro/Rutooro name."}
                  </p>
                </div>
              )}

            </div>
          </div>
        </div>
      )}
    </div>
  );
}
