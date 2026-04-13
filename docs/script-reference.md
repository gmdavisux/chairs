# Script Reference — Classic Furniture Archives

Quick-reference for every operational Python script in this project. Covers purpose, arguments, and which workflow step each script serves.

---

## Workflows at a Glance

### 1. Create a new page from scratch (fully automated)

```sh
python furniture_agent.py --plan          # Check backlog; choose the next page
python furniture_agent.py                 # Run the full pipeline for the next item
```

This single command does everything: research → article → image prompts → reference download → AI image generation → MDX frontmatter update. See [README.md](../README.md) for full setup.

---

### 2. Generate images for an existing page (manual AI Studio path)

Use this when you want to generate images by hand in [Google AI Studio](https://aistudio.google.com) instead of via the API.

```sh
# Step 1: produce a batch file with ready-to-paste prompts + reference URLs
python generate_aistudio_prompts.py barcelona-chair \
    --slots hero context silhouette designer \
    --output batch.txt

# Step 2: open batch.txt, paste each prompt into AI Studio, attach reference, save PNG
#         Save each PNG as: public/images/<slug>-<slot>.png

# Step 3: wire the MDX frontmatter to the new images
python update_mdx_images.py barcelona-chair
```

---

### 3. Generate images via the API (automated Gemini path)

```sh
FURNITURE_IMAGE_PROVIDER=google \
  python generate_images_gemini.py barcelona-chair \
    --use-reference-metadata \
    --slots hero context silhouette designer
```

Add `--update-mdx` to also rewrite frontmatter in the same run.

---

### 4. Regenerate specific slots (overwrite existing images)

The generation scripts always archive the previous version before overwriting, so reruns are safe.

```sh
# Regenerate only the hero and context slots
FURNITURE_IMAGE_PROVIDER=google \
  python generate_images_gemini.py barcelona-chair \
    --use-reference-metadata \
    --slots hero context
```

---

### 5. Update MDX after manually placing images

After copying images into `public/images/` by hand:

```sh
python update_mdx_images.py barcelona-chair          # default: .png
python update_mdx_images.py barcelona-chair --dry-run  # preview first
```

Or use the full sync to catch any slot that's already on disk but not in frontmatter:

```sh
python sync_images.py barcelona-chair --insert-body
```

---

### 6. Use reference images as stand-ins (no AI budget)

When AI generation isn't available or has failed, deploy the best downloaded reference images to the display slots:

```sh
python use_reference_images.py barcelona-chair            # automatic
python use_reference_images.py barcelona-chair --interactive  # pick per slot
python use_reference_images.py barcelona-chair --dry-run      # preview only
```

Or process references with basic PIL cleanup (no API calls):

```sh
python process_reference_simple.py barcelona-chair
```

Or enhance references with FAL img2img (requires FAL credentials):

```sh
python enhance_reference_images.py barcelona-chair
python enhance_reference_images.py barcelona-chair --copy-only  # skip AI, just copy
```

---

### 7. Insert `<ImageWithMeta>` components into article body

After images are in frontmatter but before the body references them:

```sh
python insert_image_slots.py barcelona-chair
python insert_image_slots.py barcelona-chair --dry-run
```

---

### 8. Fetch designer portrait images

```sh
python fetch_designer_images.py --all           # all articles
python fetch_designer_images.py --chair barcelona-chair
python fetch_designer_images.py --chair barcelona-chair --force   # overwrite existing
```

---

### 9. Audit image state across all articles

```sh
python sync_images.py --all --dry-run          # health check, no changes
python sync_images.py --all                    # sync all missing frontmatter entries
```

---

### 10. Diagnose available Gemini models

```sh
python list_gemini_models.py                   # lists models + supported methods
```

Useful when the API changes and you need to verify the current model name.

---

## Script Reference

### `furniture_agent.py`

Main autonomous pipeline. Runs CrewAI agents to research one furniture piece and produce a complete MDX article with image prompts, downloaded references, and generated images — one page per execution.

| Argument | Description |
|---|---|
| *(none)* | Build the next pending page from `backlog.json` |
| `--plan` | Show backlog status only; make no changes |

---

### `generate_images_gemini.py`

Generate images via Google Gemini (or FAL via `FURNITURE_IMAGE_PROVIDER=fal`). Reads prompts from `public/images/generated-prompts/<slug>/`. Archives every output under `public/images/generated/<slug>/YYYY-MM-DD-HHMMSS/` before deploying.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug, e.g. `barcelona-chair` |
| `--slots SLOT ...` | Restrict to specific slots: `hero silhouette context designer sketch` |
| `--use-reference-metadata` | Auto-load reference image URLs from `reference-metadata.json` |
| `--reference-images PATH` | JSON file `{slot: url}` with per-slot reference URLs |
| `--custom-prompts PATH` | JSON file `{slot: prompt}` overriding prompt files |
| `--update-mdx` | Also update MDX frontmatter after generation |
| `--format png\|jpg` | Output format (default: `png`) |

---

### `generate_aistudio_prompts.py`

Produces a formatted text batch file with ready-to-paste prompts and reference URLs for the Google AI Studio manual UI.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |
| `--slots SLOT ...` | Restrict to specific slots |
| `--output/-o PATH` | Write to file instead of stdout |
| `--include-style-guide` | Append full warm-lighting style guidance to each prompt |
| `--max-references INT` | Max reference URLs per slot (default: 5) |
| `--only-missing` | Skip slots where an image already exists on disk |

---

### `update_mdx_images.py`

After manually saving generated images as PNGs/JPGs, rewrites MDX frontmatter image paths to point to the new files.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |
| `--extension png\|jpg\|jpeg\|webp` | File extension to use (default: `png`) |
| `--dry-run` | Preview changes without writing |

---

### `use_reference_images.py`

Fallback when AI generation is unavailable. Reads `reference-metadata.json`, copies the best downloaded reference images into the four display slots, and updates MDX frontmatter with source/license metadata.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |
| `--interactive / -i` | Prompt for confirmation before each copy |
| `--dry-run` | Show the plan without copying |

---

### `insert_image_slots.py`

Ensures every slot listed in MDX frontmatter `images[]` has a corresponding `<ImageWithMeta>` component in the article body; inserts any that are missing.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |
| `--dry-run` | Preview without modifying files |

---

### `sync_images.py`

Scans `public/images/` for files matching `<slug>-<slot>.*`, adds missing entries to MDX frontmatter, and optionally inserts `<ImageWithMeta>` components into the body. General-purpose audit and sync tool.

| Argument | Description |
|---|---|
| `slug` | *(optional)* Single chair slug |
| `--all` | Process all MDX/MD articles |
| `--dry-run` | Preview without modifying files |
| `--insert-body` | Also insert ImageWithMeta components into the body |

---

### `process_reference_simple.py`

Zero-cost PIL-only processing. Takes downloaded reference images, composites them onto a clean neutral background, and deploys as display slot images. Writes `provenance-simple-edit.json`.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |

---

### `enhance_reference_images.py`

Sends reference images through FAL img2img to clean backgrounds and warm lighting while preserving the original chair. Produces `provenance-enhanced.json`.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |
| `--strength FLOAT` | Preservation strength 0.9–0.95 (default: 0.92; higher = less change) |
| `--copy-only` | Skip AI; copy best references directly without enhancement |

---

### `fetch_designer_images.py`

Fetches designer portrait images from Wikimedia Commons and saves to `public/images/designers/<slug>-designer.jpg`.

| Argument | Description |
|---|---|
| `--all` | Process all chairs found in `src/content/blog/` |
| `--chair SLUG` | Specific chair slug |
| `--designer NAME` | Designer name (must be paired with `--chair`) |
| `--enhance` | AI-upscale low-quality images via FAL |
| `--force` | Overwrite existing images |

---

### `generate_images_standalone.py`

Two-step LangChain + OpenAI pipeline: (1) AI-generates image prompts from MDX content, (2) generates images via FAL or OpenAI. Alternative to the Gemini path when you prefer OpenAI/FAL.

| Argument | Description |
|---|---|
| `slug` | Furniture piece slug |
| `--prompts-only` | Only generate prompt files; skip image generation |
| `--images-only` | Only generate images (prompt files must already exist) |

---

### `prepare_gemini_batch.py`

Earlier companion to `generate_aistudio_prompts.py`. Reads prompt files, checks existing images, finds reference images, and formats a batch document for AI Studio. Can also output raw JSON.

Use `generate_aistudio_prompts.py` for newer workflows; `prepare_gemini_batch.py` is the simpler predecessor.

---

### `list_gemini_models.py`

One-shot diagnostic. Connects to Google Gemini and prints every available model name with its supported generation methods. No arguments needed.

```sh
python list_gemini_models.py
```

---

### `image_archive.py`

Library module — not meant to be run directly. Provides the timestamped archive system used by all image generation scripts. Every generated image is archived under `public/images/generated/<slug>/YYYY-MM-DD-HHMMSS/` before being deployed to its display location.

Key public functions:
- `archive_and_deploy_image()` — archive + deploy a single image
- `create_archive_directory()` — make a timestamped archive dir
- `get_latest_archive_directory()` — find the most recent archive for a slug
- `list_archive_directories()` — list all archives for a slug

---

## Decision Tree: Which Script Do I Need?

```
Starting from zero → furniture_agent.py
                         │
                      Page exists, need images
                         │
              ┌──────────┴──────────────────┐
         Have API access?               No API access
              │                              │
    ┌─────────┴──────────┐          use_reference_images.py
    │                    │          process_reference_simple.py
 Gemini API         AI Studio
    │               (manual)
generate_images_gemini.py   generate_aistudio_prompts.py
    │                              → update_mdx_images.py
    └──────────┬──────────────────┘
               │
          Images exist, wire them up
               │
    sync_images.py / update_mdx_images.py / insert_image_slots.py
               │
          Need designer portrait
               │
    fetch_designer_images.py
```
