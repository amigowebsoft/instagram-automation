"""
carousel/generator.py
Dynamic Multi-Theme Instagram Carousel Slide Generator.
Supports dynamic switching between Light Mode, Dark Vivid Gradient, Warm Minimal, and Cyber Neon themes.
Maintains bold typography, crisp high-contrast cards, and structured layouts across all styles.
"""

import os
import re
import json
import math
import zlib
import textwrap
from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── Paths ────────────────────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "posts"

# ─── Canvas Dimensions ────────────────────────────────────────────────────────
W, H = 1080, 1350   # Instagram portrait format (4:5)

# ─── Multi-Theme Definitions ──────────────────────────────────────────────────
THEMES = [
    # 0: Clean Light Tech (Light Slate & White Cards)
    {
        'name': 'Clean Light Tech',
        'bg_type': 'gradient',
        'bg_top': (248, 250, 252),
        'bg_bottom': (241, 245, 249),
        'card_bg': (255, 255, 255),
        'card_border': (226, 232, 240),
        'card_shadow': (15, 23, 42, 18),
        'text_primary': (15, 23, 42),
        'text_secondary': (51, 65, 85),
        'text_muted': (100, 116, 139),
        'accent': (79, 70, 229),       # Electric Indigo
        'sub_accent': (2, 132, 199),    # Sky Blue
        'badge_text': (255, 255, 255),
    },
    # 1: Dark Vivid Electric (Slate 900 Gradient & Bold White Text)
    {
        'name': 'Dark Vivid Electric',
        'bg_type': 'gradient',
        'bg_top': (15, 23, 42),
        'bg_bottom': (30, 27, 75),
        'card_bg': (30, 41, 59),
        'card_border': (71, 85, 105),
        'card_shadow': (0, 0, 0, 80),
        'text_primary': (255, 255, 255),
        'text_secondary': (226, 232, 240),
        'text_muted': (148, 163, 184),
        'accent': (56, 189, 248),      # Bright Sky Cyan
        'sub_accent': (168, 85, 247),  # Electric Purple
        'badge_text': (15, 23, 42),
    },
    # 2: Warm Minimal Ivory (Warm Stone & Rose Accent)
    {
        'name': 'Warm Minimal Ivory',
        'bg_type': 'plain',
        'bg_top': (250, 250, 249),
        'bg_bottom': (250, 250, 249),
        'card_bg': (255, 255, 255),
        'card_border': (231, 229, 228),
        'card_shadow': (28, 25, 23, 14),
        'text_primary': (28, 25, 23),
        'text_secondary': (68, 64, 60),
        'text_muted': (120, 113, 108),
        'accent': (225, 29, 72),       # Rose Red
        'sub_accent': (217, 119, 6),   # Amber Gold
        'badge_text': (255, 255, 255),
    },
    # 3: Cyber Midnight (Deep Dark & Neon Border Accent)
    {
        'name': 'Cyber Midnight',
        'bg_type': 'gradient',
        'bg_top': (9, 13, 22),
        'bg_bottom': (17, 24, 39),
        'card_bg': (17, 24, 39),
        'card_border': (14, 165, 233),
        'card_shadow': (0, 0, 0, 120),
        'text_primary': (255, 255, 255),
        'text_secondary': (203, 213, 225),
        'text_muted': (148, 163, 184),
        'accent': (14, 165, 233),      # Cyan
        'sub_accent': (236, 72, 153),  # Hot Pink
        'badge_text': (255, 255, 255),
    }
]


# ─── Font Loading ─────────────────────────────────────────────────────────────

def load_font(size: int, weight: str = 'regular') -> ImageFont.FreeTypeFont:
    """Load Inter font at given size with system fallback."""
    font_map = {
        'black':      'Inter-Black.ttf',
        'bold':       'Inter-Bold.ttf',
        'semibold':   'Inter-SemiBold.ttf',
        'regular':    'Inter-Regular.ttf',
        'light':      'Inter-Light.ttf',
        'extrabold':  'Inter-ExtraBold.ttf',
    }
    font_file = FONTS_DIR / font_map.get(weight, 'Inter-Regular.ttf')
    try:
        return ImageFont.truetype(str(font_file), size)
    except Exception:
        system_fonts = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for sf in system_fonts:
            try:
                return ImageFont.truetype(sf, size)
            except Exception:
                continue
        return ImageFont.load_default()


def strip_emoji(text: str) -> str:
    """Remove emoji characters that can't render in standard TTF fonts."""
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF\U00002500-\U00002BEF]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


# ─── Drawing Utilities ────────────────────────────────────────────────────────

def create_theme_canvas(theme: dict) -> tuple[Image.Image, ImageDraw.Draw]:
    """Create background canvas based on current theme configuration."""
    img = Image.new('RGBA', (W, H), theme['bg_top'])
    draw = ImageDraw.Draw(img)

    if theme['bg_type'] == 'gradient':
        for y in range(H):
            t = y / H
            r = int(theme['bg_top'][0] * (1 - t) + theme['bg_bottom'][0] * t)
            g = int(theme['bg_top'][1] * (1 - t) + theme['bg_bottom'][1] * t)
            b = int(theme['bg_top'][2] * (1 - t) + theme['bg_bottom'][2] * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
    else:
        draw.rectangle([0, 0, W, H], fill=theme['bg_top'])

    # Decorative top bar
    draw.rectangle([0, 0, W, 8], fill=theme['accent'])

    return img, ImageDraw.Draw(img)


def draw_styled_card(img: Image.Image, x1: int, y1: int, x2: int, y2: int,
                     theme: dict, radius: int = 24, border_color: tuple = None) -> tuple[Image.Image, ImageDraw.Draw]:
    """Draw a styled card with drop shadow according to current theme."""
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    
    # Soft drop shadow
    shadow_fill = theme.get('card_shadow', (0, 0, 0, 20))
    s_draw.rounded_rectangle([x1 + 4, y1 + 8, x2 - 4, y2 + 12], radius=radius, fill=shadow_fill)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)
    
    # Card background & border
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=theme['card_bg'])
    b_col = border_color or theme['card_border']
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, outline=b_col, width=1)
    
    return img, draw


def draw_text_wrapped(draw: ImageDraw.Draw, text: str, x: int, y: int,
                      max_width: int, font: ImageFont.FreeTypeFont,
                      fill: tuple, line_spacing: int = 12,
                      align: str = 'left') -> int:
    """Draw word-wrapped text cleanly. Returns Y position after last line."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    line_height = font.getbbox('Hg')[3] + line_spacing
    current_y = y

    for line in lines:
        if align == 'center':
            bbox = font.getbbox(line)
            line_w = bbox[2] - bbox[0]
            draw.text((x + (max_width - line_w) // 2, current_y), line,
                      font=font, fill=fill)
        else:
            draw.text((x, current_y), line, font=font, fill=fill)
        current_y += line_height

    return current_y


def draw_slide_number(draw: ImageDraw.Draw, current: int, total: int, theme: dict):
    """Draw slide pagination indicators at bottom."""
    dot_w, dot_h = 8, 8
    gap = 14
    total_w = total * dot_w + (total - 1) * gap
    start_x = (W - total_w) // 2
    y = H - 65

    inactive_color = theme['text_muted']

    for i in range(total):
        cx = start_x + i * (dot_w + gap)
        if i == current - 1:
            draw.rounded_rectangle([cx - 6, y, cx + 18, y + dot_h],
                                   radius=4, fill=theme['accent'])
        else:
            draw.ellipse([cx, y, cx + dot_w, y + dot_h],
                         fill=inactive_color)


def draw_watermark(draw: ImageDraw.Draw, account_name: str, theme: dict):
    """Draw clean watermark tag at bottom."""
    font = load_font(22, 'semibold')
    account_name = account_name or '@AINewsDaily'
    draw.text((W // 2, H - 35), account_name,
              font=font, fill=theme['text_muted'], anchor='mm')


# ─── Individual Slide Renderers ───────────────────────────────────────────────

def render_slide1(data: dict, slide_num: int, total: int,
                  theme: dict, account_name: str) -> Image.Image:
    """HOOK SLIDE — Ultra bold title, crisp card layout."""
    img, draw = create_theme_canvas(theme)

    # Top Category Badge: "AI BREAKTHROUGH"
    label_font = load_font(18, 'bold')
    label = "AI BREAKTHROUGH"
    bbox = label_font.getbbox(label)
    lw = bbox[2] - bbox[0]
    lx = (W - lw) // 2
    ly = 110

    draw.rounded_rectangle([lx - 24, ly - 10, lx + lw + 24, ly + 32],
                           radius=20, fill=theme['accent'])
    draw.text((lx, ly), label, font=label_font, fill=theme['badge_text'])

    # Hook pill text
    hook = strip_emoji(data.get('hook', 'This changes everything')).upper()
    hook_font = load_font(24, 'extrabold')
    hook_bbox = hook_font.getbbox(hook)
    hx = (W - (hook_bbox[2] - hook_bbox[0])) // 2
    draw.text((hx, 220), hook, font=hook_font, fill=theme['accent'])

    # Main Hero White Card Container
    card_x1, card_y1 = 60, 280
    card_x2, card_y2 = W - 60, H - 180
    img, draw = draw_styled_card(img, card_x1, card_y1, card_x2, card_y2, theme, radius=28)

    # Inner Headline
    headline = strip_emoji(data.get('headline', 'Major AI Update'))
    hl_font = load_font(62, 'bold')

    words = headline.split()
    lines = []
    current = []
    for w in words:
        test = ' '.join(current + [w])
        if hl_font.getbbox(test)[2] <= (card_x2 - card_x1 - 80):
            current.append(w)
        else:
            if current:
                lines.append(' '.join(current))
            current = [w]
    if current:
        lines.append(' '.join(current))

    line_h = hl_font.getbbox('Hg')[3] + 16
    total_h = len(lines) * line_h
    start_y = card_y1 + ((card_y2 - card_y1) - total_h - 100) // 2

    # Draw headline lines
    for i, line in enumerate(lines):
        bbox = hl_font.getbbox(line)
        lw2 = bbox[2] - bbox[0]
        lx2 = card_x1 + ((card_x2 - card_x1) - lw2) // 2
        draw.text((lx2, start_y + i * line_h), line, font=hl_font, fill=theme['text_primary'])

    # Divider bar inside card
    div_y = start_y + total_h + 30
    draw.line([(card_x1 + 100, div_y), (card_x2 - 100, div_y)], fill=theme['card_border'], width=2)

    # Subtext inside card
    sub = strip_emoji(data.get('subtext', 'Here is what you need to know'))
    sub_font = load_font(28, 'medium')
    sub_bbox = sub_font.getbbox(sub)
    sw = sub_bbox[2] - sub_bbox[0]
    draw.text(((W - sw) // 2, div_y + 40), sub, font=sub_font, fill=theme['text_secondary'])

    draw_slide_number(draw, slide_num, total, theme)
    draw_watermark(draw, account_name, theme)

    return img.convert('RGB')


def render_slide2(data: dict, slide_num: int, total: int,
                  theme: dict, account_name: str) -> Image.Image:
    """EXPLAIN SLIDE — Clear breakdown with key insight card."""
    img, draw = create_theme_canvas(theme)

    # Section Heading
    heading = strip_emoji(data.get('heading', "What's Happening?"))
    h_font = load_font(48, 'bold')
    draw.text((60, 90), heading, font=h_font, fill=theme['text_primary'])

    # Accent Underline Bar
    draw.rectangle([60, 160, 160, 166], fill=theme['accent'])

    # Main text body in a styled card
    main_text = strip_emoji(data.get('main_text', 'A major new AI development just dropped.'))
    img, draw = draw_styled_card(img, 60, 200, W - 60, 620, theme, radius=24)

    body_font = load_font(34, 'regular')
    draw_text_wrapped(draw, main_text, 100, 250, W - 200,
                      body_font, theme['text_primary'], line_spacing=18)

    # Key insight card below
    key_point = strip_emoji(data.get('key_point', 'The single most important fact'))
    img, draw = draw_styled_card(img, 60, 660, W - 60, 950, theme, radius=24, border_color=theme['accent'])

    # Left accent vertical bar
    draw.rounded_rectangle([60, 660, 72, 950], radius=12, fill=theme['accent'])

    # Label
    label_font = load_font(18, 'bold')
    draw.text((105, 700), "KEY TAKEAWAY", font=label_font, fill=theme['accent'])

    key_font = load_font(32, 'bold')
    draw_text_wrapped(draw, key_point, 105, 740, W - 210, key_font, theme['text_primary'], line_spacing=14)

    draw_slide_number(draw, slide_num, total, theme)
    draw_watermark(draw, account_name, theme)
    return img.convert('RGB')


def render_slide3(data: dict, slide_num: int, total: int,
                  theme: dict, account_name: str) -> Image.Image:
    """IMPACT SLIDE — Hero stat + 3 impact points."""
    img, draw = create_theme_canvas(theme)

    # Section Heading
    heading = strip_emoji(data.get('heading', 'Why This Matters'))
    h_font = load_font(48, 'bold')
    draw.text((60, 90), heading, font=h_font, fill=theme['text_primary'])
    draw.rectangle([60, 160, 160, 166], fill=theme['accent'])

    # Big stat hero box
    big_stat = strip_emoji(data.get('big_stat', '10x Impact'))
    stat_font = load_font(72, 'black')
    stat_bbox = stat_font.getbbox(big_stat[:16])
    sw = stat_bbox[2] - stat_bbox[0]
    sx = (W - sw) // 2

    draw.text((sx, 200), big_stat[:16], font=stat_font, fill=theme['accent'])

    # 3 impact cards
    impacts = [
        strip_emoji(data.get('impact_1', 'Changes how we work with AI')),
        strip_emoji(data.get('impact_2', 'Saves hours of manual work')),
        strip_emoji(data.get('impact_3', 'Opens new opportunities')),
    ]
    numbers = ['01', '02', '03']

    start_y = 350
    card_h = 160
    gap = 25

    for i, (impact, num) in enumerate(zip(impacts, numbers)):
        y1 = start_y + i * (card_h + gap)
        y2 = y1 + card_h

        img, draw = draw_styled_card(img, 60, y1, W - 60, y2, theme, radius=20)

        # Number Badge Circle
        cx, cy = 120, (y1 + y2) // 2
        draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=theme['accent'])

        num_font = load_font(22, 'bold')
        draw.text((cx, cy), num, font=num_font, fill=theme['badge_text'], anchor='mm')

        # Impact text
        imp_font = load_font(28, 'semibold')
        draw_text_wrapped(draw, impact, 180, y1 + (card_h - 60) // 2, W - 270,
                          imp_font, theme['text_primary'], line_spacing=8)

    draw_slide_number(draw, slide_num, total, theme)
    draw_watermark(draw, account_name, theme)
    return img.convert('RGB')


def render_slide4(data: dict, slide_num: int, total: int,
                  theme: dict, account_name: str) -> Image.Image:
    """USE CASES SLIDE — 4 grid cards."""
    img, draw = create_theme_canvas(theme)

    # Section Heading
    heading = strip_emoji(data.get('heading', 'How YOU Can Use This'))
    h_font = load_font(48, 'bold')
    draw.text((60, 90), heading, font=h_font, fill=theme['text_primary'])
    draw.rectangle([60, 160, 160, 166], fill=theme['accent'])

    usecases = [
        strip_emoji(data.get('usecase_1', 'Automate repetitive tasks')),
        strip_emoji(data.get('usecase_2', 'Create content faster')),
        strip_emoji(data.get('usecase_3', 'Build products at scale')),
        strip_emoji(data.get('usecase_4', 'Stay ahead of competitors')),
    ]
    badges = ['01', '02', '03', '04']

    card_w = (W - 145) // 2
    card_h = 320
    pad = 25
    grid_start_y = 210

    for i, (use, badge) in enumerate(zip(usecases, badges)):
        row = i // 2
        col_idx = i % 2
        cx1 = 60 + col_idx * (card_w + pad)
        cy1 = grid_start_y + row * (card_h + pad)
        cx2 = cx1 + card_w
        cy2 = cy1 + card_h

        img, draw = draw_styled_card(img, cx1, cy1, cx2, cy2, theme, radius=24)

        # Top Badge Circle
        bx, by = cx1 + 45, cy1 + 45
        draw.ellipse([bx - 22, by - 22, bx + 22, by + 22], fill=theme['accent'])
        b_font = load_font(18, 'bold')
        draw.text((bx, by), badge, font=b_font, fill=theme['badge_text'], anchor='mm')

        # Use case text
        uc_font = load_font(26, 'bold')
        draw_text_wrapped(draw, use, cx1 + 25, cy1 + 100,
                          card_w - 50, uc_font, theme['text_primary'],
                          line_spacing=10)

    # Bottom motivational line
    mot_font = load_font(26, 'semibold')
    mot = "The tools are here. Will you take advantage?"
    draw_text_wrapped(draw, mot, 60, grid_start_y + 2 * (card_h + pad) + 40,
                      W - 120, mot_font, theme['text_secondary'],
                      align='center')

    draw_slide_number(draw, slide_num, total, theme)
    draw_watermark(draw, account_name, theme)
    return img.convert('RGB')


def render_slide5(data: dict, slide_num: int, total: int,
                  theme: dict, account_name: str) -> Image.Image:
    """CTA SLIDE — Bottom line + Call to action."""
    img, draw = create_theme_canvas(theme)

    # Top Label
    label_font = load_font(18, 'bold')
    label = "THE BOTTOM LINE"
    bbox = label_font.getbbox(label)
    lw = bbox[2] - bbox[0]
    lx = (W - lw) // 2
    draw.rounded_rectangle([lx - 20, 100, lx + lw + 20, 140], radius=16, fill=theme['accent'])
    draw.text((lx, 110), label, font=label_font, fill=theme['badge_text'])

    # Big Summary line inside hero card
    summary = strip_emoji(data.get('summary_line', 'The AI revolution is accelerating rapidly.'))
    img, draw = draw_styled_card(img, 60, 180, W - 60, 520, theme, radius=28)

    s_font = load_font(44, 'bold')
    draw_text_wrapped(draw, summary, 100, 240, W - 200,
                      s_font, theme['text_primary'],
                      line_spacing=14, align='center')

    # CTA Question Card
    q = strip_emoji(data.get('cta_question', 'Would you use this in your workflow?'))
    img, draw = draw_styled_card(img, 60, 560, W - 60, 720, theme, radius=24, border_color=theme['accent'])

    q_font = load_font(32, 'bold')
    draw_text_wrapped(draw, q, 90, 615, W - 180,
                      q_font, theme['text_primary'], align='center')

    # Action CTAs
    ctas = [
        strip_emoji(data.get('cta_action', 'Save this for later')),
        'Drop your thoughts in the comments below',
        'Share this with someone in tech',
    ]
    cta_font = load_font(26, 'semibold')
    cta_y = 760

    for cta in ctas:
        bbox = cta_font.getbbox(cta)
        cta_w = bbox[2] - bbox[0]
        draw.text(((W - cta_w) // 2, cta_y), cta,
                  font=cta_font, fill=theme['text_secondary'])
        cta_y += 55

    # Follow Button Badge
    badge_y1 = H - 220
    badge_y2 = badge_y1 + 75
    badge_x1, badge_x2 = W // 2 - 240, W // 2 + 240

    draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2],
                           radius=38, fill=theme['accent'])
    fol_font = load_font(28, 'bold')
    draw.text((W // 2, (badge_y1 + badge_y2) // 2), 'Follow for Daily AI Updates',
              font=fol_font, fill=theme['badge_text'], anchor='mm')

    draw_slide_number(draw, slide_num, total, theme)
    draw_watermark(draw, account_name, theme)
    return img.convert('RGB')


# ─── Main Generator ───────────────────────────────────────────────────────────

SLIDE_RENDERERS = [
    render_slide1,
    render_slide2,
    render_slide3,
    render_slide4,
    render_slide5,
]


def generate_carousel(post_data: dict, output_dir: Path = None,
                      account_name: str = None, post_index: int = 0) -> list[str]:
    """
    Generate all 5 carousel slide images for a post.
    Dynamically cycles through diverse visual themes (Light, Dark Vivid, Warm Ivory, Cyber Neon).
    Returns list of absolute file paths to generated slide JPGs.
    """
    today_str = date.today().isoformat()
    post_topic = post_data.get('topic', 'ai_news')
    clean_topic = re.sub(r'[^a-zA-Z0-9]', '_', post_topic)[:30].strip('_').lower()

    if output_dir is None:
        target_dir = OUTPUT_DIR / today_str / clean_topic
    else:
        target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    account_name = account_name or os.getenv('IG_ACCOUNT_NAME', '@AINewsDaily')
    slides_data = post_data.get('slides', {})

    # Select theme dynamically based on post index / topic hash
    theme_idx = (post_index + zlib.adler32(clean_topic.encode())) % len(THEMES)
    selected_theme = THEMES[theme_idx]

    safe_topic = post_topic[:50].encode('ascii', 'ignore').decode('ascii')
    print(f"[Generator] Rendering carousel [{selected_theme['name']}]: {safe_topic}")
    paths = []

    for i in range(1, 6):
        slide_key = f"slide{i}"
        sdata = slides_data.get(slide_key, {})

        renderer = SLIDE_RENDERERS[i - 1]
        img = renderer(sdata, i, 5, selected_theme, account_name)

        out_path = target_dir / f"slide_{i:02d}.jpg"
        img.save(out_path, 'JPEG', quality=95, optimize=True)
        paths.append(str(out_path))
        print(f"[Generator]   Slide {i}/5 -> {out_path.name}")

    print(f"[Generator] [OK] Carousel complete: 5 slides")
    return paths


def download_fonts():
    """Ensure assets/fonts directory exists."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_all_carousels(posts_content: list, account_name: str = None) -> list:
    """
    Generate carousels for a list of posts.
    Dynamically assigns a different theme style (Clean Light, Dark Vivid, Warm Ivory, Cyber Neon) to each post.
    """
    download_fonts()
    all_paths = []
    print(f"[Generator] Rendering {len(posts_content)} carousels with dynamic multi-theme designs...")
    for idx, post in enumerate(posts_content):
        paths = generate_carousel(post, account_name=account_name, post_index=idx)
        all_paths.append(paths)
    print(f"[Generator] [OK] All {len(posts_content)} carousels generated successfully")
    return all_paths


if __name__ == '__main__':
    test_post = {
        'topic': 'Google AI Boss Takes Over Race Against OpenAI',
        'slides': {
            'slide1': {
                'hook': 'This changes everything',
                'headline': 'Google AI Boss Leads the Race Against OpenAI',
                'subtext': 'Here is what you need to know',
            },
            'slide2': {
                'heading': "What's Happening?",
                'main_text': 'Google is restructuring its entire AI division to accelerate model training and surpass competing LLMs.',
                'key_point': 'New leadership aims to double deployment velocity across all Google products.',
            },
            'slide3': {
                'heading': 'Why This Matters',
                'big_stat': '10x Speedup',
                'impact_1': 'Faster releases for Gemini models',
                'impact_2': 'Deeper integration into Android',
                'impact_3': 'More powerful free developer tools',
            },
            'slide4': {
                'heading': 'How YOU Can Use This',
                'usecase_1': 'Build apps with Gemini API',
                'usecase_2': 'Automate daily workflows',
                'usecase_3': 'Leverage new multimodal AI',
                'usecase_4': 'Stay ahead of your competitors',
            },
            'slide5': {
                'heading': 'The Bottom Line',
                'summary_line': 'The battle for AI supremacy is heating up faster than ever.',
                'cta_question': 'Which AI ecosystem do you prefer?',
                'cta_action': 'Save this post for later',
            }
        }
    }
    for idx in range(4):
        paths = generate_carousel(test_post, output_dir=OUTPUT_DIR / "test_themes" / f"theme_{idx}", post_index=idx)
        print(f"\n[OK] Theme {idx} complete")
