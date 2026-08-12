"""
agents/research_agent.py
AI News Research Agent
Fetches latest AI news from multiple RSS sources, scores them with Gemini,
and returns the top 5 most viral and impactful updates.
"""

import os
import json
import time
import feedparser
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

load_dotenv()
_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))

# ─── RSS Feed Sources ──────────────────────────────────────────────────────────
RSS_FEEDS = [
    # Tech & AI News
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "source": "TechCrunch AI"},
    {"url": "https://venturebeat.com/category/ai/feed/", "source": "VentureBeat AI"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "source": "The Verge AI"},
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "source": "Ars Technica"},
    {"url": "https://www.wired.com/feed/category/business/ai/rss", "source": "Wired AI"},
    # Google News AI searches
    {"url": "https://news.google.com/rss/search?q=OpenAI+ChatGPT&hl=en-US&gl=US&ceid=US:en", "source": "Google News: OpenAI"},
    {"url": "https://news.google.com/rss/search?q=Google+Gemini+AI&hl=en-US&gl=US&ceid=US:en", "source": "Google News: Gemini"},
    {"url": "https://news.google.com/rss/search?q=Claude+Anthropic+AI&hl=en-US&gl=US&ceid=US:en", "source": "Google News: Claude"},
    {"url": "https://news.google.com/rss/search?q=DeepSeek+AI+2025&hl=en-US&gl=US&ceid=US:en", "source": "Google News: DeepSeek"},
    {"url": "https://news.google.com/rss/search?q=Meta+AI+LLM&hl=en-US&gl=US&ceid=US:en", "source": "Google News: Meta AI"},
    {"url": "https://news.google.com/rss/search?q=Midjourney+AI+image&hl=en-US&gl=US&ceid=US:en", "source": "Google News: Midjourney"},
    {"url": "https://news.google.com/rss/search?q=AI+agents+automation+2025&hl=en-US&gl=US&ceid=US:en", "source": "Google News: AI Agents"},
    {"url": "https://news.google.com/rss/search?q=AI+tools+launch+startup&hl=en-US&gl=US&ceid=US:en", "source": "Google News: AI Tools"},
    {"url": "https://news.google.com/rss/search?q=Runway+ElevenLabs+AI+video&hl=en-US&gl=US&ceid=US:en", "source": "Google News: AI Video"},
    {"url": "https://news.google.com/rss/search?q=Microsoft+Copilot+AI&hl=en-US&gl=US&ceid=US:en", "source": "Google News: Microsoft AI"},
]

# Keywords that boost viral score
VIRAL_KEYWORDS = [
    'launch', 'released', 'new', 'breakthrough', 'revolutionary', 'first',
    'free', 'open source', 'beats', 'outperforms', 'surpasses', 'record',
    'billion', 'million users', 'viral', 'trending', 'game-changing',
    'gpt-5', 'gemini', 'claude', 'deepseek', 'sora', 'dall-e'
]


def fetch_rss_feeds() -> list[dict]:
    """Fetch articles from all RSS feeds. Returns raw article list."""
    articles = []
    seen_urls = set()
    seen_titles = set()
    cutoff = datetime.now() - timedelta(hours=36)  # Only last 36 hours

    for feed_info in RSS_FEEDS:
        try:
            print(f"[Research] Fetching: {feed_info['source']}")
            feed = feedparser.parse(feed_info['url'])
            
            for entry in feed.entries[:8]:  # Max 8 per source
                url = getattr(entry, 'link', '')
                title = getattr(entry, 'title', '').strip()
                
                if not title or len(title) < 10:
                    continue
                    
                if url in seen_urls or title.lower() in seen_titles:
                    continue
                    
                seen_urls.add(url)
                seen_titles.add(title.lower())

                # Parse publish date
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                # Skip old articles
                if pub_date < cutoff:
                    continue

                # Extract summary
                summary = ''
                if hasattr(entry, 'summary'):
                    summary = BeautifulSoup(entry.summary, 'html.parser').get_text()[:500]
                elif hasattr(entry, 'description'):
                    summary = BeautifulSoup(entry.description, 'html.parser').get_text()[:500]

                articles.append({
                    'title': title,
                    'summary': summary,
                    'url': url,
                    'source': feed_info['source'],
                    'published_at': pub_date.isoformat(),
                })

        except Exception as e:
            print(f"[Research] Error fetching {feed_info['source']}: {e}")
            continue

        time.sleep(0.3)  # Polite delay

    print(f"[Research] Fetched {len(articles)} total articles")
    return articles


def quick_score(article: dict) -> float:
    """Fast keyword-based scoring before AI ranking."""
    text = (article['title'] + ' ' + article['summary']).lower()
    score = 0
    for kw in VIRAL_KEYWORDS:
        if kw in text:
            score += 1
    # Recency bonus: newer = higher score
    try:
        pub = datetime.fromisoformat(article['published_at'])
        hours_old = (datetime.now() - pub).total_seconds() / 3600
        recency_bonus = max(0, 10 - hours_old / 3)
        score += recency_bonus
    except Exception:
        pass
    return score


def ai_rank_and_select(articles: list[dict]) -> list[dict]:
    """Use Gemini to rank articles and select the top 5 most viral AI updates."""
    if not articles:
        return []

    # Pre-filter: take top 25 by quick score to reduce Gemini tokens
    articles.sort(key=quick_score, reverse=True)
    candidates = articles[:25]

    # Build prompt for Gemini
    article_list = ""
    for i, art in enumerate(candidates, 1):
        article_list += f"""
{i}. TITLE: {art['title']}
   SOURCE: {art['source']}
   SUMMARY: {art['summary'][:200]}
   URL: {art['url']}
"""

    prompt = f"""You are an expert AI social media strategist. Analyze these {len(candidates)} AI news articles and select the TOP 5 most valuable for an Instagram AI news account.

Criteria (score each 1-10):
- viral_score: Will this go viral? Is it surprising, exciting, or unprecedented?
- usefulness_score: Is this genuinely useful to AI creators, businesses, and tech enthusiasts?
- innovation_score: How innovative/groundbreaking is this development?

ARTICLES:
{article_list}

Return ONLY a JSON array of exactly 5 objects. No markdown, no explanation, just the JSON:
[
  {{
    "index": <1-based index from above list>,
    "viral_score": <1-10>,
    "usefulness_score": <1-10>,
    "innovation_score": <1-10>,
    "total_score": <sum of three scores>,
    "ai_summary": "<2-3 sentence explanation of why this is important and what it means for users>"
  }},
  ...
]

Select articles from DIFFERENT companies/topics when possible for variety."""

    try:
        response = _client.models.generate_content(
            model='gemini-3.6-flash', contents=prompt
        )
        raw = response.text.strip()
        # Strip markdown code blocks if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        selected_meta = json.loads(raw)
    except Exception as e:
        print(f"[Research] Gemini ranking failed: {e}")
        # Fallback: take top 5 by quick score
        selected_meta = [
            {"index": i+1, "viral_score": 7, "usefulness_score": 7, "innovation_score": 7,
             "total_score": 21, "ai_summary": candidates[i]['summary'][:200]}
            for i in range(min(5, len(candidates)))
        ]

    # Build final selected articles list
    results = []
    seen_indices = set()
    for meta in selected_meta:
        if len(results) >= 5:
            break
        idx = meta.get('index', 1) - 1
        if idx in seen_indices:
            continue
        seen_indices.add(idx)
        
        if 0 <= idx < len(candidates):
            article = candidates[idx].copy()
            article.update({
                'viral_score': meta.get('viral_score', 7),
                'usefulness_score': meta.get('usefulness_score', 7),
                'innovation_score': meta.get('innovation_score', 7),
                'total_score': meta.get('total_score', 21),
                'ai_summary': meta.get('ai_summary', article['summary'])
            })
            results.append(article)

    print(f"[Research] Selected {len(results)} top AI news items")
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r['total_score']}/30] {r['title'][:80]}")

    return results


def run_research() -> list[dict]:
    """
    Full research pipeline:
    1. Fetch articles from all RSS feeds
    2. Quick keyword score filter
    3. AI ranking to select top 5
    Returns list of top 5 article dicts with scores.
    """
    print("[Research] Starting AI news research pipeline...")
    articles = fetch_rss_feeds()
    
    if not articles:
        print("[Research] No articles fetched. Using fallback topics.")
        return get_fallback_topics()
    
    top5 = ai_rank_and_select(articles)
    
    if not top5:
        print("[Research] AI selection failed. Using quick-scored fallback.")
        articles.sort(key=quick_score, reverse=True)
        top5 = articles[:5]
    
    return top5


def get_fallback_topics() -> list[dict]:
    """Emergency fallback topics when feeds are unavailable."""
    return [
        {
            'title': 'AI Agents Are Taking Over Software Development in 2025',
            'summary': 'Autonomous AI coding agents can now write, test, and deploy entire applications with minimal human input.',
            'url': 'https://techcrunch.com',
            'source': 'TechCrunch AI',
            'published_at': datetime.now().isoformat(),
            'viral_score': 9, 'usefulness_score': 9, 'innovation_score': 8, 'total_score': 26,
            'ai_summary': 'AI coding agents represent a paradigm shift in software development, enabling small teams to build products at unprecedented speed.'
        },
        {
            'title': 'OpenAI Launches New Model with Unprecedented Reasoning Capabilities',
            'summary': 'The latest model significantly outperforms previous versions on complex reasoning, math, and coding tasks.',
            'url': 'https://openai.com',
            'source': 'OpenAI Blog',
            'published_at': datetime.now().isoformat(),
            'viral_score': 9, 'usefulness_score': 8, 'innovation_score': 9, 'total_score': 26,
            'ai_summary': 'A major leap in AI reasoning capability that will accelerate use cases in research, coding, and complex problem-solving.'
        },
    ]


if __name__ == '__main__':
    results = run_research()
    print(f"\nTop {len(results)} AI News Items:")
    for i, item in enumerate(results, 1):
        print(f"\n{i}. {item['title']}")
        print(f"   Score: {item.get('total_score', 0)}/30")
        print(f"   Source: {item['source']}")
