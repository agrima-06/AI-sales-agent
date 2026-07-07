import HealthStatus from "@/components/HealthStatus";

export default function Home() {
  return (
    <div className="relative min-h-screen bg-slate-950 text-white overflow-hidden font-sans">
      {/* Background visual gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-violet-900/20 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/20 blur-[120px] pointer-events-none"></div>
      
      {/* Header */}
      <header className="relative w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <span className="font-bold text-white text-sm">V</span>
          </div>
          <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-zinc-300 bg-clip-text text-transparent">
            VoxSales
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs px-3 py-1 rounded-full border border-white/10 bg-white/5 text-zinc-300 font-medium tracking-wide uppercase">
            Sprint 1 Active
          </span>
        </div>
      </header>

      {/* Hero section */}
      <main className="relative max-w-7xl mx-auto px-6 pt-20 pb-32 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <div className="flex flex-col gap-6 items-start">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/5 text-xs text-violet-300 font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse"></span>
            AI Sales Operating System Foundation
          </div>
          
          <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight">
            The Voice OS for <br />
            <span className="bg-gradient-to-r from-violet-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Enterprise B2B Sales
            </span>
          </h1>

          <p className="text-lg text-zinc-400 max-w-xl leading-relaxed">
            VoxSales empowers dealers to place orders, check real-time inventories, apply complex commercial schemes, and sync transactions directly into ERPs—speaking naturally in regional languages.
          </p>

          {/* Feature Grid */}
          <div className="grid grid-cols-2 gap-4 w-full mt-6">
            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <h4 className="font-semibold text-white mb-1">Instant Telephony</h4>
              <p className="text-xs text-zinc-400">Lower than 800ms round-trip speech latencies.</p>
            </div>
            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <h4 className="font-semibold text-white mb-1">Real-time Stock</h4>
              <p className="text-xs text-zinc-400">Direct integration queries into WMS/ERP databases.</p>
            </div>
            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <h4 className="font-semibold text-white mb-1">Dynamic Schemes</h4>
              <p className="text-xs text-zinc-400">AI automatically calculates trade promotion terms.</p>
            </div>
            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02]">
              <h4 className="font-semibold text-white mb-1">Multilingual</h4>
              <p className="text-xs text-zinc-400">Natural local dialect and language parsing.</p>
            </div>
          </div>
        </div>

        {/* Dynamic status panel */}
        <div className="flex flex-col items-center justify-center lg:items-end">
          <HealthStatus />
          <div className="w-full max-w-md mt-6 text-center lg:text-right">
            <p className="text-xs text-zinc-500">
              Backend API Target: <code className="text-violet-400">http://localhost:8000/api/v1</code>
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              Verify local compose instances by executing curl tests.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between text-xs text-zinc-500 gap-4">
        <p>© 2026 VoxSales SaaS Foundation. All rights reserved.</p>
        <div className="flex items-center gap-6">
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="hover:text-white transition">
            Swagger API Docs
          </a>
          <span className="h-3 w-px bg-white/10"></span>
          <span>Sprint 1 Engineering Base</span>
        </div>
      </footer>
    </div>
  );
}
