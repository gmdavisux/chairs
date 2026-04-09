# Gemini Image Generation - Quick Reference

## Most Common Commands

### Prepare batch for manual generation (what you did)
```bash
python prepare_gemini_batch.py wassily-chair --simple --output batch.txt
# Then manually generate in AI Studio
python update_mdx_images.py wassily-chair
```

### Fully automated generation (if you have API)
```bash
python generate_images_gemini.py wassily-chair --update-mdx
```

### With custom simple prompts
```bash
# Create prompts.json with your simple prompts
python generate_images_gemini.py wassily-chair \
  --custom-prompts prompts.json \
  --update-mdx
```

### With different reference images per slot
```bash
# Create refs.json with URL mappings
python prepare_gemini_batch.py wassily-chair --output batch.txt
# Edit batch.txt, use different refs for each slot
# Generate manually, then:
python update_mdx_images.py wassily-chair
```

### Generate only specific images
```bash
python generate_images_gemini.py wassily-chair \
  --slots hero detail-material
```

### Check status
```bash
python update_mdx_images.py wassily-chair --dry-run
```

## File Formats

### Custom Prompts JSON
```json
{
  "hero": "Simple prompt for hero",
  "detail-material": "Simple prompt for material",
  "detail-structure": "Simple prompt for structure",
  "detail-silhouette": "Simple prompt for silhouette"
}
```

### Reference Images JSON
```json
{
  "hero": "https://example.com/ref1.jpg",
  "detail-material": "https://example.com/ref2.jpg",
  "detail-structure": "https://example.com/ref3.jpg",
  "detail-silhouette": "https://example.com/ref4.jpg"
}
```

## Setup

### First time
```bash
pip install google-generativeai pyyaml
echo "GOOGLE_API_KEY=your_key" >> .env
```

### Get API key
https://makersuite.google.com/app/apikey
