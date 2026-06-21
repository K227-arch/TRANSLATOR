"use client";

export default function TopBar({ processing = false }: { processing?: boolean }) {
  return (
    <header className="bg-surface-bright fixed top-0 w-full z-50 shadow-sm">
      <div className="flex items-center justify-between px-5 h-16 max-w-screen-xl mx-auto">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary cursor-pointer hover:bg-surface-container-low transition-colors p-2 rounded-full">
            menu
          </span>
          <img
            alt="AI Stick Logo"
            className="h-8 object-contain"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBG1Fpbo81YV2P6TkSyWUFE-Wl3yMFvkibVSrwDcBTDUIM5ON1X2MyqB_IibZcaGrh7tVZ-h9z0EW_Pl-aB0PwKs5vcTMiTIeX0-v29dNGsF2ad4Qg8lfrXWao0kMOCH7hL8tbUsPY3CM1XKdSXp0OCXWfZKfsRzIihsYR6u6OicZCSms18GpOiRNzt9TsUJwFHsc8CjNsDm5qaa-Tnzsc8iXOKhPYXYaqr3rX7xdE3MHu00i5GeKAMZ8Z_v7s0ue7AEt-E-bGAmQs"
          />
        </div>
        <div className="w-10 h-10 rounded-full border-2 border-primary-container overflow-hidden bg-surface-container">
          <img
            className="w-full h-full object-cover"
            alt="Profile"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuDNbCE9jYYnFcQDtvX9hdbsejbS_It0Srh36mMyIfwjPkePckA3ozpATV_d7Kp-dS9DBR9XbhF_-xd9g3gAXBuSdCCwzjqdIVmCf4GILuif--ncOUdcaPoSJv68Tj53d0Blg851OIkJUUNzOu8U47sRNP-TRzaSCbCXcWDCseV69f-trmWchu-ewJjZRcKZ_Qu-v392CbRwQD-hitmDBKj30X-hhR0qVws2pNz_aXpayI3u33kuaUstUaH6g7Hn7AAiX8gcWRLckaI"
          />
        </div>
      </div>
      {processing && (
        <div className="w-full h-1 bg-surface-container overflow-hidden">
          <div className="h-full bg-primary-fixed-dim w-1/3 animate-pulse" />
        </div>
      )}
    </header>
  );
}
