# Copilot Instructions for Chairs Project

## Core Principles

When fixing problems in this project:
1. Fix the immediate issue
2. Update the code/script to prevent recurrence
3. Document the pattern in this file under "Known Recurring Issues"
4. Update `/memories/repo/` memory files if it's a workflow-specific detail

When the user reports a recurring problem:
1. Search for the root cause in the codebase
2. Fix it permanently in the script/code
3. Add prevention documentation here
4. Show the user what was learned and how it won't recur

## Project-Specific Rules

### Content Creation
- Use JSX comments `{/* */}` in MDX files, never HTML comments `<!-- -->`
- All generated images must include provenance metadata
- Follow photographic-style-guide.md for image generation parameters
  - Fuller tonal range (deep shadows to clean highlights) for better material definition
  - Warm museum lighting (2700-3000K) but with rich contrast
  - Avoid flat/muddy mid-tones, blown highlights, or crushed blacks

### Python Scripts
- Always use the virtual environment at `.venv/`
- Image generation scripts must handle missing prompt files gracefully
- When fixing recurring issues, update both the script AND this instructions file

### Helper Scripts
- `furniture_agent.py` - Main content generation pipeline
- `use_reference_images.py <slug>` - Swap placeholders for downloaded references
- `generate_images.py <slug>` - AI image generation (Gemini/FAL)
- `update_mdx_images.py <slug>` - Update frontmatter after manual generation

### Astro/MDX Development
- Frontmatter must be valid YAML
- Image paths must be relative to `public/` directory

## Known Recurring Issues

### Issue #1: Placeholder images with no clear next steps
**Problem:** After `furniture_agent.py` runs, images are placeholders even when reference images were downloaded or AI generation failed. User doesn't know how to replace them.

**Root cause:** Image generation (Phase 4) is non-blocking. When it fails or isn't configured, the script completes successfully but leaves placeholders in place.

**Prevention:** 
- Add end-of-run summary showing which images succeeded vs fell back vs failed
- Print next-step instructions when placeholders remain
- Provide command to swap placeholders for downloaded references

**Script improvements needed:**
- Enhanced final status report in `run_build()`
- Helper script: `use_reference_images.py <slug>` to swap placeholders for references
- Document the reference→placeholder workflow in README

### Issue #2: MDX syntax errors from HTML comments
**Problem:** HTML comments `<!-- ... -->` in MDX files cause Astro build failures.

**Root cause:** MDX processes HTML comments as JSX, which doesn't support HTML comment syntax.

**Prevention:**
- Always use JSX comments `{/* ... */}` in MDX files
- The Writer agent already knows this (it's in the task description)
- When manually editing MDX, never use HTML comment syntax

**Status:** ✅ Already addressed in furniture_agent.py task descriptions (see line ~570)

### Issue #3: Missing image metadata after generation
**Problem:** Even after AI generation succeeds, frontmatter sometimes still shows "TBD" and "unknown".

**Root cause:** `_apply_image_metadata()` updates origin/license/source but not caption or altStatus.

**Prevention:**
- When generation succeeds, also update `altStatus: actual` and consider generating proper captions
- The current implementation only updates source/license/origin fields

**Script improvement needed:**
- Enhance `_apply_image_metadata()` to also set altStatus and optionally generate captions from prompts

---

*Add new rules by editing this file. Copilot will read it automatically.*
