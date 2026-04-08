# Classic Furniture Archives

A slow-growing, authoritative static website documenting timeless furniture designs — built with Astro and deployed to GitHub Pages. One beautifully crafted page at a time.

> **Editorial standard:** Every page reads like a high-end design museum catalog — warm, expert, accurate, properly cited. See [site_concept.md](site_concept.md) for the full editorial constitution.

---

## How to Run the Furniture Agent

The furniture agent is an autonomous CrewAI pipeline that researches and writes one complete furniture archive page per execution. It is deliberately slow and manual — **one page per run** — so you stay within Copilot quota limits and can review every page before it goes live.

### 1. Get a Tavily API key (free)

The Researcher agent uses [Tavily](https://tavily.com) for web search. The free tier (1,000 searches/month) is more than enough for this workflow.

1. Go to [app.tavily.com](https://app.tavily.com) and sign up
2. Copy your API key from the dashboard

### 2. Set up your `.env`

Copy the example file and fill in your keys:

```sh
cp .env.example .env
```

Then open `.env` and choose **one** LLM provider:

**Option A — Standard OpenAI API** (default):
```sh
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

**Option B — GitHub Models endpoint** (routes through your Copilot subscription, no separate OpenAI billing):
```sh
GITHUB_MODELS=1
GITHUB_TOKEN=github_pat_...   # needs Models read permission
TAVILY_API_KEY=tvly-...
```

To get a GitHub token: Settings → Developer settings → Personal access tokens → Fine-grained → enable **Models** (read).

### 3. Set up the Python environment

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the planner first

Initialises `backlog.json` from the default 40-page list and shows you what's queued:

```sh
python furniture_agent.py --plan
```

Sample output:
```
Backlog: 40 total — 1 done, 39 pending.
Next up: Barcelona Chair  [barcelona-chair]
Queue preview: wassily-chair, tulip-chair, egg-chair, wishbone-chair, le-corbusier-lc2
```

### 5. Build the next page

```sh
python furniture_agent.py
```

The agent runs five sequential steps: **Plan → Research → Write → Image Prompts → Publish**. When complete:

```
✅ PAGE COMPLETE: barcelona-chair — Review at http://localhost:4321/blog/barcelona-chair
```

Review the page in the browser, check the citations, then run again for the next one.

### 6. Review and iterate

- **Article:** `src/content/blog/[slug].md` — edit freely before deploying
- **Image prompts:** `public/images/generated-prompts/[slug]/` — seven `.txt` files ready to paste into DALL-E, Midjourney, Firefly, or any image generator
- **Backlog status:** `backlog.json` — reorder or add pages by editing this file directly

### Giving feedback to the agent

The agent reads [site_concept.md](site_concept.md) at the start of every run. To change tone, add taxonomy terms, adjust the page structure, or set new editorial standards — just edit that file. Changes take effect on the next execution.

Examples of useful edits:
- Add a new era or category to the taxonomy
- Tighten the word-count target
- Require a specific citation format
- Add a new H2 section to every page (e.g. "Collector's Notes")

### Estimated cost

| Provider | Model | Cost per page (est.) |
|---|---|---|
| OpenAI API | gpt-5.4-mini | ~$0.01–0.03 |
| GitHub Models | gpt-5.4-mini | Included in Copilot quota |

gpt-5.4-mini is billed at **0.33×** the standard GPT-4 mini rate. A full run of the 40-page backlog costs roughly $0.40–$1.20 via the OpenAI API, or essentially free via GitHub Models against your Copilot subscription.

> **Quota note:** The agent is designed to run one high-quality page per manual execution so we stay within Copilot quota limits. Never run it in a loop or with automated scheduling unless you have confirmed your quota headroom first.

### Recommended next page after the Eames Lounge Chair

**Barcelona Chair (1929) by Ludwig Mies van der Rohe** — slug: `barcelona-chair`

It is the ideal second page because:
- It predates the Eames by 27 years and anchors the Modernist era, giving the archive historical depth immediately
- Mies and Eames are the two designers most readers cite first when thinking about iconic chairs — having both early establishes the archive's authority
- The Barcelona Chair has exceptional source material: the 1929 Barcelona Pavilion, MoMA collection, Knoll production records, and rich material history (original pigskin → aniline leather)
- Its steel X-frame and hand-welded construction make for a technically compelling craft section that contrasts nicely with the Eames's plywood story


---

## Site Features

- Astro static site with Content Collections (`src/content/blog/`)
- Tailwind CSS + custom warm-neutral theme (amber accents, serif headings)
- Two-column article layout: prose + sticky sidebar on desktop
- RSS feed, sitemap, SEO meta tags
- 100/100 Lighthouse performance target

## Project Structure

```text
chairs/
├── src/
│   ├── content/blog/        ← Published Markdown articles
│   ├── layouts/BlogPost.astro
│   ├── pages/
│   └── styles/global.css
├── public/
│   └── images/
│       └── generated-prompts/[slug]/  ← Image prompts from agent
├── furniture_agent.py       ← Autonomous page builder
├── site_concept.md          ← Editorial constitution (agent reads this)
├── backlog.json             ← Page queue (auto-created on first --plan run)
├── requirements.txt         ← Python dependencies
├── .env.example             ← Copy to .env and fill in keys
└── astro.config.mjs
```

## Setting up the Python Virtual Environment

The furniture agent requires **Python 3.10 or later** — `crewai` uses union type syntax (`X | Y`) that Python 3.9 does not support. macOS ships with Python 3.9; install 3.11 first if needed:

```sh
brew install python@3.11
```

Then create and activate the venv:

```sh
# 1. Create the virtual environment with Python 3.11
python3.11 -m venv .venv

# 2. Activate it (macOS / Linux)
source .venv/bin/activate

# 3. Install all Python dependencies
pip install -r requirements.txt
```

You'll need to re-activate the venv in every new terminal session before running the agent:

```sh
source .venv/bin/activate
```

**Selecting the interpreter in VS Code:**
1. Open the Command Palette (`Cmd+Shift+P`)
2. Run **Python: Select Interpreter**
3. Choose the entry showing `.venv` — it will look like `Python 3.x.x ('.venv': venv)`

VS Code will then use this interpreter automatically for any Python file or integrated terminal in this workspace.

---

## Astro Commands

All commands are run from the root of the project:

| Command               | Action                                     |
| :-------------------- | :----------------------------------------- |
| `npm install`         | Install dependencies                       |
| `npm run dev`         | Start local dev server at `localhost:4321` |
| `npm run build`       | Build production site to `./dist/`         |
| `npm run preview`     | Preview production build locally           |

## Credit

This theme is based off of the lovely [Bear Blog](https://github.com/HermanMartinus/bearblog/).
