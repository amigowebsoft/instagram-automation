# ⚡ AI Instagram Automation System
### Powered by Google Antigravity 2.0

A fully autonomous AI-powered Instagram media operation that **researches, designs, writes, and publishes 5 premium AI news carousel posts every day at 9:00 AM** — zero manual effort required.

---

## 🏗️ Architecture

```
Antigravity 2.0 Sidecar (8:00 AM cron)
         │
         ▼
   main_pipeline.py  ←── Orchestrator
    ├── research_agent.py    (15 RSS feeds + Gemini ranking)
    ├── content_agent.py     (Gemini slide copy + captions)
    ├── carousel/generator.py (Pillow 1080×1350 slides)
    ├── publisher_agent.py   (Cloudinary + Instagram Graph API)
    └── storage/db.py        (SQLite persistence)
         │
         ▼
   dashboard/app.py  ←── Flask Web Dashboard (localhost:5000)
```

---

## 📋 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
copy .env.example .env
# Edit .env with your real values
```

### 3. Run setup
```bash
python setup.py
```

### 4. Test dry run (no Instagram posting)
```bash
python main_pipeline.py --dry-run
```

### 5. Launch dashboard
```bash
python dashboard/app.py
# Open: http://localhost:5000
```

### 6. Enable live posting
```
# In .env:
LIVE_MODE=true
```

---

## 🔑 Credentials Required

### Instagram Graph API
1. Go to [Meta Developer Portal](https://developers.facebook.com/)
2. Create an App → Add "Instagram Graph API" product
3. Connect your Instagram Business or Creator account
4. Generate a long-lived access token
5. Find your numeric User ID via Graph Explorer

```
IG_USER_ID=123456789
IG_ACCESS_TOKEN=EAABwzLixnjYBO...
```

### Google Gemini API
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key

```
GEMINI_API_KEY=AIzaSy...
```

### Cloudinary (Free Image Hosting)
1. Sign up at [cloudinary.com](https://cloudinary.com/users/register_free)
2. Go to Dashboard → copy your Cloud name, API Key, API Secret

```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdef...
```

---

## ⏰ Daily Schedule

| Time    | Action |
|---------|--------|
| 8:00 AM | RSS feed research across 15 sources |
| 8:05 AM | Gemini AI ranks and selects top 5 news |
| 8:15 AM | Content agent generates 5-slide copy + captions |
| 8:30 AM | Carousel generator renders 25 slides (1080×1350px) |
| 8:45 AM | Images uploaded to Cloudinary |
| 9:00 AM | All 5 carousels published to Instagram |

---

## 🎨 Carousel Design

Each post contains **5 premium slides**:

| Slide | Type | Content |
|-------|------|---------|
| 1 | **HOOK** | Gradient headline + emoji + teaser |
| 2 | **EXPLAIN** | Clear explanation + key insight card |
| 3 | **IMPACT** | 3 real-world impacts + big stat |
| 4 | **USE CASES** | 2×2 grid of use cases |
| 5 | **CTA** | Summary + engagement question + follow badge |

**Design specs:**
- Size: 1080 × 1350 px (4:5 Instagram portrait)
- Background: Deep navy → dark purple gradient
- Accents: Neon cyan `#00D4FF` + electric purple `#8B5CF6`
- Typography: Inter Black (headings) + Inter Regular (body)
- Effects: Glassmorphism cards, glow orbs, gradient text

---

## 📊 Dashboard Features

Access at `http://localhost:5000`

- **Live stats** — news fetched, posts published, total reach
- **Countdown timer** — time until next 9:00 AM auto-publish  
- **Top 5 news** — ranked list with viral/usefulness/innovation scores
- **Carousel previews** — click any post to see all 5 slides + caption
- **Publish log** — real-time status of every publish attempt
- **Analytics** — total likes, comments, saves, reach across all posts
- **Manual controls** — trigger dry run or live publish at any time

---

## 🤖 Automation Commands

```bash
# Full dry run (no Instagram posting)
python main_pipeline.py --dry-run

# Live run (posts to Instagram)
python main_pipeline.py --live

# Fetch analytics for today's posts
python main_pipeline.py --analytics

# Setup only (fonts + DB)
python main_pipeline.py --setup

# Test just the research agent
python agents/research_agent.py

# Test content generation
python agents/content_agent.py

# Test carousel rendering
python carousel/generator.py

# Verify credentials
python agents/publisher_agent.py
```

---

## 📁 Project Structure

```
H:\AgenticAI\
├── .env                    ← Your credentials (never commit!)
├── .env.example            ← Credentials template
├── requirements.txt        ← Python dependencies
├── main_pipeline.py        ← Daily automation orchestrator
├── setup.py                ← One-command setup
│
├── agents/
│   ├── research_agent.py   ← RSS fetch + Gemini ranking
│   ├── content_agent.py    ← Gemini content generation
│   └── publisher_agent.py  ← Cloudinary + Instagram API
│
├── carousel/
│   ├── generator.py        ← Pillow slide renderer
│   └── assets/fonts/       ← Inter font files
│
├── dashboard/
│   ├── app.py              ← Flask backend
│   ├── templates/index.html← Dashboard UI
│   └── static/             ← CSS + JS
│
├── storage/
│   ├── db.py               ← SQLite ORM
│   └── ai_news.db          ← Database (auto-created)
│
├── scheduler/
│   └── sidecar.json        ← Antigravity 2.0 cron config
│
└── output/posts/           ← Generated slides (by date)
```

---

## 🛠️ Troubleshooting

**Slides rendering as blank/fallback?**
→ Run `python setup.py --fonts` to download Inter font files

**Instagram API returns 400?**
→ Ensure your token has `instagram_content_publish` permission
→ Check your account is Business or Creator type

**Cloudinary upload fails?**
→ Verify `CLOUDINARY_CLOUD_NAME`, `API_KEY`, `API_SECRET` in `.env`

**Gemini returns empty content?**
→ Verify `GEMINI_API_KEY` is valid at aistudio.google.com
→ Check your Gemini API quota

**No news articles fetched?**
→ RSS feeds may be rate-limiting — the system will retry on next run
→ Fallback topics will be used if all feeds fail

---

## 📈 Scaling Tips

- **More accounts**: Duplicate the project folder with different `.env` files
- **More posts/day**: Increase the RSS sources in `research_agent.py`  
- **Custom brand**: Edit the color palette in `carousel/generator.py` (`COLORS` dict)
- **Custom watermark**: Set `IG_ACCOUNT_NAME` in `.env`
- **Custom hashtags**: Edit `HASHTAG_POOL` in `content_agent.py`

---

*Built with Google Antigravity 2.0 · Gemini 2.0 Flash · Meta Graph API · Cloudinary*
