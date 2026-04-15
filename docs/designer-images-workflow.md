# Designer Images Workflow

This document describes the automated workflow for fetching and managing designer portrait images.

## Naming Convention

All designer images follow the pattern: `{chair-slug}-designer.jpg`

Examples:
- `barcelona-chair-designer.jpg` → Ludwig Mies van der Rohe
- `tulip-chair-designer.jpg` → Eero Saarinen
- `eames-lounge-chair-designer.jpg` → Charles and Ray Eames
- `wassily-chair-designer.jpg` → Marcel Breuer

All images are saved to: `/public/images/`

## Automated Fetching

The `fetch_designer_images.py` script automatically searches for designer portraits with real likeness and downloads them with the correct naming convention.

### Automatic Portrait Pipeline (used by `furniture_agent.py`)

When `furniture_agent.py` reaches the `designer` image slot it now runs a multi-step real-photo lookup **before** any AI image generation:

1. **Wikidata SPARQL** — queries the canonical P18 (image) property; most famous mid-century designers have a portrait recorded here.
2. **Wikimedia Commons search** — text search for `{designer name} portrait photograph` returning up to 10 candidates.
3. **Gemini Vision ranking** — downloads thumbnails and sends them to `gemini-1.5-flash` (multimodal) to visually identify which image is an actual portrait of the designer's face, not a sketch or building.
4. If a real photo is found it is downloaded, archived, and saved directly — `status: real_photo` in `provenance-generated.json`.
5. If no real photo is found, AI generation falls back to **Gemini Imagen → FAL** (OpenAI is skipped for this slot due to its stricter policies on portraits of real people).

### Prerequisites

```bash
# Install dependencies
python3 -m pip install -r requirements.txt
```

### Usage

**Fetch all missing designer images (interactive):**
```bash
python fetch_designer_images.py --all
```

This will:
1. Scan all MDX files in `src/content/blog/`
2. Extract the `designer` field from frontmatter
3. Search Wikimedia Commons for portrait images
4. Present options for you to select the best image
5. Download and save as `{chair-slug}-designer.jpg`

**Fetch for a specific chair:**
```bash
python fetch_designer_images.py --chair barcelona-chair --designer "Ludwig Mies van der Rohe"
```

**With AI enhancement for low-quality images:**
```bash
python fetch_designer_images.py --all --enhance
```

Note: Enhancement requires FAL_KEY in `.env` file.

## Manual Process

If you prefer to manually download designer images:

1. Search Wikimedia Commons: https://commons.wikimedia.org/
2. Look for public domain or CC-licensed portrait photographs
3. Download at least 800px width
4. Save to `/public/images/{chair-slug}-designer.jpg`
5. Add frontmatter to the MDX file:

```yaml
designerImage: "/images/{chair-slug}-designer.jpg"
designerBio: "Brief biography of the designer"
designerYears: "1886-1969"
```

## Image Quality Guidelines

- **Minimum resolution:** 800x800px (will be displayed at ~300px in sidebar)
- **Format:** JPEG preferred
- **License:** Public domain or CC-BY/CC-BY-SA
- **Content:** Portrait-style photograph showing the designer
- **Quality:** If image is low quality, use `--enhance` flag

## Wikimedia Commons Sources

Good search terms for finding designer portraits:
- `[Designer Name] portrait photograph`
- `[Designer Name] architect`
- `[Designer Name] designer`

Most mid-century designers have public domain or Creative Commons licensed portraits available.

## Current Status

Designer images that exist:
- ✅ `barcelona-chair-designer.jpg` (Ludwig Mies van der Rohe)
- ✅ `egg-chair-designer.jpg` (Arne Jacobsen - was placeholder, needs replacement)
- ✅ `tulip-chair-designer.jpg` (Eero Saarinen - was placeholder, needs replacement)

Designer images needed:
- ❌ `eames-lounge-chair-designer.jpg` (Charles and Ray Eames)
- ❌ `wassily-chair-designer.jpg` (Marcel Breuer)

## Syncing Images

### Sync Script

Use `sync_images.py` to automatically add existing images to MDX frontmatter:

```bash
# Check what's missing (dry run)
python sync_images.py egg-chair --dry-run

# Add missing images to frontmatter
python sync_images.py egg-chair

# Also insert images into post body
python sync_images.py egg-chair --insert-body

# Process all chairs
python sync_images.py --all
```

The script:
1. Scans `/public/images/` for `{chair-slug}-{slot}.jpg` files
2. Checks the MDX frontmatter for missing images
3. Adds them to the `images` array (or `designerImage`/`heroImage` fields)
4. Optionally inserts `<ImageWithMeta>` components in the post body

## Adding to MDX Files

Once you have the designer image, update the MDX frontmatter:

```yaml
---
title: "Barcelona Chair"
designer: "Ludwig Mies van der Rohe"
designerBio: "German-American architect and furniture designer, pioneer of modernist architecture. Known for the aphorism 'less is more' and his use of modern materials like industrial steel and plate glass."
designerYears: "1886–1969"
designerImage: "/images/barcelona-chair-designer.jpg"
era: "Modernist"
category: "Iconic Chairs"
---
```

The designer section will appear in the sidebar with the image, name, years, and bio.
