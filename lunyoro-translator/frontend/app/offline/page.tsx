"use client";

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center bg-background">
      <div className="w-20 h-20 rounded-2xl bg-primary-fixed/40 flex items-center justify-center mb-6">
        <span className="material-symbols-outlined text-[40px] text-primary"
          style={{ fontVariationSettings: "'FILL' 1" }}>
          wifi_off
        </span>
      </div>
      <h1 className="text-2xl font-bold text-on-background mb-2">You're offline</h1>
      <p className="text-on-surface-variant text-sm max-w-xs leading-relaxed mb-6">
        No internet connection. Previous translations and dictionary lookups you've made are still available in the cache.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="px-6 py-3 bg-primary text-on-primary rounded-full font-semibold text-sm hover:opacity-90 active:scale-95 transition-all"
      >
        Try again
      </button>
    </div>
  );
}
