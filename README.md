<div align="center">

# 🔍 AI SEO & Page Auditor

**Технический SEO- и GEO-аудит посадочных страниц по 30 метрикам, сравнение с конкурентами и генерация мета-тегов через LLM**

[![Live Demo](https://img.shields.io/badge/Live_Demo-4seo.vercel.app-white?style=for-the-badge&logo=vercel&logoColor=black)](https://4seo.vercel.app/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter_API-6366F1?style=for-the-badge)](https://openrouter.ai/)

👉 **[Открыть работающий сервис — 4seo.vercel.app](https://4seo.vercel.app/)**

</div>

---

## ⚡ О проекте

**AI SEO & Page Auditor** — веб-сервис для быстрой технической диагностики сайтов и оценки готовности страниц к цитированию в нейропоиске (**GEO** — Яндекс Нейро, Google AI Overviews, Perplexity).

В отличие от базовых браузерных проверок (таких как стандартный Lighthouse), аудитор анализирует качество и пиксельную ширину мета-тегов, смысловую связку `Title` и `H1`, долю текста к HTML-коду, семантическое ядро страницы и сразу формирует готовый код для вставки в `<head>` без риска сломать дизайн.

---

## 🎯 Основные возможности

- 📊 **30 SEO- и GEO-проверок по 5 категориям:**
  - **Мета и индексация:** `<title>` (символы и ширина в пикселях), `meta description`, самоссылающийся `canonical`, `meta robots`, `<html lang>`, кодировка `UTF-8`, наличие `favicon`.
  - **Контент и структура:** единый `H1`, пересечение ключевых слов `Title ↔ H1`, иерархия `H1–H3` без перескоков уровней, объём текста, время чтения, `Text-to-HTML ratio` и **топ-8 ключевых слов страницы**.
  - **Медиа и скорость:** `viewport`, атрибуты `alt` и размеры `width`/`height` (защита от сдвига макета CLS), `loading="lazy"`, вес HTML-документа в КБ, сжатие `Gzip`/`Brotli`.
  - **Ссылки и безопасность:** `HTTPS`, поиск смешанного контента (`Mixed Content`), пустые якоря (`href="#"`), `rel="noopener"` у внешних ссылок и HTTP-заголовки безопасности (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options`).
  - **Соцсети и GEO (нейропоиск):** полный `Open Graph`, `Twitter Card`, микроразметка `Schema.org (JSON-LD)`, наличие списков/таблиц и вопросительных подзаголовков для FAQ-блоков.
- 🔎 **Интерактивный SERP-предпросмотр:** показывает текущий вид сниппета в поиске и позволяет в один клик примерить 3 варианта `Title` и `Description`, сгенерированных нейросетью.
- ⚔️ **Сравнение двух сайтов (`POST /api/compare`):** параллельный разбор вашей страницы и страницы конкурента с наглядной таблицей метрик и выводом лидера.
- 🧩 **Безопасный генератор кода для `<head>`:** формирует готовый блок мета-тегов и `Schema.org JSON-LD`, не затрагивая видимую вёрстку и стили страницы.
- 🛡️ **Умный обход блокировок (WAF / SPA):** автоматически определяет защиту Cloudflare/антибот (`403`/`429`) или клиентский рендеринг (React/Vue/Tilda) и предлагает пошаговый разбор через ручную вставку HTML.
- 📥 **Экспорт отчётов:** выгрузка полного отчёта в `.md` (Markdown) или `.json` в один клик, а также локальная история недавних проверок.

---

## 🛠️ Стек технологий

| Слой | Технологии |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, Uvicorn, Pydantic, `httpx` (async), `BeautifulSoup4` |
| **AI / LLM** | OpenRouter API с автоматическим фоллбэком моделей + локальный эвристический движок |
| **Frontend** | Vanilla HTML5, CSS3 (Bento-сетка, Canvas-анимация горизонта), ES6+ JavaScript |
| **Тестирование и деплой** | `pytest`, Docker, Vercel Serverless (`vercel.json`) |

---

## 📁 Структура проекта

```text
ai-seo-auditor/
├── app.py                  # FastAPI-приложение, эндпоинты /api/audit и /api/compare, security-заголовки
├── auditor/
│   ├── parser.py           # SSRF-защита, асинхронный парсер HTML и 30 SEO/GEO-проверок
│   ├── llm.py              # Интеграция с OpenRouter API, цепочка фоллбэков и генератор <head>
│   └── demo_data.py        # Встроенные демо-страницы для мгновенного тестирования
├── static/
│   ├── index.html          # Семантическая разметка (100/100 self-SEO)
│   ├── styles.css          # Тёмный Bento-интерфейс (Russo One + IBM Plex Sans + JetBrains Mono)
│   ├── app.js              # Canvas-горизонт, SERP-превью, экспорт отчётов и сравнение URL
│   └── favicon.svg         # Векторная иконка сервиса
├── tests/
│   └── test_parser.py      # Автотесты парсера, скоринга, LLM-фоллбэка и SSRF-защиты
├── vercel.json             # Конфигурация деплоя на Vercel
├── Dockerfile              # Контейнеризация для облачного запуска
└── requirements.txt        # Зависимости Python