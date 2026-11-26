from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("seo_auditor.llm")

STOP_TAIL_WORDS = {
    "и", "а", "но", "или", "в", "во", "на", "с", "со", "к", "ко", "по", "о", "об", "от", "до",
    "за", "из", "у", "для", "при", "про", "без", "под", "над", "через", "что", "как", "где",
    "the", "and", "or", "for", "with", "to", "in", "on", "of", "at", "by",
}


def _truncate_words(text: str, max_len: int) -> str:
    """Truncate text cleanly at word boundaries without leaving dangling prepositions."""
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if len(clean) <= max_len:
        return clean
    cut = clean[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    cut = cut.rstrip(" ,.;:—–-")
    words = cut.split(" ")
    while len(words) > 2 and words[-1].lower() in STOP_TAIL_WORDS:
        words.pop()
    return " ".join(words).rstrip(" ,.;:—–-")


def _format_provider_label(provider: str, model: str) -> str:
    m = model.lower()
    if "gemma-4-31b" in m:
        return "ИИ-анализ: Gemma 4 31B"
    if "gemma-4-26b" in m:
        return "ИИ-анализ: Gemma 4 26B"
    if "nemotron-3-ultra" in m:
        return "ИИ-анализ: Nemotron 3 Ultra"
    if "openrouter/free" in m:
        return "ИИ-анализ: OpenRouter AI"
    if provider == "gemini":
        return "ИИ-анализ: Gemini Flash"
    if provider == "nvidia":
        return "ИИ-анализ: NVIDIA NIM"
    return f"ИИ-анализ: {provider.upper()}"


def _resolve_provider_config(provider: str | None, custom_api_key: str | None) -> dict[str, str] | None:
    prov = (provider or "auto").lower().strip()
    key = (custom_api_key or "").strip()

    if prov == "openrouter" or (prov == "auto" and (os.getenv("OPENROUTER_API_KEY") or key.startswith("sk-or-"))):
        api_key = key or os.getenv("OPENROUTER_API_KEY", "").strip()
        if api_key:
            return {
                "provider": "openrouter",
                "type": "openai",
                "api_key": api_key,
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "model": os.getenv("OPENROUTER_MODEL", "openrouter/free").strip() or "openrouter/free",
            }

    if prov == "nvidia" or (prov == "auto" and (os.getenv("NVIDIA_API_KEY") or key.startswith("nvapi-"))):
        api_key = key or os.getenv("NVIDIA_API_KEY", "").strip()
        if api_key:
            return {
                "provider": "nvidia",
                "type": "openai",
                "api_key": api_key,
                "base_url": "https://integrate.api.nvidia.com/v1/chat/completions",
                "model": os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
            }

    if prov == "gemini" or (prov == "auto" and os.getenv("GEMINI_API_KEY")):
        api_key = key or os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            return {
                "provider": "gemini",
                "type": "gemini",
                "api_key": api_key,
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            }

    return None


def _build_prompt(audit: dict[str, Any]) -> str:
    meta = audit["meta"]
    headings = audit["headings"]
    issues = [
        f"- [{c['status'].upper()}] {c['title']}: {c['detail']}"
        for c in audit["checks"]
        if c["status"] in ("fail", "warn")
    ][:12]
    payload = {
        "url": audit["url"],
        "score": audit["score"],
        "title": meta["title"],
        "description": meta["description"],
        "h1": headings["h1"],
        "h2": headings["h2"][:8],
        "top_keywords": [k["word"] for k in audit.get("top_keywords", [])],
        "json_ld_types": meta["json_ld_types"],
        "word_count": audit["stats"]["word_count"],
        "issues": issues,
        "text_preview": audit["text_preview"][:850],
    }
    schema_hint = (
        "{\n"
        '  "summary": "Короткий деловой вывод на 2 предложения о состоянии страницы и главном приоритете.",\n'
        '  "weaknesses": ["Конкретная проблема 1", "Конкретная проблема 2", "Конкретная проблема 3"],\n'
        '  "suggested_titles": ["Вариант Title 1 (45-60 символов)", "Вариант Title 2", "Вариант Title 3"],\n'
        '  "suggested_descriptions": ["Вариант Description 1 (130-160 символов)", "Вариант Description 2"],\n'
        '  "geo_recommendations": ["Совет под нейропоиск 1", "Совет под нейропоиск 2", "Совет под нейропоиск 3"],\n'
        '  "json_ld_snippet": "Готовый валидный JSON-LD (строка JSON без тегов <script>) для Schema.org под тематику страницы"\n'
        "}"
    )
    return (
        "Ты опытный SEO- и GEO-специалист (оптимизация под Яндекс, Google и нейропоиск). "
        "Проанализируй данные страницы и верни СТРОГО валидный JSON без пояснений вокруг по схеме:\n"
        f"{schema_hint}\n\n"
        f"Данные страницы:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _build_default_json_ld(audit: dict[str, Any], title: str, description: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": audit["url"],
        "inLanguage": audit["meta"].get("lang") or "ru",
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_head_snippet(audit: dict[str, Any], best_title: str, best_desc: str, json_ld_str: str) -> str:
    """Build invisible <head> SEO snippet that never touches visible page layout."""
    url = audit["url"]
    lines = [
        "<!-- Невидимые SEO- и GEO-теги для вставки внутрь <head> (визуал страницы не меняют) -->",
        f"<title>{best_title}</title>",
        f'<meta name="description" content="{best_desc}">',
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:title" content="{best_title}">',
        f'<meta property="og:description" content="{best_desc}">',
        f'<meta property="og:url" content="{url}">',
        '<meta property="og:type" content="website">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<script type="application/ld+json">',
        json_ld_str,
        "</script>",
    ]
    return "\n".join(lines)


def build_heuristic_recommendations(audit: dict[str, Any]) -> dict[str, Any]:
    """Clean deterministic fallback when no LLM key is provided or API is unreachable."""
    meta = audit["meta"]
    headings = audit["headings"]
    stats = audit["stats"]
    kws = [k["word"].capitalize() for k in audit.get("top_keywords", [])[:3]]

    raw_topic = (headings["h1"][0] if headings["h1"] else meta["title"]) or "Страница сайта"
    topic = _truncate_words(raw_topic.strip(" .—-"), 44)
    kw_tail = ", ".join(kws[:2]).lower() if kws else "цены и условия"

    weaknesses: list[str] = []
    for c in audit["checks"]:
        if c["status"] == "fail":
            weaknesses.append(f"{c['title']} — {c['fix']}")
    for c in audit["checks"]:
        if c["status"] == "warn" and len(weaknesses) < 4:
            weaknesses.append(f"{c['title']} — {c['fix']}")
    if not weaknesses:
        weaknesses.append("Критических технических ошибок не найдено: фокус на расширение семантики и контента.")

    suggested_titles = list(
        dict.fromkeys(
            [
                _truncate_words(f"{topic} — {kw_tail}, кейсы и расчет", 62),
                _truncate_words(f"{topic}: обзор, этапы работы и заказ онлайн", 62),
                _truncate_words(f"{topic} под ключ — условия, сроки и отзывы", 62),
            ]
        )
    )

    suggested_descriptions = [
        _truncate_words(
            f"{topic}. Понятные этапы работы, реальные примеры и быстрый расчет стоимости. Оставьте заявку на сайте и получите план решения.",
            158,
        ),
        _truncate_words(
            f"Подробно про {topic.lower()}: характеристики, ответы на частые вопросы и сравнение вариантов. Актуальные условия и контакты.",
            158,
        ),
    ]

    geo_tips: list[str] = []
    if not meta["json_ld_types"]:
        geo_tips.append("Добавьте микроразметку Schema.org (JSON-LD) в <head> — нейропоиск опирается на нее для понимания сути компании и услуг.")
    if len(headings["h2"]) < 3:
        geo_tips.append("Оформите подзаголовки H2 в виде прямых вопросов и ответов (FAQ), чтобы ИИ мог цитировать их в быстрых ответах.")
    if stats["word_count"] < 250:
        geo_tips.append("Добавьте конкретные цифры, сроки, цены и таблицу сравнения — генеративные модели предпочитают фактологический контент.")
    if len(geo_tips) < 3:
        geo_tips.append("Вынесите главный тезис и суть предложения в первый абзац под H1 (до 50 слов) для попадания в AI Overviews.")

    score = audit["score"]
    if score >= 80:
        verdict = f"Техническая база страницы сильная ({score}/100). Главная точка роста — усилить структурированные данные и подачу под нейропоиск."
    elif score >= 55:
        verdict = f"Средний уровень оптимизации ({score}/100). Исправление мета-тегов и структуры заголовков быстро даст прирост в выдаче."
    else:
        verdict = f"Обнаружены критические пробелы в базовом SEO ({score}/100). Начните с заполнения Title, Description, единого H1 и alt-атрибутов."

    json_ld_str = _build_default_json_ld(audit, suggested_titles[0], suggested_descriptions[0])
    head_snippet = build_head_snippet(audit, suggested_titles[0], suggested_descriptions[0], json_ld_str)

    return {
        "mode": "heuristic",
        "provider_label": "Локальный разбор",
        "summary": verdict,
        "weaknesses": weaknesses[:4],
        "suggested_titles": suggested_titles,
        "suggested_descriptions": suggested_descriptions,
        "geo_recommendations": geo_tips[:3],
        "head_snippet": head_snippet,
    }


async def _call_openai_model(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    is_openrouter: bool = False,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if is_openrouter:
        headers["HTTP-Referer"] = "https://github.com"
        headers["X-Title"] = "AI SEO & Page Auditor"

    is_gemma = "gemma" in model.lower()
    messages = (
        [{"role": "user", "content": prompt}]
        if is_gemma
        else [
            {"role": "system", "content": "Отвечай строго валидным JSON на русском языке."},
            {"role": "user", "content": prompt},
        ]
    )
    body: dict[str, Any] = {
        "model": model,
        "temperature": 0.3,
        "messages": messages,
    }
    if is_openrouter and any(k in model.lower() for k in ("nemotron", "openrouter/free")):
        body["reasoning"] = {"enabled": False}

    resp = await client.post(base_url, headers=headers, json=body)
    if resp.status_code >= 400:
        logger.warning("LLM HTTP %s for model %s: %s", resp.status_code, model, resp.text[:400])
        resp.raise_for_status()

    data = resp.json()
    msg = data["choices"][0]["message"]
    raw_text = msg.get("content") or msg.get("reasoning") or ""
    return _extract_json(raw_text)


async def generate_ai_recommendations(
    audit: dict[str, Any],
    provider: str | None = None,
    custom_api_key: str | None = None,
) -> dict[str, Any]:
    """Call configured LLM provider with multi-model fallback or fall back to heuristic mode."""
    cfg = _resolve_provider_config(provider, custom_api_key)
    if not cfg:
        return build_heuristic_recommendations(audit)

    prompt = _build_prompt(audit)
    try:
        async with httpx.AsyncClient(timeout=22.0) as client:
            if cfg["type"] == "gemini":
                endpoint = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{cfg['model']}:generateContent?key={cfg['api_key']}"
                )
                resp = await client.post(
                    endpoint,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
                    },
                )
                resp.raise_for_status()
                raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _extract_json(raw_text)
                used_model = cfg["model"]
            else:
                models_to_try = [cfg["model"]]
                if cfg["provider"] == "openrouter":
                    for fallback_m in (
                        "openrouter/free",
                        "google/gemma-4-31b-it:free",
                        "nvidia/nemotron-3-ultra:free",
                        "google/gemma-4-26b-a4b-it:free",
                    ):
                        if fallback_m not in models_to_try:
                            models_to_try.append(fallback_m)

                parsed = None
                used_model = models_to_try[0]
                last_err: Exception | None = None
                for candidate_model in models_to_try:
                    try:
                        parsed = await _call_openai_model(
                            client,
                            cfg["base_url"],
                            cfg["api_key"],
                            candidate_model,
                            prompt,
                            is_openrouter=(cfg["provider"] == "openrouter"),
                        )
                        used_model = candidate_model
                        break
                    except Exception as exc:
                        last_err = exc
                        logger.warning("Model %s failed (%s), trying next fallback...", candidate_model, exc)
                if parsed is None:
                    raise last_err or RuntimeError("All OpenRouter fallback models failed")

        titles = [_truncate_words(str(x), 65) for x in parsed.get("suggested_titles", []) if str(x).strip()][:3]
        descs = [_truncate_words(str(x), 165) for x in parsed.get("suggested_descriptions", []) if str(x).strip()][:2]
        if not titles or not descs:
            fallback = build_heuristic_recommendations(audit)
            titles = titles or fallback["suggested_titles"]
            descs = descs or fallback["suggested_descriptions"]

        raw_json_ld = parsed.get("json_ld_snippet")
        if isinstance(raw_json_ld, dict):
            json_ld_str = json.dumps(raw_json_ld, ensure_ascii=False, indent=2)
        elif isinstance(raw_json_ld, str) and raw_json_ld.strip().startswith("{"):
            json_ld_str = raw_json_ld.strip()
        else:
            json_ld_str = _build_default_json_ld(audit, titles[0], descs[0])

        head_snippet = build_head_snippet(audit, titles[0], descs[0], json_ld_str)

        return {
            "mode": "llm",
            "provider_label": _format_provider_label(cfg["provider"], used_model),
            "summary": str(parsed.get("summary", "")).strip(),
            "weaknesses": [str(x) for x in parsed.get("weaknesses", [])][:5],
            "suggested_titles": titles,
            "suggested_descriptions": descs,
            "geo_recommendations": [str(x) for x in parsed.get("geo_recommendations", [])][:4],
            "head_snippet": head_snippet,
        }
    except Exception as exc:
        logger.error("Falling back to local heuristic engine due to LLM error: %s", exc)
        return build_heuristic_recommendations(audit)


async def generate_comparison_summary(
    audit_a: dict[str, Any],
    audit_b: dict[str, Any],
    provider: str | None = None,
    custom_api_key: str | None = None,
) -> str:
    """Short comparison verdict between two audited pages."""
    winner = audit_a if audit_a["score"] >= audit_b["score"] else audit_b
    loser = audit_b if winner is audit_a else audit_a
    diff = abs(audit_a["score"] - audit_b["score"])
    if diff == 0:
        return f"Обе страницы набрали по {audit_a['score']}/100 баллов. Сравните метрики по категориям ниже, чтобы найти точки отрыва."
    return (
        f"Лидирует {winner['url']} ({winner['score']}/100 против {loser['score']}/100, отрыв +{diff} баллов): "
        f"меньше технических ошибок ({winner['summary_counts']['fail']} против {loser['summary_counts']['fail']}) "
        f"и {winner['stats']['word_count']} слов контента."
    )
