# Complete FAL Prompt for Wassily Chair

## FAL API Endpoint
`fal-ai/flux/dev`

## API Configuration

### FAL Client Call
```python
fal_client.run(
    "fal-ai/flux/dev",
    arguments={
        "prompt": "[SEE BELOW]",
        "image_size": "square_hd",
        "num_inference_steps": 40,
        "guidance_scale": 3.5,
        "num_images": 1,
        "enable_safety_checker": False,
        "image_url": "[REFERENCE IMAGE URL]",
        "strength": 0.6  # Default from FURNITURE_IMAGE_STRENGTH env var
    }
)
```

## Reference Images

The system attempts to use one of these reference images (from Wikimedia):

1. **ref-001** (used for hero and detail-material slots):
   - Source: https://commons.wikimedia.org/wiki/File:Wassily_Chair_by_Marcel_Breuer,_reproduction,_1925,_chrome_covered_steel_and_belting_leather_-_University_of_Arizona_Museum_of_Art_-_University_of_Arizona_-_Tucson,_AZ_-_DSC08029.jpg
   - Direct URL: https://commons.wikimedia.org/wiki/Special:FilePath/Wassily_Chair_by_Marcel_Breuer%2C_reproduction%2C_1925%2C_chrome_covered_steel_and_belting_leather_-_University_of_Arizona_Museum_of_Art_-_University_of_Arizona_-_Tucson%2C_AZ_-_DSC08029.jpg

2. **ref-002** (used for detail-structure and detail-silhouette slots):
   - Source: https://commons.wikimedia.org/wiki/File:Marcel_Breuer_-_Wassily_Chair_-_Eileen_Gray_-_Adjustable_table_E-1027_.jpg
   - Direct URL: https://commons.wikimedia.org/wiki/Special:FilePath/Marcel_Breuer_-_Wassily_Chair_-_Eileen_Gray_-_Adjustable_table_E-1027_.jpg

---

## Slot 1: Hero Image

### Full Prompt
```
Photorealistic museum-catalog image of Wassily Chair by Marcel Breuer. Slot intent: hero. Marcel Breuer Wassily Chair (Model B3) from 1925, three-quarter view showing the iconic chrome-plated tubular steel frame with black leather straps forming the seat and backrest. Soft warm lighting at 2700K highlights the gleaming metal curves and rich leather texture. Clean minimal background with subtle era-appropriate architectural elements. Sharp focus on the chair's revolutionary cantilevered structure and Bauhaus geometry. Natural shadows emphasize the interplay between industrial steel and organic leather. Match the exact colors and materials from the reference images - chrome steel and black leather only. No people, no clutter, no text.

Use soft diffused warm light in the 2700-3000K range. Keep natural color grading, moderate contrast, realistic material textures, and clean negative space. Preserve historical fidelity: authentic silhouette, proportions, joinery, and era plausibility. CRITICAL: Use ONLY colors, materials, and finishes visible in the reference images. Do not invent or fabricate colors, materials, or structural details not present in references. No people or clutter.
```

### Negative Prompt
```
harsh shadows, cool lighting, daylight, fluorescent, over-saturated colors, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, low resolution, blur, motion blur, incorrect colors, wrong materials, fabricated details, invented finishes, altered proportions, modified geometry
```

### Reference Image URL
```
https://commons.wikimedia.org/wiki/Special:FilePath/Wassily_Chair_by_Marcel_Breuer%2C_reproduction%2C_1925%2C_chrome_covered_steel_and_belting_leather_-_University_of_Arizona_Museum_of_Art_-_University_of_Arizona_-_Tucson%2C_AZ_-_DSC08029.jpg
```

---

## Slot 2: Detail - Material

### Full Prompt
```
Photorealistic museum-catalog image of Wassily Chair by Marcel Breuer. Slot intent: detail-material. Extreme close-up of black belting leather strap on the Wassily Chair, showing the grain texture, natural patina, and slight creasing where it wraps around the tubular steel frame. Soft warm 2700K lighting reveals the material's subtle variations and authentic aged character. Shallow depth of field with the chrome steel tube edge just visible in soft focus. Natural shadows define the leather's dimensional quality and organic surface against the industrial metal. Use only the exact black leather color and chrome finish visible in reference images. No distracting background elements.

Use soft diffused warm light in the 2700-3000K range. Keep natural color grading, moderate contrast, realistic material textures, and clean negative space. Preserve historical fidelity: authentic silhouette, proportions, joinery, and era plausibility. CRITICAL: Use ONLY colors, materials, and finishes visible in the reference images. Do not invent or fabricate colors, materials, or structural details not present in references. No people or clutter.
```

### Negative Prompt
```
harsh shadows, cool lighting, daylight, fluorescent, over-saturated colors, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, low resolution, blur, motion blur, incorrect colors, wrong materials, fabricated details, invented finishes, altered proportions, modified geometry
```

### Reference Image URL
```
https://commons.wikimedia.org/wiki/Special:FilePath/Wassily_Chair_by_Marcel_Breuer%2C_reproduction%2C_1925%2C_chrome_covered_steel_and_belting_leather_-_University_of_Arizona_Museum_of_Art_-_University_of_Arizona_-_Tucson%2C_AZ_-_DSC08029.jpg
```

---

## Slot 3: Detail - Structure

### Full Prompt
```
Photorealistic museum-catalog image of Wassily Chair by Marcel Breuer. Slot intent: detail-structure. Detail view of the Wassily Chair's structural connection point where continuous bent tubular steel forms the cantilevered frame corner. Focus on the seamless chrome-plated steel tube radius and the leather strap attachment hardware. Soft warm 2700K lighting reveals the precision of the bent metal work and the industrial fastening method. Natural shadows emphasize the three-dimensional geometry and material transitions. Match the exact chrome finish and black leather from reference images. Clean background, sharp focus on the joinery and frame intersection that defines Breuer's revolutionary construction technique.

Use soft diffused warm light in the 2700-3000K range. Keep natural color grading, moderate contrast, realistic material textures, and clean negative space. Preserve historical fidelity: authentic silhouette, proportions, joinery, and era plausibility. CRITICAL: Use ONLY colors, materials, and finishes visible in the reference images. Do not invent or fabricate colors, materials, or structural details not present in references. No people or clutter.
```

### Negative Prompt
```
harsh shadows, cool lighting, daylight, fluorescent, over-saturated colors, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, low resolution, blur, motion blur, incorrect colors, wrong materials, fabricated details, invented finishes, altered proportions, modified geometry
```

### Reference Image URL
```
https://commons.wikimedia.org/wiki/Special:FilePath/Marcel_Breuer_-_Wassily_Chair_-_Eileen_Gray_-_Adjustable_table_E-1027_.jpg
```

---

## Slot 4: Detail - Silhouette

### Full Prompt
```
Photorealistic museum-catalog image of Wassily Chair by Marcel Breuer. Slot intent: detail-silhouette. Pure profile silhouette of the Wassily Chair from the side, capturing the distinctive cantilevered geometry and angular proportions that define its iconic form. Low-angle perspective against a clean neutral background with subtle 1920s Bauhaus architectural context - bare wall with geometric window detail. Soft warm 2700K lighting creates gentle rim light on the chrome tubular steel frame edges while preserving the strong graphic silhouette. The suspended leather seat and backrest planes are clearly visible in profile, showcasing Breuer's revolutionary floating construction. Use only chrome steel and black leather colors matching reference images exactly. No decorative elements, no people, sharp focus on the chair's revolutionary spatial geometry.

Use soft diffused warm light in the 2700-3000K range. Keep natural color grading, moderate contrast, realistic material textures, and clean negative space. Preserve historical fidelity: authentic silhouette, proportions, joinery, and era plausibility. CRITICAL: Use ONLY colors, materials, and finishes visible in the reference images. Do not invent or fabricate colors, materials, or structural details not present in references. No people or clutter.
```

### Negative Prompt
```
harsh shadows, cool lighting, daylight, fluorescent, over-saturated colors, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, low resolution, blur, motion blur, incorrect colors, wrong materials, fabricated details, invented finishes, altered proportions, modified geometry
```

### Reference Image URL
```
https://commons.wikimedia.org/wiki/Special:FilePath/Marcel_Breuer_-_Wassily_Chair_-_Eileen_Gray_-_Adjustable_table_E-1027_.jpg
```

---

## Additional Parameters

- **Image Size**: `square_hd` (1024x1024)
- **Inference Steps**: 40
- **Guidance Scale**: 3.5
- **Number of Images**: 1
- **Safety Checker**: Disabled
- **Strength**: 0.6 (for img2img guidance)

## Notes

- The `strength` parameter controls how much the output should adhere to the reference image (0.6 = moderate adaptation)
- The reference images are from Wikimedia Commons and serve as style/composition guides
- All four slots use the same negative prompt to ensure consistent quality requirements
- The FLUX/dev model is called via FAL's API endpoint
