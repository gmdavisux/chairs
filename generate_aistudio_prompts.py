#!/usr/bin/env python3
"""
Generate AI Studio-ready prompts with multiple reference URLs.

This tool creates formatted prompts optimized for Google AI Studio's manual
workflow, including multiple reference image URLs and style guidance.

Handles legacy pages by extracting prompts from MDX files when archives don't exist.

Usage:
    python generate_aistudio_prompts.py wassily-chair
    python generate_aistudio_prompts.py eames-lounge-chair --slots hero context
    python generate_aistudio_prompts.py tulip-chair --output aistudio-batch.txt
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from typing import Optional

# Paths
ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"
REFERENCE_DIR = ROOT / "public" / "images" / "reference"
IMAGES_DIR = ROOT / "public" / "images"
CONTENT_DIR = ROOT / "src" / "content" / "blog"

# Image slot configuration
IMAGE_SLOTS = [
    ("hero", "hero.txt"),
    ("sketch", "sketch.txt"),
    ("context", "context.txt"),
    ("designer", "designer.txt"),
]

# Style reference URL for sketch rendering
SKETCH_STYLE_REFERENCE = "https://media.licdn.com/dms/image/v2/C5622AQEsWIESc2lxXA/feedshare-shrink_8192/feedshare-shrink_8192/0/1547756609958?e=1777507200&v=beta&t=nOHIpJChD4qrQLIvoyYaAefHxR3caB007sifJ2i9slk"

# Style guide text
STYLE_GUIDE = """
STYLE GUIDANCE:
- Soft, diffused warm illumination at 2700-3000K
- Gentle highlights with well-defined but not harsh shadows
- Fuller tonal range utilizing both shadow detail and highlight clarity
- Rich contrast with full tonal range from true blacks to clean whites
- Target subject occupancy: roughly 60-75 percent of frame
- Three-quarter or slight low-angle view with minimal distortion
- Clean negative space, no clutter
- Preserve signature silhouette and geometry
- Authentic materials and finishes
- Era-appropriate setting (minimal, if any)
"""


def load_reference_metadata(slug: str) -> dict:
    """Load reference metadata if available."""
    ref_folder = REFERENCE_DIR / f"{slug}-reference"
    metadata_file = ref_folder / "reference-metadata.json"
    
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return {}


def extract_references_from_mdx(slug: str) -> list[dict]:
    """Extract reference image URLs from MDX file sources."""
    mdx_path = CONTENT_DIR / f"{slug}.mdx"
    if not mdx_path.exists():
        mdx_path = CONTENT_DIR / f"{slug}.md"
        if not mdx_path.exists():
            return []
    
    try:
        content = mdx_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return []
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return []
        
        data = yaml.safe_load(parts[1])
        references = []
        
        # Extract hero image source
        hero_source = data.get("heroImageSource", "")
        if "wikimedia.org" in hero_source or "commons.wikimedia.org" in hero_source:
            if "https://" in hero_source:
                url_start = hero_source.find("https://")
                url = hero_source[url_start:].split()[0].rstrip("'\")")
                references.append({
                    'id': 'hero-ref',
                    'url': url,
                    'source': 'MDX heroImageSource'
                })
        
        # Extract from images array
        images = data.get("images", [])
        for idx, img in enumerate(images):
            source = img.get("source", "")
            if "wikimedia.org" in source or "commons.wikimedia.org" in source:
                if "https://" in source:
                    url_start = source.find("https://")
                    url = source[url_start:].split()[0].rstrip("'\")")
                    references.append({
                        'id': f'ref-{idx+1}',
                        'url': url,
                        'source': f'MDX image {img.get("id", idx)}'
                    })
        
        return references
    except Exception:
        return []


def get_reference_urls(slug: str, limit: int = 5) -> list[dict]:
    """Get available reference image URLs for a slug."""
    metadata = load_reference_metadata(slug)
    references = []
    
    if 'items' in metadata:
        for item in metadata['items']:
            if item.get('status') == 'downloaded' and item.get('downloadUrl'):
                references.append({
                    'id': item.get('id', 'unknown'),
                    'url': item['downloadUrl'],
                    'source': item.get('sourcePage', 'Unknown')
                })
                if len(references) >= limit:
                    break
    
    # If no references found, try to extract from MDX file
    if not references:
        mdx_refs = extract_references_from_mdx(slug)
        if mdx_refs:
            references = mdx_refs[:limit]
    
    return references


def extract_prompt_from_mdx(slug: str, slot: str) -> Optional[str]:
    """Extract prompt information from MDX file as fallback."""
    mdx_path = CONTENT_DIR / f"{slug}.mdx"
    if not mdx_path.exists():
        mdx_path = CONTENT_DIR / f"{slug}.md"
        if not mdx_path.exists():
            return None
    
    try:
        content = mdx_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        
        data = yaml.safe_load(parts[1])
        chair_name = slug.replace("-", " ").title()
        designer = data.get("designer", "")
        title = data.get("title", "")
        
        # Slot-specific extraction with proper styling
        if slot == "hero":
            alt = data.get("heroImageAlt", "")
            if alt and designer:
                return f"Photorealistic high-quality studio photograph of {designer} {alt}. Soft, diffused warm illumination at 2700-3000K producing gentle highlights with well-defined natural shadows and rich tonal depth. Clean minimal neutral background. Three-quarter view showing signature silhouette and geometry. Sharp focus on material texture, grain, and hardware detail. Full tonal range from deep shadows to clean highlights. Natural color grading. No people, no clutter, no text."
        
        elif slot == "sketch":
            # For sketch, never use photography language
            return None  # Force template generation which has proper marker rendering language
        
        elif slot == "context":
            images = data.get("images", [])
            for img in images:
                if "context" in img.get("id", ""):
                    alt = img.get("alt", "")
                    if alt and designer:
                        # Extract setting info if available
                        return f"{designer} {chair_name} in an elegant mid-century modern interior. {alt} Warm lighting at 2700K showing the relationship between furniture and architectural space. Era-appropriate minimal setting that anchors period authenticity."
        
        elif slot == "designer":
            # Designer portraits need archival photography style
            if designer:
                return f"Black and white archival portrait photograph of {designer}, furniture designer. Professional studio photographer style. Clear, dignified composition typical of modernist designer portraits. Natural lighting. Historical photography aesthetic."
        
    except Exception:
        pass
    
    return None


def generate_template_prompt(slug: str, slot: str) -> str:
    """Generate a detailed template prompt when no prompt is available."""
    chair_name = slug.replace("-", " ").title()
    
    templates = {
        "hero": f"Photorealistic high-quality studio photograph of the iconic {chair_name}, three-quarter view showing the signature silhouette, geometry, and authentic materials. Soft, diffused warm illumination at 2700-3000K producing gentle highlights with well-defined natural shadows and rich tonal depth. Clean minimal neutral background. Sharp focus on material texture showing visible grain, stitching, and hardware detail. Full tonal range from deep shadows to clean highlights. Enhanced contrast preserving shadow and highlight detail. Natural color grading. Clean negative space. No people, no clutter, no text.",
        
        "sketch": f"Professional industrial design marker rendering of the {chair_name}. **CRITICAL: NOT A SILHOUETTE** - Use dynamic three-quarter or perspective angle showing sculptural form and dimensional depth, NOT flat side profile. Cool gray Prismacolor or Copic markers (20%, 30%, 50% gray tones) defining the form with smooth graduated shading. Always include judicious selective color accents - single or limited strategic hues highlighting key features or materials. Confident, sketchy black ink construction lines that extend beyond the form with skeletal quality - multiple overlapping line strokes showing the drawing process, not tight technical drawing. Lines can overshoot corners and edges, emphasizing gesture and construction over precision. White or subtly tinted paper background (pale blue, warm beige, or neutral tone). Background features abstract geometric shapes, color blocks, or marker splashes adding visual interest without competing with subject. Emphasize pure form through shading. Balance between technical precision and hand-drawn spontaneity. No signature, text, annotations, or dimension lines.",
        
        "context": f"The {chair_name} in an elegant mid-century modern interior setting. Positioned to show how the enveloping form creates presence within the architectural space. Warm lighting at 2700K emphasizing both the chair's form and the refined atmosphere. Architectural photography capturing the relationship between sculptural furniture and modernist interior design. Minimal era-appropriate context that anchors period authenticity without visual crowding. Clean negative space around the subject.",
        
        "designer": f"Black and white archival portrait photograph of the {chair_name} designer. Professional studio photographer style. Clear, dignified composition typical of modernist designer portraits. Natural lighting. Historical photography aesthetic with neutral background. Museum-quality archival print."
    }
    
    return templates.get(slot, f"{chair_name} - {slot} view. Professional photograph with high-quality studio lighting.")


def read_prompt(slug: str, slot: str) -> Optional[str]:
    """Read prompt file for a given slug and slot, with fallbacks."""
    filename = next((f for s, f in IMAGE_SLOTS if s == slot), None)
    if not filename:
        return None
    
    # Try 1: Archived prompt file
    prompt_path = PROMPTS_DIR / slug / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    
    # Try 2: Extract from MDX file
    mdx_prompt = extract_prompt_from_mdx(slug, slot)
    if mdx_prompt:
        return mdx_prompt
    
    # Try 3: Generate template
    return generate_template_prompt(slug, slot)


def check_image_exists(slug: str, slot: str) -> bool:
    """Check if image already exists for this slot."""
    for ext in ['.png', '.jpg', '.jpeg']:
        if (IMAGES_DIR / f"{slug}-{slot}{ext}").exists():
            return True
    return False


def format_aistudio_prompt(
    slug: str,
    slot: str,
    prompt: str,
    references: list[dict],
    include_style: bool = False
) -> str:
    """Format a prompt for AI Studio with references."""
    
    output = []
    output.append("=" * 80)
    output.append(f"SLOT: {slot.upper()}")
    
    exists = check_image_exists(slug, slot)
    if exists:
        output.append(f"STATUS: ✓ Image exists")
    else:
        output.append(f"STATUS: ⚠️  NEEDS GENERATION")
    
    output.append(f"OUTPUT FILENAME: {slug}-{slot}.png")
    output.append("=" * 80)
    output.append("")
    
    output.append("COPY THIS ENTIRE BLOCK INTO AI STUDIO:")
    output.append("┌" + "─" * 78 + "┐")
    
    # Prompt text
    output.append("│ " + " " * 76 + " │")
    prompt_lines = prompt.split('\n')
    for line in prompt_lines:
        if line.strip():
            # Wrap long lines
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= 74:
                    current_line += (" " if current_line else "") + word
                else:
                    output.append("│ " + current_line.ljust(76) + " │")
                    current_line = word
            if current_line:
                output.append("│ " + current_line.ljust(76) + " │")
    
    # Add style guide if requested
    if include_style:
        output.append("│ " + " " * 76 + " │")
        style_lines = STYLE_GUIDE.strip().split('\n')
        for line in style_lines:
            if line.strip():
                output.append("│ " + line[:76].ljust(76) + " │")
    
    output.append("│ " + " " * 76 + " │")
    
    # Reference URLs section
    if references or slot == "sketch":
        output.append("│ " + "REFERENCE IMAGES:".ljust(76) + " │")
        output.append("│ " + " " * 76 + " │")
        
        # Add sketch style reference first if this is a sketch slot
        if slot == "sketch":
            output.append("│ " + "Style Reference (marker rendering):".ljust(76) + " │")
            style_url = SKETCH_STYLE_REFERENCE
            output.append("│ " + style_url[:76].ljust(76) + " │")
            if len(style_url) > 76:
                output.append("│ " + style_url[76:].ljust(76) + " │")
            output.append("│ " + " " * 76 + " │")
        
        # Add chair reference URLs
        if references:
            output.append("│ " + "Chair References:".ljust(76) + " │")
            for ref in references[:3]:  # Limit to 3 for best results
                url = ref['url']
                output.append("│ " + url[:76].ljust(76) + " │")
                if len(url) > 76:
                    # Handle URLs longer than 76 chars
                    remaining = url[76:]
                    while remaining:
                        output.append("│ " + remaining[:76].ljust(76) + " │")
                        remaining = remaining[76:]
        else:
            output.append("│ " + "⚠️ No reference images - find on Wikimedia Commons".ljust(76) + " │")
    
    output.append("│ " + " " * 76 + " │")
    output.append("└" + "─" * 78 + "┘")
    output.append("")
    output.append("→ In AI Studio: Paste prompt, then click '+' to add each reference URL")
    output.append("")
    output.append("")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI Studio-ready prompts with multiple reference URLs"
    )
    parser.add_argument(
        "slug",
        help="Furniture piece slug (e.g., wassily-chair)"
    )
    parser.add_argument(
        "--slots",
        nargs="+",
        choices=["hero", "sketch", "context", "designer"],
        help="Generate only specific slots (default: all)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: print to console)"
    )
    parser.add_argument(
        "--include-style-guide",
        action="store_true",
        help="Include full style guide in each prompt"
    )
    parser.add_argument(
        "--max-references",
        type=int,
        default=5,
        help="Maximum number of reference URLs per slot (default: 5)"
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only generate prompts for images that don't exist yet"
    )
    
    args = parser.parse_args()
    
    # Get reference URLs
    references = get_reference_urls(args.slug, limit=args.max_references)
    
    if not references:
        print(f"⚠️  No reference images found for {args.slug}", file=sys.stderr)
        print(f"   Generating prompts anyway using MDX/template fallback.", file=sys.stderr)
        print(f"   For best results, find reference images on Wikimedia Commons.\n", file=sys.stderr)
    
    # Filter slots
    slots_to_process = [s for s, _ in IMAGE_SLOTS]
    if args.slots:
        slots_to_process = [s for s in slots_to_process if s in args.slots]
    
    # Generate prompts
    all_output = []
    all_output.append("╔" + "═" * 78 + "╗")
    all_output.append("║" + " " * 20 + "AI STUDIO GENERATION PROMPTS" + " " * 30 + "║")
    all_output.append("║" + " " * 78 + "║")
    all_output.append("║" + f"  Furniture: {args.slug}".ljust(78) + "║")
    all_output.append("║" + f"  References: {len(references)} available".ljust(78) + "║")
    all_output.append("╚" + "═" * 78 + "╝")
    all_output.append("")
    all_output.append("WORKFLOW:")
    all_output.append("1. Open https://aistudio.google.com/")
    all_output.append("2. For each slot below:")
    all_output.append("   a. Copy the entire boxed block (prompt + reference URLs)")
    all_output.append("   b. Paste the PROMPT TEXT into AI Studio's prompt field")
    all_output.append("   c. Click '+' to add each REFERENCE IMAGE URL one by one")
    all_output.append("      - For sketches: Add style reference first, then chair references")
    all_output.append("      - For other slots: Add 2-3 chair reference URLs")
    all_output.append("   d. Click Generate and wait for result")
    all_output.append("   e. Download image as PNG with the OUTPUT FILENAME shown")
    all_output.append("3. After generating all images:")
    all_output.append(f"   python update_mdx_images.py {args.slug}")
    all_output.append("")
    all_output.append("")
    
    generated_count = 0
    skipped_count = 0
    
    for slot in slots_to_process:
        prompt = read_prompt(args.slug, slot)
        
        if not prompt:
            continue
        
        # Skip if image exists and --only-missing is set
        if args.only_missing and check_image_exists(args.slug, slot):
            skipped_count += 1
            continue
        
        formatted = format_aistudio_prompt(
            args.slug,
            slot,
            prompt,
            references,
            include_style=args.include_style_guide
        )
        all_output.append(formatted)
        generated_count += 1
    
    # Summary
    all_output.append("=" * 80)
    all_output.append("SUMMARY")
    all_output.append("=" * 80)
    all_output.append(f"Prompts generated: {generated_count}")
    if args.only_missing:
        all_output.append(f"Skipped (already exist): {skipped_count}")
    all_output.append(f"Chair reference images available: {len(references)}")
    all_output.append("")
    all_output.append("TIPS:")
    all_output.append("• Multiple reference images (2-3) produce significantly better results")
    all_output.append("• For sketches: Style reference ensures marker rendering aesthetic")
    all_output.append("• Copy entire boxed blocks for faster workflow")
    all_output.append("")
    
    output_text = "\n".join(all_output)
    
    # Output
    if args.output:
        args.output.write_text(output_text, encoding="utf-8")
        print(f"✓ Generated prompts saved to: {args.output}")
        print(f"  Prompts: {generated_count}")
        if skipped_count > 0:
            print(f"  Skipped: {skipped_count}")
        print(f"  References: {len(references)}")
    else:
        print(output_text)
    
    return 0 if generated_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
