(() => {
  "use strict";

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Crisp, smooth ASCII Wake pointer trail (clearly visible, no glitchy dots)
  (function initAsciiWake() {
    const canvas = document.getElementById("wakeCanvas");
    if (!canvas || reducedMotion) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const RAMP = " .:-=+*#%@";
    const cellSize = 15;
    let cols = 0;
    let rows = 0;
    let heat = new Float32Array(0);
    let rate = new Float32Array(0);
    let last = 0;
    const pointer = { x: -1, y: -1, t: 0, has: false };

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = `600 ${Math.round(cellSize * 0.82)}px "JetBrains Mono", ui-monospace, monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      cols = Math.ceil(w / cellSize);
      rows = Math.ceil(h / cellSize);
      const n = cols * rows;
      heat = new Float32Array(n);
      rate = new Float32Array(n).fill(1.35);
    }

    function draw() {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      for (let gy = 0; gy < rows; gy++) {
        for (let gx = 0; gx < cols; gx++) {
          const idx = gy * cols + gx;
          const lum = heat[idx];
          if (lum <= 0.03) continue;
          const ch = RAMP[Math.min(RAMP.length - 1, Math.floor(lum * (RAMP.length - 1)))];
          if (ch === " ") continue;
          ctx.fillStyle = `rgba(214, 222, 248, ${(lum * 0.44).toFixed(3)})`;
          ctx.fillText(ch, gx * cellSize + cellSize / 2, gy * cellSize + cellSize / 2);
        }
      }
    }

    function stamp(px, py, radiusCells, decayRate) {
      const cx = px / cellSize;
      const cy = py / cellSize;
      const r = Math.max(1.2, radiusCells);
      const minGx = Math.max(0, Math.floor(cx - r));
      const maxGx = Math.min(cols - 1, Math.ceil(cx + r));
      const minGy = Math.max(0, Math.floor(cy - r));
      const maxGy = Math.min(rows - 1, Math.ceil(cy + r));
      for (let gy = minGy; gy <= maxGy; gy++) {
        for (let gx = minGx; gx <= maxGx; gx++) {
          const d = Math.hypot(gx + 0.5 - cx, gy + 0.5 - cy);
          if (d > r) continue;
          const falloff = Math.pow(1 - d / r, 1.35);
          const idx = gy * cols + gx;
          if (falloff > heat[idx]) {
            heat[idx] = falloff;
            rate[idx] = decayRate;
          }
        }
      }
    }

    resize();
    window.addEventListener("pointermove", (e) => {
      const x = e.clientX;
      const y = e.clientY;
      const now = performance.now();
      if (pointer.has) {
        const dx = x - pointer.x;
        const dy = y - pointer.y;
        const dist = Math.hypot(dx, dy);
        const dt = Math.max(1, now - pointer.t);
        const speed = dist / dt;
        const radiusCells = Math.max(1.5, Math.min(3.2, 3.0 / (1 + speed * 1.1)));
        const decayRate = Math.max(0.95, Math.min(2.6, 1.05 + speed * 1.6));
        const steps = Math.max(1, Math.ceil(dist / (cellSize * 0.4)));
        for (let s = 1; s <= steps; s++) {
          const t = s / steps;
          stamp(pointer.x + dx * t, pointer.y + dy * t, radiusCells, decayRate);
        }
      } else {
        stamp(x, y, 2.2, 1.2);
      }
      pointer.x = x;
      pointer.y = y;
      pointer.t = now;
      pointer.has = true;
    }, { passive: true });

    window.addEventListener("resize", resize, { passive: true });

    function loop(now) {
      const dt = last ? Math.min(64, now - last) / 1000 : 1 / 60;
      last = now;
      for (let i = 0; i < heat.length; i++) {
        if (heat[i] > 0) {
          heat[i] = Math.max(0, heat[i] - rate[i] * dt);
        }
      }
      draw();
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  })();

  // 2. Animated Celestial Horizon & Orbiting Light Flare (Hero top centerpiece)
  (function initHorizon() {
    const canvas = document.getElementById("horizonCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const stars = Array.from({ length: 56 }, (_, i) => ({
      rx: ((i * 73 + 19) % 100) / 100,
      ry: ((i * 41 + 11) % 100) / 100,
      r: (i % 3 === 0) ? 1.3 : 0.8,
      speed: 0.4 + (i % 5) * 0.25,
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
        const sy = s.ry * (h * 0.72);
        const alpha = 0.14 + 0.22 * (0.5 + 0.5 * Math.sin(t * s.speed + s.phase));
        ctx.fillStyle = `rgba(226, 232, 240, ${alpha.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(sx, sy, s.r, 0, Math.PI * 2);
        ctx.fill();
      });

      const cx = w / 2;
      const radius = Math.max(760, w * 0.66);
      const cy = -radius + 132;

      // Outer atmospheric corona
      const corona = ctx.createRadialGradient(cx, cy, radius - 6, cx, cy, radius + 120);
      corona.addColorStop(0, "rgba(226, 232, 248, 0.34)");
      corona.addColorStop(0.28, "rgba(165, 180, 225, 0.14)");
      corona.addColorStop(0.65, "rgba(100, 116, 155, 0.04)");
      corona.addColorStop(1, "rgba(7, 7, 10, 0)");

      ctx.fillStyle = corona;
      ctx.beginPath();
      ctx.arc(cx, cy, radius + 120, 0, Math.PI * 2);
      ctx.fill();

      // Dark planetary sphere with internal subtle rim reflection
      const planetFill = ctx.createRadialGradient(cx, cy + radius * 0.25, radius * 0.15, cx, cy, radius);
      planetFill.addColorStop(0, "#0b0c12");
      planetFill.addColorStop(0.86, "#07070a");
      planetFill.addColorStop(0.97, "#111420");
      planetFill.addColorStop(1, "#262b3d");
      ctx.fillStyle = planetFill;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Base silver horizon rim
      const baseRim = ctx.createLinearGradient(cx - radius * 0.55, 0, cx + radius * 0.55, 0);
      baseRim.addColorStop(0, "rgba(255,255,255,0)");
      baseRim.addColorStop(0.5, "rgba(226, 232, 248, 0.52)");
      baseRim.addColorStop(1, "rgba(255,255,255,0)");
      ctx.strokeStyle = baseRim;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0.18 * Math.PI, 0.82 * Math.PI);
      ctx.stroke();

      // Orbiting light pulse sweeping smoothly back and forth along the horizon arc
      const sweepAngle = Math.PI * 0.5 + Math.sin(t * 0.75) * 0.24;
      const fx = cx + Math.cos(sweepAngle) * radius;
      const fy = cy + Math.sin(sweepAngle) * radius;

      const flare = ctx.createRadialGradient(fx, fy, 0, fx, fy, 135);
      flare.addColorStop(0, "rgba(255, 255, 255, 0.82)");
      flare.addColorStop(0.2, "rgba(219, 230, 255, 0.34)");
      flare.addColorStop(0.55, "rgba(148, 163, 210, 0.08)");
      flare.addColorStop(1, "rgba(7, 7, 10, 0)");

      ctx.fillStyle = flare;
      ctx.beginPath();
      ctx.arc(fx, fy, 135, 0, Math.PI * 2);
      ctx.fill();

      // Bright core arc segment around the traveling flare
      ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, sweepAngle - 0.055, sweepAngle + 0.055);
      ctx.stroke();

      if (!reducedMotion) {
        t += 0.022;
        requestAnimationFrame(drawHorizon);
      }
    }

    drawHorizon();
    window.addEventListener("resize", () => {
      if (reducedMotion) drawHorizon();
    }, { passive: true });
  })();

  // 3. Hero CTA smooth scroll + Silver Spotlight highlight on target input & submit button
  const heroStartBtn = document.getElementById("heroStartBtn");
  const urlInput = document.getElementById("urlInput");
  const submitBtn = document.getElementById("submitBtn");
  const auditorSection = document.getElementById("auditor-section");

  heroStartBtn?.addEventListener("click", () => {
    auditorSection.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => {
      urlInput.focus();
      urlInput.classList.add("target-spotlight");
      submitBtn.classList.add("target-spotlight");
      setTimeout(() => {
        urlInput.classList.remove("target-spotlight");
        submitBtn.classList.remove("target-spotlight");
      }, 2400);
    }, 350);
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
  const pageTypeSelect = document.getElementById("pageTypeSelect");
  const diagCard = document.getElementById("diagCard");
  const errorBox = document.getElementById("errorBox");
  const resultsEl = document.getElementById("results");
  const submitHtmlBtn = document.getElementById("submitHtmlBtn");

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

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitHtmlBtn.disabled = isLoading;
    submitBtn.querySelector("span").textContent = isLoading ? "Сканируем..." : "Проверить";
    submitHtmlBtn.querySelector("span").textContent = isLoading ? "Анализируем..." : "Разобрать HTML";
  }

  async function runAudit(body) {
    diagCard.classList.add("hidden");
    errorBox.classList.add("hidden");
    setLoading(true);
    try {
      const resp = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...body,
          page_type: pageTypeSelect.value,
        }),
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
    compareBtn.querySelector("span").textContent = "Сравниваем...";
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
      compareBtn.disabled = false;
      compareBtn.querySelector("span").textContent = "Сравнить";
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
