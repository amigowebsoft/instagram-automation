"""
main_pipeline.py
AI Instagram Automation Orchestrator
Runs the full daily pipeline: research → content → carousel → publish
"""

import os
import sys
import time
import argparse
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.db import (
    init_db, save_news_items, mark_selected_news, save_post,
    update_post_cloudinary, update_post_published, update_post_failed,
    log_publish, get_today_posts, save_analytics
)
from agents.research_agent import run_research
from agents.content_agent import process_all_news
from carousel.generator import generate_all_carousels, download_fonts
from agents.publisher_agent import publish_all_posts, fetch_analytics, validate_credentials


# ─── Config ───────────────────────────────────────────────────────────────────
LIVE_MODE      = os.getenv('LIVE_MODE', 'false').lower() == 'true'
IG_ACCOUNT     = os.getenv('IG_ACCOUNT_NAME', '@AINewsDaily')
POST_DELAY     = int(os.getenv('POST_DELAY_SECONDS', '120'))


def log(msg: str, level: str = 'INFO'):
    ts = datetime.now().strftime('%H:%M:%S')
    prefix = {'INFO': '[i]', 'OK': '[OK]', 'WARN': '[!]', 'ERROR': '[ERR]', 'STEP': '[>>]'}.get(level, '[i]')
    print(f"[{ts}] {prefix} {msg}")


def run_pipeline(dry_run: bool = True):
    """
    Full automation pipeline:
      8:00 AM  → Research & select top 5 news
      8:15 AM  → Generate carousel content
      8:30 AM  → Render carousel images
      8:45 AM  → Upload to Cloudinary
      9:00 AM  → Publish all 5 to Instagram
    """
    start = datetime.now()
    today = date.today().isoformat()
    mode_label = "DRY RUN" if dry_run else "LIVE"

    print("\n" + "=" * 60)
    log(f"AI Instagram Automation - Daily Pipeline [{mode_label}]", 'STEP')
    log(f"Date: {today}  |  Account: {IG_ACCOUNT}", 'INFO')
    print("=" * 60 + "\n")

    # ── Phase 1: Init DB ──────────────────────────────────────────
    init_db()

    # ── Phase 2: Research ─────────────────────────────────────────
    log("PHASE 1 - AI News Research", 'STEP')
    try:
        top5_news = run_research()
    except Exception as e:
        log(f"Research failed: {e}", 'ERROR')
        return False

    if not top5_news:
        log("No news items found - aborting", 'ERROR')
        return False

    # Save to DB
    news_ids = save_news_items(top5_news)
    mark_selected_news(news_ids)
    log(f"Selected {len(top5_news)} top AI news items", 'OK')

    # ── Phase 3: Content Generation ───────────────────────────────
    log("PHASE 2 - Content Generation", 'STEP')
    try:
        all_post_content = process_all_news(top5_news)
    except Exception as e:
        log(f"Content generation failed: {e}", 'ERROR')
        return False

    log(f"Generated content for {len(all_post_content)} posts", 'OK')

    # ── Phase 4: Carousel Rendering ───────────────────────────────
    log("PHASE 3 - Carousel Image Rendering", 'STEP')
    try:
        all_slide_paths = generate_all_carousels(all_post_content, IG_ACCOUNT)
    except Exception as e:
        log(f"Carousel generation failed: {e}", 'ERROR')
        return False

    log(f"Rendered {sum(len(p) for p in all_slide_paths)} slides across {len(all_slide_paths)} carousels", 'OK')

    # ── Phase 5: Save posts to DB & prepare for publishing ────────
    log("PHASE 4 - Preparing Posts", 'STEP')
    posts_for_publishing = []
    db_post_ids = []

    for i, (content, slide_paths) in enumerate(zip(all_post_content, all_slide_paths)):
        news_item = content.get('news_item', {})
        post_rec = {
            'news_item_id': news_ids[i] if i < len(news_ids) else None,
            'topic':        content.get('topic', ''),
            'slide_paths':  slide_paths,
            'caption':      content.get('caption', ''),
            'hashtags':     content.get('hashtags', []),
        }
        db_id = save_post(post_rec)
        db_post_ids.append(db_id)

        posts_for_publishing.append({
            'db_id':      db_id,
            'topic':      content.get('topic', ''),
            'caption':    content.get('caption', ''),
            'hashtags':   content.get('hashtags', []),
            'slide_paths': slide_paths,
        })

    # ── Phase 6: Publish ──────────────────────────────────────────
    log("PHASE 5 - Publishing to Instagram", 'STEP')

    if not dry_run:
        ok, msg = validate_credentials()
        if not ok:
            log(f"Credentials invalid: {msg}", 'ERROR')
            log("Set LIVE_MODE=false or fix credentials in .env", 'WARN')
            dry_run = True

    results = publish_all_posts(posts_for_publishing, dry_run=dry_run)

    # ── Phase 7: Record results ───────────────────────────────────
    published_count = 0
    for i, (result, db_id) in enumerate(zip(results, db_post_ids)):
        if result['success']:
            published_count += 1
            update_post_cloudinary(db_id, result.get('cloudinary_urls', []))
            update_post_published(db_id, result['instagram_media_id'])
            log_publish(db_id, 1, 'success',
                        f"Published: {result['instagram_media_id']}")
        else:
            update_post_failed(db_id, result.get('error', 'Unknown error'))
            log_publish(db_id, 1, 'failed', result.get('error', 'Unknown'))
            log(f"Post {i+1} failed: {result.get('error', '')}", 'ERROR')

    # ── Summary ───────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    print("\n" + "=" * 60)
    log(f"Pipeline complete in {elapsed:.0f}s", 'OK')
    log(f"Published: {published_count}/{len(results)} posts", 'OK')
    if dry_run:
        log("DRY RUN - No actual Instagram posts were made", 'WARN')
        log("Set LIVE_MODE=true in .env to enable live posting", 'INFO')
    print("=" * 60 + "\n")

    return published_count > 0


def fetch_daily_analytics():
    """Fetch and store analytics for all published posts from today."""
    posts = get_today_posts()
    published = [p for p in posts if p['status'] == 'published' and p.get('instagram_media_id')]
    if not published:
        log("No published posts to fetch analytics for", 'INFO')
        return

    from agents.publisher_agent import fetch_analytics
    for post in published:
        log(f"Fetching analytics for post {post['id']}...")
        data = fetch_analytics(post['instagram_media_id'])
        if data:
            data['post_id'] = post['id']
            data['instagram_media_id'] = post['instagram_media_id']
            save_analytics(data)
            log(f"  Likes: {data.get('likes',0)} | Reach: {data.get('reach',0)} | Saves: {data.get('saves',0)}", 'OK')


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='AI Instagram Automation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_pipeline.py --dry-run       # Test without posting to Instagram
  python main_pipeline.py --live          # Full live run (requires credentials)
  python main_pipeline.py --analytics     # Fetch analytics for today's posts
  python main_pipeline.py --setup         # Download fonts and init DB only
        """
    )
    parser.add_argument('--dry-run',   action='store_true', help='Run without Instagram posting (default)')
    parser.add_argument('--live',      action='store_true', help='Enable live Instagram posting')
    parser.add_argument('--analytics', action='store_true', help='Fetch analytics only')
    parser.add_argument('--setup',     action='store_true', help='Setup only (fonts + DB)')
    args = parser.parse_args()

    if args.setup:
        log("Running setup...", 'STEP')
        init_db()
        download_fonts()
        log("Setup complete!", 'OK')
        return

    if args.analytics:
        log("Fetching analytics...", 'STEP')
        fetch_daily_analytics()
        return

    # Determine live/dry mode
    is_live = args.live or LIVE_MODE
    is_dry  = args.dry_run or not is_live

    if is_live and not args.live and not LIVE_MODE:
        log("LIVE_MODE not set - defaulting to dry-run. Use --live or set LIVE_MODE=true", 'WARN')
        is_dry = True

    run_pipeline(dry_run=is_dry)


if __name__ == '__main__':
    main()
