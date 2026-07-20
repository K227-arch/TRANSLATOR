"use client";

interface TopBarProps {
  processing?: boolean;
  section?: string;
  onBack?: () => void;
}

export default function TopBar({ processing = false, section, onBack }: TopBarProps) {
  return (
    <header className="bg-surface-bright fixed top-0 w-full z-50 border-b border-outline-variant/30">
      <div className="flex items-center justify-between px-5 h-16 max-w-screen-xl mx-auto">
        {/* Left — back/menu + logo or section title */}
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
            <span className="text-lg font-semibold text-on-background">{section}</span>
          ) : (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                  translate
                </span>
              </div>
              <span className="font-bold text-on-background text-base tracking-tight">AI Stick</span>
            </div>
          )}
        </div>

        {/* Right — avatar */}
        <div className="w-9 h-9 rounded-full border-2 border-primary-container overflow-hidden bg-surface-container-high flex items-center justify-center">
          <span className="material-symbols-outlined text-on-surface-variant text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            account_circle
          </span>
        </div>
      </div>

      {/* Processing bar */}
      {processing && (
        <div className="h-0.5 w-full bg-surface-container overflow-hidden">
          <div className="h-full bg-primary-fixed-dim animate-[shimmer_1.5s_ease-in-out_infinite]"
            style={{ width: "40%", animation: "shimmer 1.5s ease-in-out infinite" }}
          />
        </div>
      )}
    </header>
  );
}
