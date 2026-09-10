"use client";

interface TopBarProps {
  processing?: boolean;
  section?: string;
  onBack?: () => void;
  onHelp?: () => void;
}

export default function TopBar({ processing = false, section, onBack, onHelp }: TopBarProps) {
  return (
    <header
      className="fixed top-0 w-full z-50 border-b border-outline-variant/40"
      style={{ background: "rgba(14,14,14,0.85)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)" }}
    >
      <div className="flex items-center justify-between px-5 h-16 max-w-screen-xl mx-auto">
        {/* Left */}
        <div className="flex items-center gap-3">
          {onBack ? (
            <button
              onClick={onBack}
              className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container transition-colors text-on-surface"
              aria-label="Back"
            >
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
          ) : null}

          {section ? (
            <span className="text-lg font-semibold text-on-background tracking-tight">{section}</span>
          ) : (
            <div className="flex items-center gap-2.5">
              <img
                src="/logo.png"
                alt="AI Stick"
                width={34}
                height={34}
                className="rounded-lg"
                style={{ objectFit: "contain" }}
              />
              <span className="text-sm font-bold text-primary tracking-wider uppercase hidden sm:block">AI Stick</span>
            </div>
          )}
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          {onHelp && (
            <button
              onClick={onHelp}
              className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-surface-container transition-colors text-on-surface-variant"
              aria-label="Help"
            >
              <span className="material-symbols-outlined text-[22px]">help</span>
            </button>
          )}
          <div className="w-9 h-9 rounded-full border border-primary/40 overflow-hidden bg-surface-container flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              account_circle
            </span>
          </div>
        </div>
      </div>

      {/* Processing bar */}
      {processing && (
        <div className="h-px w-full bg-outline-variant overflow-hidden">
          <div
            className="h-full bg-primary"
            style={{ width: "40%", animation: "shimmer 1.5s ease-in-out infinite" }}
          />
        </div>
      )}
    </header>
  );
}
