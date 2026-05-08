"use client";

export default function TopBar({ processing = false }: { processing?: boolean }) {
  return (
    <header className="bg-surface sticky top-0 z-40 shadow-sm">
      <div className="flex justify-between items-center w-full px-margin py-base max-w-screen-xl mx-auto">
        <div className="flex items-center gap-sm">
          <div className="h-10 w-10 rounded-full bg-primary-container flex items-center justify-center">
            <span className="text-primary-fixed font-bold text-sm">AI</span>
          </div>
          <h1 className="text-h1 font-bold text-primary" style={{ fontSize: 22 }}>AI Stick</h1>
        </div>
        <div className="flex items-center gap-md">
          <button className="p-xs hover:bg-surface-container rounded-full transition-colors">
            <span className="material-symbols-outlined text-primary">settings</span>
          </button>
        </div>
      </div>
      {processing && (
        <div className="w-full h-1 bg-surface-container overflow-hidden">
          <div className="h-full bg-secondary w-1/3 animate-pulse" />
        </div>
      )}
    </header>
  );
}
