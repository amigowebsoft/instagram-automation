"""
agents/publisher_agent.py
Instagram Publisher Agent — uploads images to Cloudinary,
then publishes carousels via the Meta Graph API v21.0.
"""

import os
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

IG_USER_ID      = os.getenv('IG_USER_ID', '')
IG_ACCESS_TOKEN = os.getenv('IG_ACCESS_TOKEN', '')
IG_API_BASE     = 'https://graph.instagram.com/v21.0'
POST_DELAY      = int(os.getenv('POST_DELAY_SECONDS', '120'))
MAX_RETRIES     = 3
RETRY_DELAY     = 30

cloudinary.config(
    cloud_name  = os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    api_key     = os.getenv('CLOUDINARY_API_KEY', ''),
    api_secret  = os.getenv('CLOUDINARY_API_SECRET', ''),
    secure      = True
)


def validate_credentials() -> tuple:
    """Returns (ok: bool, message: str)."""
    if not IG_USER_ID:        return False, "IG_USER_ID not set in .env"
    if not IG_ACCESS_TOKEN:   return False, "IG_ACCESS_TOKEN not set in .env"
    if not os.getenv('CLOUDINARY_CLOUD_NAME'): return False, "CLOUDINARY_CLOUD_NAME not set"
    try:
        r = requests.get(f"{IG_API_BASE}/{IG_USER_ID}",
                         params={'fields': 'id,username', 'access_token': IG_ACCESS_TOKEN},
                         timeout=10)
        d = r.json()
        if 'error' in d:
            return False, f"Instagram API: {d['error'].get('message', 'Unknown error')}"
        print(f"[Publisher] [OK] Authenticated as @{d.get('username', 'unknown')}")
        return True, "OK"
    except Exception as e:
        return False, f"Token validation failed: {e}"


# ── Step 1: Cloudinary Upload ─────────────────────────────────────────────────

def upload_to_cloudinary(image_paths: list, post_id: str) -> list:
    """Upload slide images to Cloudinary, return list of public URLs."""
    urls = []
    for i, path in enumerate(image_paths):
        if not Path(path).exists():
            raise FileNotFoundError(f"Slide not found: {path}")
        public_id = f"ai_instagram/{post_id}/slide_{i+1:02d}"
        print(f"[Publisher] Uploading slide {i+1}/{len(image_paths)} to Cloudinary...")
        result = cloudinary.uploader.upload(
            path, public_id=public_id, overwrite=True,
            resource_type='image', format='jpg',
            quality='auto:good',
        )
        url = result.get('secure_url', '')
        if not url:
            raise RuntimeError(f"No URL returned for slide {i+1}")
        urls.append(url)
        print(f"[Publisher]   → {url[:70]}...")
    return urls


# ── Steps 2-4: Instagram Graph API ───────────────────────────────────────────

def _create_item_container(image_url: str) -> str:
    r = requests.post(
        f"{IG_API_BASE}/{IG_USER_ID}/media",
        params={'image_url': image_url, 'is_carousel_item': 'true',
                'access_token': IG_ACCESS_TOKEN},
        timeout=30
    )
    d = r.json()
    if 'error' in d:
        raise RuntimeError(f"Item container error: {d['error'].get('message', d)}")
    return d['id']


def _create_carousel_container(item_ids: list, caption: str) -> str:
    r = requests.post(
        f"{IG_API_BASE}/{IG_USER_ID}/media",
        params={'media_type': 'CAROUSEL', 'children': ','.join(item_ids),
                'caption': caption, 'access_token': IG_ACCESS_TOKEN},
        timeout=30
    )
    d = r.json()
    if 'error' in d:
        raise RuntimeError(f"Carousel container error: {d['error'].get('message', d)}")
    return d['id']


def _publish_container(container_id: str) -> str:
    r = requests.post(
        f"{IG_API_BASE}/{IG_USER_ID}/media_publish",
        params={'creation_id': container_id, 'access_token': IG_ACCESS_TOKEN},
        timeout=30
    )
    d = r.json()
    if 'error' in d:
        raise RuntimeError(f"Publish error: {d['error'].get('message', d)}")
    return d['id']


def publish_post(post_data: dict, image_paths: list, dry_run=False) -> dict:
    """
    Full publish pipeline for a single carousel.
    Returns dict: {success, instagram_media_id, cloudinary_urls, error}
    """
    result = {'success': False, 'instagram_media_id': None, 'cloudinary_urls': [], 'error': None}

    caption  = post_data.get('caption', '')
    hashtags = post_data.get('hashtags', [])
    tag_str  = ' '.join(hashtags[:30]) if isinstance(hashtags, list) else str(hashtags)
    full_cap = f"{caption}\n\n{tag_str}"
    if len(full_cap) > 2200:
        full_cap = full_cap[:2197] + '...'

    post_id_str = str(post_data.get('db_id', f"post_{int(time.time())}"))

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[Publisher] [POST] '{post_data.get('topic','')[:50]}' (attempt {attempt})")

            # Cloudinary upload
            cloudinary_urls = upload_to_cloudinary(image_paths, post_id_str)
            result['cloudinary_urls'] = cloudinary_urls

            if dry_run:
                print(f"[Publisher] [DRY RUN] Would post {len(cloudinary_urls)} slides")
                result['success'] = True
                result['instagram_media_id'] = f"dry_run_{post_id_str}"
                return result

            # Create item containers
            print("[Publisher] Creating media containers...")
            item_ids = []
            for url in cloudinary_urls:
                item_ids.append(_create_item_container(url))
                time.sleep(1)

            # Create carousel
            carousel_id = _create_carousel_container(item_ids, full_cap)
            print(f"[Publisher] Carousel container: {carousel_id}")

            # Publish
            time.sleep(3)
            media_id = _publish_container(carousel_id)
            result['success'] = True
            result['instagram_media_id'] = media_id
            print(f"[Publisher] [OK] Published! ID: {media_id}")
            return result

        except Exception as e:
            result['error'] = str(e)
            print(f"[Publisher] [ERROR] Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"[Publisher] Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)

    return result


def publish_all_posts(posts: list, dry_run=False) -> list:
    """Publish all 5 carousels with configured delay between posts."""
    results = []
    for i, post in enumerate(posts):
        print(f"\n[Publisher] ======= Post {i+1}/{len(posts)} =======")
        result = publish_post(post, post.get('slide_paths', []), dry_run=dry_run)
        results.append(result)
        if i < len(posts) - 1 and not dry_run:
            print(f"[Publisher] Waiting {POST_DELAY}s before next post...")
            time.sleep(POST_DELAY)

    ok = sum(1 for r in results if r['success'])
    print(f"\n[Publisher] [OK] {ok}/{len(posts)} posts published successfully")
    return results


def fetch_analytics(instagram_media_id: str) -> dict:
    """Fetch post engagement metrics from Instagram Insights."""
    try:
        r = requests.get(
            f"{IG_API_BASE}/{instagram_media_id}/insights",
            params={'metric': 'impressions,reach,likes,comments,saved,shares',
                    'access_token': IG_ACCESS_TOKEN},
            timeout=15
        )
        data = r.json()
        if 'error' in data:
            return {}
        metrics = {item['name']: item.get('values', [{}])[0].get('value', 0)
                   for item in data.get('data', [])}
        total  = metrics.get('likes', 0) + metrics.get('comments', 0) + metrics.get('saved', 0)
        reach  = metrics.get('reach', 1) or 1
        return {
            'likes': metrics.get('likes', 0),
            'comments': metrics.get('comments', 0),
            'saves': metrics.get('saved', 0),
            'shares': metrics.get('shares', 0),
            'reach': metrics.get('reach', 0),
            'impressions': metrics.get('impressions', 0),
            'engagement_rate': round(total / reach * 100, 2),
            'raw_data': data,
        }
    except Exception as e:
        print(f"[Publisher] Analytics error: {e}")
        return {}


if __name__ == '__main__':
    ok, msg = validate_credentials()
    print(f"Credentials: {'[OK] Valid' if ok else '[ERROR] Invalid'} — {msg}")

