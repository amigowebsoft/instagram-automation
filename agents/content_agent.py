"""
agents/content_agent.py
AI Content Generation Agent — generates carousel copy, captions, and hashtags.
"""

import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()
_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))


def generate_slide_content(news_item: dict) -> dict:
    """Generate 5-slide carousel content via Gemini."""
    title   = news_item.get('title', '')
    summary = news_item.get('ai_summary') or news_item.get('summary', '')
    source  = news_item.get('source', 'AI News')

    prompt = f"""You are a world-class viral Instagram content creator for AI news.
Create content for a 5-slide carousel about this AI update:

TITLE: {title}
SUMMARY: {summary}
SOURCE: {source}

Return ONLY a valid JSON object (no markdown, no code fences) with this exact structure:
{{
  "slide1": {{
    "hook": "<4-7 word punchy attention hook>",
    "headline": "<powerful headline, max 10 words>",
    "subtext": "<1-line teaser, max 12 words>",
    "emoji": "<2-3 relevant emojis>"
  }},
  "slide2": {{
    "heading": "What's Happening? 🤔",
    "main_text": "<clear 2-3 sentence explanation, no jargon>",
    "key_point": "<single most important fact in 10 words>",
    "emoji": "💡"
  }},
  "slide3": {{
    "heading": "Why This Matters 🔥",
    "impact_1": "<first real-world impact, 8-12 words>",
    "impact_2": "<second real-world impact, 8-12 words>",
    "impact_3": "<third real-world impact, 8-12 words>",
    "big_stat": "<impressive number or bold claim e.g. '10x faster'>"
  }},
  "slide4": {{
    "heading": "How YOU Can Use This 🚀",
    "usecase_1": "<creator/business use case, max 10 words>",
    "usecase_2": "<use case, max 10 words>",
    "usecase_3": "<use case, max 10 words>",
    "usecase_4": "<use case, max 10 words>"
  }},
  "slide5": {{
    "heading": "The Bottom Line 🎯",
    "summary_line": "<one powerful sentence wrapping up why this is huge>",
    "cta_question": "<engaging follower question e.g. 'Would you use this?'>",
    "cta_action": "<save/share CTA e.g. 'Save this for later 💾'>"
  }}
}}"""

    try:
        response = _client.models.generate_content(
            model='gemini-3.6-flash', contents=prompt
        )
        raw = response.text.strip()
        # Strip markdown fences if present
        if '```' in raw:
            for part in raw.split('```'):
                cleaned = part.lstrip('json').strip()
                if cleaned.startswith('{'):
                    raw = cleaned
                    break
        return json.loads(raw)
    except Exception as e:
        print(f"[Content] Slide gen error: {e}. Using fallback.")
        return _fallback_slides(news_item)


def generate_caption(news_item: dict, slides: dict) -> str:
    """Generate Instagram caption with hooks, CTAs."""
    title = news_item.get('title', '')
    summary = news_item.get('ai_summary') or news_item.get('summary', '')
    hook = slides.get('slide1', {}).get('hook', '')
    cta_q = slides.get('slide5', {}).get('cta_question', 'Would you use this?')

    prompt = f"""Write a viral Instagram caption for an AI news account. Topic: {title}

Summary: {summary}
Hook phrase: {hook}
Engagement question: {cta_q}

Requirements:
- Start with a POWERFUL first line (determines whether people read on)
- 150-250 words total
- Short punchy sentences
- 2-3 naturally placed emojis
- End with EXACTLY these 3 lines (on separate lines):
  {cta_q}
  Save this for later 💾
  Follow for daily AI updates 🤖

NO hashtags in caption. Return only the caption text."""

    try:
        response = _client.models.generate_content(
            model='gemini-3.6-flash', contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Content] Caption error: {e}. Using fallback.")
        return (
            f"🚨 {title}\n\n"
            f"{summary[:250]}\n\n"
            f"The AI landscape is shifting faster than ever — and staying ahead is everything.\n\n"
            f"{cta_q}\n"
            f"Save this for later 💾\n"
            f"Follow for daily AI updates 🤖"
        )


def generate_hashtags(news_item: dict) -> list:
    """Return 30 targeted hashtags based on article content."""
    text = (news_item.get('title', '') + ' ' + news_item.get('summary', '')).lower()

    core = ['#AINews', '#ArtificialIntelligence', '#AITools', '#TechNews', '#AIUpdates']

    contextual = []
    mapping = {
        ('openai', 'chatgpt', 'gpt'):       ['#ChatGPT', '#OpenAI', '#GPT4'],
        ('gemini', 'google'):               ['#GoogleAI', '#Gemini', '#GoogleGemini'],
        ('claude', 'anthropic'):            ['#Claude', '#Anthropic'],
        ('deepseek',):                      ['#DeepSeek', '#DeepSeekAI'],
        ('meta', 'llama'):                  ['#MetaAI', '#LLaMA', '#OpenSource'],
        ('midjourney', 'image', 'dall-e'):  ['#AIArt', '#MidJourney', '#AIImage'],
        ('video', 'sora', 'runway'):        ['#AIVideo', '#Sora', '#RunwayML'],
        ('voice', 'audio', 'elevenlabs'):   ['#AIVoice', '#ElevenLabs', '#VoiceAI'],
        ('code', 'coding', 'copilot'):      ['#AICoding', '#AIDevTools', '#Developer'],
        ('agent', 'autonomous', 'automation'): ['#AIAgent', '#AIAutomation'],
        ('startup', 'launch', 'funding'):   ['#AIStartup', '#TechStartup'],
        ('microsoft', 'copilot'):           ['#Microsoft', '#Copilot'],
    }
    for keywords, tags in mapping.items():
        if any(k in text for k in keywords):
            contextual.extend(tags)

    general = [
        '#MachineLearning', '#DeepLearning', '#GenerativeAI', '#LLM',
        '#FutureTech', '#Innovation', '#AIRevolution', '#TechTrends',
        '#FutureOfWork', '#AIProductivity', '#AIBusiness', '#Tech',
        '#DigitalTransformation', '#Creator', '#BuildInPublic', '#Viral',
    ]

    all_tags = list(dict.fromkeys(core + contextual + general))
    return all_tags[:30]


def process_news_item(news_item: dict) -> dict:
    """Full content pipeline for a single news item."""
    print(f"[Content] Generating: {news_item.get('title', '')[:60]}...")
    slides  = generate_slide_content(news_item)
    caption = generate_caption(news_item, slides)
    tags    = generate_hashtags(news_item)
    return {
        'topic':     news_item.get('title', ''),
        'source':    news_item.get('source', ''),
        'url':       news_item.get('url', ''),
        'news_item': news_item,
        'slides':    slides,
        'caption':   caption,
        'hashtags':  tags,
    }


def process_all_news(news_items: list) -> list:
    """Process all selected news items."""
    import time
    print(f"[Content] Processing {len(news_items)} items...")
    results = []
    for i, item in enumerate(news_items, 1):
        print(f"[Content] [{i}/{len(news_items)}]")
        results.append(process_news_item(item))
        if i < len(news_items):
            time.sleep(4)  # Rate limiting for Gemini free tier
    print(f"[Content] Done - {len(results)} posts generated.")
    return results


def _fallback_slides(news_item: dict) -> dict:
    title   = news_item.get('title', 'AI Update')
    summary = news_item.get('summary', 'A major new AI development.')
    return {
        'slide1': {'hook': 'This changes everything 🚨', 'headline': title[:60],
                   'subtext': 'Here is what you need to know', 'emoji': '🤖⚡🚀'},
        'slide2': {'heading': "What's Happening? 🤔", 'main_text': summary[:300],
                   'key_point': 'A major AI update just dropped', 'emoji': '💡'},
        'slide3': {'heading': 'Why This Matters 🔥', 'impact_1': 'Changes how we work with AI tools',
                   'impact_2': 'Saves hours of manual work daily', 'impact_3': 'Opens new opportunities for creators',
                   'big_stat': '10x Productivity'},
        'slide4': {'heading': 'How YOU Can Use This 🚀', 'usecase_1': 'Automate repetitive tasks instantly',
                   'usecase_2': 'Create content 10x faster', 'usecase_3': 'Build products without a full team',
                   'usecase_4': 'Stay ahead of your competition'},
        'slide5': {'heading': 'The Bottom Line 🎯',
                   'summary_line': 'The AI revolution is accelerating. Are you keeping up?',
                   'cta_question': 'Would you use this in your workflow?',
                   'cta_action': 'Save this for later 💾'},
    }


if __name__ == '__main__':
    test = {
        'title': 'OpenAI Launches GPT-5 with Multimodal Capabilities',
        'summary': 'GPT-5 can reason, see, hear, and code at near-human levels.',
        'source': 'OpenAI Blog',
        'ai_summary': 'GPT-5 is the most capable AI model ever released, combining all modalities.',
    }
    result = process_news_item(test)
    print(json.dumps(result['slides'], indent=2))
    print("\nCAPTION:\n", result['caption'])
    print("\nHASHTAGS:\n", ' '.join(result['hashtags']))
