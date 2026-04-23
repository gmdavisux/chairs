import sys
import os
import yaml
import re
from pathlib import Path

# Usage: python generate_csv_row.py <slug>
# Example: python generate_csv_row.py tulip-chair

BLOG_DIR = Path(__file__).parent / 'src' / 'content' / 'blog'
BASE_URL = 'https://chairs.usersimple.com'
PINTEREST_BOARD = 'Classic Furniture Archives'

# Helper to parse frontmatter from MDX
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---', re.DOTALL)

def parse_frontmatter(mdx_path):
    with open(mdx_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError(f'No frontmatter found in {mdx_path}')
    frontmatter = yaml.safe_load(match.group(1))
    return frontmatter

def csv_escape(val):
    if val is None:
        return ''
    val = str(val)
    # Only quote if necessary, and escape quotes by doubling them
    if any(c in val for c in [',', '"', '\n']):
        val = '"' + val.replace('"', '""') + '"'
    return val

def main():
    if len(sys.argv) != 2:
        print('Usage: python generate_csv_row.py <slug>')
        sys.exit(1)
    slug = sys.argv[1]
    mdx_path = BLOG_DIR / f'{slug}.mdx'
    if not mdx_path.exists():
        print(f'File not found: {mdx_path}')
        sys.exit(1)
    fm = parse_frontmatter(mdx_path)

    # Title: title (designer - yearDesigned)
    designer = (fm.get('designer') or '').strip()
    year = str(fm.get('yearDesigned') or '').strip()
    base_title = fm['title']
    if designer and year:
        title = f'{base_title} ({designer} - {year})'
    elif designer:
        title = f'{base_title} ({designer})'
    elif year:
        title = f'{base_title} ({year})'
    else:
        title = base_title

    # Media URL: heroImage
    hero_image = fm.get('heroImage', '')
    media_url = BASE_URL + hero_image if hero_image.startswith('/') else hero_image

    # Pinterest board
    pinterest_board = PINTEREST_BOARD

    # Thumbnail: empty
    thumbnail = ''

    # Description: from frontmatter
    description = fm.get('description', '')

    # Link: /blog/<slug>
    link = f'{BASE_URL}/blog/{slug}'

    # Publish date
    pub_date = fm.get('pubDate', '')

    # Keywords: comma separated
    keywords = fm.get('keywords', [])
    if isinstance(keywords, list):
        keywords = ', '.join([k.strip() for k in keywords if k and str(k).strip()])
    else:
        keywords = str(keywords).strip()

    # Always quote description, and quote any field with comma, quote, or newline
    def csv_escape_force(field, force_quote=False):
        if field is None:
            return ''
        field = str(field)
        needs_quote = force_quote or any(c in field for c in [',', '"', '\n'])
        if needs_quote:
            field = field.replace('"', '""')
            return f'"{field}"'
        return field

    row = [
        csv_escape_force(title),
        csv_escape_force(media_url),
        csv_escape_force(pinterest_board),
        csv_escape_force(thumbnail),
        csv_escape_force(description, force_quote=True),
        csv_escape_force(link),
        csv_escape_force(pub_date),
        csv_escape_force(keywords)
    ]
    print(','.join(row))

if __name__ == '__main__':
    main()
