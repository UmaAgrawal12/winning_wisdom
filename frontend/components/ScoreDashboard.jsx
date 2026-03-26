const motionD = (window.framerMotion && window.framerMotion.motion) || { div: "div" };

function ScoreDashboard({ score, metrics }) {
  return (
    <div className="space-y-8">
      <motionD.div className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur-2xl">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-neon-blue/80">Performance Analysis</p>
        <div className="mt-2 flex items-end gap-3">
          <h2 className="font-display text-4xl font-bold tracking-tight">Reel Score Dashboard</h2>
          <p className="bg-gradient-to-r from-violet-300 to-fuchsia-300 bg-clip-text text-4xl font-extrabold text-transparent">
            {score}
          </p>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {metrics.map((item) => (
            <div key={item.label} className="rounded-3xl border border-white/10 bg-[#171f33aa] p-4">
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-xs uppercase tracking-widest text-slate-400">{item.label}</span>
                <span className="font-display font-bold text-white">{item.value}%</span>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet-500 via-blue-500 to-fuchsia-500 transition-all duration-700"
                  style={{ width: `${item.value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </motionD.div>

      <motionD.div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-[24px] border border-white/10 bg-white/5 p-5 backdrop-blur-xl">
          <h3 className="font-display text-xl font-bold">AI Verdict</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">
            Your hook is exceptional, but visual retention drops around the second act. Improve caption brightness and pacing
            contrast to keep watch-through stable on mobile.
          </p>
        </div>
        <div className="rounded-[24px] border border-fuchsia-400/30 bg-gradient-to-br from-fuchsia-500/20 to-rose-600/20 p-5 backdrop-blur-xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-rose-200">Priority Fix</p>
          <p className="mt-2 text-sm leading-relaxed text-rose-100">
            Increase caption brightness by 40% and add one visual pattern break around 0:15 to recover contrast.
          </p>
        </div>
      </motionD.div>
    </div>
  );
}
