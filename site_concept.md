# Classic Furniture Archives — Site Concept

## Mission

Build a beautiful, authoritative, slow-growing static website about timeless furniture designs using Astro + GitHub Pages. This is not a shopping aggregator or a trend publication — it is a permanent digital archive built to the standard of a high-end design museum catalog, meant to outlast the individual pieces it documents.

**Goal:** One beautifully crafted page at a time, each authoritative enough to be cited, distinctive enough to be shared, honest enough to be trusted.

---

## Tone & Voice

**Warm, expert storytelling.** Every article reads like it was written by a senior contributor to *Domus*, *Wallpaper\**, or the curatorial notes for a retrospective at the Vitra Design Museum — human, passionate, accurate, and never condescending.

- Write for the curious generalist as much as the design professional
- Prefer narrative over list-making; prefer story over specification
- Cite primary sources: exhibition records, manufacturer statements, original designer interviews, museum collection databases
- Never fabricate dates, quotes, or award histories
- Acknowledge uncertainty honestly ("widely attributed to…" / "the exact date is disputed") rather than inventing false precision
- Avoid filler superlatives ("iconic," "revolutionary," "groundbreaking") unless immediately justified by specific evidence

---

## Page Anatomy

Every page follows this structure consistently.

### Frontmatter (YAML)

```yaml
title: "Full descriptive title"
description: "One sentence, 100–160 characters, written for search and sharing."
pubDate: YYYY-MM-DD
heroImage: /images/[slug]-hero.jpg
designer: "Full designer name(s)"
era: "Era label"
category: "Category label"
```

### Body Structure

1. **Hook paragraph** (no heading): An arresting opening scene, quoted moment, or unexpected fact — 100–200 words that earns the reader's attention before any heading appears. Place the reader *in the room* with the object or the designer.

2. **H2: The Concept** — What problem was being solved, and for whom? What was the cultural and design context? What precedent did the designer react against?

3. **H2: The Design** — What did they make, and why does every decision matter? Materials, proportions, signature elements, visual logic. Describe it as if the reader has never seen it.

4. **H2: The Craft / The Making** — Manufacturing process, material sourcing, production history, the specific challenges solved. Include technical details that reward careful reading.

5. **H2: Meet the Designer** — Focused biography anchored to this specific piece. Not a Wikipedia summary — a portrait of the person at the moment this object was made.

6. **H2: Why It Endures** (or "The Legacy") — Cultural reception, museum collections, pop-culture appearances, critical reassessment, the aftermarket, what it says about its era now that we have distance.

7. **Affiliate placeholder** (HTML comment at end of body):
   `<!-- AFFILIATE: Original/authenticated replica purchase links -->`

8. **References section**: Numbered list of formatted citations — source name, author if known, URL or archive location.

### Word Count

1800–2200 words per article. Long enough to be authoritative; short enough to be read in one sitting without losing the thread.

---

## Taxonomy

### Eras
- Arts & Crafts (1880–1920)
- Bauhaus (1919–1933)
- Modernist (1925–1950)
- Mid-Century Modern (1945–1969)
- Danish Modern (1940–1975)
- Functionalism (1930–1960)
- Space Age (1960–1975)
- Pop Design (1965–1975)
- Post-Modern (1978–1995)
- Late Modern (1970–1995)
- Contemporary Classics (2000–present)

### Categories
- Iconic Chairs
- Dining Chairs
- Lounge Chairs
- Chaise Longues
- Rocking Chairs
- Soft Seating (beanbags, ottomans, pods)
- Wire & Metal
- Space Age
- Avant-Garde
- Arts & Crafts
- Sofas
- Tables (key pieces only)
- Contemporary Classics

---

## Imagery Standards

Every page has four images:

| Image | Purpose | Generation approach |
|---|---|---|
| Hero shot | Full object, studio white seamless, museum lighting | DALL-E / Midjourney prompt |
| Detail 1 | Primary material close-up (grain, leather, weave) | DALL-E / Midjourney prompt |
| Detail 2 | Structural joint, hardware, or base | DALL-E / Midjourney prompt |
| Detail 3 | Signature silhouette or profile view | DALL-E / Midjourney prompt |

All prompts saved to `public/images/generated-prompts/[slug]/prompts.json`.

Three public-domain reference queries per page targeting: Wikimedia Commons, Library of Congress, museum digital collections (MoMA, V&A, Cooper Hewitt, Vitra Design Museum archive).

---

## Content Standards

### Facts & Citations
- All manufacture dates, designer birth/death years, manufacturer names, exhibition prizes, and museum acquisitions must be sourced
- Speculative or contested claims must be marked explicitly
- Inline citations use `[1]`, `[2]` format throughout the body
- References section uses numbered list with full source details

### Related Links
- Every page should reference 2–4 related pieces by designer, era, or category
- Links use the slug format: `/blog/[slug]`
- Never link to a page that has not yet been published — cross-check `backlog.json` status

### Affiliate Strategy
- One placeholder block per page at end of body
- Authenticated manufacturers only: Vitra, Herman Miller, Carl Hansen & Søn, Fritz Hansen, Knoll, Artek, Cassina, Tecta, ClassiCon
- Never recommend unlicensed reproductions or counterfeits

---

## Agent Operating Principles

1. **One page per execution** — the agent builds one excellent page and stops
2. **Never duplicate** — check `src/content/blog/` for existing slugs before writing anything
3. **Backlog is truth** — `backlog.json` is the canonical record of what is published, pending, and in progress
4. **Quality over speed** — if research is thin, run additional searches before writing
5. **Reviewable output** — every completed page prints its localhost preview URL so a human can review before deployment
6. **Graceful degradation** — if a tool call fails, log the error clearly rather than silently producing incomplete content
7. **Respect the voice** — every page should read as if it belongs alongside the Eames Lounge Chair piece already on the site

---

## Sample Backlog Priorities (First 10)

1. Barcelona Chair — Mies van der Rohe (1929)
2. Wassily Chair — Marcel Breuer (1925)
3. Tulip Chair — Eero Saarinen (1956)
4. Egg Chair — Arne Jacobsen (1958)
5. Wishbone Chair — Hans J. Wegner (1949)
6. LC2 Grand Confort — Le Corbusier, Jeanneret & Perriand (1928)
7. Diamond Chair — Harry Bertoia (1952)
8. Ball Chair — Eero Aarnio (1963)
9. Paimio Chair — Alvar Aalto (1932)
10. Womb Chair — Eero Saarinen (1948)

---

*This document is the agent's editorial constitution. It must be read at the start of every run.*
