# Google Gemini Image Generation

This script automates image generation using Google's Gemini AI (Imagen) as an alternative to FAL.

## Setup

1. **Install the required package:**
   ```bash
   pip install google-genai
   ```

2. **Get your Google API key:**
   - Visit https://makersuite.google.com/app/apikey
   - Create a new API key
   - Add it to your `.env` file:
     ```
     GOOGLE_API_KEY=your_actual_key_here
     ```

## Usage

### Basic Usage (uses prompts from generated-prompts folder)

```bash
python generate_images_gemini.py wassily-chair
```

This will:
- Read prompts from `public/images/generated-prompts/wassily-chair/`
- Generate all 4 images (hero, detail-material, detail-structure, detail-silhouette)
- Save as PNG files in `public/images/`

### With Custom Prompts

```bash
python generate_images_gemini.py wassily-chair --custom-prompts my-prompts.json
```

**Example custom prompts file** (`my-prompts.json`):
```json
{
  "hero": "Simple prompt for hero image",
  "detail-material": "Simple prompt for material detail",
  "detail-structure": "Simple prompt for structure detail",
  "detail-silhouette": "Simple prompt for silhouette"
}
```

### With Reference Images

```bash
python generate_images_gemini.py wassily-chair --reference-images refs.json
```

**Example reference images file** (`refs.json`):
```json
{
  "hero": "https://commons.wikimedia.org/wiki/Special:FilePath/Image1.jpg",
  "detail-material": "https://example.com/ref2.jpg",
  "detail-structure": "https://example.com/ref3.jpg",
  "detail-silhouette": "https://example.com/ref4.jpg"
}
```

### Combined: Custom Prompts + Reference Images + Auto-update MDX

```bash
python generate_images_gemini.py wassily-chair \
  --custom-prompts my-prompts.json \
  --reference-images refs.json \
  --update-mdx
```

The `--update-mdx` flag will automatically update the `.mdx` file to use `.png` extensions.

### Generate Only Specific Slots

```bash
python generate_images_gemini.py wassily-chair \
  --slots hero detail-material \
  --custom-prompts simple-prompts.json
```

This only generates the hero and detail-material images.

## Example Workflow (What You Did Manually)

Here's how to automate what you did manually:

1. **Create a simple prompts file** when the generated ones don't work:
   ```json
   {
     "hero": "Wassily Chair, chrome steel and black leather, museum lighting",
     "detail-material": "Close-up of leather and steel connection, Wassily Chair",
     "detail-structure": "Bent tubular steel frame detail, Wassily Chair",
     "detail-silhouette": "Side profile of Wassily Chair showing cantilevered design"
   }
   ```

2. **Create a reference images file** with different refs for different slots:
   ```json
   {
     "hero": "https://commons.wikimedia.org/.../ref-001.jpg",
     "detail-material": "https://commons.wikimedia.org/.../ref-002.jpg",
     "detail-structure": "https://commons.wikimedia.org/.../ref-001.jpg",
     "detail-silhouette": "https://commons.wikimedia.org/.../ref-002.jpg"
   }
   ```

3. **Run the generation:**
   ```bash
   python generate_images_gemini.py wassily-chair \
     --custom-prompts simple-prompts.json \
     --reference-images my-refs.json \
     --update-mdx
   ```

4. **Done!** Images are saved as PNGs and the MDX file is updated.

## Options

- `--custom-prompts PATH`: Use custom prompts from a JSON file
- `--reference-images PATH`: Use reference images from a JSON file
- `--update-mdx`: Automatically update the MDX file to use .png extensions
- `--slots SLOT [SLOT...]`: Generate only specific slots
- `--format {png,jpg}`: Output format (default: png)

## Example Files

Check out:
- `example-custom-prompts.json` - Simple prompt examples
- `example-reference-images.json` - Reference image URL examples

## Tips

- **Simpler is better**: Gemini works well with shorter, clearer prompts
- **Different references**: Use different reference images for different detail shots
- **Rate limiting**: The script waits 2 seconds between generations to avoid rate limits
- **PNG format**: Gemini generates PNGs by default, which is what you wanted

## Troubleshooting

**"google-generativeai not found"**:
```bash
pip install google-generativeai
```

**"GOOGLE_API_KEY environment variable is required"**:
Add your key to `.env`:
```
GOOGLE_API_KEY=your_key_here
```

**Reference image download fails**:
The script will continue without the reference image. Check that URLs are accessible.
