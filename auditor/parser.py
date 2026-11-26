from __future__ import annotations

import ipaddress
import json
import math
import re
import socket
import time
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

STOP_WORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она",
    "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только", "ее",
    "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда",
    "даже", "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него", "до",
    "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей",
    "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем",
    "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
    "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним", "здесь",
    "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем",
    "всех", "никогда", "можно", "при", "наконец", "два", "об", "другой", "хоть", "после",
    "над", "больше", "тот", "через", "эти", "нас", "про", "всего", "них", "какая", "много",
    "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой", "перед", "иногда",
    "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда", "конечно", "всю",
    "между", "the", "and", "for", "that", "this", "with", "you", "are", "from", "your",
    "have", "not", "but", "what", "all", "were", "when", "can", "there", "use", "each",
    "which", "how", "will", "other", "about", "out", "many", "then", "them", "these", "some",
    "into", "has", "more", "two", "like", "see", "time", "could", "no", "make", "than",
}


class FetchError(Exception):
    """Structured error raised when a target URL cannot be fetched or is client-rendered SPA."""

    def __init__(self, message: str, code: str = "fetch_error", reason: str = "", status_code: int = 0) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.reason = reason or message
        self.status_code = status_code


def validate_public_url(raw_url: str) -> str:
    """Normalize and validate URL, blocking private/loopback hosts (SSRF guard)."""
    url = raw_url.strip()
    if not url:
        raise FetchError("Укажите URL страницы.", code="invalid_url")
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise FetchError("Некорректный формат URL. Пример: https://example.com", code="invalid_url")

    hostname = (parsed.hostname or "").lower()
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.endswith(".local"):
        raise FetchError("Локальные адреса недоступны для сканирования.", code="ssrf_blocked")

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise FetchError("Приватные IP-адреса недоступны для сканирования.", code="ssrf_blocked")
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            for info in infos:
                addr = ipaddress.ip_address(info[4][0])
                if addr.is_private or addr.is_loopback or addr.is_link_local:
                    raise FetchError("Домен указывает на внутренний IP-адрес.", code="ssrf_blocked")
        except socket.gaierror:
            pass

    return url


async def fetch_html(url: str, timeout: float = 15.0) -> tuple[str, str, int, int, dict[str, str]]:
    """Fetch HTML and headers from URL. Returns (html, final_url, status_code, elapsed_ms, headers)."""
    safe_url = validate_public_url(url)
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
            },
        ) as client:
            response = await client.get(safe_url)
    except httpx.TimeoutException as exc:
        raise FetchError(
            "Сайт не ответил за 15 секунд.",
            code="blocked_or_spa",
            reason="Сервер превысил время ожидания ответа (таймаут 15 сек) или фильтрует облачные IP-адреса.",
        ) from exc
    except httpx.HTTPError as exc:
        raise FetchError(
            f"Не удалось подключиться к сайту: {exc}",
            code="fetch_error",
            reason="Ошибка сетевого соединения или некорректный домен.",
        ) from exc

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    headers = {k.lower(): v for k, v in response.headers.items()}
    content_type = headers.get("content-type", "")
    server_hdr = headers.get("server", "").lower()

    if response.status_code in (401, 403, 406, 429, 503):
        waf_name = "антибот-системой (WAF)"
        if "cloudflare" in server_hdr or "cf-ray" in headers:
            waf_name = "Cloudflare"
        elif "ddos-guard" in server_hdr:
            waf_name = "DDoS-Guard"
        elif "qrator" in server_hdr:
            waf_name = "Qrator"
        raise FetchError(
            f"Сайт закрыт от автоматического парсинга (HTTP {response.status_code}).",
            code="blocked_or_spa",
            reason=f"Сервер отклонил запрос кодом {response.status_code} — сработала защита {waf_name}.",
            status_code=response.status_code,
        )

    if response.status_code >= 400:
        raise FetchError(
            f"Сервер вернул ошибку HTTP {response.status_code}.",
            code="fetch_error",
            reason=f"Страница недоступна (код ответа {response.status_code}).",
            status_code=response.status_code,
        )

    if "html" not in content_type.lower() and "<html" not in response.text[:600].lower():
        raise FetchError(
            f"По адресу находится не HTML-страница ({content_type}).",
            code="fetch_error",
            reason="Аудитор анализирует только веб-страницы в формате HTML.",
        )

    soup_check = BeautifulSoup(response.text, "html.parser")
    for t in soup_check(["script", "style", "noscript", "svg", "template"]):
        t.decompose()
    visible_words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", soup_check.get_text(" "))
    if len(visible_words) < 25:
        raise FetchError(
            "Страница рендерится только через JavaScript (SPA).",
            code="blocked_or_spa",
            reason=f"В исходном HTML найдено всего {len(visible_words)} слов — контент подгружается скриптами в браузере (React/Vue/Tilda).",
            status_code=response.status_code,
        )

    return response.text, str(response.url), response.status_code, elapsed_ms, headers


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _estimate_title_px(title: str) -> int:
    px = 0.0
    for ch in title:
        if ch.isupper() or ch in "MWЖЩШЮФ@":
            px += 11.5
        elif ch in "ilI1.,!|:; ":
            px += 5.0
        else:
            px += 9.2
    return int(round(px))


def _extract_json_ld_types(soup: BeautifulSoup) -> list[str]:
    types: list[str] = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if "@graph" in item and isinstance(item["@graph"], list):
                for node in item["@graph"]:
                    if isinstance(node, dict) and "@type" in node:
                        t = node["@type"]
                        types.extend(t if isinstance(t, list) else [str(t)])
            elif "@type" in item:
                t = item["@type"]
                types.extend(t if isinstance(t, list) else [str(t)])
    return sorted(set(types))


def _extract_top_keywords(words: list[str], limit: int = 8) -> list[dict[str, Any]]:
    filtered = [w.lower() for w in words if len(w) >= 3 and not w.isdigit() and w.lower() not in STOP_WORDS]
    counts = Counter(filtered)
    return [{"word": word, "count": cnt} for word, cnt in counts.most_common(limit)]


def _normalize_url_for_cmp(u: str) -> str:
    p = urlparse(u.strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    path = (p.path or "/").rstrip("/") or "/"
    return f"{host}{path}"


def analyze_html(
    html: str,
    url: str = "https://example.com",
    status_code: int = 200,
    response_time_ms: int = 0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Parse HTML and compute 30 technical SEO + GEO metrics and weighted score."""
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    soup = BeautifulSoup(html, "html.parser")
    html_bytes = len(html.encode("utf-8", errors="ignore"))
    html_kb = round(html_bytes / 1024, 1)

    parsed_url = urlparse(url)
    is_https = parsed_url.scheme == "https"
    base_host = (parsed_url.hostname or "").lower()

    title_tags = soup.find_all("title")
    title = _clean_text(title_tags[0].get_text()) if title_tags else ""
    title_px = _estimate_title_px(title)

    desc_tags = soup.find_all("meta", attrs={"name": re.compile(r"^description$", re.I)})
    description = _clean_text(desc_tags[0].get("content", "")) if desc_tags else ""

    canonical_tags = soup.find_all(
        "link",
        attrs={"rel": lambda v: bool(v) and "canonical" in [x.lower() for x in (v if isinstance(v, list) else [v])]},
    )
    canonical = _clean_text(canonical_tags[0].get("href", "")) if canonical_tags else ""

    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    viewport = _clean_text(viewport_tag.get("content", "")) if viewport_tag else ""

    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots = _clean_text(robots_tag.get("content", "")) if robots_tag else ""

    charset_meta = soup.find("meta", attrs={"charset": True}) or soup.find(
        "meta", attrs={"http-equiv": re.compile(r"^content-type$", re.I)}
    )
    has_utf8 = "utf-8" in str(charset_meta).lower() if charset_meta else False

    favicon_tag = soup.find(
        "link",
        attrs={"rel": lambda v: bool(v) and any("icon" in x.lower() for x in (v if isinstance(v, list) else [v]))},
    )
    has_favicon = bool(favicon_tag and favicon_tag.get("href"))

    html_tag = soup.find("html")
    lang = _clean_text(html_tag.get("lang", "")) if html_tag else ""

    og_tags: dict[str, str] = {}
    for prop in ("og:title", "og:description", "og:image", "og:url", "og:type"):
        tag = soup.find("meta", attrs={"property": re.compile(f"^{re.escape(prop)}$", re.I)})
        og_tags[prop] = _clean_text(tag.get("content", "")) if tag else ""

    tw_card = soup.find("meta", attrs={"name": re.compile(r"^twitter:card$", re.I)})
    tw_title = soup.find("meta", attrs={"name": re.compile(r"^twitter:title$", re.I)})
    has_twitter_card = bool(tw_card or tw_title)

    json_ld_types = _extract_json_ld_types(soup)

    all_headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    heading_levels = [int(h.name[1]) for h in all_headings]
    hierarchy_skips = 0
    for prev, curr in zip(heading_levels, heading_levels[1:]):
        if curr - prev > 1:
            hierarchy_skips += 1

    h1_list = [_clean_text(h.get_text()) for h in soup.find_all("h1") if _clean_text(h.get_text())]
    h2_list = [_clean_text(h.get_text()) for h in soup.find_all("h2") if _clean_text(h.get_text())]
    h3_list = [_clean_text(h.get_text()) for h in soup.find_all("h3") if _clean_text(h.get_text())]
    question_headings = sum(1 for h in (h2_list + h3_list) if "?" in h)

    images = soup.find_all("img")
    images_total = len(images)
    images_missing_alt = 0
    images_missing_dims = 0
    images_lazy = 0
    mixed_content_count = 0

    for img in images:
        alt = _clean_text(img.get("alt", ""))
        if not alt:
            images_missing_alt += 1
        if not (img.get("width") and img.get("height")):
            images_missing_dims += 1
        if (img.get("loading") or "").lower() == "lazy":
            images_lazy += 1
        src = str(img.get("src") or "")
        if is_https and src.lower().startswith("http://"):
            mixed_content_count += 1

    for sc in soup.find_all(["script", "link"], src=True):
        s = str(sc.get("src") or "")
        if is_https and s.lower().startswith("http://"):
            mixed_content_count += 1

    links_internal = 0
    links_external = 0
    empty_links = 0
    unsafe_external_links = 0

    for a in soup.find_all("a"):
        href = str(a.get("href", "")).strip()
        if not href or href == "#" or href.lower().startswith("javascript:"):
            empty_links += 1
            continue
        if href.startswith(("#", "mailto:", "tel:")):
            continue
        p = urlparse(href)
        if not p.hostname or p.hostname.lower() == base_host:
            links_internal += 1
        else:
            links_external += 1
            target = (a.get("target") or "").lower()
            rel = " ".join(a.get("rel") or []).lower()
            if target == "_blank" and "noopener" not in rel:
                unsafe_external_links += 1

    body_clone = BeautifulSoup(html, "html.parser")
    lists_count = len(body_clone.find_all(["ul", "ol"]))
    tables_count = len(body_clone.find_all("table"))
    for tag in body_clone(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    body_text = _clean_text(body_clone.get_text(" "))
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", body_text)
    word_count = len(words)
    reading_time_min = max(1, math.ceil(word_count / 180)) if word_count else 0
    text_bytes = len(body_text.encode("utf-8", errors="ignore"))
    text_html_ratio = round((text_bytes / html_bytes) * 100, 1) if html_bytes > 0 else 0.0
    top_keywords = _extract_top_keywords(words, limit=8)

    checks: list[dict[str, str]] = []
    score = 0

    def add_check(category: str, status: str, check_title: str, detail: str, impact: str, fix: str, points: int) -> None:
        nonlocal score
        score += points
        checks.append({
            "category": category,
            "status": status,
            "title": check_title,
            "detail": detail,
            "impact": impact,
            "fix": fix,
        })

    # === 1. Мета и индексация (7 проверок, 31 балл) ===
    t_len = len(title)
    if not title:
        add_check("Мета и индексация", "fail", "Заголовок страницы в поиске (<title>)", "Тег <title> отсутствует.", "Главный фактор релевантности в Яндексе и Google.", "Добавьте уникальный <title> длиной 45–60 символов.", 0)
    elif 35 <= t_len <= 65 and title_px <= 580:
        add_check("Мета и индексация", "pass", "Заголовок страницы в поиске (<title>)", f"{t_len} симв. (~{title_px} px) — помещается в сниппет целиком.", "Формирует кликабельный заголовок в выдаче.", "", 10)
    else:
        add_check("Мета и индексация", "warn", "Длина или ширина <title>", f"{t_len} симв. (~{title_px} px, норма: 35–65 симв. / до 580 px).", "Слишком длинный заголовок обрежется многоточием, короткий хуже ранжируется.", "Скорректируйте <title> до 45–60 символов без лишней воды.", 5)

    if len(title_tags) <= 1:
        add_check("Мета и индексация", "pass", "Отсутствие дублей <title>", "На странице ровно один тег <title>.", "Исключает путаницу при индексации.", "", 2)
    else:
        add_check("Мета и индексация", "fail", f"Найдено несколько <title> ({len(title_tags)} шт.)", "В коде присутствуют дублирующиеся заголовки.", "Поисковик может выбрать нерелевантный вариант.", "Оставьте только один тег <title> внутри <head>.", 0)

    d_len = len(description)
    if not description:
        add_check("Мета и индексация", "fail", "Описание страницы в сниппете (Description)", "Тег meta description не заполнен.", "Поисковик соберет случайный кусок текста, что снизит CTR.", "Напишите продающий meta description на 130–160 символов.", 0)
    elif 110 <= d_len <= 165:
        add_check("Мета и индексация", "pass", "Описание страницы в сниппете (Description)", f"{d_len} символов — оптимально для сниппета.", "Повышает кликабельность страницы в результатах поиска.", "", 8)
    else:
        add_check("Мета и индексация", "warn", "Длина meta description вне нормы", f"Сейчас {d_len} символов (рекомендуется 110–165).", "Слишком длинное описание обрежется в поиске.", "Уложите суть оффера в 135–160 символов.", 4)

    if canonical:
        is_self = _normalize_url_for_cmp(canonical) == _normalize_url_for_cmp(url)
        if is_self:
            add_check("Мета и индексация", "pass", "Канонический адрес (Canonical)", "Указан корректный самоссылающийся canonical.", "Защищает страницу от дублей с UTM-метками.", "", 4)
        else:
            add_check("Мета и индексация", "warn", "Canonical ведет на другой URL", f"Указано: {canonical[:90]}", "Поисковики будут индексировать целевой URL вместо текущего.", "Проверьте, намеренно ли страница склеена с другим адресом.", 2)
    else:
        add_check("Мета и индексация", "warn", "Канонический адрес (Canonical)", "Тег <link rel=\"canonical\"> не найден.", "Параметры в URL могут плодить дубли страниц.", "Добавьте <link rel=\"canonical\" href=\"...\"> в <head>.", 0)

    if "noindex" in robots.lower():
        add_check("Мета и индексация", "fail", "Разрешение индексации (Robots)", f"Обнаружена директива: {robots}", "Страница полностью скрыта из поиска Яндекса и Google.", "Уберите noindex из meta robots, если страница публичная.", 0)
    else:
        add_check("Мета и индексация", "pass", "Разрешение индексации (Robots)", "Запретов на индексацию (noindex) не обнаружено.", "Страница открыта для поисковых роботов.", "", 3)

    if lang and has_utf8:
        add_check("Мета и индексация", "pass", "Язык страницы и кодировка UTF-8", f"lang=\"{lang}\", кодировка UTF-8 настроена.", "Гарантирует корректное отображение текста и региона.", "", 2)
    else:
        add_check("Мета и индексация", "warn", "Язык страницы (lang) или кодировка UTF-8", f"lang={lang or 'не указан'}, UTF-8={'да' if has_utf8 else 'нет'}.", "Помогает поисковикам и озвучке точно определять язык.", "Добавьте lang=\"ru\" в <html> и <meta charset=\"utf-8\">.", 1)

    if has_favicon:
        add_check("Мета и индексация", "pass", "Иконка сайта (Favicon)", "Тег <link rel=\"icon\"> подключен.", "Повышает узнаваемость и CTR в выдаче Яндекса и Google.", "", 2)
    else:
        add_check("Мета и индексация", "warn", "Иконка сайта (Favicon)", "В <head> не найдено подключение favicon.", "В поисковой выдаче отображается пустая серая иконка.", "Добавьте <link rel=\"icon\" href=\"/favicon.ico\"> в <head>.", 0)

    # === 2. Контент и структура (6 проверок, 26 баллов) ===
    if len(h1_list) == 1:
        add_check("Контент и структура", "pass", "Главный заголовок страницы (H1)", f"«{h1_list[0][:85]}»", "Задает главную тему страницы для пользователей и роботов.", "", 8)
    elif len(h1_list) == 0:
        add_check("Контент и структура", "fail", "Главный заголовок страницы (H1)", "Тег <h1> на странице отсутствует.", "Поисковым системам сложнее определить основной запрос страницы.", "Добавьте ровно один тег <h1> в первый экран страницы.", 0)
    else:
        add_check("Контент и структура", "warn", f"Найдено несколько H1 ({len(h1_list)} шт.)", "На странице больше одного заголовка первого уровня.", "Размывает тематический вес главного заголовка.", "Оставьте один главный <h1>, остальные замените на <h2>.", 4)

    if title and h1_list:
        t_words = {w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", title) if w.lower() not in STOP_WORDS}
        h_words = {w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", h1_list[0]) if w.lower() not in STOP_WORDS}
        overlap = t_words & h_words
        if overlap:
            add_check("Контент и структура", "pass", "Смысловая связка Title и H1", f"Общие ключевые слова: {', '.join(list(overlap)[:4])}.", "Подтверждает релевантность страницы поисковому запросу.", "", 4)
        else:
            add_check("Контент и структура", "warn", "Расхождение между Title и H1", "В Title и H1 нет общих ключевых слов.", "Снижает релевантность по главному запросу.", "Согласуйте ключевые фразы в тегах <title> и <h1>.", 1)
    else:
        add_check("Контент и структура", "warn", "Смысловая связка Title и H1", "Невозможно проверить без заполненных Title и H1.", "Нужны оба тега для оценки релевантности.", "Заполните <title> и <h1>.", 0)

    if len(h2_list) >= 2:
        add_check("Контент и структура", "pass", "Структура разделов (H2–H3)", f"H2: {len(h2_list)}, H3: {len(h3_list)} — четкое деление на смысловые блоки.", "Улучшает глубину просмотра и навигацию по странице.", "", 5)
    elif len(h2_list) == 1:
        add_check("Контент и структура", "warn", "Структура разделов (H2–H3)", "Найден всего 1 подзаголовок H2.", "Крупные блоки текста хуже сканируются пользователем.", "Разбейте контент на 3–5 логических разделов с тегами H2.", 2)
    else:
        add_check("Контент и структура", "fail", "Структура разделов (H2–H3)", "Подзаголовки H2 отсутствуют.", "Сплошной текст хуже ранжируется и плохо цитируется ИИ.", "Добавьте подзаголовки <h2> для ключевых блоков страницы.", 0)

    if hierarchy_skips == 0 and heading_levels:
        add_check("Контент и структура", "pass", "Логическая вложенность заголовков", "Перескоков уровней (например, H1 -> H4) не найдено.", "Помогает поисковикам и скринридерам строить оглавление.", "", 3)
    else:
        add_check("Контент и структура", "warn", "Нарушена иерархия уровней заголовков", f"Обнаружено пропусков уровней: {hierarchy_skips}.", "Использование заголовков ради размера шрифта ломает структуру.", "Соблюдайте последовательность H1 -> H2 -> H3, стили задавайте через CSS.", 1)

    if word_count >= 250:
        add_check("Контент и структура", "pass", "Объем текстового контента", f"{word_count} слов (~{reading_time_min} мин. чтения).", "Достаточно текста для уверенного ранжирования по группе запросов.", "", 4)
    elif word_count >= 100:
        add_check("Контент и структура", "warn", "Небольшой объем текста", f"Всего {word_count} слов (рекомендуется от 250 слов).", "Мало текста для охвата среднечастотных запросов.", "Добавьте описание преимуществ, этапов работы и блок FAQ.", 2)
    else:
        add_check("Контент и структура", "fail", "Критически мало текстового контента", f"Найдено {word_count} слов.", "Страница может считаться малоценной (Thin Content).", "Наполните страницу полезным текстом или включите SSR.", 0)

    if text_html_ratio >= 12.0:
        add_check("Контент и структура", "pass", "Доля текста к коду (Text-to-HTML)", f"{text_html_ratio}% полезного текста от объема HTML.", "Хороший баланс контента и разметки без лишнего мусора.", "", 2)
    else:
        add_check("Контент и структура", "warn", "Низкая доля текста к коду (Text-to-HTML)", f"{text_html_ratio}% (желательно от 12%).", "Слишком много инлайн-скриптов или тяжелой разметки на малое число слов.", "Вынесите CSS/JS во внешние файлы и расширьте текстовые блоки.", 1)

    # === 3. Медиа и скорость (6 проверок, 17 баллов) ===
    if viewport:
        add_check("Медиа и скорость", "pass", "Адаптация под мобильные (Viewport)", "Тег meta viewport настроен.", "Обязательное условие для Mobile-First индексации Google и Яндекса.", "", 4)
    else:
        add_check("Медиа и скорость", "fail", "Адаптация под мобильные (Viewport)", "Отсутствует meta name=\"viewport\".", "На смартфонах страница откроется в десктопном масштабе.", "Добавьте <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">.", 0)

    if images_total == 0:
        add_check("Медиа и скорость", "pass", "Описания картинок для поиска (alt)", "Изображений на странице нет.", "Ошибок с пустыми alt нет.", "", 5)
    elif images_missing_alt == 0:
        add_check("Медиа и скорость", "pass", "Описания картинок для поиска (alt)", f"Все {images_total} изображений имеют атрибут alt.", "Картинки индексируются в поиске по изображениям и доступны скринридерам.", "", 5)
    else:
        ratio = (images_total - images_missing_alt) / images_total
        add_check(
            "Медиа и скорость",
            "fail" if ratio < 0.5 else "warn",
            f"Описания картинок (alt): не заполнено у {images_missing_alt} из {images_total}",
            "Часть изображений не имеет текстового описания alt.",
            "Поисковые роботы не понимают, что изображено на картинках.",
            "Пропишите лаконичный описательный alt для всех значимых фото и схем.",
            int(round(5 * ratio)),
        )

    if images_total == 0 or images_missing_dims == 0:
        add_check("Медиа и скорость", "pass", "Стабильность верстки картинок (width/height)", "У изображений заданы размеры или картинок нет.", "Предотвращает скачки контента (CLS) при загрузке страницы.", "", 2)
    else:
        add_check("Медиа и скорость", "warn", "Не заданы width/height у изображений", f"У {images_missing_dims} из {images_total} тегов <img> нет явных размеров.", "При загрузке картинок верстка может прыгать (ухудшается Core Web Vitals CLS).", "Укажите атрибуты width и height или CSS aspect-ratio.", 0)

    if images_total <= 2 or images_lazy > 0:
        add_check("Медиа и скорость", "pass", "Отложенная загрузка картинок (Lazy Load)", "Настроена корректно для количества изображений на странице.", "Ускоряет отрисовку первого экрана.", "", 2)
    else:
        add_check("Медиа и скорость", "warn", "Нет loading=\"lazy\" у изображений", f"На странице {images_total} картинок и ни одной с loading=\"lazy\".", "Браузер грузит все нижние картинки сразу, замедляя старт страницы.", "Добавьте loading=\"lazy\" всем изображениям ниже первого экрана.", 0)

    if html_kb <= 250:
        add_check("Медиа и скорость", "pass", "Вес HTML-документа", f"{html_kb} КБ — легкий и быстрый документ.", "Быстро скачивается даже на мобильном интернете.", "", 2)
    else:
        add_check("Медиа и скорость", "warn", "Большой размер HTML-документа", f"{html_kb} КБ (рекомендуется до 250 КБ).", "Тяжелый HTML замедляет парсинг и Time to First Byte.", "Уберите встроенный Base64 и вынесите крупные скрипты.", 1)

    enc = headers.get("content-encoding", "")
    if not headers or any(x in enc.lower() for x in ("gzip", "br", "zstd")):
        add_check("Медиа и скорость", "pass", "Сжатие трафика (Gzip / Brotli)", f"Кодирование: {enc or 'локальный HTML'}.", "Уменьшает объем передаваемых данных в 3–5 раз.", "", 2)
    else:
        add_check("Медиа и скорость", "warn", "Не обнаружено сжатие Gzip / Brotli", "Заголовок Content-Encoding отсутствует.", "Страница передается в несжатом виде.", "Включите gzip или brotli на уровне веб-сервера / CDN.", 0)

    # === 4. Ссылки и безопасность (5 проверок, 12 баллов) ===
    if is_https:
        add_check("Ссылки и безопасность", "pass", "Защищенный протокол HTTPS", "Страница работает по HTTPS.", "Базовый фактор доверия браузеров и поисковых систем.", "", 3)
    else:
        add_check("Ссылки и безопасность", "fail", "Отсутствует HTTPS", "Страница открыта по незащищенному HTTP.", "Браузеры помечают сайт как небезопасный, позиции в поиске ниже.", "Настройте SSL-сертификат и 301-редирект с HTTP на HTTPS.", 0)

    if mixed_content_count == 0:
        add_check("Ссылки и безопасность", "pass", "Отсутствие смешанного контента (Mixed Content)", "Небезопасных http:// ресурсов на странице не найдено.", "Скрипты и картинки не блокируются браузером.", "", 2)
    else:
        add_check("Ссылки и безопасность", "fail", f"Смешанный контент ({mixed_content_count} ресурсов)", "На HTTPS-странице подключаются файлы по http://.", "Браузер может заблокировать загрузку стилей, скриптов или картинок.", "Переведите все ссылки на ресурсы на https://.", 0)

    if empty_links == 0:
        add_check("Ссылки и безопасность", "pass", "Корректность ссылок (нет пустых якорей)", "Пустых ссылок вида href=\"\" или href=\"#\" не найдено.", "Улучшает навигацию и распределение ссылочного веса.", "", 3)
    else:
        add_check("Ссылки и безопасность", "warn", f"Найдены пустые или якорные ссылки ({empty_links} шт.)", "Ссылки с href=\"\" или href=\"#\" не ведут на реальные разделы.", "Создают лишний шум для краулера и ухудшают UX.", "Замените заглушки на реальные URL или кнопки <button>.", 1)

    if unsafe_external_links == 0:
        add_check("Ссылки и безопасность", "pass", "Безопасность внешних ссылок (noopener)", "Внешние ссылки с target=\"_blank\" защищены.", "Защищает вкладку от уязвимости reverse tabnabbing.", "", 2)
    else:
        add_check("Ссылки и безопасность", "warn", f"Внешние ссылки без rel=\"noopener\" ({unsafe_external_links} шт.)", "Ссылки открываются в новой вкладке без атрибута noopener.", "Снижает оценку безопасности в аудитах (включая Lighthouse).", "Добавьте rel=\"noopener noreferrer\" к внешним ссылкам с target=\"_blank\".", 1)

    sec_headers = [h for h in ("strict-transport-security", "x-content-type-options", "x-frame-options") if h in headers]
    if not headers or len(sec_headers) >= 2:
        add_check("Ссылки и безопасность", "pass", "Заголовки безопасности HTTP", f"Активны: {', '.join(sec_headers) or 'локальный режим'}.", "Защищают сайт от подмены типов файлов и кликджекинга.", "", 2)
    else:
        add_check("Ссылки и безопасность", "warn", "Слабые HTTP-заголовки безопасности", f"Найдено заголовков: {len(sec_headers)} из 3 (HSTS, X-Content-Type-Options, X-Frame-Options).", "Повышает защищенность сайта в браузерах.", "Настройте базовые security-заголовки на сервере или в Vercel/Cloudflare.", 1)

    # === 5. Соцсети и GEO / нейропоиск (6 проверок, 14 баллов) ===
    og_core = sum(1 for k in ("og:title", "og:description", "og:image") if og_tags.get(k))
    if og_core == 3:
        add_check("Соцсети и GEO", "pass", "Разметка Open Graph (Telegram / соцсети)", "Заполнены og:title, og:description и og:image.", "При отправке ссылки в мессенджер формируется красивая карточка с обложкой.", "", 3)
    elif og_core > 0:
        add_check("Соцсети и GEO", "warn", f"Open Graph заполнен частично ({og_core}/3)", "Не хватает части базовых OG-тегов.", "Превью ссылки в Telegram или VK может отображаться без картинки или описания.", "Заполните все три тега: og:title, og:description и og:image.", 1)
    else:
        add_check("Соцсети и GEO", "warn", "Отсутствует разметка Open Graph", "Теги og:title, og:description и og:image не найдены.", "Ссылка в мессенджерах выглядит как голый текст без превью.", "Добавьте базовые Open Graph мета-теги в <head>.", 0)

    if og_tags.get("og:url") and og_tags.get("og:type"):
        add_check("Соцсети и GEO", "pass", "Расширенные теги og:url и og:type", "Указаны тип контента и канонический OG-адрес.", "Помогает соцсетям корректно группировать репосты.", "", 2)
    else:
        add_check("Соцсети и GEO", "warn", "Не указаны og:url или og:type", "Дополнительные OG-поля не заполнены.", "Не критично, но улучшает точность парсинга соцсетями.", "Добавьте og:type=\"website\" и og:url в <head>.", 0)

    if has_twitter_card:
        add_check("Соцсети и GEO", "pass", "Карточка для X / Twitter (Twitter Card)", "Теги twitter:card / twitter:title присутствуют.", "Обеспечивает крупное превью при публикации ссылки.", "", 2)
    else:
        add_check("Соцсети и GEO", "warn", "Карточка для X / Twitter (Twitter Card)", "Тег meta name=\"twitter:card\" не найден.", "При репосте в X/Twitter не покажется крупная карточка.", "Добавьте <meta name=\"twitter:card\" content=\"summary_large_image\">.", 0)

    if json_ld_types:
        add_check("Соцсети и GEO", "pass", "Микроразметка Schema.org (JSON-LD)", f"Найдены схемы: {', '.join(json_ld_types[:5])}.", "Помогает Google, Яндексу и LLM-поисковикам точно понимать сущности на странице.", "", 4)
    else:
        add_check("Соцсети и GEO", "warn", "Нет микроразметки Schema.org (JSON-LD)", "Структурированные данные JSON-LD не обнаружены.", "Снижает шансы на расширенный сниппет и точное цитирование в нейропоиске.", "Вставьте готовый блок <script type=\"application/ld+json\"> из соседней вкладки.", 0)

    if lists_count > 0 or tables_count > 0:
        add_check("Соцсети и GEO", "pass", "Списки и таблицы для нейропоиска (GEO)", f"Списков: {lists_count}, таблиц: {tables_count}.", "LLM-поисковики (Яндекс Нейро, AI Overviews) чаще всего цитируют структурированные списки и таблицы.", "", 2)
    else:
        add_check("Соцсети и GEO", "warn", "Нет списков и таблиц для нейропоиска (GEO)", "На странице нет тегов <ul>, <ol> или <table>.", "Нейросетям сложнее вытаскивать факты и сравнения из сплошных абзацев.", "Оформите преимущества, этапы или тарифы в виде маркированного списка или таблицы.", 0)

    if question_headings > 0:
        add_check("Соцсети и GEO", "pass", "Вопросительные подзаголовки (FAQ-сигнал)", f"Найдено заголовков с вопросами: {question_headings}.", "Прямые вопросы в H2/H3 повышают вероятность попадания в блок быстрых ответов ИИ.", "", 1)
    else:
        add_check("Соцсети и GEO", "warn", "Нет заголовков в формате вопросов (FAQ)", "Подзаголовки H2/H3 сформулированы без вопросов.", "Пользователи часто задают нейропоиску вопросы целиком.", "Добавьте 2–3 подзаголовка в формате вопроса («Сколько стоит...», «Как работает...»).", 0)

    score = max(0, min(100, score))
    if score >= 85:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "D"

    return {
        "url": url,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "score": score,
        "grade": grade,
        "checks_total": len(checks),
        "summary_counts": {
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "warn": sum(1 for c in checks if c["status"] == "warn"),
            "fail": sum(1 for c in checks if c["status"] == "fail"),
        },
        "meta": {
            "title": title,
            "title_length": t_len,
            "title_px": title_px,
            "description": description,
            "description_length": d_len,
            "canonical": canonical,
            "viewport": viewport,
            "robots": robots,
            "lang": lang,
            "has_utf8": has_utf8,
            "has_favicon": has_favicon,
            "open_graph": og_tags,
            "has_twitter_card": has_twitter_card,
            "json_ld_types": json_ld_types,
        },
        "headings": {
            "h1": h1_list[:10],
            "h2": h2_list[:15],
            "h3": h3_list[:15],
            "hierarchy_skips": hierarchy_skips,
        },
        "stats": {
            "word_count": word_count,
            "reading_time_min": reading_time_min,
            "html_kb": html_kb,
            "text_html_ratio": text_html_ratio,
            "images_total": images_total,
            "images_missing_alt": images_missing_alt,
            "images_missing_dims": images_missing_dims,
            "links_internal": links_internal,
            "links_external": links_external,
            "empty_links": empty_links,
        },
        "top_keywords": top_keywords,
        "text_preview": body_text[:1500],
        "checks": checks,
    }
