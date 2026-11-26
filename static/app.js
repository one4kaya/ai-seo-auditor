(() => {
  "use strict";

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Soft, wide, slowly drifting atmospheric Horizon (Hero top centerpiece)
  (function initHorizon() {
    const canvas = document.getElementById("horizonCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const stars = Array.from({ length: 44 }, (_, i) => ({
      rx: ((i * 73 + 19) % 100) / 100,
      ry: ((i * 41 + 11) % 100) / 100,
      r: (i % 3 === 0) ? 1.15 : 0.75,
      speed: 0.35 + (i % 5) * 0.2,
      phase: i * 0.7,
    }));

    let t = 0;
    function drawHorizon() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      // Subtle twinkling stars in upper sky
      stars.forEach((s) => {
        const sx = s.rx * w;
        const sy = s.ry * (h * 0.65);
        const alpha = 0.1 + 0.16 * (0.5 + 0.5 * Math.sin(t * s.speed + s.phase));
        ctx.fillStyle = `rgba(226, 232, 240, ${alpha.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(sx, sy, s.r, 0, Math.PI * 2);
        ctx.fill();
      });

      const cx = w / 2;
      const radius = Math.max(820, w * 0.72);
      const cy = -radius + 78;

      // Soft outer atmospheric corona
      const corona = ctx.createRadialGradient(cx, cy, radius - 8, cx, cy, radius + 140);
      corona.addColorStop(0, "rgba(210, 220, 244, 0.18)");
      corona.addColorStop(0.32, "rgba(148, 163, 210, 0.08)");
      corona.addColorStop(0.7, "rgba(90, 105, 145, 0.02)");
      corona.addColorStop(1, "rgba(7, 7, 10, 0)");

      ctx.fillStyle = corona;
      ctx.beginPath();
      ctx.arc(cx, cy, radius + 140, 0, Math.PI * 2);
      ctx.fill();

      // Dark planetary sphere with subtle rim
      const planetFill = ctx.createRadialGradient(cx, cy + radius * 0.25, radius * 0.15, cx, cy, radius);
      planetFill.addColorStop(0, "#0b0c12");
      planetFill.addColorStop(0.88, "#07070a");
      planetFill.addColorStop(0.98, "#0e111b");
      planetFill.addColorStop(1, "#1c2030");
      ctx.fillStyle = planetFill;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Barely noticeable thin horizon contour
      const baseRim = ctx.createLinearGradient(cx - radius * 0.55, 0, cx + radius * 0.55, 0);
      baseRim.addColorStop(0, "rgba(255,255,255,0)");
      baseRim.addColorStop(0.5, "rgba(226, 232, 248, 0.18)");
      baseRim.addColorStop(1, "rgba(255,255,255,0)");
      ctx.strokeStyle = baseRim;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0.18 * Math.PI, 0.82 * Math.PI);
      ctx.stroke();

      // Wide, soft, slowly drifting atmospheric glow along the horizon contour
      const driftAngle = Math.PI * 0.5 + Math.sin(t * 0.35) * 0.22;
      const fx = cx + Math.cos(driftAngle) * radius;
      const fy = cy + Math.sin(driftAngle) * radius;

      ctx.save();
      ctx.translate(fx, fy);
      ctx.scale(2.4, 0.65);
      const wideGlow = ctx.createRadialGradient(0, 0, 0, 0, 0, 170);
      wideGlow.addColorStop(0, "rgba(226, 234, 252, 0.16)");
      wideGlow.addColorStop(0.45, "rgba(186, 200, 235, 0.07)");
      wideGlow.addColorStop(1, "rgba(7, 7, 10, 0)");
      ctx.fillStyle = wideGlow;
      ctx.beginPath();
      ctx.arc(0, 0, 170, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      if (!reducedMotion) {
        t += 0.016;
        requestAnimationFrame(drawHorizon);
      }
    }

    drawHorizon();
    window.addEventListener("resize", () => {
      if (reducedMotion) drawHorizon();
    }, { passive: true });
  })();

  // 2. Hero CTA smooth scroll + Silver Spotlight highlight on target inputs & submit buttons
  const heroStartBtn = document.getElementById("heroStartBtn");
  const heroCompareBtn = document.getElementById("heroCompareBtn");
  const urlInput = document.getElementById("urlInput");
  const submitBtn = document.getElementById("submitBtn");
  const auditorSection = document.getElementById("auditor-section");
  const compareSection = document.getElementById("compare-section");
  const urlAInput = document.getElementById("urlAInput");
  const urlBInput = document.getElementById("urlBInput");
  const compareBtnEl = document.getElementById("compareBtn");

  function spotlightElements(sectionEl, focusEl, targets) {
    sectionEl.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => {
      focusEl.focus();
      targets.forEach((el) => el?.classList.add("target-spotlight"));
      setTimeout(() => {
        targets.forEach((el) => el?.classList.remove("target-spotlight"));
      }, 2400);
    }, 350);
  }

  heroStartBtn?.addEventListener("click", () => {
    spotlightElements(auditorSection, urlInput, [urlInput, submitBtn]);
  });

  heroCompareBtn?.addEventListener("click", () => {
    spotlightElements(compareSection, urlAInput, [urlAInput, urlBInput, compareBtnEl]);
  });

  // 4. Recent Audits History in localStorage
  const HISTORY_KEY = "seo_auditor_history_v1";
  const historyBar = document.getElementById("historyBar");
  const historyChips = document.getElementById("historyChips");

  function loadHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveToHistory(auditData) {
    if (!auditData || !auditData.url || auditData.url.includes(".example")) return;
    const items = loadHistory().filter((x) => x.url !== auditData.url);
    items.unshift({ url: auditData.url, score: auditData.score, grade: auditData.grade });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 4)));
    renderHistory();
  }

  function renderHistory() {
    const items = loadHistory();
    if (!items.length) {
      historyBar.classList.add("hidden");
      return;
    }
    historyBar.classList.remove("hidden");
    historyChips.innerHTML = "";
    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "history-chip";
      const shortHost = item.url.replace(/^https?:\/\//, "").replace(/\/$/, "");
      btn.textContent = `${shortHost} · ${item.score}/100`;
      btn.addEventListener("click", () => {
        switchInputTab("url");
        urlInput.value = item.url;
        runAudit({ url: item.url });
      });
      historyChips.appendChild(btn);
    });
  }
  renderHistory();

  // 5. Main Audit Logic
  const form = document.getElementById("auditForm");
  const htmlInput = document.getElementById("htmlInput");
  const urlPanel = document.getElementById("urlPanel");
  const htmlPanel = document.getElementById("htmlPanel");
  const diagCard = document.getElementById("diagCard");
  const errorBox = document.getElementById("errorBox");
  const resultsEl = document.getElementById("results");
  const submitHtmlBtn = document.getElementById("submitHtmlBtn");
  const auditProgress = document.getElementById("auditProgress");
  const auditProgressText = document.getElementById("auditProgressText");

  let activeTab = "url";
  let lastAudit = null;
  let activeFilter = "issues";

  function switchInputTab(tabName) {
    activeTab = tabName;
    document.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
    urlPanel.classList.toggle("hidden", tabName !== "url");
    htmlPanel.classList.toggle("hidden", tabName !== "html");
  }

  document.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => switchInputTab(btn.dataset.tab));
  });

  document.getElementById("switchToHtmlBtn")?.addEventListener("click", () => {
    switchInputTab("html");
    diagCard.classList.add("hidden");
    htmlInput.focus();
  });

  document.querySelectorAll("[data-demo]").forEach((btn) => {
    btn.addEventListener("click", () => runAudit({ demo_id: btn.dataset.demo }));
  });

  document.querySelectorAll("[data-detail-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.detailTab;
      document.querySelectorAll("[data-detail-tab]").forEach((b) => b.classList.toggle("active", b === btn));
      document.getElementById("detailChecks").classList.toggle("hidden", target !== "checks");
      document.getElementById("detailStructure").classList.toggle("hidden", target !== "structure");
      document.getElementById("detailCode").classList.toggle("hidden", target !== "code");
      document.getElementById("checkFilters").classList.toggle("hidden", target !== "checks");
    });
  });

  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeFilter = btn.dataset.filter;
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.toggle("active", b === btn));
      if (lastAudit) renderChecks(lastAudit.checks);
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (activeTab === "url") {
      runAudit({ url: urlInput.value.trim() });
    } else {
      runAudit({ raw_html: htmlInput.value.trim(), url: urlInput.value.trim() || "https://custom-html.local/" });
    }
  });

  let auditProgressTimer = null;

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitHtmlBtn.disabled = isLoading;
    submitBtn.querySelector(".btn-label").textContent = isLoading ? "Сканируем..." : "Проверить";
    submitHtmlBtn.querySelector(".btn-label").textContent = isLoading ? "Анализируем..." : "Разобрать HTML";
    submitBtn.querySelector(".btn-spinner")?.classList.toggle("hidden", !isLoading);
    submitHtmlBtn.querySelector(".btn-spinner")?.classList.toggle("hidden", !isLoading);

    if (auditProgressTimer) {
      clearInterval(auditProgressTimer);
      auditProgressTimer = null;
    }

    if (isLoading) {
      const steps = [
        "Скачивание HTML страницы...",
        "Проверка 30 SEO- и GEO-метрик...",
        "Генерация рекомендаций через LLM...",
      ];
      let stepIdx = 0;
      auditProgressText.textContent = steps[0];
      auditProgress.classList.remove("hidden");
      auditProgressTimer = setInterval(() => {
        stepIdx = Math.min(steps.length - 1, stepIdx + 1);
        auditProgressText.textContent = steps[stepIdx];
      }, 1700);
    } else {
      auditProgress.classList.add("hidden");
    }
  }

  async function runAudit(body) {
    diagCard.classList.add("hidden");
    errorBox.classList.add("hidden");
    setLoading(true);
    try {
      const resp = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) {
        if (data.code === "blocked_or_spa") {
          document.getElementById("diagTitle").textContent = data.detail || "Сайт закрыт от парсинга";
          document.getElementById("diagReason").textContent = data.reason || "";
          diagCard.classList.remove("hidden");
        } else {
          errorBox.textContent = data.detail || "Ошибка при анализе страницы.";
          errorBox.classList.remove("hidden");
        }
        return;
      }
      lastAudit = data;
      saveToHistory(data);
      renderAudit(data);
    } catch (err) {
      errorBox.textContent = err.message || "Не удалось выполнить запрос.";
      errorBox.classList.remove("hidden");
    } finally {
      setLoading(false);
    }
  }

  function updateSerpPreview(mode) {
    if (!lastAudit) return;
    document.querySelectorAll("[data-serp]").forEach((b) => b.classList.toggle("active", b.dataset.serp === mode));
    document.getElementById("serpUrl").textContent = lastAudit.url;
    if (mode === "current") {
      document.getElementById("serpTitle").textContent = lastAudit.meta.title || "(не указан тег <title>)";
      document.getElementById("serpDesc").textContent =
        lastAudit.meta.description || "(нет meta description — поисковик соберет случайный фрагмент текста)";
    } else {
      const idx = Number(mode) || 0;
      const titles = lastAudit.ai.suggested_titles || [];
      const descs = lastAudit.ai.suggested_descriptions || [];
      document.getElementById("serpTitle").textContent = titles[idx] || titles[0] || lastAudit.meta.title;
      document.getElementById("serpDesc").textContent = descs[idx % Math.max(1, descs.length)] || descs[0] || "";
    }
  }

  document.querySelectorAll("[data-serp]").forEach((btn) => {
    btn.addEventListener("click", () => updateSerpPreview(btn.dataset.serp));
  });

  function renderAudit(data) {
    resultsEl.classList.remove("hidden");

    const circumference = 326.7;
    const offset = circumference - (circumference * data.score) / 100;
    const ring = document.getElementById("scoreRing");
    ring.style.strokeDashoffset = String(offset);
    ring.style.stroke = data.score >= 80 ? "var(--pass)" : data.score >= 55 ? "var(--warn)" : "var(--fail)";
    document.getElementById("scoreNum").textContent = data.score;
    document.getElementById("scoreGrade").textContent = `GRADE ${data.grade}`;
    document.getElementById("aiProviderPill").textContent = data.ai.provider_label;

    updateSerpPreview("current");

    document.getElementById("kpiWords").textContent = `${data.stats.word_count} слов`;
    document.getElementById("kpiAlt").textContent = `${data.stats.images_missing_alt}/${data.stats.images_total}`;
    document.getElementById("kpiSpeed").textContent = `${data.response_time_ms} мс · ${data.stats.html_kb} КБ`;
    document.getElementById("kpiIssues").textContent = `${data.summary_counts.fail} / ${data.summary_counts.warn}`;

    document.getElementById("aiSummary").textContent = data.ai.summary;

    const priorities = data.checks.filter((c) => c.status !== "pass").slice(0, 3);
    renderBullets(
      "priorityList",
      priorities.length
        ? priorities.map((c) => `${c.title} — ${c.fix}`)
        : ["Критических ошибок не найдено: страница готова к индексации."]
    );
    renderBullets("aiGeo", data.ai.geo_recommendations);
    renderCopyList("aiTitles", data.ai.suggested_titles);
    renderCopyList("aiDescriptions", data.ai.suggested_descriptions);

    activeFilter = "issues";
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.toggle("active", b.dataset.filter === "issues"));
    renderChecks(data.checks);

    const kwCloud = document.getElementById("kwCloud");
    kwCloud.innerHTML = "";
    (data.top_keywords || []).forEach((item) => {
      const span = document.createElement("span");
      span.className = "kw-chip";
      span.textContent = `${item.word} (${item.count})`;
      kwCloud.appendChild(span);
    });
    renderBullets("listH1", data.headings.h1.length ? data.headings.h1 : ["Не найдены"]);
    renderBullets("listH2", data.headings.h2.length ? data.headings.h2 : ["Не найдены"]);
    renderBullets("listH3", data.headings.h3.length ? data.headings.h3 : ["Не найдены"]);

    document.getElementById("headCodeBlock").textContent = data.ai.head_snippet || "";

    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderBullets(elId, items) {
    const ul = document.getElementById(elId);
    ul.innerHTML = "";
    (items || []).forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      ul.appendChild(li);
    });
  }

  function renderCopyList(elId, items) {
    const box = document.getElementById(elId);
    box.innerHTML = "";
    (items || []).forEach((text) => {
      const row = document.createElement("div");
      row.className = "copy-card";
      const span = document.createElement("span");
      span.textContent = text;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "copy-btn";
      btn.textContent = "Копировать";
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(text);
          btn.textContent = "Готово";
          setTimeout(() => (btn.textContent = "Копировать"), 1500);
        } catch {
          btn.textContent = "Ошибка";
        }
      });
      row.append(span, btn);
      box.appendChild(row);
    });
  }

  function renderChecks(checks) {
    const list = document.getElementById("checksList");
    list.innerHTML = "";
    const filtered = checks.filter((c) => {
      if (activeFilter === "all") return true;
      if (activeFilter === "issues") return c.status === "fail" || c.status === "warn";
      return c.status === activeFilter;
    });
    if (!filtered.length) {
      list.innerHTML = '<div class="check-detail">В этой категории пунктов нет.</div>';
      return;
    }
    filtered.forEach((c) => {
      const item = document.createElement("div");
      item.className = "check-item";
      item.innerHTML = `
        <span class="dot ${c.status}"></span>
        <div>
          <div class="check-top">
            <span class="check-title"></span>
            <span class="check-cat"></span>
          </div>
          <div class="check-detail"></div>
          ${c.impact ? '<div class="check-impact"></div>' : ""}
          ${c.fix ? '<div class="check-fix"></div>' : ""}
        </div>
      `;
      item.querySelector(".check-title").textContent = c.title;
      item.querySelector(".check-cat").textContent = c.category;
      item.querySelector(".check-detail").textContent = c.detail;
      if (c.impact) item.querySelector(".check-impact").textContent = `На что влияет: ${c.impact}`;
      if (c.fix) item.querySelector(".check-fix").textContent = c.fix;
      list.appendChild(item);
    });
  }

  document.getElementById("copyCodeBtn")?.addEventListener("click", async (e) => {
    const code = document.getElementById("headCodeBlock").textContent;
    if (!code) return;
    await navigator.clipboard.writeText(code);
    e.target.textContent = "Скопировано";
    setTimeout(() => (e.target.textContent = "Скопировать код"), 1500);
  });

  document.getElementById("exportMdBtn")?.addEventListener("click", () => {
    if (!lastAudit) return;
    const d = lastAudit;
    const lines = [
      `# SEO & GEO Аудит: ${d.url}`,
      "",
      `- **Оценка:** ${d.score}/100 (Grade ${d.grade})`,
      `- **Проверено критериев:** ${d.checks_total}`,
      `- **Слов на странице:** ${d.stats.word_count}`,
      `- **Режим:** ${d.ai.provider_label}`,
      "",
      "## Вывод",
      d.ai.summary,
      "",
      "## Рекомендуемые Title",
      ...d.ai.suggested_titles.map((t) => `- ${t}`),
      "",
      "## Рекомендуемые Description",
      ...d.ai.suggested_descriptions.map((t) => `- ${t}`),
      "",
      "## Чек-лист проверок",
      ...d.checks.map((c) => `- [${c.status.toUpperCase()}] **${c.title}**: ${c.detail}${c.fix ? " -> " + c.fix : ""}`),
    ];
    downloadBlob(lines.join("\n"), "seo-audit-report.md", "text/markdown;charset=utf-8");
  });

  document.getElementById("exportJsonBtn")?.addEventListener("click", () => {
    if (!lastAudit) return;
    downloadBlob(JSON.stringify(lastAudit, null, 2), "seo-audit-report.json", "application/json;charset=utf-8");
  });

  function downloadBlob(content, filename, type) {
    const blob = new Blob([content], { type });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // 6. Competitor Comparison Section
  const compareForm = document.getElementById("compareForm");
  const compareBtn = document.getElementById("compareBtn");
  const compareError = document.getElementById("compareError");
  const compareResults = document.getElementById("compareResults");
  const compareProgress = document.getElementById("compareProgress");
  const compareProgressText = document.getElementById("compareProgressText");
  let compareProgressTimer = null;

  compareForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    compareError.classList.add("hidden");
    compareResults.classList.add("hidden");
    const url_a = document.getElementById("urlAInput").value.trim();
    const url_b = document.getElementById("urlBInput").value.trim();
    if (!url_a || !url_b) {
      compareError.textContent = "Укажите оба URL для сравнения.";
      compareError.classList.remove("hidden");
      return;
    }
    compareBtn.disabled = true;
    compareBtn.querySelector(".btn-label").textContent = "Сравниваем...";
    compareBtn.querySelector(".btn-spinner")?.classList.remove("hidden");

    const cmpSteps = [
      "Параллельное сканирование страниц...",
      "Сравнение 30 SEO- и GEO-метрик...",
      "Формирование вывода через LLM...",
    ];
    let cmpIdx = 0;
    compareProgressText.textContent = cmpSteps[0];
    compareProgress.classList.remove("hidden");
    compareProgressTimer = setInterval(() => {
      cmpIdx = Math.min(cmpSteps.length - 1, cmpIdx + 1);
      compareProgressText.textContent = cmpSteps[cmpIdx];
    }, 1700);

    try {
      const resp = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url_a, url_b }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.reason || data.detail || "Не удалось сравнить сайты.");
      }
      renderComparison(data);
    } catch (err) {
      compareError.textContent = err.message;
      compareError.classList.remove("hidden");
    } finally {
      if (compareProgressTimer) {
        clearInterval(compareProgressTimer);
        compareProgressTimer = null;
      }
      compareProgress.classList.add("hidden");
      compareBtn.disabled = false;
      compareBtn.querySelector(".btn-label").textContent = "Сравнить";
      compareBtn.querySelector(".btn-spinner")?.classList.add("hidden");
    }
  });

  function renderComparison(data) {
    const a = data.site_a;
    const b = data.site_b;
    compareResults.classList.remove("hidden");
    document.getElementById("compareVerdict").textContent = data.verdict;
    document.getElementById("thSiteA").textContent = a.url;
    document.getElementById("thSiteB").textContent = b.url;

    const rows = [
      ["Итоговый SEO-скор", `${a.score}/100 (${a.grade})`, `${b.score}/100 (${b.grade})`, a.score >= b.score, b.score >= a.score],
      ["Критичных ошибок", a.summary_counts.fail, b.summary_counts.fail, a.summary_counts.fail <= b.summary_counts.fail, b.summary_counts.fail <= a.summary_counts.fail],
      ["Объем текста (слов)", a.stats.word_count, b.stats.word_count, a.stats.word_count >= b.stats.word_count, b.stats.word_count >= a.stats.word_count],
      ["Подзаголовки H2 / H3", `${a.headings.h2.length} / ${a.headings.h3.length}`, `${b.headings.h2.length} / ${b.headings.h3.length}`, a.headings.h2.length >= b.headings.h2.length, b.headings.h2.length >= a.headings.h2.length],
      ["Микроразметка JSON-LD", a.meta.json_ld_types.join(", ") || "Нет", b.meta.json_ld_types.join(", ") || "Нет", a.meta.json_ld_types.length > 0, b.meta.json_ld_types.length > 0],
      ["Время ответа сервера", `${a.response_time_ms} мс`, `${b.response_time_ms} мс`, a.response_time_ms <= b.response_time_ms, b.response_time_ms <= a.response_time_ms],
    ];

    const tbody = document.getElementById("compareBody");
    tbody.innerHTML = "";
    rows.forEach(([label, valA, valB, winA, winB]) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${label}</td><td class="${winA ? "win-cell" : ""}">${valA}</td><td class="${winB ? "win-cell" : ""}">${valB}</td>`;
      tbody.appendChild(tr);
    });
  }
})();
