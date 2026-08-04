"use client";
import type { Tab } from "@/app/page";

const FEATURES: { id: Tab; icon: string; title: string; desc: string; howTo: string }[] = [
  {
    id: "translate",
    icon: "g_translate",
    title: "Translator",
    desc: "Translate text between English and Runyoro/Rutooro using AI models. Get instant translations with both NLLB and MarianMT for comparison.",
    howTo: "Type or paste text in the input box, select your direction (English → Runyoro or Runyoro → English), then tap Translate. Use thumbs up/down to rate the quality.",
  },
  {
    id: "camera",
    icon: "photo_camera",
    title: "AI Stick Lens",
    desc: "Point your phone camera or webcam at signs, menus, or documents to detect and translate text in real-time with overlays.",
    howTo: "Tap 'Open Camera' to start scanning. The app auto-detects text every 3 seconds and overlays translations. You can also upload a photo of text.",
  },
  {
    id: "chat",
    icon: "chat_bubble",
    title: "AI Chat",
    desc: "Ask questions about Runyoro/Rutooro grammar, culture, vocabulary, and get detailed explanations powered by AI.",
    howTo: "Type your question in the chat box. The AI responds in English explaining grammar rules, cultural context, or translations. Use quick chips for common topics.",
  },
  {
    id: "editor",
    icon: "edit_note",
    title: "Word Editor",
    desc: "Write in Runyoro/Rutooro with real-time spellcheck. Highlights misspelled words and suggests corrections.",
    howTo: "Start typing in Runyoro. Misspelled words get underlined in red — tap them for suggestions. Use the Translate button to convert your text to English.",
  },
  {
    id: "dictionary",
    icon: "menu_book",
    title: "Dictionary",
    desc: "Search for word definitions, meanings, and examples in both English and Runyoro/Rutooro.",
    howTo: "Type a word in the search box. Results show definitions, part of speech, and domain. Switch between English→Runyoro and Runyoro→English lookup.",
  },
  {
    id: "history",
    icon: "history",
    title: "History",
    desc: "View all your recent translations in one place. Useful for reviewing or re-using past translations.",
    howTo: "Your translations are saved automatically. Scroll through to find previous work. Tap any entry to see the full translation.",
  },
];

export default function HelpPage({ onNavigate }: { onNavigate: (t: Tab) => void }) {
  return (
    <div className="flex flex-col gap-6 pb-8">
      {/* Header */}
      <div className="text-center">
        <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-primary-container/40 flex items-center justify-center">
          <span className="material-symbols-outlined text-primary text-[32px]">help</span>
        </div>
        <h2 className="text-2xl font-bold text-on-background">How can we help?</h2>
        <p className="text-on-surface-variant mt-1 text-sm max-w-sm mx-auto">
          Explore each feature to find what works best for you.
        </p>
      </div>

      {/* Feature cards */}
      <div className="space-y-4">
        {FEATURES.map(({ id, icon, title, desc, howTo }) => (
          <div key={id} className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
            <button
              onClick={() => onNavigate(id)}
              className="w-full p-4 flex items-start gap-4 text-left hover:bg-surface-container/30 transition-colors"
            >
              <div className="w-11 h-11 rounded-xl bg-primary-container/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="material-symbols-outlined text-primary text-[24px]">{icon}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-on-background text-[15px]">{title}</h3>
                  <span className="material-symbols-outlined text-outline text-[18px]">arrow_forward</span>
                </div>
                <p className="text-sm text-on-surface-variant mt-1 leading-relaxed">{desc}</p>
                <p className="text-xs text-primary/80 mt-2 leading-relaxed">
                  <span className="font-semibold">How to use:</span> {howTo}
                </p>
              </div>
            </button>
          </div>
        ))}
      </div>

      {/* Quick tips */}
      <div className="bg-primary-container/10 border border-primary/20 rounded-2xl p-5">
        <h3 className="font-semibold text-on-background text-sm flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-primary text-[18px]">tips_and_updates</span>
          Quick Tips
        </h3>
        <ul className="space-y-2 text-sm text-on-surface-variant">
          <li className="flex items-start gap-2">
            <span className="text-primary font-bold">•</span>
            Use the Translator for quick text translations — it shows both AI models so you can pick the best one.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary font-bold">•</span>
            AI Stick Lens is perfect for translating signs, menus, or printed text using your camera.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary font-bold">•</span>
            The AI Chat can explain grammar rules, cultural meanings, and help you learn the language.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary font-bold">•</span>
            Give feedback (thumbs up/down) on translations — it helps improve the AI for everyone.
          </li>
        </ul>
      </div>
    </div>
  );
}
