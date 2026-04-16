#!/usr/bin/env python3
"""
furniture_agent.py — Autonomous furniture archive builder using CrewAI.

Builds one classic furniture page at a time for the Chairs site (Astro + GitHub Pages).
Every execution produces exactly one new page and stops.

Usage:
    python furniture_agent.py           # Build the next pending page
    python furniture_agent.py --plan    # Sync and display backlog status only
"""

import argparse
import base64
import hashlib
import importlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# GitHub Models uses an OpenAI-compatible endpoint routed through the
# Copilot/Azure AI inference gateway. Set GITHUB_MODELS=1 in .env to opt in.
# The token is the same GITHUB_TOKEN used for PyGithub.
_GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
BACKLOG = ROOT / "backlog.json"
CONCEPT = ROOT / "site_concept.md"
CONTENT_DIR = ROOT / "src" / "content" / "blog"
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"
IMAGES_DIR = ROOT / "public" / "images"
REFERENCE_IMAGES_DIR = IMAGES_DIR / "reference"
CHECKPOINTS_DIR = ROOT / ".checkpoints"
DEFAULT_PLACEHOLDER_IMAGE = IMAGES_DIR / "blog-placeholder-1.jpg"
PHASE6_FALLBACK_GUARD_ENV = "FURNITURE_PHASE6_FALLBACK_ACTIVE"
PHASE6_FALLBACK_SCRIPT = ROOT / "generate_images_standalone.py"
PHASE6_FALLBACK_MAX_ERROR_LINES = 4
PLACEHOLDER_IMAGE_CANDIDATES = [
    IMAGES_DIR / "blog-placeholder-1.jpg",
    IMAGES_DIR / "blog-placeholder-2.jpg",
    IMAGES_DIR / "blog-placeholder-3.jpg",
    IMAGES_DIR / "blog-placeholder-4.jpg",
]
PLACEHOLDER_SLOTS = [
    ("hero", "Hero view of the full chair profile"),
    ("detail-material", "Close-up of the chair material and finish"),
    ("detail-structure", "Detail of structural joinery or hardware"),
    ("detail-silhouette", "Profile or silhouette detail of the chair form"),
]
IMAGE_SLOT_PROMPT_FILES = [
    ("hero", "hero.txt"),
    ("detail-material", "detail-material.txt"),
    ("detail-structure", "detail-structure.txt"),
    ("silhouette", "silhouette.txt"),
]
STYLE_NEGATIVE_PROMPT = (
    "harsh shadows, cool lighting, daylight, fluorescent, over-saturated colors, "
    "cluttered background, people, rugs, lamps, artwork, books, decorative props, "
    "text, logos, watermark, modern anachronistic elements, cartoonish, painterly, "
    "low resolution, blur, motion blur"
)
STYLE_PROMPT_SUFFIX = (
    "Use soft diffused warm light in the 2700-3000K range. Keep natural color grading, "
    "moderate contrast, realistic material textures, and clean negative space. Preserve "
    "historical fidelity: authentic silhouette, proportions, joinery, and era plausibility. "
    "No people or clutter."
)


# ── Checkpointing ─────────────────────────────────────────────────────────
# Task outputs are saved to .checkpoints/<slug>/<name>.txt as each task
# completes. If a run fails part-way through, the next run can resume from
# whatever was already written rather than starting over from scratch.

_CHECKPOINT_NAMES = ["plan", "research", "article_body", "description"]


def _checkpoint_path(slug: str, name: str) -> Path:
    return CHECKPOINTS_DIR / slug / f"{name}.txt"


def make_task_checkpoint_callback(slug: str, name: str):
    """Return a CrewAI Task callback that writes the task output to disk."""
    def _callback(output) -> None:
        try:
            raw = str(getattr(output, "raw", output)).strip()
            if not raw:
                return
            cp = _checkpoint_path(slug, name)
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(raw, encoding="utf-8")
            log.info("Checkpoint saved: .checkpoints/%s/%s.txt", slug, name)
        except Exception as exc:  # never let a checkpoint write crash the agent
            log.warning("Checkpoint write failed (%s/%s): %s", slug, name, exc)
    return _callback


def load_checkpoint(slug: str, name: str) -> Optional[str]:
    """Return a cleaned, validated checkpoint text, or None if missing or corrupt."""
    cp = _checkpoint_path(slug, name)
    if not cp.exists():
        return None
    raw = cp.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    cleaned = _clean_llm_output(raw, name)
    if not _is_valid_checkpoint(name, cleaned):
        log.warning(
            "Checkpoint .checkpoints/%s/%s.txt failed validation — will re-run.",
            slug, name,
        )
        return None
    return cleaned


def clear_checkpoints(slug: str) -> None:
    """Remove checkpoint files after a successful build."""
    cp_dir = CHECKPOINTS_DIR / slug
    if not cp_dir.exists():
        return
    for name in _CHECKPOINT_NAMES:
        cp = cp_dir / f"{name}.txt"
        if cp.exists():
            cp.unlink()
    try:
        cp_dir.rmdir()  # only removes if empty
    except OSError:
        pass
    log.info("Checkpoints cleared for '%s'.", slug)


# ── Default backlog (~40 classic pieces) ──────────────────────────────────
INITIAL_PAGES = [
    {"slug": "barcelona-chair",       "title": "Barcelona Chair",                       "designer": "Ludwig Mies van der Rohe",                      "era": "Modernist",           "category": "Iconic Chairs"},
    {"slug": "wassily-chair",         "title": "Wassily Chair",                         "designer": "Marcel Breuer",                                 "era": "Bauhaus",             "category": "Iconic Chairs"},
    {"slug": "tulip-chair",           "title": "Tulip Chair",                           "designer": "Eero Saarinen",                                 "era": "Mid-Century Modern",  "category": "Iconic Chairs"},
    {"slug": "egg-chair",             "title": "Egg Chair",                             "designer": "Arne Jacobsen",                                 "era": "Mid-Century Modern",  "category": "Iconic Chairs"},
    {"slug": "swan-chair",            "title": "Swan Chair",                            "designer": "Arne Jacobsen",                                 "era": "Mid-Century Modern",  "category": "Iconic Chairs"},
    {"slug": "ant-chair",             "title": "Ant Chair",                             "designer": "Arne Jacobsen",                                 "era": "Mid-Century Modern",  "category": "Dining Chairs"},
    {"slug": "panton-chair",          "title": "Panton Chair",                          "designer": "Verner Panton",                                 "era": "Late Modern",         "category": "Iconic Chairs"},
    {"slug": "wishbone-chair",        "title": "Wishbone Chair (CH24)",                 "designer": "Hans J. Wegner",                                "era": "Danish Modern",       "category": "Dining Chairs"},
    {"slug": "the-chair-wegner",      "title": "The Chair (JH501)",                     "designer": "Hans J. Wegner",                                "era": "Danish Modern",       "category": "Iconic Chairs"},
    {"slug": "shell-chair-ch07",      "title": "Shell Chair (CH07)",                    "designer": "Hans J. Wegner",                                "era": "Danish Modern",       "category": "Lounge Chairs"},
    {"slug": "ox-chair",              "title": "Ox Chair (EJ100)",                      "designer": "Hans J. Wegner",                                "era": "Danish Modern",       "category": "Lounge Chairs"},
    {"slug": "le-corbusier-lc2",      "title": "LC2 Grand Confort",                     "designer": "Le Corbusier, Pierre Jeanneret & Charlotte Perriand", "era": "Modernist",   "category": "Lounge Chairs"},
    {"slug": "le-corbusier-lc4",      "title": "LC4 Chaise Longue",                     "designer": "Le Corbusier, Pierre Jeanneret & Charlotte Perriand", "era": "Modernist",   "category": "Chaise Longues"},
    {"slug": "red-and-blue-chair",    "title": "Red and Blue Chair",                    "designer": "Gerrit Rietveld",                               "era": "De Stijl",            "category": "Avant-Garde"},
    {"slug": "zig-zag-chair",         "title": "Zig-Zag Chair",                         "designer": "Gerrit Rietveld",                               "era": "De Stijl",            "category": "Avant-Garde"},
    {"slug": "hill-house-chair",      "title": "Hill House Ladder-Back Chair",           "designer": "Charles Rennie Mackintosh",                     "era": "Arts & Crafts",       "category": "Arts & Crafts"},
    {"slug": "diamond-chair",         "title": "Diamond Chair",                         "designer": "Harry Bertoia",                                 "era": "Mid-Century Modern",  "category": "Wire & Metal"},
    {"slug": "platner-chair",         "title": "Platner Easy Chair",                    "designer": "Warren Platner",                                "era": "Mid-Century Modern",  "category": "Wire & Metal"},
    {"slug": "womb-chair",            "title": "Womb Chair",                            "designer": "Eero Saarinen",                                 "era": "Mid-Century Modern",  "category": "Lounge Chairs"},
    {"slug": "paimio-chair",          "title": "Paimio Chair (No. 41)",                 "designer": "Alvar Aalto",                                   "era": "Functionalism",       "category": "Lounge Chairs"},
    {"slug": "tank-chair-aalto",      "title": "Tank Chair (No. 400)",                  "designer": "Alvar Aalto",                                   "era": "Functionalism",       "category": "Lounge Chairs"},
    {"slug": "chieftain-chair",       "title": "Chieftain Chair",                       "designer": "Finn Juhl",                                     "era": "Danish Modern",       "category": "Lounge Chairs"},
    {"slug": "pelican-chair",         "title": "Pelican Chair",                         "designer": "Finn Juhl",                                     "era": "Danish Modern",       "category": "Lounge Chairs"},
    {"slug": "butterfly-chair",       "title": "Butterfly Chair (BKF)",                 "designer": "Bonet, Kurchan & Ferrari-Hardoy",               "era": "Modernist",           "category": "Iconic Chairs"},
    {"slug": "ball-chair",            "title": "Ball Chair (Globe Chair)",              "designer": "Eero Aarnio",                                   "era": "Space Age",           "category": "Space Age"},
    {"slug": "pastil-chair",          "title": "Pastil Chair",                          "designer": "Eero Aarnio",                                   "era": "Space Age",           "category": "Space Age"},
    {"slug": "djinn-chair",           "title": "Djinn Chair",                           "designer": "Olivier Mourgue",                               "era": "Space Age",           "category": "Space Age"},
    {"slug": "mushroom-chair",        "title": "Mushroom Chair (F560)",                 "designer": "Pierre Paulin",                                 "era": "Late Modern",         "category": "Lounge Chairs"},
    {"slug": "tongue-chair",          "title": "Tongue Chair (F577)",                   "designer": "Pierre Paulin",                                 "era": "Late Modern",         "category": "Iconic Chairs"},
    {"slug": "ribbon-chair",          "title": "Ribbon Chair (F582)",                   "designer": "Pierre Paulin",                                 "era": "Late Modern",         "category": "Iconic Chairs"},
    {"slug": "cone-chair",            "title": "Cone Chair",                            "designer": "Verner Panton",                                 "era": "Late Modern",         "category": "Iconic Chairs"},
    {"slug": "sacco-beanbag",         "title": "Sacco Bean Bag",                        "designer": "Piero Gatti, Cesare Paolini & Franco Teodoro",  "era": "Pop Design",          "category": "Soft Seating"},
    {"slug": "blow-chair",            "title": "Blow Chair",                            "designer": "De Pas, D'Urbino, Lomazzi & Scolari",           "era": "Pop Design",          "category": "Avant-Garde"},
    {"slug": "up-5-chair",            "title": "Up 5 Armchair",                         "designer": "Gaetano Pesce",                                 "era": "Pop Design",          "category": "Soft Seating"},
    {"slug": "brno-chair",            "title": "Brno Chair",                            "designer": "Ludwig Mies van der Rohe",                      "era": "Modernist",           "category": "Dining Chairs"},
    {"slug": "noguchi-table",         "title": "Noguchi Coffee Table (IN-50)",           "designer": "Isamu Noguchi",                                 "era": "Mid-Century Modern",  "category": "Tables"},
    {"slug": "poet-sofa-finn-juhl",   "title": "The Poet Sofa",                         "designer": "Finn Juhl",                                     "era": "Danish Modern",       "category": "Sofas"},
    {"slug": "chair-one-magis",       "title": "Chair One",                             "designer": "Konstantin Grcic",                              "era": "Contemporary Classics","category": "Contemporary Classics"},
    {"slug": "series-7-chair",        "title": "Series 7 Chair (Model 3107)",           "designer": "Arne Jacobsen",                                 "era": "Mid-Century Modern",  "category": "Dining Chairs"},
    {"slug": "low-pad-chair",         "title": "Low Pad Chair",                         "designer": "Jasper Morrison",                               "era": "Contemporary Classics","category": "Contemporary Classics"},
]


# ── Backlog management ─────────────────────────────────────────────────────
def load_backlog() -> dict:
    """Load backlog.json from disk, or return empty structure."""
    if BACKLOG.exists():
        with open(BACKLOG, encoding="utf-8") as f:
            return json.load(f)
    return {"pages": []}


def save_backlog(backlog: dict) -> None:
    """Write backlog.json to disk."""
    with open(BACKLOG, "w", encoding="utf-8") as f:
        json.dump(backlog, f, indent=2, ensure_ascii=False)
    done = sum(1 for p in backlog["pages"] if p["status"] == "done")
    pending = sum(1 for p in backlog["pages"] if p["status"] == "pending")
    log.info("Backlog saved — %d done, %d pending.", done, pending)


def init_backlog() -> dict:
    """Build backlog from INITIAL_PAGES, marking already-published slugs as done."""
    existing = get_existing_slugs()
    pages = [
        {**p, "status": "done" if p["slug"] in existing else "pending"}
        for p in INITIAL_PAGES
    ]
    backlog = {"pages": pages}
    save_backlog(backlog)
    done = sum(1 for p in pages if p["status"] == "done")
    log.info(
        "Initialized backlog: %d pages total, %d already published.",
        len(pages), done,
    )
    return backlog


def get_existing_slugs() -> set:
    """Return the set of slugs that already exist as published markdown files."""
    md = {p.stem for p in CONTENT_DIR.glob("*.md")}
    mdx = {p.stem for p in CONTENT_DIR.glob("*.mdx")}
    return md | mdx


def pick_next_page(backlog: dict) -> Optional[dict]:
    """Return the first pending page not already published on disk."""
    existing = get_existing_slugs()
    for page in backlog["pages"]:
        if page.get("status") == "pending" and page["slug"] not in existing:
            return page
    return None


def mark_done(backlog: dict, slug: str) -> None:
    """Mark a slug as done in the backlog and save."""
    for page in backlog["pages"]:
        if page["slug"] == slug:
            page["status"] = "done"
    save_backlog(backlog)


# ── LLM factory ───────────────────────────────────────────────────────────
def make_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    Return a ChatOpenAI instance pointed at either:
      • GitHub Models endpoint  (GITHUB_MODELS=1 in .env, uses GITHUB_TOKEN)
      • Standard OpenAI API     (default, uses OPENAI_API_KEY)

    Model defaults to gpt-4o unless overridden via FURNITURE_MODEL.
    temperature=0.3 → analytical agents (Planner, Researcher, Publisher)
    temperature=0.7 → creative agents (Writer, ImagePrompter)
    """
    model = os.getenv("FURNITURE_MODEL", "gpt-4o")

    if os.getenv("GITHUB_MODELS", "").strip() in ("1", "true", "yes"):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise EnvironmentError(
                "GITHUB_MODELS=1 requires GITHUB_TOKEN to be set in .env"
            )
        log.info("Using GitHub Models endpoint (model=%s, temperature=%.1f)", model, temperature)
        return ChatOpenAI(
            model=model,
            api_key=token,
            base_url=_GITHUB_MODELS_BASE_URL,
            temperature=temperature,
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")
    log.info("Using OpenAI endpoint (model=%s, temperature=%.1f)", model, temperature)
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
    )


# ── Direct LLM pipeline (replaces CrewAI crew) ────────────────────────────
# Using LangChain ChatOpenAI directly avoids the ReAct executor format
# requirements that cause "Missing 'Action:' after 'Thought:'" hangs with
# gpt-4o via GitHub Models when tool-free agents mix with the RPM limiter.

def _llm_call(llm: ChatOpenAI, system: str, user: str) -> str:
    """Single LLM call; returns the text content of the response."""
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return response.content.strip()


def run_pipeline(page: dict, concept: str) -> tuple[str, str]:
    """
    Run the four-stage pipeline (plan → research → write → describe) using
    direct LangChain calls instead of CrewAI agents.

    Returns (article_body, description).
    Checkpoints each stage to .checkpoints/<slug>/ as it completes.
    """
    slug = page["slug"]
    title = page["title"]
    designer = page.get("designer", "Unknown")
    era = page.get("era", "Classic")
    category = page.get("category", "Iconic Chairs")

    llm_analytical = make_llm(temperature=0.3)
    llm_creative = make_llm(temperature=0.7)

    _concept_excerpt = concept[:2000].rsplit("\n", 1)[0]

    # ── Stage 1: Editorial brief ───────────────────────────────────────────
    cached_plan = load_checkpoint(slug, "plan")
    if cached_plan:
        log.info("Stage 1 (plan): loaded from checkpoint.")
        plan = cached_plan
    else:
        log.info("Stage 1 (plan): calling LLM…")
        plan = _llm_call(
            llm_analytical,
            system=(
                "You are a seasoned editorial director for a high-end design museum archive. "
                "You understand narrative arcs, design history, and what makes furniture "
                "deep-dives distinct and authoritative."
            ),
            user=(
                f"Site concept excerpt:\n\n{_concept_excerpt}\n\n"
                f"The next page to build is: **{title}** "
                f"(slug: `{slug}`, designer: {designer}, era: {era}, category: {category}).\n\n"
                "Produce a concise editorial brief (under 350 words) covering:\n"
                "- 5–7 key narrative angles specific to this piece\n"
                "- 3–4 H2 section titles (descriptive, not generic)\n"
                "- Specific facts, dates, or controversies worth investigating\n"
                "- 2–3 related pieces to cross-reference"
            ),
        )
        _save_checkpoint(slug, "plan", plan)
        log.info("Stage 1 (plan): done.")

    # ── Stage 2: Research brief ────────────────────────────────────────────
    cached_research = load_checkpoint(slug, "research")
    if cached_research:
        log.info("Stage 2 (research): loaded from checkpoint.")
        research = cached_research
    else:
        log.info("Stage 2 (research): calling LLM…")
        research = _llm_call(
            llm_analytical,
            system=(
                "You are a meticulous design historian with encyclopedic knowledge of "
                "20th-century furniture. You never fabricate dates, names, or records. "
                "If uncertain, mark the fact (unconfirmed)."
            ),
            user=(
                f"Editorial brief:\n\n{plan}\n\n"
                f"Now produce a structured research brief for **{title}** by {designer} ({era}).\n\n"
                "Cover:\n"
                "1. Exact year designed and first produced; original manufacturer\n"
                "2. Key design decisions: materials, structural innovations, prototyping\n"
                "3. Exhibition history, design awards, museum acquisitions\n"
                "4. Designer biography highlights relevant to this piece\n"
                "5. Cultural reception: notable appearances, critical reassessments\n"
                "6. Lesser-known facts that reward a careful reader\n\n"
                "Format as a numbered list with attributed sources for each fact."
            ),
        )
        _save_checkpoint(slug, "research", research)
        log.info("Stage 2 (research): done.")

    # ── Stage 3: Article body ──────────────────────────────────────────────
    cached_body = load_checkpoint(slug, "article_body")
    if cached_body:
        log.info("Stage 3 (write): loaded from checkpoint.")
        article_body = cached_body
    else:
        log.info("Stage 3 (write): calling LLM…")
        _writer_system = (
            "You write like a senior contributor to Wallpaper* or Domus — passionate, "
            "precise, never condescending. You tell the human story behind design objects, "
            "weaving biography, craft, culture, and enduring significance."
        )
        _writer_user = (
            f"Editorial brief:\n\n{plan}\n\n"
            f"Research:\n\n{research}\n\n"
            f"Write the full article for **{title}**.\n\n"
            "Requirements:\n"
            "- 1800–2200 words\n"
            "- Opening hook paragraph (no heading)\n"
            "- 4–5 H2 sections with descriptive titles\n"
            "- A 'Meet the Designer' H2 section\n"
            "- A 'Why It Endures' or 'The Legacy' H2 section\n"
            "- Inline citations [1] [2] etc. throughout\n"
            "- After the opening hook paragraph (before the first H2), place: <!-- IMAGE: hero -->\n"
            "- After the first H2 section's opening paragraph, place: <!-- IMAGE: detail-material -->\n"
            "- After the second H2 section's opening paragraph, place: <!-- IMAGE: detail-structure -->\n"
            "- After the third H2 section's opening paragraph, place: <!-- IMAGE: detail-silhouette -->\n"
            "- A '## References' section with numbered citations\n"
            "- Output: raw Markdown only. No frontmatter. No code fences."
        )
        article_body = _llm_call(llm_creative, system=_writer_system, user=_writer_user)
        article_body = _clean_llm_output(article_body, "article_body")
        _STAGE3_FAILURE_PHRASES = (
            "agent stopped due to iteration limit",
            "agent stopped due to time limit",
            "invalid format",
            "missing 'action:' after 'thought:",
        )
        if any(p in article_body.lower() for p in _STAGE3_FAILURE_PHRASES):
            raise RuntimeError(
                f"Writer LLM produced a failure message: {article_body[:120]!r}"
            )
        try:
            _validate_article_body(article_body)
        except RuntimeError as val_exc:
            log.warning("Stage 3 quality check failed: %s — retrying once…", val_exc)
            article_body = _llm_call(llm_creative, system=_writer_system, user=_writer_user)
            article_body = _clean_llm_output(article_body, "article_body")
            _validate_article_body(article_body)  # raise if still failing
        _save_checkpoint(slug, "article_body", article_body)
        log.info("Stage 3 (write): done (%d chars).", len(article_body))

    # ── Stage 4: Meta description ──────────────────────────────────────────
    cached_desc = load_checkpoint(slug, "description")
    if cached_desc:
        log.info("Stage 4 (description): loaded from checkpoint.")
        description = cached_desc
    else:
        log.info("Stage 4 (description): calling LLM…")
        description = _llm_call(
            llm_analytical,
            system="You are a precise technical editor writing web meta descriptions.",
            user=(
                f"Write a single-sentence meta description for an article about the "
                f"**{title}** by {designer} ({era}).\n\n"
                "Rules:\n"
                "- 100–160 characters total\n"
                "- Name the object, designer, and one key distinguishing fact\n"
                "- No superlatives unless essential\n"
                "- Return the sentence ONLY. No label, no quotes."
            ),
        )
        _save_checkpoint(slug, "description", description)
        log.info("Stage 4 (description): done.")

    return article_body, description


def _save_checkpoint(slug: str, name: str, text: str) -> None:
    """Write a checkpoint file, ignoring errors."""
    try:
        cp = _checkpoint_path(slug, name)
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(text.strip(), encoding="utf-8")
        log.info("Checkpoint saved: .checkpoints/%s/%s.txt", slug, name)
    except Exception as exc:
        log.warning("Checkpoint write failed (%s/%s): %s", slug, name, exc)


# ── MDX constants ─────────────────────────────────────────────────────────
_MDX_IMPORT = "import ImageWithMeta from '../../components/ImageWithMeta.astro';"
_IMAGE_SLOTS = ["hero", "detail-material", "detail-structure", "detail-silhouette"]


# ── Output cleaning and validation ────────────────────────────────────────
_REPR_PHRASES = ("description=", "summary=", "pydantic",)


def _clean_llm_output(text: str, stage: str) -> str:
    """
    Strip common LLM output artifacts from checkpoint text:
    - Python Task repr strings (extract result='...')
    - Markdown code fences
    - Stray YAML frontmatter in article body
    """
    text = text.strip()
    # Detect Python Task repr by checking start of text for signature attributes
    if any(ph in text[:100].lower() for ph in _REPR_PHRASES):
        for pattern in (r"\bresult='(.*)'\Z", r'\bresult="(.*)"\Z'):
            m = re.search(pattern, text, re.DOTALL)
            if m:
                extracted = m.group(1).strip()
                if len(extracted) > 200:
                    text = extracted
                    break
    # Strip markdown code fences (```markdown ... ```, etc.)
    m = re.match(r"^```(?:markdown|md|mdx)?\s*\n(.*?)\n?```\s*$", text, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1).strip()
    # Strip stray YAML frontmatter from article body
    if stage == "article_body" and text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2].strip()
    return text.strip()


_CHECKPOINT_REPR_INDICATORS = (
    "description=",
    "summary=",
    "agent stopped",
    "invalid format",
    "missing 'action:'",
)


def _is_valid_checkpoint(name: str, text: str) -> bool:
    """Return True if checkpoint text looks like genuine LLM output."""
    if not text or len(text) < 50:
        return False
    lowered = text[:200].lower()
    if any(ph in lowered for ph in _CHECKPOINT_REPR_INDICATORS):
        return False
    if name in ("plan", "research"):
        return len(text) >= 200
    if name == "article_body":
        word_count = len(text.split())
        h2_count = len(re.findall(r"^## ", text, re.MULTILINE))
        return word_count >= 1200 and h2_count >= 2 and "## references" in text.lower()
    if name == "description":
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        return len(lines) == 1 and 50 <= len(text.strip()) <= 300
    return True


def _validate_article_body(text: str) -> None:
    """Raise RuntimeError if article body fails minimum quality gates."""
    word_count = len(text.split())
    h2_count = len(re.findall(r"^## ", text, re.MULTILINE))
    has_refs = "## references" in text.lower()
    issues = []
    if word_count < 1200:
        issues.append(f"too short: {word_count} words (need ≥1200)")
    if h2_count < 2:
        issues.append(f"only {h2_count} H2 section(s) found (need ≥2)")
    if not has_refs:
        issues.append("missing ## References section")
    if issues:
        raise RuntimeError("Article body failed quality checks: " + "; ".join(issues))


def _post_process_article(body: str, slug: str) -> str:
    """
    Replace <!-- IMAGE: {slot} --> markers with ImageWithMeta components.
    Injects missing components after H2 sections when the LLM placed fewer than 4.
    """
    def _tag(slot: str) -> str:
        return f'<ImageWithMeta id="{slug}-{slot}" images={{props.entryImages}} />'

    # Replace explicit markers
    for slot in _IMAGE_SLOTS:
        body = body.replace(f"<!-- IMAGE: {slot} -->", _tag(slot))

    # Count how many are now in the body
    placed = len(re.findall(r"<ImageWithMeta ", body))
    if placed >= len(_IMAGE_SLOTS):
        return body

    # Determine which slots are still missing
    used = set(re.findall(rf'id="{re.escape(slug)}-([^"]+)"', body))
    missing = [s for s in _IMAGE_SLOTS if s not in used]
    if not missing:
        return body

    # Inject missing slots after the paragraph following each H2 heading
    lines = body.split("\n")
    h2_indices = [i for i, ln in enumerate(lines) if re.match(r"^## ", ln)]
    offset = 0
    for i, slot in enumerate(missing):
        if i < len(h2_indices):
            h2_pos = h2_indices[i] + offset
            insert_at = h2_pos + 1
            # Skip blank lines immediately after heading
            while insert_at < len(lines) and not lines[insert_at].strip():
                insert_at += 1
            # Move to end of the first paragraph (stop at blank line)
            while insert_at < len(lines) and lines[insert_at].strip():
                insert_at += 1
            lines.insert(insert_at, _tag(slot))
            lines.insert(insert_at, "")
            offset += 2
        else:
            # Append before ## References as a last resort
            ref_idx = next(
                (j for j, ln in enumerate(lines) if re.match(r"^## [Rr]eferences", ln)),
                None,
            )
            ins = (ref_idx + offset if ref_idx is not None else len(lines))
            lines.insert(ins, _tag(slot))
            lines.insert(ins, "")
            offset += 2
    return "\n".join(lines)


# ── Output extraction and file I/O ─────────────────────────────────────────
def _get_task_raw(tasks_output, index: int) -> str:
    """Safely extract raw string output from a task result at a given index."""
    try:
        output = tasks_output[index]
        return str(getattr(output, "raw", output))
    except (IndexError, AttributeError):
        return ""


# Labels in order — must match the ImagePrompter task format exactly.
_PROMPT_LABELS = [
    ("HERO",            "hero.txt"),
    ("DETAIL_1",        "detail-material.txt"),
    ("DETAIL_2",        "detail-structure.txt"),
    ("DETAIL_3",        "silhouette.txt"),
    ("CONTEXT",         "context.txt"),
    ("DESIGNER",        "designer.txt"),
    ("PUBLIC_DOMAIN_1", "search-wikimedia.txt"),
    ("PUBLIC_DOMAIN_2", "search-museum.txt"),
    ("PUBLIC_DOMAIN_3", "search-archive.txt"),
]


def save_image_prompts(slug: str, prompts_raw: str) -> None:
    """
    Parse the labelled plain-text output from ImagePrompter and write each
    prompt to its own .txt file inside public/images/generated-prompts/<slug>/.
    Files are ready to copy-paste directly into DALL-E, Midjourney, Firefly,
    or any archive search engine.
    """
    out_dir = PROMPTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Split on label lines (e.g. "HERO", "DETAIL_1", ...)
    label_pattern = re.compile(
        r"^(" + "|".join(re.escape(lbl) for lbl, _ in _PROMPT_LABELS) + r")\s*$",
        re.MULTILINE,
    )
    parts = label_pattern.split(prompts_raw.strip())
    # parts is: [pre-text, LABEL, body, LABEL, body, ...]
    sections: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        label = parts[i].strip()
        body = parts[i + 1].strip()
        sections[label] = body

    if not sections:
        # Fallback: couldn't parse the format — dump everything to a single file
        log.warning("Could not parse labelled prompt format; saving raw output.")
        fallback = out_dir / "prompts-raw.txt"
        fallback.write_text(prompts_raw, encoding="utf-8")
        log.info("Raw prompts written: %s", fallback)
        return

    written = 0
    for label, filename in _PROMPT_LABELS:
        content = sections.get(label, "")
        if content:
            out_path = out_dir / filename
            out_path.write_text(content, encoding="utf-8")
            written += 1
            log.info("  Prompt saved: %s", out_path)
        else:
            log.warning("  No content for label '%s' — skipping %s", label, filename)

    log.info("Image prompts written: %d/%d files in %s", written, len(_PROMPT_LABELS), out_dir)


def ensure_placeholder_hero(slug: str) -> Path:
    """Create a page-scoped placeholder hero image if one does not already exist."""
    hero_path = IMAGES_DIR / f"{slug}-hero.jpg"
    if hero_path.exists():
        return hero_path

    if DEFAULT_PLACEHOLDER_IMAGE.exists():
        shutil.copyfile(DEFAULT_PLACEHOLDER_IMAGE, hero_path)
        log.info("Placeholder hero image created: %s", hero_path)
    else:
        log.warning(
            "Default placeholder image not found at %s; hero image remains missing.",
            DEFAULT_PLACEHOLDER_IMAGE,
        )
    return hero_path


def ensure_placeholder_images(slug: str) -> list[Path]:
    """Create a standard set of image placeholders for expected image slots."""
    created_paths: list[Path] = []
    existing_candidates = [p for p in PLACEHOLDER_IMAGE_CANDIDATES if p.exists()]

    if not existing_candidates:
        log.warning("No placeholder source images found in %s", IMAGES_DIR)
        return created_paths

    for index, (slot, _alt_hint) in enumerate(PLACEHOLDER_SLOTS):
        out_path = IMAGES_DIR / f"{slug}-{slot}.jpg"
        if not out_path.exists():
            source_img = existing_candidates[index % len(existing_candidates)]
            shutil.copyfile(source_img, out_path)
            log.info("Placeholder image created: %s", out_path)
        created_paths.append(out_path)

    return created_paths


def collect_image_sources(page: dict) -> Path:
    """
    Collect image source URLs for editorial/reference use across mixed licenses.
    This includes Commons, museum collections, archives, and manufacturer pages.
    This phase runs after publishing and must not block page creation.
    """
    slug = page["slug"]
    title = page["title"]
    designer = page.get("designer", "")
    out_dir = PROMPTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "image-sources.txt"

    search_tool = TavilySearchResults(max_results=5)
    queries = [
        ("WIKIMEDIA", f"{title} {designer} site:commons.wikimedia.org"),
        ("MUSEUMS", f"{title} {designer} site:moma.org OR site:vam.ac.uk OR site:collection.cooperhewitt.org OR site:designmuseum.dk"),
        ("ARCHIVES", f"{title} {designer} site:archive.org OR site:loc.gov"),
        ("MANUFACTURERS", f"{title} {designer} site:hermanmiller.com OR site:vitra.com OR site:knoll.com OR site:cassina.com OR site:artek.fi OR site:fritzhansen.com OR site:carlhansen.com"),
    ]

    lines = [
        f"Image source discovery for: {title} [{slug}]",
        "",
        "Notes:",
        "- Reference usage can include any license class; preserve provenance and license notes.",
        "- Blog publication still requires explicit frontmatter license/source metadata per selected image.",
        "",
    ]

    for label, query in queries:
        lines.append(f"[{label} QUERY]")
        lines.append(query)
        lines.append("")

        results = []
        try:
            raw = search_tool.invoke({"query": query})
        except Exception:
            raw = search_tool.invoke(query)

        if isinstance(raw, dict):
            results = raw.get("results", [])
        elif isinstance(raw, list):
            results = raw

        if not results:
            lines.append("No results returned.")
            lines.append("")
            continue

        lines.append(f"[{label} RESULTS]")
        for i, item in enumerate(results[:5], start=1):
            if isinstance(item, dict):
                name = item.get("title") or item.get("name") or "Untitled"
                url = item.get("url") or item.get("link") or ""
                lines.append(f"{i}. {name}")
                lines.append(f"   {url}")
        lines.append("")

    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    legacy_path = out_dir / "public-domain-sources.txt"
    if not legacy_path.exists():
        legacy_path.write_text(out_path.read_text(encoding="utf-8"), encoding="utf-8")

    log.info("Image sources written: %s", out_path)
    return out_path


def _extract_urls(text: str) -> list[str]:
    """Extract unique URLs from free-form text while preserving order."""
    seen: set[str] = set()
    urls: list[str] = []
    for match in re.findall(r"https?://\S+", text):
        cleaned = match.strip().rstrip(")]}>,.;")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def _wikimedia_direct_file_url(page_url: str) -> Optional[str]:
    """
    Convert a Wikimedia Commons file page URL into a direct file endpoint.

    Example:
      https://commons.wikimedia.org/wiki/File:Example.jpg
      -> https://commons.wikimedia.org/wiki/Special:FilePath/Example.jpg
    """
    parsed = urlparse(page_url)
    if "commons.wikimedia.org" not in parsed.netloc:
        return None

    marker = "/wiki/File:"
    if marker not in parsed.path:
        return None

    filename = parsed.path.split(marker, 1)[1]
    if not filename:
        return None

    # Keep path separators encoded, as titles may contain UTF-8 and punctuation.
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(unquote(filename), safe='')}"


def _is_direct_image_url(url: str) -> bool:
    """Return True when URL appears to target an image file directly."""
    lowered = url.lower().split("?", 1)[0]
    return lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"))


def _direct_image_url(source_url: str) -> Optional[str]:
    """
    Resolve a source URL into a direct image URL when possible.
    Supports Wikimedia file pages and already-direct image asset URLs.
    """
    wiki_url = _wikimedia_direct_file_url(source_url)
    if wiki_url:
        return wiki_url
    if _is_direct_image_url(source_url):
        return source_url
    return None


def _download_binary(url: str, out_path: Path, timeout_seconds: int = 20) -> bool:
    """Download a binary asset to disk with a browser-like User-Agent."""
    req = Request(url, headers={"User-Agent": "chairs-reference-harvester/1.0"})
    with urlopen(req, timeout=timeout_seconds) as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        payload = response.read()

    # Some redirects resolve to HTML pages; keep only plausible image payloads.
    if "text/html" in content_type:
        return False
    if len(payload) < 1024:
        return False

    out_path.write_bytes(payload)
    return True


def collect_reference_images(page: dict, sources_path: Path) -> Path:
    """
    Build a local reference-image set for AI ideation plus provenance metadata.

    Output structure:
      public/images/reference/<slug>-reference/
        - ref-001.jpg ...
        - reference-metadata.json
    """
    slug = page["slug"]
    ref_dir = REFERENCE_IMAGES_DIR / f"{slug}-reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = ref_dir / "reference-metadata.json"
    if not sources_path.exists():
        metadata_path.write_text(
            json.dumps(
                {
                    "slug": slug,
                    "title": page.get("title", ""),
                    "status": "no-source-file",
                    "items": [],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return metadata_path

    raw = sources_path.read_text(encoding="utf-8")
    urls = _extract_urls(raw)
    max_refs = 8
    ref_items: list[dict] = []
    downloaded = 0

    for index, source_url in enumerate(urls[: max_refs * 2], start=1):
        if len(ref_items) >= max_refs:
            break

        direct_url = _direct_image_url(source_url)
        ext = ".jpg"
        if direct_url:
            lowered = direct_url.lower()
            for candidate in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"):
                if candidate in lowered:
                    ext = ".jpg" if candidate == ".jpeg" else candidate
                    break

        item = {
            "id": f"ref-{index:03d}",
            "sourcePage": source_url,
            "downloadUrl": direct_url,
            "localPath": None,
            "license": "unknown",
            "origin": "mixed_license_reference",
            "status": "metadata-only",
            "notes": "Direct image download unavailable for this source URL.",
        }

        if direct_url:
            local_name = f"ref-{index:03d}{ext}"
            out_file = ref_dir / local_name
            try:
                if _download_binary(direct_url, out_file):
                    item["localPath"] = str(out_file.relative_to(ROOT)).replace("\\", "/")
                    item["status"] = "downloaded"
                    if "commons.wikimedia.org" in direct_url:
                        item["notes"] = "Downloaded from Wikimedia Special:FilePath endpoint."
                    else:
                        item["notes"] = "Downloaded from direct image URL (license not inferred; verify before publication)."
                    downloaded += 1
                else:
                    item["notes"] = "Direct URL resolved to non-image content; kept as metadata-only."
            except Exception as exc:
                item["notes"] = f"Download failed: {exc}"

        ref_items.append(item)

    metadata = {
        "slug": slug,
        "title": page.get("title", ""),
        "referenceFolder": str(ref_dir.relative_to(ROOT)).replace("\\", "/"),
        "collectedAt": date.today().isoformat(),
        "downloadedCount": downloaded,
        "totalCount": len(ref_items),
        "items": ref_items,
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log.info(
        "Reference image metadata written: %s (downloaded %d/%d)",
        metadata_path,
        downloaded,
        len(ref_items),
    )
    return metadata_path


def _build_frontmatter(page: dict, description: str, today_str: str) -> str:
    """Assemble YAML frontmatter string from page metadata and extracted description."""
    slug = page["slug"]
    title = page["title"]
    designer = page.get("designer", "")
    era = page.get("era", "")
    category = page.get("category", "")
    # Sanitize description: strip surrounding quotes/whitespace, ensure single line
    desc = description.strip().strip('"').strip("'").replace("\n", " ")
    if not desc or len(desc) < 20:
        desc = f"An authoritative history of the {title} by {designer}."
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "{desc}"',
        f"pubDate: {today_str}",
        f"heroImage: /images/{slug}-hero.jpg",
        f'heroImageAlt: "{title} highlighting form and materials"',
        "heroImageAltStatus: pending",
        'heroImageCaption: "TBD"',
        'heroImageSource: "TBD"',
        "heroImageLicense: unknown",
        "heroImageOrigin: placeholder",
        "images:",
        f"  - id: {slug}-hero",
        f"    src: /images/{slug}-hero.jpg",
        f'    alt: "{title} highlighting form and materials"',
        "    altStatus: pending",
        '    caption: "TBD"',
        '    source: "TBD"',
        "    license: unknown",
        "    origin: placeholder",
        f"  - id: {slug}-detail-material",
        f"    src: /images/{slug}-detail-material.jpg",
        f'    alt: "Close-up of material texture on {title}"',
        "    altStatus: pending",
        '    caption: "TBD"',
        '    source: "TBD"',
        "    license: unknown",
        "    origin: placeholder",
        f"  - id: {slug}-detail-structure",
        f"    src: /images/{slug}-detail-structure.jpg",
        '    alt: "Detail of visible joints, screws, or frame transitions"',
        "    altStatus: pending",
        '    caption: "TBD"',
        '    source: "TBD"',
        "    license: unknown",
        "    origin: placeholder",
        f"  - id: {slug}-detail-silhouette",
        f"    src: /images/{slug}-detail-silhouette.jpg",
        f'    alt: "Profile silhouette of {title} showing signature geometry"',
        "    altStatus: pending",
        '    caption: "TBD"',
        '    source: "TBD"',
        "    license: unknown",
        "    origin: placeholder",
        f'designer: "{designer}"',
        f'era: "{era}"',
        f'category: "{category}"',
        "---",
    ]
    return "\n".join(lines)


def extract_and_save(result, page: dict) -> Path:
    """
    Extract article from the crew result and write it to disk.

    Task indices: 0=plan, 1=research, 2=write, 3=publish(description only)
    The Writer (index 2) returns the article body.
    The Publisher (index 3) returns only the meta description sentence.
    Frontmatter is assembled in Python to avoid LLM token overflow.
    """
    slug = page["slug"]
    today_str = date.today().isoformat()

    try:
        tasks_output = result.tasks_output
    except AttributeError:
        tasks_output = []

    # Article body from Writer (task 2)
    article_body = _get_task_raw(tasks_output, 2)
    # Meta description from Publisher (task 3)
    description = _get_task_raw(tasks_output, 3)

    # Reject known CrewAI failure strings so they don't become article content.
    _FAILURE_PHRASES = (
        "agent stopped due to iteration limit",
        "agent stopped due to time limit",
        "invalid format",
        "missing 'action:' after 'thought:",
    )
    if any(p in article_body.lower() for p in _FAILURE_PHRASES):
        raise RuntimeError(
            f"Writer task produced a failure message instead of article content: "
            f"{article_body[:120]!r}"
        )

    if not article_body:
        # Last-resort fallback: use the full crew result string and strip any frontmatter
        fallback = str(result)
        # If CrewAI somehow included frontmatter, strip it
        if fallback.startswith("---"):
            parts = fallback.split("---", 2)
            article_body = parts[2].strip() if len(parts) >= 3 else fallback
        else:
            article_body = fallback
        log.warning("Writer task output missing; using full crew result as article body fallback.")

    frontmatter = _build_frontmatter(page, description, today_str)
    full_markdown = f"{frontmatter}\n\n{article_body.strip()}\n"

    # Write the article
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    article_path = CONTENT_DIR / f"{slug}.md"
    article_path.write_text(full_markdown.strip() + "\n", encoding="utf-8")
    log.info("Article written: %s", article_path)

    # Create guaranteed placeholder assets for immediate publishing.
    ensure_placeholder_hero(slug)
    ensure_placeholder_images(slug)

    return article_path


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a truthy/falsey environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _safe_int_env(name: str, default: int) -> int:
    """Read an integer env var with fallback when parsing fails."""
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _now_iso_utc() -> str:
    """Return UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_relpath(path: Path) -> str:
    """Return a workspace-relative path string with POSIX separators."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _file_sha256(path: Path) -> str:
    """Compute SHA-256 for a file path."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_prompt_bundle(slug: str) -> dict[str, str]:
    """Read slot prompt files from public/images/generated-prompts/<slug>."""
    prompt_dir = PROMPTS_DIR / slug
    prompts: dict[str, str] = {}
    for slot, filename in IMAGE_SLOT_PROMPT_FILES:
        prompt_path = prompt_dir / filename
        if prompt_path.exists():
            text = prompt_path.read_text(encoding="utf-8").strip()
            if text:
                prompts[slot] = text
    return prompts


def _load_reference_image_url(slug: str) -> Optional[str]:
    """Load a best-effort reference image URL from reference metadata."""
    metadata_path = REFERENCE_IMAGES_DIR / f"{slug}-reference" / "reference-metadata.json"
    if not metadata_path.exists():
        return None

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for item in metadata.get("items", []):
        url = item.get("downloadUrl") or item.get("sourcePage")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None


def _build_style_prompt(base_prompt: str, page: dict, slot: str) -> str:
    """Wrap a slot prompt with shared style and fidelity constraints."""
    title = page.get("title", "furniture piece")
    designer = page.get("designer", "")
    header = f"Photorealistic high-quality studio photograph of {title}"
    if designer:
        header += f" by {designer}"
    return (
        f"{header}. Slot intent: {slot}. "
        f"{base_prompt.strip()}\n\n{STYLE_PROMPT_SUFFIX}"
    )


def _normalize_image_size(raw_size: str) -> str:
    """Normalize image size value into an accepted WxH pattern."""
    size = raw_size.strip().lower()
    if re.fullmatch(r"\d+x\d+", size):
        return size
    return "1024x1024"


def _download_image_url(url: str, out_path: Path, timeout_seconds: int) -> None:
    """Download an image URL to disk, validating that payload is binary content."""
    if not _download_binary(url, out_path, timeout_seconds=timeout_seconds):
        raise RuntimeError("Image URL resolved to non-image payload")


def _generate_with_openai(
    prompt: str,
    negative_prompt: str,
    size: str,
    model: str,
    timeout_seconds: int,
) -> dict:
    """Generate one image via OpenAI image APIs."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI image generation")

    client = OpenAI(api_key=api_key, timeout=timeout_seconds)
    prompt_text = f"{prompt}\n\nNegative prompt: {negative_prompt}"
    response = client.images.generate(
        model=model,
        prompt=prompt_text,
        size=size,
        response_format="url",
    )

    if not getattr(response, "data", None):
        raise RuntimeError("OpenAI image API returned no image data")

    first = response.data[0]
    image_url = getattr(first, "url", None)
    image_b64 = getattr(first, "b64_json", None)
    revised_prompt = getattr(first, "revised_prompt", None)
    return {
        "image_url": image_url,
        "image_bytes": base64.b64decode(image_b64) if image_b64 else None,
        "revised_prompt": revised_prompt,
        "raw": response.model_dump() if hasattr(response, "model_dump") else str(response),
    }


def _generate_with_fal(
    prompt: str,
    negative_prompt: str,
    size: str,
    model: str,
    reference_url: Optional[str],
) -> dict:
    """Generate one image via fal-client if available."""
    try:
        fal_client = importlib.import_module("fal_client")
    except ImportError as exc:
        raise RuntimeError(
            "fal-client is not installed; install it to use FURNITURE_IMAGE_PROVIDER=fal"
        ) from exc

    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is required for FAL image generation")

    arguments = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_size": size,
    }
    if reference_url:
        arguments["image_url"] = reference_url

    if hasattr(fal_client, "run"):
        response = fal_client.run(model, arguments=arguments)
    elif hasattr(fal_client, "subscribe"):
        response = fal_client.subscribe(model, arguments=arguments)
    else:
        raise RuntimeError("Unsupported fal-client version; expected run() or subscribe()")

    if not isinstance(response, dict):
        raise RuntimeError("FAL response format is not a dictionary")

    image_url = None
    if isinstance(response.get("images"), list) and response["images"]:
        first = response["images"][0]
        if isinstance(first, dict):
            image_url = first.get("url")
    if not image_url and isinstance(response.get("image"), dict):
        image_url = response["image"].get("url")
    if not image_url and isinstance(response.get("url"), str):
        image_url = response.get("url")

    if not image_url:
        raise RuntimeError("FAL did not return an image URL")

    return {
        "image_url": image_url,
        "image_bytes": None,
        "revised_prompt": None,
        "raw": response,
    }


def _provider_and_model() -> tuple[str, str]:
    """Resolve configured image provider and model values."""
    provider = os.getenv("FURNITURE_IMAGE_PROVIDER", "fal").strip().lower()
    if provider not in {"fal", "openai"}:
        provider = "fal"

    if provider == "openai":
        model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
    else:
        model = os.getenv("FURNITURE_IMAGE_MODEL", "fal-ai/flux/dev").strip() or "fal-ai/flux/dev"
    return provider, model


def _slot_alt_and_caption(slot: str, title: str, designer: str) -> tuple[str, str]:
    """Return (alt, caption) text for a generated image slot."""
    slot_meta = {
        "hero": (
            f"{title} — studio composition highlighting form and materials",
            f"AI-generated studio photograph of the {title} by {designer}.",
        ),
        "silhouette": (
            f"{title} profile silhouette showing signature geometry",
            f"AI-generated silhouette of the {title} by {designer}.",
        ),
        "context": (
            f"{title} in a mid-century modern interior setting",
            f"AI-generated context photograph of the {title} by {designer} in situ.",
        ),
        "designer": (
            f"Portrait of {designer}, designer of the {title}",
            f"AI-generated portrait of {designer}.",
        ),
        "sketch": (
            f"Industrial design marker rendering of the {title}",
            f"AI-generated design sketch of the {title} by {designer}.",
        ),
        "detail-material": (
            f"Close-up of material texture on the {title}",
            f"AI-generated material detail of the {title} by {designer}.",
        ),
        "detail-structure": (
            f"Structural detail showing joints and frame of the {title}",
            f"AI-generated structural detail of the {title} by {designer}.",
        ),
    }
    return slot_meta.get(slot, (f"{title} — {slot}", f"AI-generated {slot} image for the {title}."))


def _apply_generated_image_metadata(
    article_path: Path,
    generated_slots: set[str],
    provider: str,
    model: str,
    page: dict | None = None,
) -> bool:
    """Update frontmatter image provenance fields for successfully generated slots."""
    if not generated_slots or not article_path.exists():
        return False

    raw = article_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, flags=re.DOTALL)
    if not match:
        return False

    try:
        import yaml
    except ImportError:
        return False

    frontmatter_raw = match.group(1)
    body = match.group(2)
    data = yaml.safe_load(frontmatter_raw) or {}

    title = (page or {}).get("title") or data.get("title", "")
    designer = (page or {}).get("designer") or data.get("designer", "")
    source_label = f"AI generated via {provider}/{model}"

    if "hero" in generated_slots:
        alt, caption = _slot_alt_and_caption("hero", title, designer)
        data["heroImageAlt"] = alt
        data["heroImageAltStatus"] = "actual"
        data["heroImageCaption"] = caption
        data["heroImageSource"] = source_label
        data["heroImageLicense"] = "Original work for educational and archival purposes"
        data["heroImageOrigin"] = "original"

    images = data.get("images")
    if isinstance(images, list):
        for entry in images:
            if not isinstance(entry, dict):
                continue
            image_id = str(entry.get("id", ""))
            for slot in generated_slots:
                if image_id.endswith(slot):
                    alt, caption = _slot_alt_and_caption(slot, title, designer)
                    entry["alt"] = alt
                    entry["altStatus"] = "actual"
                    entry["caption"] = caption
                    entry["source"] = source_label
                    entry["license"] = "Original work for educational and archival purposes"
                    entry["origin"] = "original"
                    break

    serialized = yaml.safe_dump(data, sort_keys=False, allow_unicode=False).strip()
    article_path.write_text(f"---\n{serialized}\n---\n{body.lstrip()}", encoding="utf-8")
    return True


def generate_and_log_images(page: dict) -> dict:
    """Generate page slot images via configured provider and write provenance JSON."""
    slug = page["slug"]
    prompts = _read_prompt_bundle(slug)
    prompt_dir = PROMPTS_DIR / slug
    prompt_dir.mkdir(parents=True, exist_ok=True)
    provenance_path = prompt_dir / "provenance-generated.json"

    provider, model = _provider_and_model()
    fallback_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
    size = _normalize_image_size(os.getenv("FURNITURE_IMAGE_SIZE", "1024x1024"))
    timeout_seconds = _safe_int_env("FURNITURE_IMAGE_TIMEOUT_SECONDS", 60)
    max_images = max(1, min(_safe_int_env("FURNITURE_IMAGE_MAX_PER_PAGE", 4), 4))
    reference_url = _load_reference_image_url(slug)

    results: list[dict] = []
    generated_files: list[Path] = []
    generated_slots: set[str] = set()

    for slot, _filename in IMAGE_SLOT_PROMPT_FILES[:max_images]:
        base_prompt = prompts.get(slot)
        if not base_prompt:
            results.append(
                {
                    "slot": slot,
                    "status": "skipped",
                    "reason": "missing prompt file",
                }
            )
            continue

        final_prompt = _build_style_prompt(base_prompt, page, slot)
        out_file = IMAGES_DIR / f"{slug}-{slot}.jpg"
        response_payload = None

        try:
            used_provider = provider
            used_model = model
            if provider == "openai":
                response_payload = _generate_with_openai(
                    prompt=final_prompt,
                    negative_prompt=STYLE_NEGATIVE_PROMPT,
                    size=size,
                    model=model,
                    timeout_seconds=timeout_seconds,
                )
            else:
                try:
                    response_payload = _generate_with_fal(
                        prompt=final_prompt,
                        negative_prompt=STYLE_NEGATIVE_PROMPT,
                        size=size,
                        model=model,
                        reference_url=reference_url,
                    )
                except Exception as fal_exc:
                    log.warning(
                        "FAL generation failed for slot '%s'; trying OpenAI fallback: %s",
                        slot,
                        fal_exc,
                    )
                    response_payload = _generate_with_openai(
                        prompt=final_prompt,
                        negative_prompt=STYLE_NEGATIVE_PROMPT,
                        size=size,
                        model=fallback_model,
                        timeout_seconds=timeout_seconds,
                    )
                    used_provider = "openai"
                    used_model = fallback_model

            image_bytes = response_payload.get("image_bytes") if response_payload else None
            image_url = response_payload.get("image_url") if response_payload else None

            if image_bytes:
                out_file.write_bytes(image_bytes)
            elif image_url:
                _download_image_url(image_url, out_file, timeout_seconds=timeout_seconds)
            else:
                raise RuntimeError("No image URL or bytes returned by provider")

            generated_files.append(out_file)
            generated_slots.add(slot)
            results.append(
                {
                    "slot": slot,
                    "status": "success",
                    "file": _safe_relpath(out_file),
                    "hash": f"sha256:{_file_sha256(out_file)}",
                    "provider": used_provider,
                    "model": used_model,
                    "prompt": final_prompt,
                    "negativePrompt": STYLE_NEGATIVE_PROMPT,
                    "referenceUrl": reference_url,
                    "response": response_payload.get("raw") if response_payload else None,
                    "revisedPrompt": response_payload.get("revised_prompt") if response_payload else None,
                }
            )
            log.info("Generated image slot '%s': %s", slot, out_file)
        except Exception as exc:
            results.append(
                {
                    "slot": slot,
                    "status": "failed",
                    "reason": str(exc),
                    "prompt": final_prompt,
                    "negativePrompt": STYLE_NEGATIVE_PROMPT,
                    "referenceUrl": reference_url,
                }
            )
            log.warning("Image generation failed for slot '%s' (non-blocking): %s", slot, exc)

    budget = os.getenv("FURNITURE_IMAGE_BUDGET_USD", "")
    metadata = {
        "slug": slug,
        "title": page.get("title", ""),
        "generatedAt": _now_iso_utc(),
        "provider": provider,
        "model": model,
        "imageSize": size,
        "maxImages": max_images,
        "budgetUsd": budget or None,
        "results": results,
        "summary": {
            "generatedCount": len(generated_files),
            "failedCount": sum(1 for item in results if item.get("status") == "failed"),
            "skippedCount": sum(1 for item in results if item.get("status") == "skipped"),
        },
    }
    provenance_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("Generated image provenance written: %s", provenance_path)

    return {
        "provenance_path": provenance_path,
        "generated_files": generated_files,
        "generated_slots": generated_slots,
        "generated_count": len(generated_files),
    }


def maybe_auto_commit(page: dict, paths: list[Path]) -> bool:
    """Create one local commit for generated artifacts when enabled by env."""
    if not _env_bool("FURNITURE_AUTO_COMMIT", default=False):
        return False

    existing_paths: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if not path:
            continue
        if not path.exists():
            continue
        rel = _safe_relpath(path)
        if rel in seen:
            continue
        seen.add(rel)
        existing_paths.append(rel)

    if not existing_paths:
        log.info("Auto-commit enabled but no artifact paths found.")
        return False

    subprocess.run(["git", "add", "--", *existing_paths], cwd=ROOT, check=True)
    message = f"auto({page['slug']}): generate page and image artifacts"
    commit = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if commit.returncode != 0:
        log.warning("Auto-commit skipped: %s", (commit.stderr or commit.stdout).strip())
        return False

    log.info("Auto-commit created for slug '%s'.", page["slug"])
    return True


# ── Environment validation ─────────────────────────────────────────────────
def validate_env() -> None:
    """Abort early if required environment variables are missing."""
    use_github_models = os.getenv("GITHUB_MODELS", "").strip() in ("1", "true", "yes")
    llm_key = "GITHUB_TOKEN" if use_github_models else "OPENAI_API_KEY"
    # TAVILY_API_KEY is only used for post-build image source discovery (non-blocking).
    # Only the LLM key is required for the main crew to run.
    missing = [k for k in (llm_key,) if not os.getenv(k)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        if use_github_models:
            log.error("GITHUB_MODELS=1 is set — GITHUB_TOKEN must be present.")
        log.error("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)
    if not os.getenv("TAVILY_API_KEY"):
        log.warning("TAVILY_API_KEY not set — post-build image source discovery will be skipped.")


# ── Checkpoint-based helpers for run_build ─────────────────────────────────

def _assemble_from_checkpoints(page: dict, article_body: str, description: str) -> Path:
    """Write the final .mdx article file using cached task outputs (no crew run needed)."""
    slug = page["slug"]
    today_str = date.today().isoformat()
    body = _clean_llm_output(article_body, "article_body")
    _validate_article_body(body)
    body = _post_process_article(body, slug)
    frontmatter = _build_frontmatter(page, description, today_str)
    full_content = f"{frontmatter}\n\n{_MDX_IMPORT}\n\n{body.strip()}\n"
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    article_path = CONTENT_DIR / f"{slug}.mdx"
    article_path.write_text(full_content, encoding="utf-8")
    log.info("Article assembled from checkpoints: %s", article_path)
    ensure_placeholder_hero(slug)
    ensure_placeholder_images(slug)
    return article_path


def _save_partial_checkpoints(slug: str, exc: Exception) -> None:
    """
    After a crew failure, try to extract any task outputs that completed and
    save them as checkpoints so the next run can resume.
    """
    # CrewAI 0.5.0 stores completed task outputs on the exception in some cases.
    tasks_output = getattr(exc, "tasks_output", None)
    if not tasks_output:
        # The exception may be wrapping a crew result object.
        cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        tasks_output = getattr(cause, "tasks_output", None)
    if not tasks_output:
        return

    names = ["plan", "research", "article_body", "description"]
    saved = 0
    for i, name in enumerate(names):
        if i >= len(tasks_output):
            break
        raw = str(getattr(tasks_output[i], "raw", tasks_output[i])).strip()
        if raw and not load_checkpoint(slug, name):
            cp = _checkpoint_path(slug, name)
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(raw, encoding="utf-8")
            log.info("Partial checkpoint saved from failed run: .checkpoints/%s/%s.txt", slug, name)
            saved += 1
    if saved:
        log.info(
            "Saved %d partial checkpoint(s) for '%s'. "
            "Re-run the script to resume from this point.", saved, slug,
        )


def _run_phase6_standalone_fallback(slug: str) -> None:
    """
    Run the standalone image fallback once in guarded mode.

    Guarded mode prevents accidental re-entry and keeps this fallback focused on
    image generation only (no prompt regeneration drift).
    """
    guard_active = os.getenv(PHASE6_FALLBACK_GUARD_ENV, "").strip().lower() in {"1", "true", "yes", "on"}
    if guard_active:
        log.warning(
            "Phase 6 fallback re-entry detected for '%s'; skipping nested fallback run.",
            slug,
        )
        return

    cmd = [sys.executable, str(PHASE6_FALLBACK_SCRIPT), slug, "--images-only"]
    env = os.environ.copy()
    env[PHASE6_FALLBACK_GUARD_ENV] = "1"

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        err_text = (result.stderr or result.stdout or "").strip()
        if err_text:
            err_lines = err_text.splitlines()[-PHASE6_FALLBACK_MAX_ERROR_LINES:]
            err_text = "\n    " + "\n    ".join(err_lines)
        else:
            err_text = "No error output captured."
        log.warning(
            "Standalone image fallback failed for '%s' (exit %d): %s",
            slug,
            result.returncode,
            err_text,
        )
        return

    log.info("Standalone image fallback completed for '%s'.", slug)


# ── Run modes ──────────────────────────────────────────────────────────────
def run_plan_only() -> None:
    """Sync backlog status with the filesystem and display current state."""
    log.info("── Plan-only mode ─────────────────────────────────────────────")
    backlog = load_backlog()

    if not backlog["pages"]:
        backlog = init_backlog()
    else:
        # Sync: mark any pages already on disk as done
        existing = get_existing_slugs()
        changed = 0
        for p in backlog["pages"]:
            if p.get("status") == "pending" and p["slug"] in existing:
                p["status"] = "done"
                changed += 1
        if changed:
            save_backlog(backlog)
            log.info("Marked %d already-published pages as done.", changed)

    done_pages = [p for p in backlog["pages"] if p.get("status") == "done"]
    pending_pages = [p for p in backlog["pages"] if p.get("status") == "pending"]

    log.info(
        "Backlog: %d total — %d done, %d pending.",
        len(backlog["pages"]), len(done_pages), len(pending_pages),
    )

    if pending_pages:
        log.info("Next up: %s  [%s]", pending_pages[0]["title"], pending_pages[0]["slug"])
        if len(pending_pages) > 1:
            log.info(
                "Queue preview: %s",
                ", ".join(p["slug"] for p in pending_pages[1:6]),
            )
    else:
        log.info("All pages complete! Add entries to backlog.json to continue.")


def run_build() -> None:
    """Run the full CrewAI pipeline for the next pending page."""
    validate_env()

    backlog = load_backlog()
    if not backlog["pages"]:
        log.info("No backlog found — initializing from default page list.")
        backlog = init_backlog()

    page = pick_next_page(backlog)
    if page is None:
        log.info(
            "All pages in the backlog are complete. "
            "Add more entries to backlog.json to continue."
        )
        return

    log.info(
        "── Building: %s  [%s] ─────────────────────────────────────────",
        page["title"], page["slug"],
    )

    if not CONCEPT.exists():
        log.error("site_concept.md not found at %s", CONCEPT)
        sys.exit(1)

    concept = CONCEPT.read_text(encoding="utf-8")

    try:
        artifact_paths: list[Path] = [BACKLOG]
        sources_file: Optional[Path] = None
        reference_metadata_path: Optional[Path] = None
        generated_meta_path: Optional[Path] = None

        slug = page["slug"]

        # ── Pipeline (checkpoint-aware) ────────────────────────────────────
        # run_pipeline handles resume internally: each stage checks for a
        # saved checkpoint before calling the LLM, so partial progress from a
        # previous failed run is reused automatically.
        article_body, description = run_pipeline(page, concept)
        article_path = _assemble_from_checkpoints(page, article_body, description)
        artifact_paths.append(article_path)
        mark_done(backlog, page["slug"])
        clear_checkpoints(slug)  # clean up now that the article is safely on disk

        # Phase 2: non-blocking discovery of mixed-license source links.
        try:
            sources_file = collect_image_sources(page)
            artifact_paths.append(sources_file)
        except Exception as source_exc:
            log.warning(
                "Image source discovery failed (non-blocking): %s",
                source_exc,
            )

        # Phase 3: non-blocking reference image harvesting for AI ideation.
        try:
            if sources_file:
                reference_metadata_path = collect_reference_images(page, sources_file)
                artifact_paths.append(reference_metadata_path)
        except Exception as ref_exc:
            log.warning(
                "Reference image harvesting failed (non-blocking): %s",
                ref_exc,
            )

        # Phase 4: non-blocking AI image generation + provenance.
        generated_slots: set[str] = set()
        try:
            image_result = generate_and_log_images(page)
            generated_meta_path = image_result.get("provenance_path")
            if generated_meta_path:
                artifact_paths.append(generated_meta_path)
            artifact_paths.extend(image_result.get("generated_files", []))

            generated_slots = image_result.get("generated_slots", set())
            provider, model = _provider_and_model()
            if _apply_generated_image_metadata(article_path, generated_slots, provider, model, page):
                artifact_paths.append(article_path)
        except Exception as gen_exc:
            log.warning(
                "Image generation pipeline failed (non-blocking): %s",
                gen_exc,
            )

        # Phase 5: optional local auto-commit (never pushes).
        try:
            maybe_auto_commit(page, artifact_paths)
        except Exception as commit_exc:
            log.warning(
                "Local auto-commit failed (non-blocking): %s",
                commit_exc,
            )

        # Phase 6: auto-launch standalone image fallback when Phase 4 produced no images.
        if not generated_slots:
            log.info(
                "Phase 4 generated no images — launching standalone fallback for %s",
                slug,
            )
            _run_phase6_standalone_fallback(slug)

        print(
            f"\n✅ PAGE COMPLETE: {page['slug']} — "
            f"Review at http://localhost:4321/blog/{page['slug']}"
        )
    except Exception as exc:
        log.error("Build failed for '%s': %s", page["slug"], exc)
        # Write raw output for manual inspection
        fallback = ROOT / f"{page['slug']}-raw-output.txt"
        try:
            fallback.write_text(str(exc), encoding="utf-8")
            log.info("Error details written to %s", fallback)
        except OSError:
            pass
        sys.exit(1)


# ── Entry point ────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous furniture archive builder — one page per run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python furniture_agent.py           # Build next pending page\n"
            "  python furniture_agent.py --plan    # Sync backlog status only\n"
        ),
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Update and display backlog status without building a page.",
    )
    args = parser.parse_args()

    if args.plan:
        run_plan_only()
    else:
        run_build()


if __name__ == "__main__":
    main()
