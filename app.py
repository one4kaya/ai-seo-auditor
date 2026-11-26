from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auditor.demo_data import DEMO_PAGES
from auditor.llm import generate_ai_recommendations, generate_comparison_summary
from auditor.parser import FetchError, analyze_html, fetch_html

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="AI SEO & Page Auditor",
    description="Технический SEO/GEO-аудитор веб-страниц с AI-рекомендациями",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AuditRequest(BaseModel):
    url: str | None = Field(default=None)
    raw_html: str | None = Field(default=None)
    demo_id: str | None = Field(default=None)
    page_type: str = Field(default="landing")


class CompareRequest(BaseModel):
    url_a: str
    url_b: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    raw_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    current_url = str(request.base_url).rstrip("/") + "/"
    rendered = raw_html.replace("__SELF_URL__", current_url)
    return HTMLResponse(content=rendered)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/audit")
async def run_audit(payload: AuditRequest) -> Any:
    if payload.demo_id:
        demo = DEMO_PAGES.get(payload.demo_id)
        if not demo:
            return JSONResponse(status_code=404, content={"detail": "Демо-пример не найден.", "code": "not_found"})
        audit = analyze_html(demo["html"], url=demo["url"], status_code=200, response_time_ms=12)
    elif payload.raw_html and payload.raw_html.strip():
        target_url = (payload.url or "https://custom-html.local/").strip()
        audit = analyze_html(payload.raw_html, url=target_url, status_code=200, response_time_ms=5)
    elif payload.url and payload.url.strip():
        try:
            html, final_url, status_code, elapsed_ms, headers = await fetch_html(payload.url)
        except FetchError as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": exc.message,
                    "code": exc.code,
                    "reason": exc.reason,
                    "status_code": exc.status_code,
                },
            )
        audit = analyze_html(html, url=final_url, status_code=status_code, response_time_ms=elapsed_ms, headers=headers)
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": "Укажите URL, вставьте HTML-код или выберите демо-пример.", "code": "empty_input"},
        )

    audit["ai"] = await generate_ai_recommendations(audit, page_type=payload.page_type)
    return audit


@app.post("/api/compare")
async def compare_pages(payload: CompareRequest) -> Any:
    async def _audit_one(raw_url: str) -> dict[str, Any]:
        html, final_url, status_code, elapsed_ms, headers = await fetch_html(raw_url)
        return analyze_html(html, url=final_url, status_code=status_code, response_time_ms=elapsed_ms, headers=headers)

    try:
        audit_a, audit_b = await asyncio.gather(_audit_one(payload.url_a), _audit_one(payload.url_b))
    except FetchError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "detail": exc.message,
                "code": exc.code,
                "reason": exc.reason,
            },
        )

    verdict = await generate_comparison_summary(audit_a, audit_b)
    return {
        "verdict": verdict,
        "site_a": audit_a,
        "site_b": audit_b,
    }
