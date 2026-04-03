window.tailwind = window.tailwind || {};
window.tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "secondary-dim": "#7b3f61",
        "primary-fixed": "#8b9dff",
        surface: "#f8f9ff",
        "inverse-surface": "#0b0e12",
        "on-tertiary-fixed": "#073e56",
        "inverse-primary": "#8b9dff",
        "secondary-fixed": "#ffd8e9",
        primary: "#4557b4",
        "on-primary-container": "#001871",
        "on-tertiary-container": "#22516a",
        error: "#a8364b",
        "on-background": "#2d333b",
        "primary-fixed-dim": "#7d8ff0",
        background: "#f8f9ff",
        tertiary: "#37647e",
        "surface-dim": "#d5dae5",
        "on-secondary-fixed-variant": "#854769",
        "tertiary-dim": "#2a5871",
        "tertiary-fixed-dim": "#a5d2ef",
        "tertiary-container": "#b3e0fe",
        "on-primary-fixed": "#000004",
        "on-secondary": "#fff7f8",
        "on-tertiary-fixed-variant": "#2d5b74",
        "outline-variant": "#acb2bd",
        "primary-dim": "#384ba7",
        outline: "#757b85",
        "on-primary-fixed-variant": "#082282",
        "surface-container-low": "#f1f3fb",
        "secondary-fixed-dim": "#ffc4e0",
        "surface-container": "#eaeef7",
        "secondary-container": "#ffd8e9",
        "error-dim": "#6b0221",
        "on-error-container": "#6e0523",
        "on-surface-variant": "#595f69",
        "on-tertiary": "#f4f9ff",
        "tertiary-fixed": "#b3e0fe",
        "on-error": "#fff7f7",
        "primary-container": "#8b9dff",
        "on-surface": "#2d333b",
        "surface-variant": "#dde3ee",
        secondary: "#894b6d",
        "surface-container-lowest": "#ffffff",
        "on-primary": "#faf8ff",
        "surface-container-high": "#e4e8f2",
        "error-container": "#f97386",
        "surface-bright": "#f8f9ff",
        "on-secondary-container": "#793e5f",
        "surface-tint": "#4557b4",
        "inverse-on-surface": "#9b9da2",
        "surface-container-highest": "#dde3ee",
        "on-secondary-fixed": "#642c4c"
      },
      fontFamily: {
        headline: ["Plus Jakarta Sans"],
        body: ["Be Vietnam Pro"],
        label: ["Be Vietnam Pro"]
      },
      borderRadius: {
        DEFAULT: "1rem",
        lg: "2rem",
        xl: "3rem",
        full: "9999px"
      }
    }
  }
};

const API_BASE = "http://127.0.0.1:8000";
const API = `${API_BASE}/api`;

function apiFetch(input, init = {}) {
  return fetch(input, { ...init, credentials: "include" });
}


function initAnimations() {
  const elements = document.querySelectorAll('.animate-reveal');
  elements.forEach((el, index) => {
    el.style.opacity = "0"; // Ensure they start invisible
    setTimeout(() => {
      el.classList.add('animate-reveal'); // Triggers CSS animation
    }, index * 100);
  });
}



document.addEventListener("DOMContentLoaded", async () => {
  const isLoginPage = document.documentElement.getAttribute("data-page") === "login";
  if (!isLoginPage) {
    try {
      const r = await apiFetch(`${API}/auth/me`);
      if (!r.ok) {
        throw new Error("unauthenticated");
      }
    } catch (_) {
      window.location.replace("./login.html");
      return;
    }
  }

  const $ = (id) => document.getElementById(id);
  const safeJson = async (res) => {
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    return res.json();
  };
  const bodyEl = document.body;
  const bodyViewClasses = ["step1-page", "script-page", "score-page", "voice-page"];
  const viewRoots = {
    topic: document.querySelector('[data-view="topic"]'),
    script: document.querySelector('[data-view="script"]'),
    score: document.querySelector('[data-view="score"]'),
    voice: document.querySelector('[data-view="voice"]'),
  };
  const hasSinglePageViews = Object.values(viewRoots).every(Boolean);
  const desktopViewLinks = document.querySelectorAll("[data-view-link]");
  const mobileViewLinks = document.querySelectorAll("[data-mobile-view-link]");
  let activeView = "topic";
  let ensureScore = async () => {};

  const setBodyClassForView = (view) => {
    if (!bodyEl) return;
    bodyEl.classList.remove(...bodyViewClasses);
    const mapped = view === "topic" ? "step1-page" : `${view}-page`;
    bodyEl.classList.add(mapped);
  };

  const syncNavUi = (view) => {
    desktopViewLinks.forEach((link) => {
      const linkView = link.getAttribute("data-view-link");
      link.classList.toggle("active", linkView === view);
    });
    mobileViewLinks.forEach((link) => {
      const linkView = link.getAttribute("data-mobile-view-link");
      const isActive = linkView === view;
      if (isActive) {
        link.classList.add("bg-[#8b9dff]", "dark:bg-[#4557b4]", "text-white", "rounded-[2rem]", "px-6", "py-3", "scale-110");
        link.classList.remove("text-[#37647e]", "dark:text-slate-400");
      } else {
        link.classList.remove("bg-[#8b9dff]", "dark:bg-[#4557b4]", "text-white", "rounded-[2rem]", "px-6", "py-3", "scale-110");
        link.classList.add("text-[#37647e]", "dark:text-slate-400");
      }
    });
  };

  const renderView = (view, updateHash = true) => {
    if (!hasSinglePageViews) return;
    const nextView = viewRoots[view] ? view : "topic";
    activeView = nextView;
    Object.entries(viewRoots).forEach(([key, root]) => {
      if (!root) return;
      root.classList.toggle("hidden", key !== nextView);
    });
    setBodyClassForView(nextView);
    syncNavUi(nextView);
    if (updateHash) {
      const targetHash = `#${nextView}`;
      if (window.location.hash !== targetHash) {
        window.history.pushState({}, "", targetHash);
      }
    }
  };

  const getViewFromHash = () => {
    const raw = String(window.location.hash || "").replace(/^#/, "").trim().toLowerCase();
    return raw && viewRoots[raw] ? raw : "topic";
  };

  if (hasSinglePageViews) {
    renderView(getViewFromHash(), false);
    if (activeView === "score") {
      void ensureScore();
    }
    window.addEventListener("hashchange", () => {
      renderView(getViewFromHash(), false);
      if (activeView === "score") {
        void ensureScore();
      }
    });
  }

  const personaCards = document.querySelectorAll("[data-persona]");
  const topicSelect = document.getElementById("topic");
  const step2Btn = $("btn-step2");
  const defaultTopics = [
    "Outer Space Adventure",
    "Deep Jungle Mystery",
    "Underwater Party",
    "The Magic Castle"
  ];

  const setButtonLoading = (el, loadingText) => {
    if (!el) return () => {};
    const originalContent = el.innerHTML;
    el.disabled = true;
    el.innerHTML = `
      <div class="flex items-center gap-3">
        <div class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
        <span>${loadingText}</span>
      </div>
    `;
    return () => {
      el.disabled = false;
      el.innerHTML = originalContent;
    };
  };

  const setMediaButtonLoading = (el, loadingText) => {
    if (!el) return () => {};
    const originalContent = el.innerHTML;
    el.disabled = true;
    el.setAttribute("data-loading", "true");
    el.innerHTML = `
      <span class="inline-flex items-center gap-2">
        <span class="media-btn-spinner" aria-hidden="true"></span>
        <span>${loadingText}</span>
      </span>
    `;
    return () => {
      el.disabled = false;
      el.removeAttribute("data-loading");
      el.innerHTML = originalContent;
    };
  };

  async function loadTopics(persona) {
    if (!topicSelect) {
      return;
    }
    try {
      const response = await apiFetch(`${API}/topics?persona=${encodeURIComponent(persona || "arthur")}`);
      if (!response.ok) {
        throw new Error("Failed topic response");
      }
      const data = await response.json();
      const topics = Array.isArray(data.topics) && data.topics.length ? data.topics : defaultTopics;
      topicSelect.innerHTML = '<option disabled hidden selected value="">Pick a Topic!</option>' +
        topics.map((topic) => `<option value="${String(topic).toLowerCase().replace(/\s+/g, "_")}">${topic}</option>`).join("");
    } catch (_) {
      topicSelect.innerHTML = '<option disabled hidden selected value="">Pick a Topic!</option>' +
        defaultTopics.map((topic) => `<option value="${String(topic).toLowerCase().replace(/\s+/g, "_")}">${topic}</option>`).join("");
    }
  }

  function setActivePersona(activeCard) {
    personaCards.forEach((card) => {
      card.classList.remove("is-selected");
    });
    if (activeCard) {
      activeCard.classList.add("is-selected");
      activeCard.classList.remove("click-pop");
      void activeCard.offsetWidth;
      activeCard.classList.add("click-pop");
    }
  }

  personaCards.forEach((card) => {
    card.addEventListener("click", () => {
      const persona = card.getAttribute("data-persona");
      if (persona) {
        localStorage.setItem("selectedPersona", persona);
        loadTopics(persona);
      }
      setActivePersona(card);
    });
  });

  if (topicSelect) {
    topicSelect.addEventListener("change", () => {
      const selectedText = topicSelect.options[topicSelect.selectedIndex]?.text || "";
      localStorage.setItem("selectedTopic", topicSelect.value || "");
      localStorage.setItem("selectedTopicLabel", selectedText);
    });
  }

  if (topicSelect) {
    const savedPersona = localStorage.getItem("selectedPersona") || "arthur";
    if (personaCards.length) {
      const selectedCard = Array.from(personaCards).find((card) => card.getAttribute("data-persona") === savedPersona);
      setActivePersona(selectedCard || personaCards[0]);
    }
    loadTopics(savedPersona);
  }

  const currentTopic = document.getElementById("current-topic");
  if (currentTopic) {
    const selectedTopicLabel = localStorage.getItem("selectedTopicLabel") || "";
    currentTopic.textContent = selectedTopicLabel ? `Selected topic: ${selectedTopicLabel}` : "Selected topic: none yet (go back and pick one).";
  }

  if (step2Btn && topicSelect) {
    step2Btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const selectedOption = topicSelect.options[topicSelect.selectedIndex];
      const selectedValue = (topicSelect.value || "").trim();
      const selectedTopic = selectedOption?.text?.trim() || "";
      const isInvalidSelection =
        !selectedValue ||
        !selectedTopic ||
        selectedOption?.disabled ||
        selectedTopic.toLowerCase() === "pick a topic!";

      if (isInvalidSelection) {
        alert("Please pick a topic first.");
        return;
      }
      const stopLoading = setButtonLoading(step2Btn, "Generating Script...");
      const persona = localStorage.getItem("selectedPersona") || "arthur";
      try {
        const quoteData = await safeJson(
          await apiFetch(`${API}/topic/quote`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: selectedTopic, persona })
          })
        );
        const scriptData = await safeJson(
          await apiFetch(`${API}/topic/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              topic: selectedTopic,
              quote: quoteData.quote,
              source: quoteData.source,
              persona
            })
          })
        );
        const fullScript = scriptData?.spoken_script?.full_script || "";
        localStorage.setItem("selectedTopicLabel", selectedTopic);
        localStorage.setItem("selectedQuote", quoteData.quote || "");
        localStorage.setItem("selectedSource", quoteData.source || "");
        localStorage.setItem("currentScript", fullScript);
        if (hasSinglePageViews) {
          renderView("script");
        } else {
          window.location.href = "./script.html";
        }
      } catch (err) {
        stopLoading();
        alert(`Could not generate script: ${err.message}`);
      }
    });
  }

  const scriptText = $("script-text");
  const editScriptBtn = $("btn-edit-script");
  const regenerateScriptBtn = $("btn-regenerate-script");
  const scriptStatus = $("script-status");
  const selectedTopicEl = $("selected-topic");
  const selectedQuoteEl = $("selected-quote");
  const selectedSourceEl = $("selected-source");
  const quotePanelEl = $("quote-panel");
  const quoteEditForm = $("quote-edit-form");
  const quoteEditInput = $("quote-edit-input");
  const sourceEditInput = $("source-edit-input");
  const saveQuoteEditBtn = $("btn-save-quote-edit");
  const cancelQuoteEditBtn = $("btn-cancel-quote-edit");
  const editQuoteBtn = $("btn-edit-quote");
  const finishScoreBtn = $("btn-finish-score");

  if (scriptText) {
    scriptText.value = localStorage.getItem("currentScript") || "Generating script...";
  }

  const renderQuotePanel = () => {
    if (!quotePanelEl) return;
    const selectedTopicLabel = localStorage.getItem("selectedTopicLabel") || "";
    const selectedQuote = localStorage.getItem("selectedQuote") || "";
    const selectedSource = localStorage.getItem("selectedSource") || "";
    if (!selectedQuote) {
      quotePanelEl.classList.add("hidden");
      return;
    }
    quotePanelEl.classList.remove("hidden");
    if (selectedTopicEl) {
      selectedTopicEl.textContent = selectedTopicLabel ? `Topic: ${selectedTopicLabel}` : "Selected Quote";
    }
    if (selectedQuoteEl) {
      selectedQuoteEl.textContent = `"${selectedQuote}"`;
    }
    if (selectedSourceEl) {
      selectedSourceEl.textContent = selectedSource ? `Source: ${selectedSource}` : "";
    }
  };
  renderQuotePanel();

  if (editScriptBtn && scriptText) {
    editScriptBtn.addEventListener("click", () => {
      scriptText.focus();
      scriptText.selectionStart = scriptText.value.length;
      scriptText.selectionEnd = scriptText.value.length;
      scriptText.classList.add("edit-highlight");
      window.setTimeout(() => scriptText.classList.remove("edit-highlight"), 700);
      if (scriptStatus) scriptStatus.textContent = "Editing script...";
    });
  }

  const regenerateScriptFromCurrentQuote = async () => {
    const quoteFromStorage = localStorage.getItem("selectedQuote") || "";
    // Fallback: if the original quote isn't in localStorage (common after refresh),
    // regenerate using the currently loaded script text as the "quote" prompt.
    const quote = quoteFromStorage || String(scriptText?.value || "");
    const source = localStorage.getItem("selectedSource") || "Edited source";
    const topic = localStorage.getItem("selectedTopicLabel") || "";
    const persona = localStorage.getItem("selectedPersona") || "arthur";
    if (!quote || !scriptText) return;
    if (scriptStatus) scriptStatus.textContent = "Regenerating script...";
    try {
      const data = await safeJson(
        await apiFetch(`${API}/topic/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, quote, source, persona }),
        })
      );
      const fullScript = data?.spoken_script?.full_script || "";
      scriptText.value = fullScript;
      localStorage.setItem("currentScript", fullScript);
      localStorage.removeItem("scorePayload");
      if (scriptStatus) scriptStatus.textContent = "Script regenerated.";
    } catch (err) {
      if (scriptStatus) scriptStatus.textContent = `Regenerate failed: ${err.message}`;
    }
  };

  if (editQuoteBtn) {
    editQuoteBtn.addEventListener("click", () => {
      if (!quoteEditForm || !quoteEditInput || !sourceEditInput) return;
      quoteEditInput.value = localStorage.getItem("selectedQuote") || "";
      sourceEditInput.value = localStorage.getItem("selectedSource") || "Edited source";
      quoteEditForm.classList.remove("hidden");
    });
  }

  if (cancelQuoteEditBtn) {
    cancelQuoteEditBtn.addEventListener("click", () => {
      if (quoteEditForm) quoteEditForm.classList.add("hidden");
    });
  }

  if (saveQuoteEditBtn) {
    saveQuoteEditBtn.addEventListener("click", async () => {
      const cleanedQuote = String(quoteEditInput?.value || "").trim();
      const cleanedSource = String(sourceEditInput?.value || "").trim() || "Edited source";
      if (!cleanedQuote) {
        alert("Quote cannot be empty.");
        return;
      }
      localStorage.setItem("selectedQuote", cleanedQuote);
      localStorage.setItem("selectedSource", cleanedSource);
      renderQuotePanel();
      if (quoteEditForm) quoteEditForm.classList.add("hidden");
      await regenerateScriptFromCurrentQuote();
    });
  }

  if (regenerateScriptBtn) {
    regenerateScriptBtn.addEventListener("click", async () => {
      await regenerateScriptFromCurrentQuote();
    });
  }

  // If the user navigated from the Score page, auto-regenerate without another click.
  // Usage: script.html?autogen_script=1
  try {
    if (regenerateScriptBtn) {
      const params = new URLSearchParams(window.location.search || "");
      const shouldAutogenScript = String(params.get("autogen_script") || "").toLowerCase() === "1";
      if (shouldAutogenScript) {
        const url = new URL(window.location.href);
        url.searchParams.delete("autogen_script");
        window.history.replaceState({}, "", url.toString());
        if (scriptStatus) scriptStatus.textContent = "Auto-regenerating script...";
        // Call directly (more reliable than synthetic button clicks).
        void regenerateScriptFromCurrentQuote();
      }
    }
  } catch (_) {
    // If URL parsing fails, keep manual click behavior.
  }

  if (finishScoreBtn) {
    finishScoreBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!scriptText) {
        return;
      }
      const stopLoading = setButtonLoading(finishScoreBtn, "Scoring Reel...");
      const persona = localStorage.getItem("selectedPersona") || "arthur";
      const topic = localStorage.getItem("selectedTopicLabel") || "";
      const quote = localStorage.getItem("selectedQuote") || "";
      const source = localStorage.getItem("selectedSource") || "";
      try {
        const data = await safeJson(
          await apiFetch(`${API}/script/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              topic,
              quote,
              source,
              approved_script: scriptText.value,
              persona
            })
          })
        );
        localStorage.setItem("scorePayload", JSON.stringify(data));
        if (hasSinglePageViews) {
          renderView("score");
          await ensureScore();
        } else {
          window.location.href = "./score.html";
        }
      } catch (err) {
        stopLoading();
        if (scriptStatus) {
          scriptStatus.textContent = `Score failed: ${err.message}`;
        }
      }
    });
  }

  const scoreBox = $("overall-score");
  const verdictBox = $("score-verdict");
  const metricHook = $("metric-hook");
  const metricPacing = $("metric-pacing");
  const metricEmotion = $("metric-emotion");
  const metricVisual = $("metric-visual");
  const metricHookBar = $("metric-hook-bar");
  const metricPacingBar = $("metric-pacing-bar");
  const metricEmotionBar = $("metric-emotion-bar");
  const metricVisualBar = $("metric-visual-bar");
  const ytCaption = $("yt-caption");
  const ytTags = $("yt-tags");
  const igCaption = $("ig-caption");
  const igTags = $("ig-tags");
  const ttCaption = $("tt-caption");
  const ttTags = $("tt-tags");
  const fbCaption = $("fb-caption");
  const fbTags = $("fb-tags");
  const scoreStatus = $("score-status");
  const voiceBtn = $("btn-generate-voice");
  const videoBtn = $("btn-generate-video");
  const voiceAudio = $("voice-audio");
  const voiceLink = $("voice-link");
  const videoLink = $("video-link");
  const scoreStrengths = $("score-strengths");
  const scorePriorityFix = $("score-priority-fix");

  const scorePage = !!scoreBox;
  const scriptValue = localStorage.getItem("currentScript") || "";

  const animateCount = (el, targetValue) => {
    if (!el || !Number.isFinite(targetValue)) return;
    const end = Math.max(0, Math.round(targetValue));
    let current = 0;
    const step = () => {
      current += 1;
      el.textContent = String(current);
      if (current < end) requestAnimationFrame(step);
    };
    step();
  };

  const renderScore = (payload) => {
    const score = payload?.score || {};
    const seo = payload?.seo || {};
    const hashtagsToText = (arr) => (Array.isArray(arr) && arr.length ? arr.map((t) => `#${t}`).join(" ") : "--");
    if (scoreBox && typeof score.overall_score === "number") animateCount(scoreBox, score.overall_score);
    else if (scoreBox) scoreBox.textContent = score.overall_score ?? "--";
    const hook = Number(score.hook_strength?.score ?? 0);
    const pacing = Number(score.pacing?.score ?? 0);
    const emotion = Number(score.emotional_impact?.score ?? 0);
    const visual = Number(score.visual_potential?.score ?? 0);
    const overall = Number(score.overall_score ?? 0);
    // Backend uses 1–10 for dimensions and overall; align UI "ready" hints with that scale.
    const hasStrongBaseline =
      Number.isFinite(overall) &&
      overall >= 8 &&
      [hook, pacing, emotion, visual].every((metric) => Number.isFinite(metric) && metric >= 7);
    const rawPriorityFix = String(score?.priority_fix || "").trim();
    const hasPriorityFix = !!rawPriorityFix && !/no major fix needed/i.test(rawPriorityFix);

    if (verdictBox) {
      const verdict = String(score.verdict || "").trim();
      if (verdict && !/^done$/i.test(verdict)) {
        verdictBox.textContent = verdict.replace(/<[^>]*>/g, "");
      } else {
        verdictBox.textContent = hasStrongBaseline ? "Ready to Post" : "Needs Polish";
      }
    }
    const barPct = (n) => (Number.isFinite(n) ? Math.max(0, Math.min(100, (n / 10) * 100)) : 0);
    if (metricHook) metricHook.textContent = Number.isFinite(hook) ? `${hook}/10` : "--";
    if (metricPacing) metricPacing.textContent = Number.isFinite(pacing) ? `${pacing}/10` : "--";
    if (metricEmotion) metricEmotion.textContent = Number.isFinite(emotion) ? `${emotion}/10` : "--";
    if (metricVisual) metricVisual.textContent = Number.isFinite(visual) ? `${visual}/10` : "--";
    if (metricHookBar) metricHookBar.style.width = `${barPct(hook)}%`;
    if (metricPacingBar) metricPacingBar.style.width = `${barPct(pacing)}%`;
    if (metricEmotionBar) metricEmotionBar.style.width = `${barPct(emotion)}%`;
    if (metricVisualBar) metricVisualBar.style.width = `${barPct(visual)}%`;
    if (ytCaption) ytCaption.textContent = seo?.youtube?.description || seo?.youtube?.caption || "No caption generated.";
    if (ytTags) ytTags.textContent = hashtagsToText(seo?.youtube?.hashtags);
    if (igCaption) igCaption.textContent = seo?.instagram?.description || seo?.instagram?.caption || "No caption generated.";
    if (igTags) igTags.textContent = hashtagsToText(seo?.instagram?.hashtags);
    if (ttCaption) ttCaption.textContent = seo?.tiktok?.description || seo?.tiktok?.caption || "No caption generated.";
    if (ttTags) ttTags.textContent = hashtagsToText(seo?.tiktok?.hashtags);
    if (fbCaption) fbCaption.textContent = seo?.facebook?.description || seo?.facebook?.caption || "No caption generated.";
    if (fbTags) fbTags.textContent = hashtagsToText(seo?.facebook?.hashtags);
    if (scoreStrengths) {
      const rawList = score?.strengths?.strengths ?? score?.strengths?.items;
      const strengths = Array.isArray(rawList) ? rawList : [];
      scoreStrengths.innerHTML = strengths.length
        ? strengths.slice(0, 4).map((item) => `<li>${String(item)}</li>`).join("")
        : "<li>Strong consistency and good baseline structure.</li>";
    }
    if (scorePriorityFix) {
      scorePriorityFix.textContent = hasPriorityFix
        ? rawPriorityFix
        : hasStrongBaseline
          ? "Ready to post. No major fix needed."
          : "Refine one weaker section before posting.";
    }
  };

  ensureScore = async () => {
    if (!scorePage) return;
    const cached = localStorage.getItem("scorePayload");
    if (cached) {
      try {
        renderScore(JSON.parse(cached));
        return;
      } catch (_) {}
    }
    const persona = localStorage.getItem("selectedPersona") || "arthur";
    const topic = localStorage.getItem("selectedTopicLabel") || "";
    const quote = localStorage.getItem("selectedQuote") || "";
    const source = localStorage.getItem("selectedSource") || "";
    if (!scriptValue || !quote) return;
    try {
      const data = await safeJson(
        await apiFetch(`${API}/script/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, quote, source, approved_script: scriptValue, persona })
        })
      );
      localStorage.setItem("scorePayload", JSON.stringify(data));
      renderScore(data);
    } catch (err) {
      if (scoreStatus) scoreStatus.textContent = `Score load failed: ${err.message}`;
    }
  };
  ensureScore();

  if (hasSinglePageViews) {
    document.querySelectorAll("[data-nav-action]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const action = btn.getAttribute("data-nav-action");
        if (action === "autogen-script") {
          e.preventDefault();
          renderView("script");
          void regenerateScriptFromCurrentQuote();
        }
        if (action === "autogen-voice") {
          e.preventDefault();
          renderView("voice");
          if (voiceBtn) voiceBtn.click();
        }
      });
    });
  }

  if (voiceBtn) {
    voiceBtn.addEventListener("click", async () => {
      const persona = localStorage.getItem("selectedPersona") || "arthur";
      const stopLoading = setMediaButtonLoading(voiceBtn, "Generating Voice...");
      try {
        const data = await safeJson(
          await apiFetch(`${API}/script/voice`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ script_text: scriptValue, persona })
          })
        );
        const mediaBase = API_BASE || window.location.origin;
        if (data.audio_url && voiceAudio) {
          const src = data.audio_url.startsWith("/") ? `${mediaBase}${data.audio_url}` : data.audio_url;
          voiceAudio.src = src;
        }
        if (data.audio_url && voiceLink) {
          const href = data.audio_url.startsWith("/") ? `${mediaBase}${data.audio_url}` : data.audio_url;
          voiceLink.href = href;
          voiceLink.textContent = "Open generated voice file";
        }
        // Intentionally do not set a "Voice ready" status message on success.
      } catch (err) {
        if (scoreStatus) scoreStatus.textContent = `Voice failed: ${err.message}`;
      } finally {
        stopLoading();
      }
    });

    // Legacy support for old multi-page flow URLs.
    try {
      const params = new URLSearchParams(window.location.search || "");
      const shouldAutogen = String(params.get("autogen") || "").toLowerCase() === "1";
      if (shouldAutogen) {
        if (hasSinglePageViews) {
          renderView("voice");
        }
        voiceBtn.click();
      }
    } catch (_) {
      // If URL parsing fails, just keep manual click behavior.
    }
  }

  if (videoBtn) {
    videoBtn.addEventListener("click", async () => {
      const persona = localStorage.getItem("selectedPersona") || "arthur";
      const stopLoading = setMediaButtonLoading(videoBtn, "Submitting Video...");
      try {
        const data = await safeJson(
          await apiFetch(`${API}/script/video`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ script_text: scriptValue, persona, aspect_ratio: "9:16" })
          })
        );
        if (videoLink) {
          videoLink.href = "#";
          videoLink.textContent = data.video_id ? `Video job submitted: ${data.video_id}` : "Video job submitted";
        }
        if (scoreStatus) scoreStatus.textContent = `Video job submitted: ${data.video_id || "ok"}`;
      } catch (err) {
        if (scoreStatus) scoreStatus.textContent = `Video failed: ${err.message}`;
      } finally {
        stopLoading();
      }
    });
  }

  const copyButtons = document.querySelectorAll("[data-copy-target]");
  copyButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const selector = btn.getAttribute("data-copy-target");
      const target = selector ? document.querySelector(selector) : null;
      if (!target) {
        return;
      }
      const text = "value" in target ? target.value : target.textContent;
      if (!text) {
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        // Intentionally silent for static UI compatibility.
      }
    });
  });

  document.querySelectorAll("[data-logout]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        await apiFetch(`${API}/auth/logout`, { method: "POST" });
      } catch (_) {
        // Still send user to login so the session cookie is cleared client-side intent.
      }
      window.location.href = "./login.html";
    });
  });
});
