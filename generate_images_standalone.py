#!/usr/bin/env python3
"""
Standalone image prompt generation and image generation for existing articles.

Usage:
    python generate_images_standalone.py wassily-chair
    python generate_images_standalone.py wassily-chair --prompts-only
    python generate_images_standalone.py wassily-chair --images-only
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "src" / "content" / "blog"
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"
IMAGES_DIR = ROOT / "public" / "images"

# Import from furniture_agent
sys.path.insert(0, str(ROOT))
from furniture_agent import (
    IMAGE_SLOT_PROMPT_FILES,
    STYLE_NEGATIVE_PROMPT,
    _build_style_prompt,
    _download_image_url,
    _file_sha256,
    _generate_with_fal,
    _generate_with_openai,
    _normalize_image_size,
    _provider_and_model,
    _safe_int_env,
    _safe_relpath,
    load_backlog,
)


def generate_prompts_with_ai(slug: str, article_path: Path) -> dict[str, str]:
    """Use AI to generate image prompts from the article content."""
    log.info("Generating image prompts for %s using AI...", slug)
    
    article_text = article_path.read_text(encoding="utf-8")
    
    # Extract metadata from frontmatter
    backlog = load_backlog()
    page = next((p for p in backlog["pages"] if p["slug"] == slug), None)
    if not page:
        raise ValueError(f"Page {slug} not found in backlog.json")
    
    # Create AI prompt
    model = os.getenv("FURNITURE_MODEL", "gpt-4o")
    llm = ChatOpenAI(
        model=model,
        temperature=0.7,
        max_tokens=2000,
        base_url="https://models.inference.ai.azure.com" if os.getenv("GITHUB_MODELS") else None,
        api_key=os.getenv("GITHUB_TOKEN") if os.getenv("GITHUB_MODELS") else None,
    )
    
    prompt = f"""You are generating detailed image prompts for a furniture archive article.

Article: {page['title']}
Designer: {page.get('designer', 'Unknown')}
Era: {page.get('era', 'Unknown')}

Article content:
{article_text[:3000]}

Generate 4 specific image prompts following the photographic style guide:
- Soft, diffused warm lighting (2700-3000K)
- Natural color grading, moderate contrast
- Furniture as primary subject (60-75% of frame)
- Three-quarter or slight low-angle perspective
- Minimal, era-appropriate background (optional)
- NO people, clutter, text, logos, or anachronistic elements

Output exactly 4 prompts with these labels (one per line, followed by the prompt):

HERO
[1-2 sentence prompt for main hero image showing full chair]

DETAIL_1_MATERIAL
[1-2 sentence prompt focusing on material texture and surface detail]

DETAIL_2_STRUCTURE
[1-2 sentence prompt showing joints, frame, or structural connections]

DETAIL_3_SILHOUETTE
[1-2 sentence prompt capturing the profile/silhouette against minimal background]

Each prompt should be concrete and specific to this furniture piece."""
    
    response = llm.invoke(prompt)
    prompts_raw = response.content
    
    # Parse the response
    prompts = {}
    current_label = None
    current_text = []
    
    for line in prompts_raw.split('\n'):
        line = line.strip()
        if line in ['HERO', 'DETAIL_1_MATERIAL', 'DETAIL_2_STRUCTURE', 'DETAIL_3_SILHOUETTE']:
            if current_label and current_text:
                prompts[current_label] = ' '.join(current_text).strip()
            current_label = line
            current_text = []
        elif line and current_label:
            current_text.append(line)
    
    # Save last prompt
    if current_label and current_text:
        prompts[current_label] = ' '.join(current_text).strip()
    
    return prompts


def save_prompts_to_files(slug: str, prompts: dict[str, str], requested_labels=None) -> list[Path]:
    """Save prompts to individual text files, only for requested slots."""
    out_dir = PROMPTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Only map the core slots unless explicitly requested
    label_map = {
        "HERO": "hero.txt",
        "CONTEXT": "context.txt",
        "SILHOUETTE": "silhouette.txt",
        "DESIGNER": "designer.txt",
    }
    # If requested_labels is provided, filter to those only
    if requested_labels:
        label_map = {k: v for k, v in label_map.items() if k in requested_labels}

    saved_files = []
    for label, filename in label_map.items():
        if label in prompts:
            out_path = out_dir / filename
            out_path.write_text(prompts[label], encoding="utf-8")
            saved_files.append(out_path)
            log.info("  Saved: %s", out_path)
        else:
            log.warning("  Missing prompt for %s", label)
    return saved_files


def generate_images(slug: str, article_path: Path) -> dict:
    """Generate images using the existing furniture_agent workflow."""
    from furniture_agent import generate_and_log_images, load_backlog
    
    backlog = load_backlog()
    page = next((p for p in backlog["pages"] if p["slug"] == slug), None)
    if not page:
        raise ValueError(f"Page {slug} not found in backlog.json")
    
    log.info("Generating images for %s...", slug)
    result = generate_and_log_images(page)
    
    summary = result.get("summary", {})
    log.info(
        "Image generation complete: %d generated, %d reference fallback, %d failed, %d skipped",
        summary.get("generatedCount", 0),
        summary.get("referenceFallbackCount", 0),
        summary.get("failedCount", 0),
        summary.get("skippedCount", 0),
    )
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate image prompts and/or images for existing articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python generate_images_standalone.py wassily-chair
  python generate_images_standalone.py wassily-chair --prompts-only
  python generate_images_standalone.py wassily-chair --images-only
        """
    )
    parser.add_argument("slug", help="Article slug (e.g. wassily-chair)")
    parser.add_argument(
        "--prompts-only",
        action="store_true",
        help="Only generate prompts, don't generate images"
    )
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Only generate images (prompts must already exist)"
    )
    
    args = parser.parse_args()
    slug = args.slug
    
    # Check if article exists
    article_path = CONTENT_DIR / f"{slug}.md"
    if not article_path.exists():
        article_path = CONTENT_DIR / f"{slug}.mdx"
    if not article_path.exists():
        log.error("Article not found: %s", slug)
        sys.exit(1)
    
    log.info("Processing article: %s", article_path)
    
    try:
        # Step 1: Generate prompts (unless --images-only)
        if not args.images_only:
            log.info("=== Step 1: Generate Image Prompts ===")
            prompts = generate_prompts_with_ai(slug, article_path)
            # Only save prompts for requested slots if --slots is used
            requested_labels = None
            if hasattr(args, "slots") and args.slots:
                # Map slot names to prompt labels
                slot_to_label = {
                    "hero": "HERO",
                    "context": "CONTEXT",
                    "silhouette": "SILHOUETTE",
                    "designer": "DESIGNER",
                }
                requested_labels = [slot_to_label[s] for s in args.slots if s in slot_to_label]
            saved_files = save_prompts_to_files(slug, prompts, requested_labels=requested_labels)
            log.info("Generated %d prompt files", len(saved_files))
            if args.prompts_only:
                log.info("Prompts-only mode: stopping here.")
                return
        
        # Step 2: Generate images (unless --prompts-only)
        if not args.prompts_only:
            log.info("\n=== Step 2: Generate Images ===")
            result = generate_images(slug, article_path)
            
            # Check for issues
            summary = result.get("summary", {})
            if summary.get("skippedCount", 0) > 0:
                log.warning(
                    "\n⚠️  %d images were skipped. Check provenance file for details:",
                    summary["skippedCount"]
                )
                provenance_path = PROMPTS_DIR / slug / "provenance-generated.json"
                log.warning("  %s", provenance_path)
            
            if summary.get("generatedCount", 0) > 0:
                log.info("\n✅ Successfully generated %d images", summary["generatedCount"])
            
            if summary.get("referenceFallbackCount", 0) > 0:
                log.info("📷 Used %d reference fallback images", summary["referenceFallbackCount"])
        
        log.info("\n✅ Complete! Review images at:")
        log.info("  http://localhost:4321/blog/%s", slug)
        
    except Exception as exc:
        log.error("Failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
