"use client";
type Tab = "home" | "translate" | "chat" | "editor";

const NAV = [
  { id: "home" as Tab,      icon: "home",         label: "Home"      },
  { id: "translate" as Tab, icon: "g_translate",   label: "Translate" },
  { id: "chat" as Tab,      icon: "chat_bubble",   label: "Chat"      },
  { id: "editor" as Tab,    icon: "edit_note",     label: "Editor"    },
];

export default function BottomNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 py-2 bg-surface-container-lowest shadow-[0_-2px_10px_rgba(93,64,55,0.08)] rounded-t-xl h-20">
      {NAV.map(({ id, icon, label }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={`flex flex-col items-center justify-center px-4 py-1 transition-all active:scale-90 ${
              isActive
                ? "bg-secondary-container text-on-secondary-container rounded-full"
                : "text-outline hover:text-primary"
            }`}
          >
            <span
              className="material-symbols-outlined"
              style={isActive ? { fontVariationSettings: "'FILL' 1, 'wght' 500" } : undefined}
            >
              {icon}
            </span>
            <span className="text-xs font-semibold mt-0.5">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
