"""
dashboard/app.py
Flask web dashboard for the AI Instagram Automation System.
Real-time status, carousel previews, analytics, and controls.
"""

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime, date, timedelta

from flask import Flask, render_template, jsonify, request, send_file, abort
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import (
    init_db, get_today_news, get_recent_news, get_today_posts,
    get_recent_posts, get_publish_log, get_analytics_summary,
    get_analytics_by_day
)

app = Flask(__name__)
app.secret_key = os.getenv('DASHBOARD_SECRET_KEY', 'change-me-in-production')
CORS(app)

OUTPUT_DIR  = Path(__file__).parent.parent / 'output' / 'posts'
LIVE_MODE   = os.getenv('LIVE_MODE', 'false').lower() == 'true'
IG_ACCOUNT  = os.getenv('IG_ACCOUNT_NAME', '@AINewsDaily')
IG_USER_ID  = os.getenv('IG_USER_ID', '')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def encode_image_b64(path: str) -> str:
    """Encode a local image file as base64 data URI for inline display."""
    try:
        p = Path(path)
        if p.exists():
            with open(p, 'rb') as f:
                return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return ''


def next_run_info() -> dict:
    """Calculate time until next scheduled 9 AM run."""
    now = datetime.now()
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    delta = target - now
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    mins, secs = divmod(rem, 60)
    return {
        'next_run': target.strftime('%Y-%m-%d %H:%M:%S'),
        'countdown': f"{hours:02d}:{mins:02d}:{secs:02d}",
        'seconds_remaining': int(delta.total_seconds()),
    }


def enrich_posts_with_previews(posts: list) -> list:
    """Add base64 slide previews to post data."""
    enriched = []
    for post in posts:
        p = dict(post)
        paths = p.get('slide_paths', [])
        p['slide_previews'] = []
        for path in paths[:5]:
            p['slide_previews'].append(encode_image_b64(path))
        enriched.append(p)
    return enriched


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Main dashboard page."""
    init_db()
    return render_template('index.html',
                           ig_account=IG_ACCOUNT,
                           live_mode=LIVE_MODE,
                           ig_connected=bool(IG_USER_ID))


@app.route('/api/status')
def api_status():
    """Real-time system status."""
    today_posts  = get_today_posts()
    today_news   = get_today_news()
    selected     = get_today_news(selected_only=True)
    schedule     = next_run_info()
    analytics    = get_analytics_summary()

    published  = [p for p in today_posts if p.get('status') == 'published']
    failed     = [p for p in today_posts if p.get('status') == 'failed']
    pending    = [p for p in today_posts if p.get('status') in ('pending', 'uploaded')]

    return jsonify({
        'timestamp':      datetime.now().isoformat(),
        'today_date':     date.today().isoformat(),
        'live_mode':      LIVE_MODE,
        'ig_account':     IG_ACCOUNT,
        'ig_connected':   bool(IG_USER_ID),
        'schedule':       schedule,
        'today_stats': {
            'news_fetched':  len(today_news),
            'news_selected': len(selected),
            'posts_total':   len(today_posts),
            'posts_published': len(published),
            'posts_failed':    len(failed),
            'posts_pending':   len(pending),
        },
        'analytics': {
            'total_posts':    analytics.get('total_posts', 0),
            'total_likes':    int(analytics.get('total_likes') or 0),
            'total_comments': int(analytics.get('total_comments') or 0),
            'total_saves':    int(analytics.get('total_saves') or 0),
            'total_reach':    int(analytics.get('total_reach') or 0),
            'avg_engagement': round(float(analytics.get('avg_engagement') or 0), 2),
        }
    })


@app.route('/api/news')
def api_news():
    """Today's researched news items."""
    news = get_today_news()
    if not news:
        news = get_recent_news(limit=20)
    return jsonify(news)


@app.route('/api/selected')
def api_selected():
    """Today's top-5 selected news items."""
    return jsonify(get_today_news(selected_only=True))


@app.route('/api/posts')
def api_posts():
    """Today's generated posts with slide previews."""
    posts = get_today_posts()
    if not posts:
        posts = get_recent_posts(limit=5)
    enriched = enrich_posts_with_previews(posts)
    # Remove large binary previews from list view, keep only first slide
    compact = []
    for p in enriched:
        pc = dict(p)
        pc['thumbnail'] = pc['slide_previews'][0] if pc.get('slide_previews') else ''
        pc.pop('slide_previews', None)
        compact.append(pc)
    return jsonify(compact)


@app.route('/api/posts/<int:post_id>/slides')
def api_post_slides(post_id: int):
    """Full slide previews for a specific post."""
    all_posts = get_recent_posts(limit=50)
    post = next((p for p in all_posts if p['id'] == post_id), None)
    if not post:
        abort(404)
    enriched = enrich_posts_with_previews([post])[0]
    return jsonify({
        'id':         post['id'],
        'topic':      post['topic'],
        'caption':    post['caption'],
        'hashtags':   post['hashtags'],
        'status':     post['status'],
        'slides':     enriched['slide_previews'],
    })


@app.route('/api/log')
def api_log():
    """Recent publish log entries."""
    return jsonify(get_publish_log(limit=50))


@app.route('/api/analytics')
def api_analytics():
    """Analytics summary + daily breakdown."""
    summary = get_analytics_summary()
    daily   = get_analytics_by_day(days=14)
    return jsonify({'summary': summary, 'daily': daily})


@app.route('/api/run', methods=['POST'])
def api_run():
    """Trigger a manual pipeline run (dry-run safe)."""
    data = request.get_json(silent=True) or {}
    live = data.get('live', False) and LIVE_MODE

    import subprocess
    cmd = [sys.executable, str(Path(__file__).parent.parent / 'main_pipeline.py')]
    if not live:
        cmd.append('--dry-run')
    else:
        cmd.append('--live')

    try:
        subprocess.Popen(cmd, cwd=str(Path(__file__).parent.parent))
        return jsonify({'status': 'started', 'live': live,
                        'message': f"Pipeline started ({'LIVE' if live else 'DRY RUN'})"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/slides/<path:image_path>')
def serve_slide(image_path: str):
    """Serve a local slide image file."""
    full_path = OUTPUT_DIR / image_path
    if full_path.exists() and full_path.suffix in ('.jpg', '.jpeg', '.png'):
        return send_file(str(full_path), mimetype='image/jpeg')
    abort(404)


if __name__ == '__main__':
    init_db()
    port = int(os.getenv('DASHBOARD_PORT', '5000'))
    print(f"\n🚀 AI Instagram Dashboard running at http://localhost:{port}")
    print(f"   Account: {IG_ACCOUNT}  |  Live Mode: {LIVE_MODE}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
