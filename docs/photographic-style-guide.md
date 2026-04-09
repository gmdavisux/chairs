# Photographic Style Guide - Classic Furniture Archives

## Intent

A single, consistent visual language for generated and normalized images that feels museum-caliber, warm, and historically faithful.

## Core Requirements

### Lighting
- Soft, diffused warm illumination at approximately 2700-3000 K.
- Gentle highlights and subtle shadows.
- Avoid cool daylight, fluorescent cast, and dramatic high-contrast styling.

### Color and Mood
- Restrained warmth and natural color rendering.
- Moderate contrast preserving tactile detail.
- No artificial oversaturation or synthetic HDR appearance.

### Composition
- Furniture is the clear focal subject.
- Target subject occupancy: roughly 60-75 percent of frame.
- Preferred viewpoint: three-quarter or slight low-angle with minimal distortion.
- Keep clean negative space and avoid visual crowding.

### Environmental Context
- Use only when needed to anchor period authenticity.
- Context should be minimal, architectural, and subordinate to object readability.
- Limit context descriptions to one clause and no more than three structural features.

### Forbidden Elements
- People
- Decorative clutter and props (rugs, lamps, books, artwork, vases)
- Text overlays, logos, and watermarks
- Cartoonish or painterly rendering styles

## Historical Fidelity Rules

Generated or transformed images must preserve:
- signature silhouette and geometry
- plausible materials and finish
- visible joinery/hardware logic
- era-appropriate setting

Reject outputs that violate any of the above.

## Master Prompt Template

Use this structure for text-to-image generation:

Photorealistic museum-catalog photograph of [precise furniture description with designer, model, materials, colorway, and viewing angle]. The scene is lit with soft, diffused warm incandescent light at dusk (about 2800 K), producing gentle amber warmth and subtle natural shadows. [Optional minimal context clause with era-appropriate architecture and no more than three structural features.] Shallow depth of field with sharp texture detail on material grain, stitching, and hardware; natural color grading; clean negative space; zero extraneous props or distractions.

## Negative Prompt Baseline

harsh shadows, cool lighting, daylight, fluorescent, oversaturated colors, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, low resolution, blur, motion blur

## Refinement Prompt Template

Refine this image to the Classic Furniture Archives style: soft diffused warm illumination (2700-3000 K), natural color balance, enhanced material texture realism, and subtle dimensional shadows without altering object structure. If background replacement is requested, use a minimalist era-appropriate architectural setting and remove all extraneous objects. Preserve historical accuracy and signature geometry.

## Image-to-Image Parameter Guidance

Preferred strength/denoise range: 0.35-0.55.

- 0.35-0.42: conservative cleanup, highest structural preservation
- 0.43-0.50: balanced normalization and style alignment
- 0.51-0.55: stronger restyling, use only when source image quality is poor

## Slot-Specific Intent

- Hero: full object readability and iconic silhouette
- Detail Material: grain, leather, textile, or finish authenticity
- Detail Structure: joints, frame transitions, hardware logic
- Detail Silhouette: profile geometry and stance clarity
