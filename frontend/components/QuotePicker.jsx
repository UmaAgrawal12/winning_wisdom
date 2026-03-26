const motionQ = (window.framerMotion && window.framerMotion.motion) || { div: "div" };

function QuotePicker({ topic, setTopic, quote, setQuote, tags, setTags, onGenerate }) {
  const availableTags = ["motivation", "success", "mindset", "discipline", "focus"];
  const toggleTag = (tag) => {
    setTags(tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag]);
  };

  return (
    <div className="grid gap-8 lg:grid-cols-12">
      <motionQ.div className="rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur-2xl lg:col-span-5">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-neon-blue/80">Phase One</p>
        <h2 className="font-display text-4xl font-bold tracking-tight">Pick Your Quote</h2>
        <p className="mt-2 text-sm text-slate-300">Define the core message for your cinematic visual essay.</p>

        <div className="mt-4 space-y-3">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full rounded-xl border-none bg-[#2d344980] px-4 py-4 outline-none transition focus:ring-2 focus:ring-violet-400/60"
            placeholder="Universal topic"
          />
          <textarea
            value={quote}
            onChange={(e) => setQuote(e.target.value)}
            rows={5}
            className="w-full rounded-xl border-none bg-[#2d344980] px-4 py-4 outline-none transition focus:ring-2 focus:ring-fuchsia-400/60"
            placeholder="The wisdom text"
          />
          <button
            onClick={onGenerate}
            className="w-full rounded-full bg-gradient-to-r from-violet-500 via-blue-500 to-fuchsia-500 px-5 py-4 font-display text-lg font-bold tracking-tight transition hover:scale-[1.01] hover:shadow-lg hover:shadow-fuchsia-500/35"
          >
            Generate Script
          </button>
        </div>
      </motionQ.div>

      <motionQ.div className="lg:col-span-7">
        <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-slate-300/80">Live Preview</p>
        <div className="relative overflow-hidden rounded-[36px] border border-white/10 shadow-2xl">
          <img
            alt="city"
            src="https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80"
            className="h-[460px] w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0b1326] via-[#0b1326aa] to-transparent p-8">
            <p className="material-symbols-outlined text-5xl text-neon-purple/50">format_quote</p>
            <p className="mt-2 max-w-xl font-display text-4xl font-bold leading-tight text-white">"{quote}"</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {availableTags.map((tag) => (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                tags.includes(tag)
                  ? "border-fuchsia-300 bg-fuchsia-500/20 text-fuchsia-100"
                  : "border-white/15 bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </motionQ.div>
    </div>
  );
}
