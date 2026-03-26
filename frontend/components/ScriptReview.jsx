const motionS = (window.framerMotion && window.framerMotion.motion) || { div: "div" };

function ScriptReview({ scriptBlocks, persona, setPersona, onApprove }) {
  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <motionS.div className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur-2xl lg:col-span-7">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-neon-blue/80">Script Editor</p>
        <h2 className="font-display text-4xl font-bold tracking-tight">Spoken Script</h2>

        <div className="mt-5 space-y-3">
          {scriptBlocks.map((block) => (
            <div key={block.t} className="rounded-xl border border-white/10 bg-[#131b2ecc] p-4">
              <p className="mb-2 font-mono text-xs font-bold tracking-widest text-neon-purple">[{block.t}]</p>
              <p className="text-sm leading-relaxed text-slate-200">{block.text}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 grid gap-4 rounded-2xl border border-white/10 bg-[#222a3d99] p-4 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-300">Narrative Persona</p>
            <p className="mt-1 text-xs text-slate-400">Arthur AI Assistant</p>
          </div>
          <div className="mt-2 flex gap-2">
            {["Arthur", "Tony"].map((p) => (
              <button
                key={p}
                onClick={() => setPersona(p)}
                className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  persona === p
                    ? "bg-gradient-to-r from-violet-500 to-blue-500 text-white shadow-md shadow-violet-500/35"
                    : "border border-white/15 bg-white/5 text-slate-300 hover:bg-white/10"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
          <button
            onClick={onApprove}
            className="rounded-full bg-gradient-to-r from-violet-500 via-blue-500 to-fuchsia-500 px-6 py-3 text-sm font-bold transition hover:scale-[1.01] hover:shadow-lg hover:shadow-blue-500/35"
          >
            Approve & Score
          </button>
        </div>
      </motionS.div>

      <motionS.div className="space-y-4 lg:col-span-5">
        <div className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur-2xl">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-300/80">Visual Overlay</p>
          <div className="relative overflow-hidden rounded-3xl">
            <img alt="overlay" src="https://images.unsplash.com/photo-1526498460520-4c246339dccb?auto=format&fit=crop&w=1200&q=80" className="h-64 w-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0b1326] via-[#0b1326aa] to-transparent p-4">
              <p className="text-sm font-semibold text-neon-blue">"In a world of echoes, be the original sound."</p>
            </div>
          </div>
        </div>
      </motionS.div>
    </div>
  );
}
