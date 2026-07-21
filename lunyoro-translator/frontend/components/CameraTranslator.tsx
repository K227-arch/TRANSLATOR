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

  // Start camera
  const startCamera = useCallback(async () => {
    setError("");
    try {
      // Try preferred facing mode first
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      streamRef.current = stream;
      setCameraActive(true);
      setCapturedImage(null);
      setRegions([]);
      setScanCount(0);
    } catch {
      // Fallback: try any available camera (webcam on desktop)
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        streamRef.current = stream;
        setCameraActive(true);
        setCapturedImage(null);
        setRegions([]);
        setScanCount(0);
      } catch {
        setError("Could not access camera. Please allow camera permissions.");
      }
    }
  }, [facingMode]);

  // Stop camera
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setCameraActive(false);
  }, []);

  // Capture frame and send to OCR
  const captureAndTranslate = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || loading) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    const imageData = canvas.toDataURL("image/jpeg", 0.75);
    setLoading(true);

    try {
      const res = await fetch(`${API}/ocr-translate-base64`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: imageData, direction }),
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setRegions(data.regions || []);
        setScanCount((c) => c + 1);
        setError("");
      }
    } catch {
      setError("Could not connect to translation server.");
    } finally {
      setLoading(false);
    }
  }, [direction, loading]);

  // Auto-capture mode
  useEffect(() => {
    if (cameraActive && !paused) {
      intervalRef.current = setInterval(captureAndTranslate, 3000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [cameraActive, paused, captureAndTranslate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => { stopCamera(); };
  }, [stopCamera]);

  // Switch camera
  const switchCamera = () => {
    stopCamera();
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  };
  useEffect(() => {
    if (cameraActive) startCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode]);

  // Upload image from gallery
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError("");
    setCapturedImage(URL.createObjectURL(file));
    stopCamera();

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/ocr-translate?direction=${direction}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setRegions(data.regions || []);
      }
    } catch {
      setError("Could not connect to translation server.");
    } finally {
      setLoading(false);
    }
  };

  // Upload image for object classification
  const handleClassifyUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setClassifyLoading(true);
    setError("");
    setCapturedImage(URL.createObjectURL(file));
    setClassifications([]);
    stopCamera();

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/classify-image?top_k=5`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.detail) {
        setError(data.detail);
      } else {
        setClassifications(data.predictions || []);
      }
    } catch {
      setError("Could not connect to translation server.");
    } finally {
      setClassifyLoading(false);
    }
  };

  // ── Full-screen camera active view ─────────────────────────────────
  if (cameraActive) {
    return (
      <div className="fixed inset-0 z-50 bg-black flex flex-col">
        {/* Camera feed — fills screen */}
        <div className="relative flex-1 overflow-hidden">
          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover"
            playsInline
            muted
            autoPlay
          />

          {/* Viewfinder corners */}
          <div className="absolute inset-8 pointer-events-none">
            <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-white/60 rounded-tl-lg" />
            <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-white/60 rounded-tr-lg" />
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-white/60 rounded-bl-lg" />
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-white/60 rounded-br-lg" />
          </div>

          {/* Scan line animation */}
          {!paused && (
            <div className="absolute inset-x-8 top-8 bottom-8 pointer-events-none overflow-hidden">
              <div
                className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary to-transparent opacity-80"
                style={{ animation: "scanline 2.5s ease-in-out infinite" }}
              />
            </div>
          )}

          {/* Translation overlays */}
          {showOverlay && regions.length > 0 && (
            <div className="absolute inset-0 pointer-events-none">
              {regions.map((region, i) => (
                <div
                  key={i}
                  className="absolute flex items-center justify-center"
                  style={{
                    left: `${region.bbox_norm.x * 100}%`,
                    top: `${region.bbox_norm.y * 100}%`,
                    width: `${region.bbox_norm.width * 100}%`,
                    height: `${region.bbox_norm.height * 100}%`,
                  }}
                >
                  <div className="absolute inset-0 bg-black/75 backdrop-blur-[2px] rounded" />
                  <span
                    className="relative text-green-300 font-bold text-center px-1 leading-tight drop-shadow-lg"
                    style={{
                      fontSize: `clamp(9px, ${Math.max(region.bbox_norm.height * 50, 2)}vw, 20px)`,
                    }}
                  >
                    {region.translated}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Top status bar */}
          <div className="absolute top-0 inset-x-0 bg-gradient-to-b from-black/60 to-transparent p-4 pt-5">
            <div className="flex items-center justify-between">
              <button
                onClick={() => { stopCamera(); }}
                className="w-9 h-9 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center active:scale-90 transition-all"
              >
                <span className="material-symbols-outlined text-white text-[20px]">close</span>
              </button>

              {/* Direction pill */}
              <button
                onClick={() => setDirection(direction === "en->lun" ? "lun->en" : "en->lun")}
                className="bg-white/15 backdrop-blur-md rounded-full px-3 py-1.5 flex items-center gap-1.5 active:scale-95 transition-all"
              >
                <span className="text-white text-xs font-medium">
                  {direction === "en->lun" ? "EN" : "LUN"}
                </span>
                <span className="material-symbols-outlined text-white/80 text-[14px]">swap_horiz</span>
                <span className="text-white text-xs font-medium">
                  {direction === "en->lun" ? "LUN" : "EN"}
                </span>
              </button>

              {/* Status */}
              <div className="flex items-center gap-2">
                {loading && (
                  <div className="w-9 h-9 bg-primary/80 backdrop-blur-md rounded-full flex items-center justify-center">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  </div>
                )}
                {!loading && regions.length > 0 && (
                  <div className="bg-green-500/80 backdrop-blur-md rounded-full px-2.5 py-1 text-white text-[10px] font-bold">
                    {regions.length} found
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom controls */}
          <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/70 to-transparent p-6 pb-8">
            <div className="flex items-center justify-center gap-5">
              {/* Gallery / Upload */}
              <label className="w-12 h-12 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center cursor-pointer active:scale-90 transition-all">
                <span className="material-symbols-outlined text-white text-[22px]">photo_library</span>
                <input type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
              </label>

              {/* Main capture button */}
              <button
                onClick={captureAndTranslate}
                disabled={loading}
                className="w-[72px] h-[72px] rounded-full border-[4px] border-white/80 flex items-center justify-center active:scale-90 transition-all disabled:opacity-50"
              >
                <div className={`w-[58px] h-[58px] rounded-full flex items-center justify-center transition-all ${loading ? "bg-primary/80" : "bg-white"}`}>
                  <span className={`material-symbols-outlined text-[30px] ${loading ? "text-white animate-pulse" : "text-black"}`}>
                    {loading ? "hourglass_top" : "center_focus_strong"}
                  </span>
                </div>
              </button>

              {/* Switch camera */}
              <button
                onClick={switchCamera}
                className="w-12 h-12 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center active:scale-90 transition-all"
              >
                <span className="material-symbols-outlined text-white text-[22px]">flip_camera_ios</span>
              </button>
            </div>

            {/* Secondary controls row */}
            <div className="flex items-center justify-center gap-4 mt-4">
              <button
                onClick={() => setPaused(!paused)}
                className={`px-3 py-1.5 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${
                  paused
                    ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40"
                    : "bg-white/10 text-white/70 border border-white/20"
                }`}
              >
                <span className="material-symbols-outlined text-[14px]">
                  {paused ? "play_arrow" : "pause"}
                </span>
                {paused ? "Resume" : "Auto-scan"}
              </button>

              <button
                onClick={() => setShowOverlay(!showOverlay)}
                className={`px-3 py-1.5 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${
                  showOverlay
                    ? "bg-green-500/20 text-green-300 border border-green-500/40"
                    : "bg-white/10 text-white/70 border border-white/20"
                }`}
              >
                <span className="material-symbols-outlined text-[14px]">
                  {showOverlay ? "visibility" : "visibility_off"}
                </span>
                Overlay
              </button>

              {regions.length > 0 && (
                <button
                  onClick={() => setShowResults(!showResults)}
                  className="px-3 py-1.5 rounded-full text-[11px] font-semibold flex items-center gap-1 bg-white/10 text-white/70 border border-white/20 transition-all"
                >
                  <span className="material-symbols-outlined text-[14px]">list</span>
                  Results
                </button>
              )}
            </div>
          </div>

          {/* Results panel (slide up) */}
          {showResults && regions.length > 0 && (
            <div className="absolute bottom-36 inset-x-4 max-h-[40vh] bg-black/85 backdrop-blur-lg rounded-2xl overflow-hidden border border-white/10">
              <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between">
                <span className="text-white/80 text-xs font-semibold">{regions.length} translations</span>
                <button onClick={() => setShowResults(false)} className="text-white/50 active:text-white">
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>
              <div className="overflow-y-auto max-h-[30vh] px-4 py-3 space-y-2">
                {Array.from({ length: Math.ceil(regions.length / 2) }, (_, i) => {
                  const pair = regions.slice(i * 2, i * 2 + 2);
                  return (
                    <p key={i} className="text-sm leading-relaxed">
                      {pair.map((region, j) => (
                        <span key={j}>
                          <span className="text-white/50">{region.original}</span>
                          {" → "}
                          <span className="text-green-300 font-medium">{region.translated}</span>
                          {j === 0 && pair.length > 1 && <span className="text-white/20">{" · "}</span>}
                        </span>
                      ))}
                    </p>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Hidden canvas */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Scan line keyframe style */}
        <style jsx>{`
          @keyframes scanline {
            0%, 100% { top: 0; }
            50% { top: 100%; }
          }
        `}</style>
      </div>
    );
  }

  // ── Inactive / Upload state ────────────────────────────────────────
  return (
    <div className="flex flex-col gap-6 py-2 w-full items-center justify-between" style={{ minWidth: 0, minHeight: "calc(100vh - 160px)" }}>
      {/* Top section */}
      <div className="flex flex-col items-center gap-6 w-full">
        {/* Uploaded image with results */}
        {capturedImage && (
        <div className="relative w-full max-w-lg aspect-[4/3] rounded-2xl overflow-hidden shadow-xl border border-outline-variant/30">
          <img src={capturedImage} alt="Captured" className="w-full h-full object-cover" />

          {/* Overlay */}
          {showOverlay && regions.length > 0 && (
            <div className="absolute inset-0 pointer-events-none">
              {regions.map((region, i) => (
                <div
                  key={i}
                  className="absolute flex items-center justify-center"
                  style={{
                    left: `${region.bbox_norm.x * 100}%`,
                    top: `${region.bbox_norm.y * 100}%`,
                    width: `${region.bbox_norm.width * 100}%`,
                    height: `${region.bbox_norm.height * 100}%`,
                  }}
                >
                  <div className="absolute inset-0 bg-black/75 backdrop-blur-[2px] rounded" />
                  <span
                    className="relative text-green-300 font-bold text-center px-1 leading-tight"
                    style={{ fontSize: `clamp(9px, ${region.bbox_norm.height * 50}vw, 18px)` }}
                  >
                    {region.translated}
                  </span>
                </div>
              ))}
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
              <div className="bg-black/70 backdrop-blur-md rounded-2xl px-5 py-3 flex items-center gap-2">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span className="text-white text-sm font-medium">Scanning...</span>
              </div>
            </div>
          )}

          {classifyLoading && (
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
              <div className="bg-black/70 backdrop-blur-md rounded-2xl px-5 py-3 flex items-center gap-2">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span className="text-white text-sm font-medium">Identifying objects...</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mode toggle: OCR vs Classify */}
      <div className="flex items-center bg-surface-container-lowest border border-outline-variant/40 rounded-full p-1 shadow-sm">
        <button
          onClick={() => { setMode("ocr"); setClassifications([]); }}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            mode === "ocr"
              ? "bg-primary text-on-primary shadow-sm"
              : "text-on-surface-variant"
          }`}
        >
          <span className="material-symbols-outlined text-[16px] align-middle mr-1">text_fields</span>
          Text OCR
        </button>
        <button
          onClick={() => { setMode("classify"); setRegions([]); }}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            mode === "classify"
              ? "bg-primary text-on-primary shadow-sm"
              : "text-on-surface-variant"
          }`}
        >
          <span className="material-symbols-outlined text-[16px] align-middle mr-1">image_search</span>
          Identify
        </button>
      </div>

      {/* Direction toggle (only for OCR mode) */}
      {mode === "ocr" && (
      <div className="flex items-center bg-surface-container-lowest border border-outline-variant/40 rounded-full p-1 shadow-sm">
        <button
          onClick={() => setDirection("en->lun")}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            direction === "en->lun"
              ? "bg-primary text-on-primary shadow-sm"
              : "text-on-surface-variant"
          }`}
        >
          English → Runyoro
        </button>
        <button
          onClick={() => setDirection("lun->en")}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
            direction === "lun->en"
              ? "bg-primary text-on-primary shadow-sm"
              : "text-on-surface-variant"
          }`}
        >
          Runyoro → English
        </button>
      </div>
      )}

      {/* Action buttons */}
      {mode === "ocr" ? (
      <div className="flex items-center justify-center gap-4 w-full">
        <button
          onClick={startCamera}
          className="flex flex-col items-center gap-2 bg-primary text-on-primary px-8 py-5 rounded-2xl shadow-lg active:scale-95 transition-all"
        >
          <span className="material-symbols-outlined text-[32px]">photo_camera</span>
          <span className="text-sm font-semibold">Open Camera</span>
        </button>

        <label className="flex flex-col items-center gap-2 bg-surface-container-lowest border border-outline-variant/40 text-on-surface px-8 py-5 rounded-2xl cursor-pointer active:scale-95 transition-all shadow-sm">
          <span className="material-symbols-outlined text-[32px] text-primary">photo_library</span>
          <span className="text-sm font-medium">Upload Text Image</span>
          <input type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
        </label>
      </div>
      ) : (
      <div className="flex items-center justify-center gap-4 w-full">
        <label className="flex flex-col items-center gap-2 bg-primary text-on-primary px-8 py-5 rounded-2xl shadow-lg cursor-pointer active:scale-95 transition-all">
          <span className="material-symbols-outlined text-[32px]">image_search</span>
          <span className="text-sm font-semibold">Upload Photo</span>
          <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleClassifyUpload} />
        </label>
      </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-error-container/30 border border-error/30 rounded-xl px-4 py-3 text-sm text-error max-w-lg w-full text-center">
          <span className="material-symbols-outlined text-[16px] align-middle mr-1">error</span>
          {error}
        </div>
      )}

      {/* Classification results (Identify mode) */}
      {classifications.length > 0 && (
        <div className="w-full max-w-lg bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center gap-2 bg-surface-container/30">
            <span className="material-symbols-outlined text-primary text-[18px]">image_search</span>
            <h3 className="text-sm font-semibold text-on-background">
              Objects Identified
            </h3>
          </div>
          <div className="px-4 py-3 space-y-3">
            {classifications.map((item, i) => (
              <div key={i} className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-on-surface-variant truncate">{item.label_en}</p>
                  <p className="text-base font-semibold text-primary truncate">{item.label_lun}</p>
                </div>
                <div className="text-xs text-on-surface-variant/60 bg-surface-container rounded-full px-2 py-0.5 shrink-0">
                  {(item.confidence * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results list (OCR mode) */}
      {regions.length > 0 && (
        <div className="w-full max-w-lg bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-outline-variant/20 flex items-center justify-between bg-surface-container/30">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">translate</span>
              <h3 className="text-sm font-semibold text-on-background">
                {regions.length} Translation{regions.length > 1 ? "s" : ""}
              </h3>
            </div>
            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className="text-xs text-primary font-medium"
            >
              {showOverlay ? "Hide overlay" : "Show overlay"}
            </button>
          </div>
          <div className="px-4 py-3 max-h-72 overflow-y-auto space-y-2">
            {Array.from({ length: Math.ceil(regions.length / 2) }, (_, i) => {
              const pair = regions.slice(i * 2, i * 2 + 2);
              return (
                <p key={i} className="text-sm leading-relaxed">
                  {pair.map((region, j) => (
                    <span key={j}>
                      <span className="text-on-surface-variant">{region.original}</span>
                      {" → "}
                      <span className="font-semibold text-primary">{region.translated}</span>
                      {j === 0 && pair.length > 1 && <span className="text-on-surface-variant/40">{" · "}</span>}
                    </span>
                  ))}
                </p>
              );
            })}
          </div>
        </div>
      )}
      </div>{/* end top section */}

      {/* Instructions — pinned to bottom above nav bar */}
      {!capturedImage && regions.length === 0 && classifications.length === 0 && (
        <div style={{ width: "100%", maxWidth: "380px", textAlign: "center", padding: "0 16px", marginTop: "auto" }}>
          {mode === "ocr" ? (
            <>
              <div className="flex justify-center gap-1 mb-3">
                {["photo_camera", "arrow_forward", "text_fields", "arrow_forward", "g_translate"].map((icon, i) => (
                  <span key={i} className={`material-symbols-outlined ${i % 2 === 0 ? "text-primary text-[28px]" : "text-on-surface-variant/40 text-[18px]"}`}>
                    {icon}
                  </span>
                ))}
              </div>
              <p style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--color-on-surface-variant)", whiteSpace: "normal", wordBreak: "normal", overflowWrap: "break-word" }}>
                Point your camera at signs, documents, or menus to instantly detect and translate text into Runyoro/Rutooro. Powered by AI Stick Lens.
              </p>
            </>
          ) : (
            <>
              <div className="flex justify-center gap-1 mb-3">
                {["image_search", "arrow_forward", "label", "arrow_forward", "g_translate"].map((icon, i) => (
                  <span key={i} className={`material-symbols-outlined ${i % 2 === 0 ? "text-primary text-[28px]" : "text-on-surface-variant/40 text-[18px]"}`}>
                    {icon}
                  </span>
                ))}
              </div>
              <p style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--color-on-surface-variant)", whiteSpace: "normal", wordBreak: "normal", overflowWrap: "break-word" }}>
                Upload a photo of any object to identify it and get its Runyoro/Rutooro name. Supports JPEG, PNG, and WebP images.
              </p>
            </>
          )}
        </div>
      )}

      {/* Hidden canvas */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
