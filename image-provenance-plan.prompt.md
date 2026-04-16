## Plan: Image Provenance and Placeholders

Add explicit image provenance metadata (license/domain/source/origin), render visible credit placeholders when metadata is missing, and support inline image attribution using MDX figure components so posts can distinguish public-domain, licensed, and AI-generated assets.

**Steps**
1. Phase 1: Schema and data model (blocks all later steps)
- Extend blog frontmatter schema in /Users/garydavis/Sites/chairs/src/content.config.ts with hero metadata and an inline image registry.
- Recommended fields: heroImageCaption, heroImageSource, heroImageLicense, heroImageOrigin; plus images[] entries with id, src, alt, caption, source, license, origin.
- Require meaningful alt text for every image slot, including placeholders. Add an altStatus field with values pending or actual so the system can track whether the description is anticipatory or image-verified.
- Restrict license/origin values via enums to keep data consistent.

2. Phase 2: Hero rendering and placeholder policy (depends on 1)
- Update /Users/garydavis/Sites/chairs/src/layouts/BlogPost.astro to read new hero metadata and render a credit strip below hero image.
- Implement placeholder labels in UI when values are absent (Source: TBD, License: TBD, Origin: TBD) per user preference.
- Add visual status treatment for origin values (public domain, licensed, AI generated, placeholder).

3. Phase 3: Inline image attribution now (depends on 1)
- Add a reusable figure component in /Users/garydavis/Sites/chairs/src/components to render image + caption + source + license + origin from an image id.
- Update /Users/garydavis/Sites/chairs/src/pages/blog/[...slug].astro to pass the post image registry into content rendering components.
- Use MDX for posts requiring inline metadata (existing loader already supports md and mdx).

4. Phase 4: Generator alignment (parallel with 2 after 1; blocks automation completeness)
- Update /Users/garydavis/Sites/chairs/furniture_agent.py output instructions so generated posts include hero metadata defaults and an initial images[] registry scaffold.
- Keep publish-first behavior and placeholders so a page is never blocked by image sourcing.
- Ensure placeholders include a descriptive alt candidate, for example detail of visible screws at the pad ends on early Eames lounge chairs, and mark it as pending until replaced with a verified image.
- Continue non-blocking public-domain discovery output; map discovered URLs into source/license/origin fields during later enrichment.

5. Phase 5: Content migration and templates (depends on 2 and 3)
- Add metadata to existing representative posts first (for example Barcelona and Eames posts), then migrate others incrementally.
- For markdown-only posts, either keep hero-only metadata or convert selected posts to MDX when inline attribution is needed.

6. Phase 6: Build guards and validation (depends on 1 and 4)
- Add validation checks that fail fast on invalid enum values but allow missing values that intentionally display placeholders.
- Add a lightweight script or content check to report posts missing source/license/origin before publish.

**Relevant files**
- /Users/garydavis/Sites/chairs/src/content.config.ts — Extend blog schema with hero and inline image provenance fields.
- /Users/garydavis/Sites/chairs/src/layouts/BlogPost.astro — Render hero credit metadata and placeholder labels.
- /Users/garydavis/Sites/chairs/src/pages/blog/[...slug].astro — Wire MDX components for inline figures with metadata.
- /Users/garydavis/Sites/chairs/astro.config.mjs — Verify MDX integration behavior remains compatible after component wiring.
- /Users/garydavis/Sites/chairs/src/components (new figure component) — Centralize inline attribution rendering.
- /Users/garydavis/Sites/chairs/furniture_agent.py — Emit metadata scaffold and keep publish-first workflow.
- /Users/garydavis/Sites/chairs/public/images/generated-prompts/*/public-domain-sources.txt — Input source list for provenance enrichment.

**Verification**
1. Run Astro content/type checks and confirm schema accepts new fields while still allowing placeholder values.
2. Open at least one post with full metadata and one with missing metadata; verify visible placeholder labels render correctly.
3. Validate hero image credit block displays source/license/origin and labels public-domain assets distinctly.
4. Validate inline MDX figure rendering shows caption and provenance badges consistently on desktop and mobile.
5. Run python furniture_agent.py once and confirm generated post includes metadata scaffold and does not fail page creation when image sourcing fails.
6. Confirm every image record has non-generic alt text and that altStatus transitions from pending to actual when the final image is selected.

**Decisions**
- License field style: single license string (enum-constrained).
- Placeholder policy: show explicit placeholder labels in UI when metadata is missing.
- Inline metadata scope: included now via MDX component path.
- Alt text policy: placeholders must carry meaningful pending alt text; finalized images must have actual alt text reviewed against the image content.
- Scope boundary: this plan adds metadata and rendering; it does not auto-download or legally verify image licenses from third-party sites.

**Further Considerations**
1. Origin taxonomy recommendation: public_domain, cc, rights_reserved, original, placeholder.
2. Migration strategy recommendation: convert only posts that need inline attribution to MDX first, keep others in Markdown.
3. Editorial workflow recommendation: require source URL + license at draft review, allow placeholders only in early generation runs.