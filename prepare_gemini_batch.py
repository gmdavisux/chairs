#!/usr/bin/env python3
"""
prepare_gemini_batch.py - Prepare prompts for manual Google Gemini generation

This script helps organize your manual workflow by:
1. Reading existing prompts or accepting custom ones
2. Organizing reference images
3. Creating a formatted batch file for easy copy-paste into AI Studio
4. Tracking which images still need generation

Usage:
    python prepare_gemini_batch.py wassily-chair
    python prepare_gemini_batch.py wassily-chair --simple
    python prepare_gemini_batch.py wassily-chair --output batch.txt
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"
IMAGES_DIR = ROOT / "public" / "images"
REFERENCE_DIR = ROOT / "public" / "images" / "reference"

IMAGE_SLOTS = [
    ("hero", "hero.txt"),
    ("silhouette", "silhouette.txt"),
    ("context", "context.txt"),
    ("designer", "designer.txt"),
]


def read_prompts(slug: str, simple: bool = False) -> dict[str, str]:
    """Read prompt files for a given slug."""
    prompt_dir = PROMPTS_DIR / slug
    prompts = {}
    
    for slot, filename in IMAGE_SLOTS:
        prompt_path = prompt_dir / filename
        if prompt_path.exists():
            full_prompt = prompt_path.read_text(encoding="utf-8").strip()
            
            if simple:
                # Extract just the core description, remove style guidance
                lines = full_prompt.split('\n')
                # Take first 2-3 sentences before any style instructions
                core = ' '.join(lines[:2]) if len(lines) > 1 else full_prompt
                if len(core) > 200:
                    core = core[:200].rsplit('.', 1)[0] + '.'
                prompts[slot] = core
            else:
                prompts[slot] = full_prompt
        else:
            print(f"⚠️  Prompt file not found: {filename}", file=sys.stderr)
    
    return prompts


def find_reference_images(slug: str) -> dict[str, list[str]]:
    """Find available reference image URLs for a slug."""
    references = {}
    
    # Check reference-metadata.json
    ref_dir = REFERENCE_DIR / f"{slug}-reference"
    metadata_path = ref_dir / "reference-metadata.json"
    
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            urls = []
            for item in metadata.get("items", []):
                if item.get("status") == "downloaded" or item.get("downloadUrl"):
                    url = item.get("downloadUrl") or item.get("sourcePage")
                    if url:
                        urls.append(url)
            
            if urls:
                references["all"] = urls
        except Exception as e:
            print(f"⚠️  Could not read reference metadata: {e}", file=sys.stderr)
    
    return references


def check_existing_images(slug: str) -> dict[str, bool]:
    """Check which images already exist."""
    status = {}
    for slot, _ in IMAGE_SLOTS:
        png_path = IMAGES_DIR / f"{slug}-{slot}.png"
        jpg_path = IMAGES_DIR / f"{slug}-{slot}.jpg"
        status[slot] = png_path.exists() or jpg_path.exists()
    return status


def format_batch_output(slug: str, prompts: dict, references: dict, existing: dict) -> str:
    """Format prompts and references for easy copy-paste."""
    output = []
    output.append("=" * 80)
    output.append(f"GOOGLE GEMINI BATCH GENERATION: {slug}")
    output.append("=" * 80)
    output.append("")
    
    # Reference images section
    if references:
        output.append("REFERENCE IMAGES (use these in AI Studio):")
        output.append("-" * 80)
        for i, url in enumerate(references.get("all", []), 1):
            output.append(f"{i}. {url}")
        output.append("")
    else:
        output.append("⚠️  No reference images found")
        output.append("")
    
    # Per-slot generation instructions
    for slot, _ in IMAGE_SLOTS:
        if slot not in prompts:
            continue
        
        status = "✓ EXISTS" if existing.get(slot) else "⚠️  NEEDS GENERATION"
        
        output.append("=" * 80)
        output.append(f"SLOT: {slot.upper()} [{status}]")
        output.append("=" * 80)
        output.append("")
        output.append("OUTPUT FILENAME:")
        output.append(f"  {slug}-{slot}.png")
        output.append("")
        output.append("PROMPT:")
        output.append("-" * 80)
        output.append(prompts[slot])
        output.append("-" * 80)
        output.append("")
        
        if references:
            output.append("SUGGESTED REFERENCE:")
            # Rotate through references for variety
            ref_index = {"hero": 0, "detail-material": 0, "detail-structure": 1, "detail-silhouette": 1}
            idx = ref_index.get(slot, 0)
            ref_urls = references.get("all", [])
            if ref_urls:
                output.append(f"  {ref_urls[idx % len(ref_urls)]}")
            output.append("")
        
        output.append("")
    
    # Summary
    total = len(prompts)
    done = sum(1 for v in existing.values() if v)
    output.append("=" * 80)
    output.append(f"SUMMARY: {done}/{total} images exist")
    output.append("=" * 80)
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Prepare prompts for manual Google Gemini batch generation"
    )
    parser.add_argument(
        "slug",
        help="Furniture piece slug (e.g., wassily-chair)",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simplified prompts (remove style guidance)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write output to file instead of stdout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for programmatic use",
    )
    
    args = parser.parse_args()
    
    # Load data
    prompts = read_prompts(args.slug, simple=args.simple)
    references = find_reference_images(args.slug)
    existing = check_existing_images(args.slug)
    
    if not prompts:
        print(f"❌ No prompts found for {args.slug}", file=sys.stderr)
        print(f"   Check: {PROMPTS_DIR / args.slug}", file=sys.stderr)
        return 1
    
    # Format output
    if args.json:
        output_data = {
            "slug": args.slug,
            "prompts": prompts,
            "references": references,
            "existing": existing,
        }
        output = json.dumps(output_data, indent=2, ensure_ascii=False)
    else:
        output = format_batch_output(args.slug, prompts, references, existing)
    
    # Write or print
    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"✓ Written to: {args.output}")
        
        # Also print summary
        total = len(prompts)
        done = sum(1 for v in existing.values() if v)
        print(f"📊 Status: {done}/{total} images exist")
        if done < total:
            print(f"⚠️  Still need: {', '.join(s for s, exists in existing.items() if not exists)}")
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
