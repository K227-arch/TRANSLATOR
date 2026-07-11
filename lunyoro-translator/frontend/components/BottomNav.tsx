"use client";
import type { Tab } from "@/app/page";

const NAV: { id: Tab; icon: string; label: string }[] = [
  { id: "home",       icon: "home",        label: "Home"      },
  { id: "translate",  icon: "g_translate", label: "Translate" },
  { id: "camera",     icon: "photo_camera", label: "Lens" },
  { id: "chat",       icon: "chat_bubble", label: "Chat"      },
  { id: "dictionary", icon: "menu_book",   label: "Dict"      },
];

export default function BottomNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 bg-surface-container-lowest border-t border-outline-variant/40 pb-safe"
      style={{ borderRadius: "16px 16px 0 0" }}
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
                  ? "bg-secondary-container text-on-secondary-container"
                  : "text-outline hover:text-primary hover:bg-surface-container"
              }`}
              style={{ minWidth: 56 }}
            >
              <span
                className="material-symbols-outlined text-[24px]"
                style={isActive ? { fontVariationSettings: "'FILL' 1, 'wght' 600" } : undefined}
              >
                {icon}
              </span>
              <span className="text-[10px] font-semibold tracking-wide">{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
