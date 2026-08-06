"use client";
import { useEffect, useState } from "react";

export default function OfflineBanner() {
  const [offline, setOffline] = useState(false);
  const [justCameBack, setJustCameBack] = useState(false);

  useEffect(() => {
    setOffline(!navigator.onLine);

    function handleOffline() { setOffline(true); setJustCameBack(false); }
    function handleOnline()  {
      setOffline(false);
      setJustCameBack(true);
      setTimeout(() => setJustCameBack(false), 3000);
    }

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online",  handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online",  handleOnline);
    };
  }, []);

  if (!offline && !justCameBack) return null;

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold transition-all ${
        offline
          ? "bg-error text-on-error"
          : "bg-tertiary text-on-tertiary"
      }`}
    >
      <span className="material-symbols-outlined text-[16px]">
        {offline ? "wifi_off" : "wifi"}
      </span>
      {offline
        ? "You're offline — showing cached translations"
        : "Back online"}
    </div>
  );
}
