"use client";
import { useState, useRef, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TranslatedRegion {
  original: string;
  translated: string;
  confidence: number;
  bbox_norm: { x: number; y: number; width: number; height: number };
}

type Direction = "en->lun" | "lun->en";

export default function CameraTranslator() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
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

  // Start camera
  const startCamera = useCallback(async () => {
    setError("");
    try {
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
    } catch (err) {
      setError("Could not access camera. Please allow camera permissions.");
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
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    // Get base64 image
    const imageData = canvas.toDataURL("image/jpeg", 0.8);
    setCapturedImage(imageData);
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
        setError("");
      }
    } catch {
      setError("Could not connect to translation server.");
    } finally {
      setLoading(false);
    }
  }, [direction]);

  // Auto-capture mode (every 3 seconds)
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
    formData.append("direction", direction);

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

  return (
    <div className="flex flex-col items-center gap-4 py-4 px-4">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-on-background flex items-center gap-2 justify-center">
          <span className="material-symbols-outlined text-primary">photo_camera</span>
          Camera Translate
        </h2>
        <p className="text-on-surface-variant mt-1 text-sm max-w-xs mx-auto leading-relaxed">
          Point your camera at text to translate it in real-time
        </p>
      </div>

      {/* Direction toggle */}
      <div className="flex items-center gap-3 bg-surface-container rounded-xl p-1">
        <button
          onClick={() => setDirection("en->lun")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            direction === "en->lun"
              ? "bg-primary text-on-primary shadow-sm"
              : "text-on-surface-variant hover:text-primary"
          }`}
        >
          English → Runyoro
        </button>
        <button
          onClick={() => setDirection("lun->en")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            direction === "lun->en"
              ? "bg-primary text-on-primary shadow-sm"
              : "text-on-surface-variant hover:text-primary"
          }`}
        >
          Runyoro → English
        </button>
      </div>

      {/* Camera viewport */}
      <div className="relative w-full max-w-lg aspect-[4/3] bg-surface-container-highest rounded-2xl overflow-hidden shadow-lg">
        {/* Video feed */}
        <video
          ref={videoRef}
          className={`w-full h-full object-cover ${!cameraActive || capturedImage ? "hidden" : ""}`}
          playsInline
          muted
          autoPlay
        />

        {/* Captured image */}
        {capturedImage && !cameraActive && (
          <img
            src={capturedImage}
            alt="Captured"
            className="w-full h-full object-cover"
          />
        )}

        {/* Placeholder when no camera */}
        {!cameraActive && !capturedImage && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-on-surface-variant">
            <span className="material-symbols-outlined text-[64px] opacity-40">photo_camera</span>
            <p className="text-sm mt-2 opacity-60">Camera off</p>
          </div>
        )}

        {/* Translation overlay */}
        {showOverlay && (cameraActive || capturedImage) && (
          <div ref={overlayRef} className="absolute inset-0 pointer-events-none">
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
                {/* Background blur effect */}
                <div className="absolute inset-0 bg-black/70 backdrop-blur-sm rounded-sm" />
                {/* Translated text */}
                <span
                  className="relative text-white font-bold text-center px-1 leading-tight"
                  style={{
                    fontSize: `clamp(8px, ${region.bbox_norm.height * 60}vw, 18px)`,
                  }}
                >
                  {region.translated}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="absolute top-3 right-3 bg-primary/90 text-on-primary px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 shadow-lg">
            <div className="w-3 h-3 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
            Translating...
          </div>
        )}

        {/* Scan line animation when active */}
        {cameraActive && !paused && (
          <div className="absolute inset-x-0 top-0 h-0.5 bg-primary/60 animate-pulse" />
        )}
      </div>

      {/* Hidden canvas for frame capture */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Controls */}
      <div className="flex items-center gap-3">
        {!cameraActive ? (
          <>
            <button
              onClick={startCamera}
              className="flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-xl font-semibold text-sm shadow-md active:scale-95 transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">photo_camera</span>
              Start Camera
            </button>
            <label className="flex items-center gap-2 bg-surface-container-high text-on-surface px-5 py-3 rounded-xl font-medium text-sm cursor-pointer active:scale-95 transition-all border border-outline-variant/40">
              <span className="material-symbols-outlined text-[20px]">upload</span>
              Upload
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileUpload}
              />
            </label>
          </>
        ) : (
          <>
            {/* Capture button */}
            <button
              onClick={captureAndTranslate}
              disabled={loading}
              className="w-14 h-14 bg-primary text-on-primary rounded-full flex items-center justify-center shadow-lg active:scale-90 transition-all disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[28px]">
                {loading ? "hourglass_top" : "center_focus_strong"}
              </span>
            </button>

            {/* Pause/Resume auto-scan */}
            <button
              onClick={() => setPaused(!paused)}
              className="w-11 h-11 bg-surface-container-high text-on-surface rounded-full flex items-center justify-center border border-outline-variant/40 active:scale-90 transition-all"
            >
              <span className="material-symbols-outlined text-[22px]">
                {paused ? "play_arrow" : "pause"}
              </span>
            </button>

            {/* Switch camera */}
            <button
              onClick={switchCamera}
              className="w-11 h-11 bg-surface-container-high text-on-surface rounded-full flex items-center justify-center border border-outline-variant/40 active:scale-90 transition-all"
            >
              <span className="material-symbols-outlined text-[22px]">flip_camera_ios</span>
            </button>

            {/* Toggle overlay */}
            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className={`w-11 h-11 rounded-full flex items-center justify-center border active:scale-90 transition-all ${
                showOverlay
                  ? "bg-primary/10 text-primary border-primary/40"
                  : "bg-surface-container-high text-on-surface border-outline-variant/40"
              }`}
            >
              <span className="material-symbols-outlined text-[22px]">
                {showOverlay ? "visibility" : "visibility_off"}
              </span>
            </button>

            {/* Stop camera */}
            <button
              onClick={stopCamera}
              className="w-11 h-11 bg-error/10 text-error rounded-full flex items-center justify-center border border-error/30 active:scale-90 transition-all"
            >
              <span className="material-symbols-outlined text-[22px]">stop</span>
            </button>
          </>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-error-container/30 border border-error/30 rounded-xl px-4 py-3 text-sm text-error max-w-lg w-full">
          <span className="material-symbols-outlined text-[16px] align-middle mr-1">error</span>
          {error}
        </div>
      )}

      {/* Detected text list */}
      {regions.length > 0 && (
        <div className="w-full max-w-lg bg-surface-container-lowest border border-outline-variant/40 rounded-2xl overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-outline-variant/30 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-on-background">
              Detected Text ({regions.length})
            </h3>
            <span className="text-xs text-on-surface-variant">
              {direction === "en->lun" ? "EN → LUN" : "LUN → EN"}
            </span>
          </div>
          <div className="divide-y divide-outline-variant/20 max-h-64 overflow-y-auto">
            {regions.map((region, i) => (
              <div key={i} className="px-4 py-3 flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded">
                    {Math.round(region.confidence * 100)}%
                  </span>
                  <span className="text-sm text-on-surface-variant line-through opacity-70">
                    {region.original}
                  </span>
                </div>
                <span className="text-sm font-medium text-primary">
                  {region.translated}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Instructions */}
      {!cameraActive && !capturedImage && regions.length === 0 && (
        <div className="w-full max-w-lg bg-surface-container/50 rounded-2xl p-5 text-center">
          <div className="flex justify-center gap-6 mb-4">
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-10 h-10 bg-primary-container/40 rounded-xl flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-[22px]">photo_camera</span>
              </div>
              <span className="text-xs text-on-surface-variant">Point</span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-10 h-10 bg-primary-container/40 rounded-xl flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-[22px]">text_fields</span>
              </div>
              <span className="text-xs text-on-surface-variant">Detect</span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-10 h-10 bg-primary-container/40 rounded-xl flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-[22px]">g_translate</span>
              </div>
              <span className="text-xs text-on-surface-variant">Translate</span>
            </div>
          </div>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            Point your camera at signs, documents, or menus to instantly translate text.
            Works with English ↔ Runyoro/Rutooro.
          </p>
        </div>
      )}
    </div>
  );
}
