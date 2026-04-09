# Classic Furniture Archives - Automation Requirements

## Purpose

Define the implementation contract for automated writing, image sourcing, image normalization, AI generation, provenance logging, and local commit behavior.

## Scope

Included:
- One page per execution
- Automated research and article drafting
- Automated reference-source discovery
- Automated image generation and normalization for four slot types
- Metadata and provenance updates
- Optional local auto-commit

Excluded:
- Automatic push to remote
- Automatic deployment/publication
- Multi-page unattended batch runs

## Run Contract

Each execution must:
1. Select exactly one pending page from backlog.
2. Generate one complete content file with valid frontmatter scaffold.
3. Generate or update image artifacts for required slots:
   - hero
   - detail-material
   - detail-structure
   - detail-silhouette
4. Write provenance metadata for all generated or transformed outputs.
5. Complete even when image steps fail, leaving explicit placeholder/proposed states.
6. Print a review URL and stop.

## Provider Policy

- The image pipeline must be provider-agnostic.
- Primary provider target: FLUX via fal.ai.
- Fallback provider target: OpenAI image API.
- Provider and model must be configurable via environment variables.
- Every output must record provider, model, and parameters used.

## Photographic Style Contract

All generated and refined assets must follow these requirements.

### Lighting
- Soft, diffused warm illumination in the 2700-3000 K range.
- No cool daylight, no fluorescent cast, no harsh contrast styling.

### Color and Tone
- Natural color grading with restrained saturation.
- Moderate contrast preserving texture detail and material realism.

### Subject and Framing
- Furniture remains primary subject (approximately 60-75 percent of frame).
- Preferred perspective: three-quarter or slight low-angle without distortion.
- Negative space should be intentional and clean.

### Context and Background
- Background is optional and subordinate to object readability.
- If included, it must be era-appropriate, architectural, and minimal.
- Context clause should name one canonical reference and no more than three structural features.

### Disallowed Elements
- People
- Decorative clutter (rugs, lamps, books, vases, artwork)
- Text overlays, logos, watermarks
- Cartoonish, painterly, or stylized render look

## Historical Fidelity Contract

Outputs must be rejected and regenerated when any of the following occurs:
- Defining silhouette or proportions are altered.
- Material identity is implausible for the documented piece.
- Joinery, hardware, or structural transitions are fabricated or incorrect.
- Scene context introduces dominant anachronistic or distracting elements.

## Prompt Envelope

Every generation request should follow this structure:
1. Subject identity block (designer, model, era, materials, colorway, viewpoint).
2. Lighting block (soft warm 2700-3000 K).
3. Optional minimal context block (era-appropriate architecture, max three features).
4. Texture and focus block (material detail, natural shadows, realistic depth of field).
5. Exclusion block (explicitly forbid clutter, people, text, logos).
6. Fidelity block (preserve authentic geometry/material behavior).

## Negative Prompt Baseline

Use this baseline where tooling supports negative prompts:

harsh shadows, cool lighting, daylight, fluorescent, over-saturated colors, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, low resolution, blur, motion blur

## Normalization and Refinement Rules

- Image-to-image refinement is allowed to align style and fidelity.
- Inpainting/background cleanup is allowed only if object truth is preserved.
- Preferred denoise/strength range: 0.35-0.55.
- Any deviation from default ranges must be logged in provenance.

## Provenance Requirements

For each image output, persist:
- slot id
- output file path
- source references used (if any)
- prompt and negative prompt
- provider and model
- generation/transform parameters
- timestamp
- content hash
- estimated cost
- review status
- rejection reason if failed QA

## Placeholder and Publication Rules

- Missing image source/license must not block page completion.
- Placeholder and proposed status labels must remain explicit in metadata and UI.
- Final review must convert provisional metadata to actual where available.

## Reference Bank vs Display Fallback

- The reference bank is broad and may include many source links or optional downloads for AI guidance and research.
- Non-AI display fallback must use only explicit slot selections, not the entire reference bank.
- Optional explicit slot manifest path: `public/images/generated-prompts/[slug]/selected-display-images.json`.

Example:

```json
{
   "hero": {
      "source": "Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Example.jpg",
      "license": "cc_by_sa",
      "origin": "public_domain"
   },
   "detail-structure": {
      "source": "Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Example-structure.jpg",
      "license": "cc_by_sa",
      "origin": "public_domain"
   }
}
```

## Local Commit Policy

- Maximum one local commit per run.
- Commit scope must include only artifacts produced by that run.
- No auto-push and no auto-deploy.
- Commit message should include slug and stage summary.

## Verification Checklist

A run is considered complete when:
1. Markdown/frontmatter schema is valid.
2. Required image slots exist or are explicitly placeholder state.
3. Provenance metadata file exists and is parseable.
4. Frontmatter image mappings match generated files.
5. Per-page cost summary is written.
6. Review URL is printed.

## Configuration Keys

Planned environment keys:
- FURNITURE_IMAGE_PROVIDER
- FAL_KEY
- FURNITURE_IMAGE_MODEL
- OPENAI_IMAGE_MODEL
- FURNITURE_IMAGE_SIZE
- FURNITURE_IMAGE_MAX_PER_PAGE
- FURNITURE_IMAGE_BUDGET_USD
- FURNITURE_IMAGE_TIMEOUT_SECONDS
- FURNITURE_AUTO_COMMIT
