"use client";
import type { Tab } from "@/app/page";

const NAV: { id: Tab; icon: string; label: string }[] = [
  { id: "home",      icon: "home",         label: "Home"      },
  { id: "translate", icon: "g_translate",  label: "Translate" },
  { id: "camera",    icon: "photo_camera", label: "Lens"      },
  { id: "editor",    icon: "edit_note",    label: "Editor"    },
  { id: "chat",      icon: "chat_bubble",  label: "Chat"      },
];

export default function BottomNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <nav
      className="fixed bottom-0 left-0 w-full z-50 border-t border-outline-variant/30 pb-safe"
      style={{
        background: "rgba(14,14,14,0.92)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        borderRadius: "16px 16px 0 0",
      }}
    >
      <div className="flex justify-around items-center h-20 px-2 max-w-screen-xl mx-auto">
        {NAV.map(({ id, icon, label }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              className={`flex flex-col items-center justify-center gap-0.5 px-3 py-1.5 rounded-2xl transition-all duration-150 active:scale-90 ${
                isActive
                  ? "text-primary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
              style={{ minWidth: 56 }}
            >
              {/* Active indicator pill */}
              <div className={`relative flex items-center justify-center w-12 h-7 rounded-full transition-all duration-200 ${isActive ? "bg-primary/15" : ""}`}>
                <span
                  className="material-symbols-outlined text-[22px]"
                  style={isActive ? { fontVariationSettings: "'FILL' 1, 'wght' 600" } : undefined}
                >
                  {icon}
                </span>
              </div>
              <span className={`text-[10px] font-semibold tracking-wide ${isActive ? "text-primary" : "text-on-surface-variant"}`}>
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
