"""
storage/db.py
SQLite database layer for the AI Instagram Automation System.
"""

import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "ai_news.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_date TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            source TEXT,
            published_at TEXT,
            viral_score REAL DEFAULT 0,
            usefulness_score REAL DEFAULT 0,
            innovation_score REAL DEFAULT 0,
            total_score REAL DEFAULT 0,
            is_selected INTEGER DEFAULT 0,
            selection_rank INTEGER,
            ai_summary TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_date TEXT NOT NULL,
            news_item_id INTEGER REFERENCES news_items(id),
            topic TEXT NOT NULL,
            slide_paths TEXT,
            caption TEXT,
            hashtags TEXT,
            cloudinary_urls TEXT,
            instagram_media_id TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            published_at TEXT
        );

        CREATE TABLE IF NOT EXISTS publish_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER REFERENCES posts(id),
            attempt INTEGER DEFAULT 1,
            status TEXT,
            message TEXT,
            instagram_response TEXT,
            logged_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER REFERENCES posts(id),
            instagram_media_id TEXT,
            fetch_date TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0,
            raw_data TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_news_fetch_date ON news_items(fetch_date);
        CREATE INDEX IF NOT EXISTS idx_news_selected ON news_items(is_selected);
        CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(post_date);
        CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ── News Items ────────────────────────────────────────────────────────────────

def save_news_items(items: list) -> list:
    conn = get_connection()
    ids = []
    today = date.today().isoformat()
    try:
        for item in items:
            cur = conn.execute("""
                INSERT INTO news_items
                    (fetch_date, title, summary, url, source, published_at,
                     viral_score, usefulness_score, innovation_score, total_score, ai_summary)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                today, item.get('title', ''), item.get('summary', ''),
                item.get('url', ''), item.get('source', ''),
                item.get('published_at', ''), item.get('viral_score', 0),
                item.get('usefulness_score', 0), item.get('innovation_score', 0),
                item.get('total_score', 0), item.get('ai_summary', '')
            ))
            ids.append(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()
    return ids


def mark_selected_news(item_ids: list):
    conn = get_connection()
    try:
        today = date.today().isoformat()
        conn.execute("UPDATE news_items SET is_selected=0, selection_rank=NULL WHERE fetch_date=?", (today,))
        for rank, iid in enumerate(item_ids, 1):
            conn.execute("UPDATE news_items SET is_selected=1, selection_rank=? WHERE id=?", (rank, iid))
        conn.commit()
    finally:
        conn.close()


def get_today_news(selected_only=False):
    conn = get_connection()
    try:
        today = date.today().isoformat()
        if selected_only:
            rows = conn.execute("SELECT * FROM news_items WHERE fetch_date=? AND is_selected=1 ORDER BY selection_rank", (today,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM news_items WHERE fetch_date=? ORDER BY total_score DESC", (today,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_news(limit=30):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM news_items ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Posts ─────────────────────────────────────────────────────────────────────

def save_post(post: dict) -> int:
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO posts (post_date, news_item_id, topic, slide_paths, caption, hashtags)
            VALUES (?,?,?,?,?,?)
        """, (
            date.today().isoformat(), post.get('news_item_id'),
            post.get('topic', ''), json.dumps(post.get('slide_paths', [])),
            post.get('caption', ''), json.dumps(post.get('hashtags', []))
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_post_cloudinary(post_id: int, urls: list):
    conn = get_connection()
    try:
        conn.execute("UPDATE posts SET cloudinary_urls=?, status='uploaded' WHERE id=?",
                     (json.dumps(urls), post_id))
        conn.commit()
    finally:
        conn.close()


def update_post_published(post_id: int, media_id: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE posts SET instagram_media_id=?, status='published', published_at=datetime('now') WHERE id=?",
                     (media_id, post_id))
        conn.commit()
    finally:
        conn.close()


def update_post_failed(post_id: int, error: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE posts SET status='failed', error_message=? WHERE id=?", (error, post_id))
        conn.commit()
    finally:
        conn.close()


def get_today_posts():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM posts WHERE post_date=? ORDER BY id", (date.today().isoformat(),)).fetchall()
        result = []
        for r in rows:
            p = dict(r)
            p['slide_paths'] = json.loads(p.get('slide_paths') or '[]')
            p['hashtags'] = json.loads(p.get('hashtags') or '[]')
            p['cloudinary_urls'] = json.loads(p.get('cloudinary_urls') or '[]')
            result.append(p)
        return result
    finally:
        conn.close()


def get_recent_posts(limit=20):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for r in rows:
            p = dict(r)
            p['slide_paths'] = json.loads(p.get('slide_paths') or '[]')
            p['hashtags'] = json.loads(p.get('hashtags') or '[]')
            p['cloudinary_urls'] = json.loads(p.get('cloudinary_urls') or '[]')
            result.append(p)
        return result
    finally:
        conn.close()


# ── Publish Log ───────────────────────────────────────────────────────────────

def log_publish(post_id: int, attempt: int, status: str, message: str, response=''):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO publish_log (post_id, attempt, status, message, instagram_response) VALUES (?,?,?,?,?)",
                     (post_id, attempt, status, message, response))
        conn.commit()
    finally:
        conn.close()


def get_publish_log(limit=50):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT pl.*, p.topic FROM publish_log pl
            LEFT JOIN posts p ON pl.post_id=p.id
            ORDER BY pl.logged_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Analytics ─────────────────────────────────────────────────────────────────

def save_analytics(data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO analytics
                (post_id, instagram_media_id, fetch_date, likes, comments,
                 saves, shares, reach, impressions, engagement_rate, raw_data)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get('post_id'), data.get('instagram_media_id', ''),
            date.today().isoformat(), data.get('likes', 0), data.get('comments', 0),
            data.get('saves', 0), data.get('shares', 0), data.get('reach', 0),
            data.get('impressions', 0), data.get('engagement_rate', 0),
            json.dumps(data.get('raw_data', {}))
        ))
        conn.commit()
    finally:
        conn.close()


def get_analytics_summary():
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as total_posts, SUM(likes) as total_likes,
                   SUM(comments) as total_comments, SUM(saves) as total_saves,
                   SUM(reach) as total_reach, AVG(engagement_rate) as avg_engagement
            FROM analytics
        """).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_analytics_by_day(days=7):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT fetch_date, SUM(likes) as likes, SUM(comments) as comments,
                   SUM(saves) as saves, SUM(reach) as reach,
                   AVG(engagement_rate) as engagement_rate
            FROM analytics GROUP BY fetch_date
            ORDER BY fetch_date DESC LIMIT ?
        """, (days,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    print("[DB] Ready.")
