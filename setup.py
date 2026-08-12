"""
setup.py
One-command setup for the AI Instagram Automation System.
Downloads fonts, initializes the database, installs the Antigravity sidecar.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

PROJECT_ROOT  = Path(__file__).parent
SIDECAR_SRC   = PROJECT_ROOT / "scheduler" / "sidecar.json"
SIDECAR_DEST  = Path.home() / ".gemini" / "config" / "sidecars" / "ai-instagram-automation.json"


def check_env():
    """Check that .env exists with required keys."""
    env_path = PROJECT_ROOT / '.env'
    if not env_path.exists():
        example = PROJECT_ROOT / '.env.example'
        if example.exists():
            shutil.copy(example, env_path)
            print("[Setup] Created .env from .env.example -- please fill in your credentials!")
        else:
            print("[Setup] WARNING: .env not found. Create it from .env.example")
        return False

    from dotenv import dotenv_values
    vals = dotenv_values(str(env_path))
    required = ['GEMINI_API_KEY', 'IG_USER_ID', 'IG_ACCESS_TOKEN',
                'CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
    missing = [k for k in required if not vals.get(k) or 'your_' in vals.get(k, '')]
    if missing:
        print(f"[Setup] WARNING: Missing credentials in .env: {', '.join(missing)}")
        return False
    print("[Setup] All required credentials found in .env")
    return True


def init_database():
    """Initialize SQLite database."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from storage.db import init_db
    init_db()
    print("[Setup] Database initialized at storage/ai_news.db")


def download_fonts():
    """Download Inter font files."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from carousel.generator import download_fonts as dl
    dl()
    print("[Setup] Fonts downloaded to carousel/assets/fonts/")


def install_sidecar():
    """Install the Antigravity 2.0 sidecar for daily scheduling."""
    SIDECAR_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SIDECAR_SRC, SIDECAR_DEST)
    print(f"[Setup] Sidecar installed at {SIDECAR_DEST}")
    print("[Setup] Antigravity 2.0 will automatically run the pipeline at 8:00 AM daily")


def verify_install():
    """Quick smoke test — import all modules."""
    errors = []
    modules = [
        ('storage.db', 'init_db'),
        ('agents.research_agent', 'run_research'),
        ('agents.content_agent', 'process_news_item'),
        ('agents.publisher_agent', 'validate_credentials'),
        ('carousel.generator', 'generate_carousel'),
        ('dashboard.app', 'app'),
    ]
    sys.path.insert(0, str(PROJECT_ROOT))
    for mod, attr in modules:
        try:
            m = __import__(mod, fromlist=[attr])
            getattr(m, attr)
            print(f"[Verify] OK  {mod}.{attr}")
        except Exception as e:
            print(f"[Verify] ERR {mod}.{attr} -- {e}")
            errors.append(mod)

    if errors:
        print(f"\n[Verify] WARNING: {len(errors)} module(s) failed. Run: pip install -r requirements.txt")
    else:
        print("\n[Verify] All modules loaded successfully!")


def run_all():
    print("\n" + "═" * 55)
    print("  AI Instagram Automation System — Setup")
    print("═" * 55 + "\n")

    print("Step 1: Checking credentials...")
    check_env()

    print("\nStep 2: Initializing database...")
    try:
        init_database()
    except Exception as e:
        print(f"[Setup] ❌ DB init failed: {e}")

    print("\nStep 3: Downloading fonts...")
    try:
        download_fonts()
    except Exception as e:
        print(f"[Setup] ⚠️  Font download failed: {e} (system fonts will be used)")

    print("\nStep 4: Installing Antigravity sidecar...")
    try:
        install_sidecar()
    except Exception as e:
        print(f"[Setup] ❌ Sidecar install failed: {e}")

    print("\nStep 5: Verifying installation...")
    verify_install()

    print("\n" + "═" * 55)
    print("  Setup Complete! Next steps:")
    print("═" * 55)
    print("  1. Fill in credentials:   edit .env")
    print("  2. Test dry run:          python main_pipeline.py --dry-run")
    print("  3. Launch dashboard:      python dashboard/app.py")
    print("  4. Enable live posting:   set LIVE_MODE=true in .env")
    print("  5. Auto-schedule:         Antigravity 2.0 sidecar is active")
    print("═" * 55 + "\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Setup AI Instagram Automation')
    parser.add_argument('--fonts',    action='store_true', help='Download fonts only')
    parser.add_argument('--db',       action='store_true', help='Init database only')
    parser.add_argument('--sidecar',  action='store_true', help='Install sidecar only')
    parser.add_argument('--verify',   action='store_true', help='Verify install only')
    args = parser.parse_args()

    if   args.fonts:   download_fonts()
    elif args.db:      init_database()
    elif args.sidecar: install_sidecar()
    elif args.verify:  verify_install()
    else:              run_all()
