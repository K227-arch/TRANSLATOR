"use client";
type Tab = "home" | "translate" | "chat" | "editor";

const NAV = [
  { id: "home",      icon: "home",        label: "Home"      },
  { id: "translate", icon: "translate",   label: "Translate" },
  { id: "chat",      icon: "chat_bubble", label: "Chat"      },
  { id: "editor",    icon: "description", label: "Editor"    },
] as const;

export default function BottomNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <nav className="fixed bottom-0 left-0 w-full flex justify-around items-center px-gutter py-md bg-surface-container-lowest shadow-[0_-8px_24px_rgba(7,2,53,0.08)] z-50 rounded-t-xl">
      {NAV.map(({ id, icon, label }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={`flex flex-col items-center gap-xs px-lg py-xs rounded-full transition-all active:scale-90 ${
              isActive
                ? "bg-secondary-container text-on-secondary-container"
                : "text-on-surface-variant opacity-70 hover:bg-surface-container-high"
            }`}
          >
            <span
              className="material-symbols-outlined"
              style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}
            >
              {icon}
            </span>
            <span className="text-label-sm font-semibold">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
