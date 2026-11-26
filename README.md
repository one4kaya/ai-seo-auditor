---
title: AI SEO & Page Auditor
emoji: 🔍
colorFrom: gray
colorTo: slate
sdk: docker
app_port: 7860
pinned: false
---

# AI SEO & Page Auditor

Веб-сервис на **Python (FastAPI)** для комплексного технического SEO- и GEO-аудита посадочных страниц по **30 критериям**, сравнения конкурентов и генерации готовых мета-тегов через LLM.

## Основные возможности
- **30 SEO- и GEO-проверок (5 категорий):** мета-теги и пиксельная ширина `<title>`, самоссылающийся `canonical`, иерархия `H1–H3`, доля текста к коду, топ-8 ключевых слов, `alt` и размеры `width/height` (CLS), `loading="lazy"`, сжатие Gzip/Brotli, HTTPS/Mixed Content, Open Graph, Twitter Cards, `Schema.org JSON-LD` и FAQ-сигналы для нейропоиска.
- **Интерактивный SERP-предпросмотр:** показывает текущий вид сниппета в поиске и позволяет в один клик примерить варианты `Title` и `Description` от нейросети.
- **Сравнение с конкурентом (`POST /api/compare`):** параллельный анализ двух URL с таблицей метрик и выводом лидера.
- **Генератор кода для `<head>`:** формирует только невидимые мета-теги и `JSON-LD` без вмешательства в видимую верстку и дизайн сайта.
- **Диагностика закрытых сайтов:** распознает блокировки Cloudflare/WAF и клиентские SPA, предлагая пошаговый разбор через вставку исходного HTML.

## Стек
- **Backend:** Python 3.12, FastAPI, Uvicorn, httpx, BeautifulSoup4, Pydantic
- **Frontend:** Vanilla HTML5 / CSS3 / ES6+ (Bento-сетка, Canvas-горизонт, ASCII-след курсора)
- **Тесты и деплой:** Pytest, Vercel (`vercel.json`), Docker

## Локальный запуск

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

uvicorn app:app --reload --port 7860
```

Запуск тестов:
```bash
pytest -v
```
