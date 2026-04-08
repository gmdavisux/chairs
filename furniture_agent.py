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
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from crewai import Agent, Crew, Task
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
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
    return {p.stem for p in CONTENT_DIR.glob("*.md")}


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

    Model is always gpt-5.4-mini (0.33x cost tier on GitHub Copilot billing).
    temperature=0.3 → analytical agents (Planner, Researcher, Publisher)
    temperature=0.7 → creative agents (Writer, ImagePrompter)
    """
    model = os.getenv("FURNITURE_MODEL", "gpt-5.4-mini")

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


# ── CrewAI crew builder ────────────────────────────────────────────────────
def build_crew(page: dict, concept: str) -> Crew:
    slug = page["slug"]
    title = page["title"]
    designer = page.get("designer", "Unknown")
    era = page.get("era", "Classic")
    category = page.get("category", "Iconic Chairs")
    today = date.today().isoformat()

    # TavilySearchResults reads TAVILY_API_KEY from the environment automatically.
    # max_results=6 keeps token usage low while giving the Researcher enough sources.
    search_tool = TavilySearchResults(max_results=6)

    # ── Agents ────────────────────────────────────────────────────────────
    planner = Agent(
        role="Editorial Director",
        goal=(
            "Confirm the next furniture page assignment and produce a focused editorial "
            "brief that guides the research and writing teams."
        ),
        backstory=(
            "You are a seasoned editorial director for a high-end design museum archive. "
            "You understand narrative arcs, design history, and what makes a furniture "
            "deep-dive distinct and authoritative. You read the site concept carefully "
            "before issuing any brief."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    researcher = Agent(
        role="Design Historian & Researcher",
        goal=(
            "Gather verified, citation-ready facts about the furniture piece and its "
            "designer using web search."
        ),
        backstory=(
            "You are a meticulous design historian who cross-references multiple primary "
            "sources. You never fabricate dates, names, or exhibition records. Every fact "
            "you surface is backed by a real, attributable source. You run multiple "
            "targeted searches to ensure completeness."
        ),
        tools=[search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Senior Design Writer",
        goal=(
            "Write an authoritative, warm, 1800–2200 word Markdown article about the "
            "furniture piece that matches the voice of the existing site."
        ),
        backstory=(
            "You write like a senior contributor to Wallpaper* or Domus — passionate, "
            "precise, and never condescending. You tell the human story behind design "
            "objects, weaving together biography, craft, culture, and enduring "
            "significance. You use inline citations like [1], [2] throughout, and end "
            "with a numbered References section."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    image_prompter = Agent(
        role="Visual Director",
        goal=(
            "Create detailed image generation prompts and public domain search queries "
            "for the furniture piece."
        ),
        backstory=(
            "You are a visual director with deep knowledge of furniture photography, "
            "studio lighting, and archival image research. You know exactly which shots "
            "will make a design archive page authoritative — hero views, material "
            "details, structural close-ups, and context shots."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    publisher = Agent(
        role="Publisher",
        goal=(
            "Assemble the final, complete Markdown file — YAML frontmatter plus article "
            "body — ready to save as an Astro content collection entry."
        ),
        backstory=(
            "You are a precise technical editor who ensures every page has complete, "
            "valid Astro frontmatter, proper Markdown structure, an accurate description "
            "field extracted from the article, and no formatting artifacts."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Tasks ─────────────────────────────────────────────────────────────
    plan_task = Task(
        description=(
            f"Read this site concept document carefully:\n\n{concept}\n\n"
            f"The next page to build is: **{title}** "
            f"(slug: `{slug}`, designer: {designer}, era: {era}, category: {category}).\n\n"
            "Produce a concise editorial brief (under 350 words) covering:\n"
            "- 5–7 key narrative angles specific to this piece\n"
            "- 3–4 H2 section titles (descriptive, not generic)\n"
            "- Specific facts, dates, or controversies worth investigating\n"
            "- 2–3 related pieces already on the site (check the sample backlog in the concept)"
        ),
        expected_output=(
            "A short editorial brief with narrative angles, proposed section titles, "
            "and specific research questions."
        ),
        agent=planner,
    )

    research_task = Task(
        description=(
            f"Research **{title}** by {designer} using web search. Run at least 4 "
            "targeted searches covering different aspects. Find:\n\n"
            "1. Exact year the design was created and first manufactured, with manufacturer name\n"
            "2. Key design decisions: materials chosen, structural innovations, prototyping history\n"
            "3. Exhibition history, design awards, and museum collection acquisitions\n"
            "4. Designer biography highlights specifically relevant to this piece\n"
            "5. Cultural reception: notable appearances, critical reassessments, collector market\n"
            "6. Any lesser-known facts that would reward a careful reader\n\n"
            "Return a structured research brief with numbered facts and source URLs for citations."
        ),
        expected_output=(
            "A structured research brief with at least 15 verified facts, each with a "
            "source URL for citation."
        ),
        agent=researcher,
        context=[plan_task],
    )

    # Build the designer slug and related-page hints for the sidebar block
    designer_slug = re.sub(r"[^a-z0-9]+", "-", designer.lower()).strip("-")
    related_slugs_hint = ", ".join(
        p["slug"] for p in INITIAL_PAGES
        if p["slug"] != slug and (
            p.get("designer") == designer
            or p.get("era") == era
            or p.get("category") == category
        )
    )[:200]

    write_task = Task(
        description=(
            f"Using the editorial brief and research, write the full article for "
            f"**{title}**.\n\n"
            "Requirements:\n"
            "- 1800–2200 words\n"
            "- Opening hook paragraph with no heading (place the reader in the moment)\n"
            "- 4–5 H2 sections with descriptive, non-generic titles\n"
            "- A 'Meet the Designer' H2 section\n"
            "- A 'Why It Endures' or 'The Legacy' H2 section\n"
            "- Inline citations [1] [2] etc. throughout body text\n"
            "- Affiliate placeholder comment at the very end of the body:\n"
            "  `<!-- AFFILIATE: Original/authenticated replica purchase links -->`\n"
            "- A '## References' section with numbered, formatted citations\n"
            "- Tone: warm, expert, museum-catalog quality — match the voice of the "
            "existing Eames Lounge Chair page on this site\n\n"
            "SIDEBAR BLOCK (mandatory):\n"
            "Immediately after the opening hook paragraph, insert this sidebar as a "
            "Markdown blockquote with bold headings. Use real slugs where pages likely "
            "exist; append '*(coming soon)*' for pages not yet published.\n\n"
            "> **Meet the Designer**\n"
            f"> [{designer}](/designers/{designer_slug}) — one-sentence bio teaser.\n"
            ">\n"
            "> **Related Chairs**\n"
            f"> Choose 3–4 from these relevant slugs: {related_slugs_hint}\n"
            "> Format each as: `> - [Chair Name](/blog/slug)`\n"
            "> Append *(coming soon)* if the page doesn't exist yet.\n\n"
            "Output: raw Markdown only. No frontmatter. No code fences around the output."
        ),
        expected_output=(
            "Full article body in Markdown, 1800–2200 words, no frontmatter, "
            "with sidebar blockquote after opening hook, ending with References section."
        ),
        agent=writer,
        context=[plan_task, research_task],
    )

    image_task = Task(
        description=(
            f"Create image generation prompts for **{title}** (slug: `{slug}`).\n\n"
            "Output EXACTLY this plain-text format — no JSON, no markdown fences, "
            "no extra commentary. Each section is separated by a blank line and starts "
            "with its label on its own line followed by the prompt on the next line.\n\n"
            "FORMAT:\n"
            "HERO\n"
            "<full hero prompt here>\n"
            "\n"
            "DETAIL_1\n"
            "<close-up prompt: primary material or surface texture>\n"
            "\n"
            "DETAIL_2\n"
            "<close-up prompt: structural joint, hardware, or base detail>\n"
            "\n"
            "DETAIL_3\n"
            "<close-up prompt: signature silhouette or profile view>\n"
            "\n"
            "PUBLIC_DOMAIN_1\n"
            "<Wikimedia Commons search query>\n"
            "\n"
            "PUBLIC_DOMAIN_2\n"
            "<museum digital collection search query — MoMA, V&A, Cooper Hewitt, Vitra>\n"
            "\n"
            "PUBLIC_DOMAIN_3\n"
            "<Library of Congress or archive.org search query>\n\n"
            "Prompt quality requirements:\n"
            "- HERO: photorealistic studio shot, pure white seamless background, "
            "museum-quality three-point lighting, full object visible, no people, "
            "35mm product photography aesthetic, 8K resolution\n"
            "- DETAIL shots: extreme macro close-up, shallow depth of field, "
            "specific material or construction element unique to this design\n"
            "- PUBLIC DOMAIN queries: precise terminology a museum archivist would use"
        ),
        expected_output=(
            "Plain text with 7 labeled sections (HERO, DETAIL_1-3, PUBLIC_DOMAIN_1-3), "
            "ready to copy-paste into any image generator or archive search."
        ),
        agent=image_prompter,
        context=[plan_task],
    )

    publish_task = Task(
        description=(
            f"Assemble the complete, final Markdown file for **{title}**.\n\n"
            "Steps:\n"
            "1. Extract a precise 1-sentence description (100–160 characters) from the "
            "article's opening paragraph.\n"
            "2. Prepend this exact YAML frontmatter block to the article body:\n\n"
            "---\n"
            f'title: "{title}"\n'
            'description: "[your extracted description here]"\n'
            f"pubDate: {today}\n"
            f"heroImage: /images/{slug}-hero.jpg\n"
            f'designer: "{designer}"\n'
            f'era: "{era}"\n'
            f'category: "{category}"\n'
            "---\n\n"
            "3. Return the COMPLETE file content: the frontmatter block, a blank line, "
            "then the full article body.\n"
            "4. Do NOT wrap the output in code fences. Output the raw file content only.\n"
            "5. The description field must contain real extracted text, not a placeholder."
        ),
        expected_output=(
            f"Complete Markdown file content — YAML frontmatter + article body — "
            f"ready to write as src/content/blog/{slug}.md"
        ),
        agent=publisher,
        context=[write_task, image_task],
    )

    return Crew(
        agents=[planner, researcher, writer, image_prompter, publisher],
        tasks=[plan_task, research_task, write_task, image_task, publish_task],
        verbose=True,
    )


# ── Output extraction and file I/O ─────────────────────────────────────────
def _get_task_raw(tasks_output, index: int) -> str:
    """Safely extract raw string output from a task result at a given index."""
    try:
        output = tasks_output[index]
        # CrewAI TaskOutput exposes .raw in most versions; fall back to str()
        return str(getattr(output, "raw", output))
    except (IndexError, AttributeError):
        return ""


# Labels in order — must match the ImagePrompter task format exactly.
_PROMPT_LABELS = [
    ("HERO",            "hero.txt"),
    ("DETAIL_1",        "detail-1-material.txt"),
    ("DETAIL_2",        "detail-2-structure.txt"),
    ("DETAIL_3",        "detail-3-silhouette.txt"),
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


def extract_and_save(result, page: dict) -> Path:
    """
    Extract article and image prompts from the crew result and write them to disk.

    Task indices: 0=plan, 1=research, 2=write, 3=image, 4=publish
    The Publisher (index 4) returns the complete file with frontmatter.
    The ImagePrompter (index 3) returns the JSON prompts block.
    """
    slug = page["slug"]

    try:
        tasks_output = result.tasks_output
    except AttributeError:
        tasks_output = []

    # Full file from Publisher
    full_markdown = _get_task_raw(tasks_output, 4)
    if not full_markdown:
        # Fallback: use the complete result string
        full_markdown = str(result)
        log.warning("Publisher task output missing; using full crew result as fallback.")

    # Image prompts from ImagePrompter
    prompts_raw = _get_task_raw(tasks_output, 3)

    # Write the article
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    article_path = CONTENT_DIR / f"{slug}.md"
    article_path.write_text(full_markdown.strip() + "\n", encoding="utf-8")
    log.info("Article written: %s", article_path)

    # Write image prompts
    if prompts_raw:
        save_image_prompts(slug, prompts_raw)
    else:
        log.warning("No image prompts output found for slug '%s'.", slug)

    return article_path


# ── Environment validation ─────────────────────────────────────────────────
def validate_env() -> None:
    """Abort early if required environment variables are missing."""
    use_github_models = os.getenv("GITHUB_MODELS", "").strip() in ("1", "true", "yes")
    llm_key = "GITHUB_TOKEN" if use_github_models else "OPENAI_API_KEY"
    missing = [k for k in (llm_key, "TAVILY_API_KEY") if not os.getenv(k)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        if use_github_models:
            log.error("GITHUB_MODELS=1 is set — GITHUB_TOKEN must be present.")
        log.error("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)


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
        crew = build_crew(page, concept)
        result = crew.kickoff()
        extract_and_save(result, page)
        mark_done(backlog, page["slug"])
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
