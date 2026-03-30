const API = "http://127.0.0.1:8000/api";
const BACKEND = "http://127.0.0.1:8000";

const els = {
  persona: document.getElementById("persona"),
  topicSelect: document.getElementById("topic-select"),
  topic: document.getElementById("topic"),
  quote: document.getElementById("quote"),
  source: document.getElementById("source"),
  script: document.getElementById("script"),
  revise: document.getElementById("revise-suggestions"),
  scoreOverall: document.getElementById("score-overall"),
  scoreVerdict: document.getElementById("score-verdict"),
  scoreHook: document.getElementById("score-hook"),
  scorePacing: document.getElementById("score-pacing"),
  scoreEmotion: document.getElementById("score-emotion"),
  scoreStructure: document.getElementById("score-structure"),
  scorePersona: document.getElementById("score-persona"),
  scoreVisual: document.getElementById("score-visual"),
  seoYoutubeCaption: document.getElementById("seo-youtube-caption"),
  seoYoutubeTags: document.getElementById("seo-youtube-tags"),
  seoInstagramCaption: document.getElementById("seo-instagram-caption"),
  seoInstagramTags: document.getElementById("seo-instagram-tags"),
  seoTiktokCaption: document.getElementById("seo-tiktok-caption"),
  seoTiktokTags: document.getElementById("seo-tiktok-tags"),
  seoFacebookCaption: document.getElementById("seo-facebook-caption"),
  seoFacebookTags: document.getElementById("seo-facebook-tags"),
  s1: document.getElementById("s1-status"),
  s2: document.getElementById("s2-status"),
  s3: document.getElementById("s3-status"),
  audio: document.getElementById("audio"),
  videoLink: document.getElementById("video-link"),
};

function setActiveTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tab}`);
  });
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    setActiveTab(btn.dataset.tab);
  });
});

document.querySelectorAll("[data-go-tab]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const nextTab = btn.dataset.goTab;
    setActiveTab(nextTab);

    // When moving from Topic to Script, auto-generate script.
    if (nextTab === "script") {
      await generateScript();
    }
  });
});

function status(el, msg) {
  el.textContent = msg || "";
}

function renderSeoBlock(seo) {
  const y = seo?.youtube || {};
  const i = seo?.instagram || {};
  const t = seo?.tiktok || {};
  const f = seo?.facebook || {};

  els.seoYoutubeCaption.textContent = y.caption || y.description || "--";
  els.seoYoutubeTags.textContent = Array.isArray(y.hashtags) && y.hashtags.length ? y.hashtags.map((tag) => `#${tag}`).join(" ") : "--";

  els.seoInstagramCaption.textContent = i.caption || i.description || "--";
  els.seoInstagramTags.textContent = Array.isArray(i.hashtags) && i.hashtags.length ? i.hashtags.map((tag) => `#${tag}`).join(" ") : "--";

  els.seoTiktokCaption.textContent = t.caption || t.description || "--";
  els.seoTiktokTags.textContent = Array.isArray(t.hashtags) && t.hashtags.length ? t.hashtags.map((tag) => `#${tag}`).join(" ") : "--";

  els.seoFacebookCaption.textContent = f.caption || f.description || "--";
  els.seoFacebookTags.textContent = Array.isArray(f.hashtags) && f.hashtags.length ? f.hashtags.map((tag) => `#${tag}`).join(" ") : "--";
}

async function j(path, opt) {
  const r = await fetch(API + path, opt);
  if (!r.ok) {
    throw new Error(await r.text());
  }
  return r.json();
}

async function loadCuratedTopics() {
  try {
    els.topicSelect.innerHTML = '<option value="">Loading topics...</option>';
    const d = await j(`/topics?persona=${encodeURIComponent(els.persona.value)}`);
    const topics = Array.isArray(d.topics) ? d.topics : [];
    if (!topics.length) {
      els.topicSelect.innerHTML = '<option value="">No topics found</option>';
      return;
    }
    els.topicSelect.innerHTML =
      '<option value="">Select a curated topic...</option>' +
      topics
        .map((t) => `<option value="${String(t).replace(/"/g, "&quot;")}">${t}</option>`)
        .join("");
  } catch (e) {
    els.topicSelect.innerHTML = '<option value="">Could not load topics</option>';
  }
}

els.topicSelect.onchange = async () => {
  const selected = els.topicSelect.value || "";
  if (selected) {
    els.topic.value = selected;
    try {
      status(els.s1, "Generating quote...");
      const d = await j("/topic/quote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: selected, persona: els.persona.value }),
      });
      els.quote.value = d.quote || "";
      els.source.value = d.source || "";
      status(els.s1, "✓ Quote updated from selected topic.");
    } catch (e) {
      status(els.s1, "❌ Error: " + e.message);
    }
  }
};

els.persona.onchange = async () => {
  await loadCuratedTopics();
};

document.getElementById("btn-topic-quote").onclick = async () => {
  try {
    status(els.s1, "Generating quote...");
    const d = await j("/topic/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: els.topic.value, persona: els.persona.value }),
    });
    els.quote.value = d.quote || "";
    els.source.value = d.source || "";
    status(els.s1, "✓ Quote updated.");
  } catch (e) {
    status(els.s1, "❌ Error: " + e.message);
  }
};

async function generateScript() {
  try {
    status(els.s1, "Generating script...");
    const d = await j("/topic/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quote: els.quote.value,
        source: els.source.value,
        persona: els.persona.value,
      }),
    });
    els.script.value = d?.spoken_script?.full_script || "";
    status(els.s1, "✓ Script generated.");
  } catch (e) {
    status(els.s1, "❌ Error: " + e.message);
  }
}

document.getElementById("btn-generate-script").onclick = generateScript;

document.getElementById("btn-revise").onclick = async () => {
  try {
    status(els.s1, "Regenerating script...");
    const d = await j("/script/revise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: els.topic.value || els.quote.value,
        quote: els.quote.value,
        source: els.source.value,
        current_script: els.script.value,
        suggestions: els.revise.value,
        persona: els.persona.value,
      }),
    });
    els.script.value = d?.spoken_script?.full_script || "";
    status(els.s1, "✓ Script regenerated.");
  } catch (e) {
    status(els.s1, "❌ Error: " + e.message);
  }
};

async function scoreScript() {
  try {
    status(els.s2, "Scoring...");
    const d = await j("/script/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: els.topic.value || els.quote.value,
        quote: els.quote.value,
        source: els.source.value,
        approved_script: els.script.value,
        persona: els.persona.value,
      }),
    });
    const s = d.score || {};
    els.scoreOverall.textContent = s.overall_score ?? "--";
    els.scoreVerdict.textContent = (s.verdict || "--").replace(/<[^>]*>/g, "");
    els.scoreHook.textContent = s.hook_strength?.score ?? "--";
    els.scorePacing.textContent = s.pacing?.score ?? "--";
    els.scoreEmotion.textContent = s.emotional_impact?.score ?? "--";
    els.scoreStructure.textContent = s.structure?.score ?? "--";
    els.scorePersona.textContent = s.persona_consistency?.score ?? "--";
    els.scoreVisual.textContent = s.visual_potential?.score ?? "--";
    renderSeoBlock(d.seo || {});
    status(els.s2, "✓ Scored.");
  } catch (e) {
    status(els.s2, "❌ Error: " + e.message);
  }
}

document.getElementById("btn-approve-score").onclick = async () => {
  setActiveTab("score");
  await scoreScript();
};

document.getElementById("btn-generate-voice").onclick = async () => {
  try {
    status(els.s3, "Generating voice...");
    const d = await j("/script/voice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        script_text: els.script.value,
        persona: els.persona.value,
        script_id: `${els.persona.value}_${Date.now()}`,
      }),
    });
    if (d.audio_url) {
      els.audio.src = d.audio_url.startsWith("/") ? BACKEND + d.audio_url : d.audio_url;
    }
    status(els.s3, "✓ Voice ready.");
  } catch (e) {
    status(els.s3, "❌ Error: " + e.message);
  }
};

document.getElementById("btn-generate-video").onclick = async () => {
  try {
    status(els.s3, "Submitting video job...");
    const d = await j("/script/video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        script_text: els.script.value,
        persona: els.persona.value,
        script_id: `${els.persona.value}_${Date.now()}`,
        aspect_ratio: "9:16",
      }),
    });
    const id = d.video_id;
    if (!id) {
      throw new Error("No video_id returned");
    }

    for (let i = 0; i < 120; i += 1) {
      await new Promise((r) => setTimeout(r, 3000));
      const st = await fetch(`${API}/script/video/${id}`).then((r) => r.json());
      const s = (st.status || "").toLowerCase();
      if (s === "completed" && st.video_url) {
        els.videoLink.href = st.video_url;
        els.videoLink.textContent = st.video_url;
        status(els.s3, "✓ Video ready.");
        return;
      }
      if (s === "failed" || s === "error") {
        throw new Error(st.error_message || "Video failed");
      }
      status(els.s3, `⏳ Rendering... ${i + 1}/120`);
    }
    throw new Error("Video timeout");
  } catch (e) {
    status(els.s3, "❌ Error: " + e.message);
  }
};

// Initialize dropdown on first load.
loadCuratedTopics();
