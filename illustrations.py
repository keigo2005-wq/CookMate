"""レシピカードに表示する、料理ごとのイラスト（SVG）を自動生成する。

写真の代わりに、料理のジャンルが一目で伝わるフラットデザインの
イラストを自作している。すべて自作のベクター画像のため、
解像度による劣化がなく、著作権の心配もない（無料）。

レシピ100件それぞれで見た目が変わるように、次の3つを組み合わせている。
1. 料理の種類（麺・ご飯・スープ・肉料理など）に応じた土台のイラスト
2. レシピIDから決まる、色合いのバリエーション（色相を少しずつ回転させる）
3. 実際の材料から選ぶ、小さな食材アイコン（トマト・にんじん・卵など）
"""

_VIEWBOX = "0 0 300 120"

# ---------------------------------------------------------------------------
# 1. 料理の種類ごとの土台イラスト（内側の図形だけを持ち、背景色と分けて管理する）
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, tuple[str, str]] = {
    "meat": (
        """
        <ellipse cx="150" cy="97" rx="92" ry="12" fill="#00000014"/>
        <ellipse cx="150" cy="95" rx="90" ry="12" fill="#F3D8C2"/>
        <path d="M90 85 Q80 40 150 35 Q220 40 210 85 Q200 100 150 100 Q100 100 90 85 Z" fill="#C1440E"/>
        <path d="M90 85 Q80 40 150 35 Q220 40 210 85" fill="none" stroke="#E0632A" stroke-width="3" opacity="0.6"/>
        <path d="M105 55 L120 80 M135 45 L150 85 M165 45 L178 82 M192 55 L200 78"
              stroke="#8C2E08" stroke-width="4" stroke-linecap="round"/>
        <line x1="55" y1="30" x2="55" y2="95" stroke="#7A6A63" stroke-width="4" stroke-linecap="round"/>
        <line x1="45" y1="30" x2="45" y2="55" stroke="#7A6A63" stroke-width="4" stroke-linecap="round"/>
        <line x1="55" y1="30" x2="55" y2="55" stroke="#7A6A63" stroke-width="4" stroke-linecap="round"/>
        <line x1="65" y1="30" x2="65" y2="55" stroke="#7A6A63" stroke-width="4" stroke-linecap="round"/>
        """,
        "#FFE0CC",
    ),
    "fish": (
        """
        <ellipse cx="150" cy="92" rx="95" ry="10" fill="#00000014"/>
        <ellipse cx="150" cy="90" rx="95" ry="10" fill="#CFE8EE"/>
        <path d="M70 60 Q150 20 230 55 Q240 60 230 65 Q150 100 70 60 Z" fill="#4A90A4"/>
        <path d="M70 60 Q150 20 230 55" fill="none" stroke="#6FB0C2" stroke-width="3" opacity="0.6"/>
        <path d="M60 60 L35 45 L40 60 L35 75 Z" fill="#38788A"/>
        <circle cx="205" cy="52" r="5" fill="#FFFFFF"/>
        <circle cx="205" cy="52" r="2.5" fill="#1F3A44"/>
        <path d="M110 55 Q120 62 110 70 M130 52 Q140 60 130 68 M150 51 Q160 59 150 67"
              stroke="#6FB0C2" stroke-width="3" fill="none" stroke-linecap="round"/>
        """,
        "#DCEEF5",
    ),
    "egg": (
        """
        <ellipse cx="150" cy="97" rx="90" ry="10" fill="#00000014"/>
        <ellipse cx="150" cy="95" rx="90" ry="10" fill="#F3E6BF"/>
        <path d="M85 70 Q90 35 150 40 Q205 42 210 75 Q212 95 150 95 Q90 95 85 70 Z" fill="#FFFFFF"/>
        <ellipse cx="150" cy="68" rx="26" ry="24" fill="#FFC107"/>
        <ellipse cx="141" cy="59" rx="7" ry="6" fill="#FFE082"/>
        """,
        "#FFF6DA",
    ),
    "noodle": (
        """
        <ellipse cx="150" cy="100" rx="90" ry="10" fill="#00000012"/>
        <path d="M70 55 Q150 30 230 55 L220 95 Q150 110 80 95 Z" fill="#FFFFFF" stroke="#C1440E" stroke-width="4"/>
        <path d="M95 60 Q110 75 95 85 M120 55 Q135 72 118 82 M150 53 Q165 70 148 80 M180 55 Q195 72 178 82 M205 58 Q218 75 202 85"
              stroke="#F4A24C" stroke-width="5" fill="none" stroke-linecap="round"/>
        <line x1="225" y1="35" x2="245" y2="80" stroke="#8C6A4A" stroke-width="4" stroke-linecap="round"/>
        <line x1="238" y1="32" x2="258" y2="77" stroke="#8C6A4A" stroke-width="4" stroke-linecap="round"/>
        """,
        "#FFF1DD",
    ),
    "rice": (
        """
        <ellipse cx="150" cy="100" rx="80" ry="10" fill="#00000012"/>
        <path d="M75 55 Q150 32 225 55 L213 95 Q150 112 87 95 Z" fill="#FFFFFF" stroke="#E76F51" stroke-width="4"/>
        <ellipse cx="150" cy="55" rx="45" ry="18" fill="#FDFDFD"/>
        <circle cx="130" cy="52" r="2.5" fill="#EEE"/>
        <circle cx="150" cy="48" r="2.5" fill="#EEE"/>
        <circle cx="168" cy="53" r="2.5" fill="#EEE"/>
        <circle cx="140" cy="60" r="2.5" fill="#EEE"/>
        <circle cx="120" cy="45" r="10" fill="#7FB77E"/>
        <circle cx="178" cy="42" r="8" fill="#E76F51"/>
        """,
        "#FDE8D0",
    ),
    "soup": (
        """
        <ellipse cx="150" cy="94" rx="76" ry="10" fill="#00000012"/>
        <path d="M75 60 Q150 40 225 60 L212 92 Q150 108 88 92 Z" fill="#FFFFFF" stroke="#D4805A" stroke-width="4"/>
        <ellipse cx="150" cy="60" rx="70" ry="12" fill="#F4A24C"/>
        <path d="M120 30 Q112 20 120 10 M150 30 Q142 20 150 10 M180 30 Q172 20 180 10"
              stroke="#C7B9AE" stroke-width="4" fill="none" stroke-linecap="round"/>
        """,
        "#FFE9C7",
    ),
    "salad": (
        """
        <ellipse cx="150" cy="94" rx="78" ry="10" fill="#00000012"/>
        <path d="M75 58 Q150 36 225 58 L213 92 Q150 108 87 92 Z" fill="#FFFFFF" stroke="#7FB77E" stroke-width="4"/>
        <ellipse cx="120" cy="58" rx="22" ry="14" fill="#7FB77E"/>
        <ellipse cx="165" cy="52" rx="20" ry="13" fill="#9CCB8F"/>
        <circle cx="195" cy="65" r="12" fill="#E76F51"/>
        <path d="M110 70 L125 50 L140 70 Z" fill="#F4A24C"/>
        """,
        "#E9F5E3",
    ),
    "tofu": (
        """
        <ellipse cx="150" cy="97" rx="85" ry="10" fill="#00000012"/>
        <ellipse cx="150" cy="95" rx="85" ry="10" fill="#E3F3DE"/>
        <rect x="105" y="45" width="45" height="45" rx="4" fill="#FFFFFF" stroke="#DDEEDD" stroke-width="2"/>
        <rect x="150" y="45" width="45" height="45" rx="4" fill="#F7FBF6" stroke="#DDEEDD" stroke-width="2"/>
        <path d="M100 40 L130 25 L160 40 Z" fill="#7FB77E"/>
        """,
        "#F1F8ED",
    ),
    "bread": (
        """
        <ellipse cx="150" cy="94" rx="85" ry="10" fill="#00000012"/>
        <path d="M85 85 Q80 35 150 32 Q220 35 215 85 Z" fill="#E8B978"/>
        <path d="M85 85 Q150 100 215 85 L215 90 Q150 105 85 90 Z" fill="#C98F4E"/>
        <path d="M110 45 Q150 30 190 45" stroke="#C98F4E" stroke-width="3" fill="none" stroke-linecap="round"/>
        """,
        "#FBF1DE",
    ),
    "default": (
        """
        <circle cx="150" cy="64" r="45" fill="#00000012"/>
        <circle cx="150" cy="62" r="45" fill="#FFFFFF" stroke="#F0DCC8" stroke-width="6"/>
        <circle cx="150" cy="62" r="26" fill="#FFE0CC"/>
        <line x1="60" y1="30" x2="60" y2="95" stroke="#C7B9AE" stroke-width="4" stroke-linecap="round"/>
        <line x1="240" y1="30" x2="240" y2="95" stroke="#C7B9AE" stroke-width="4" stroke-linecap="round"/>
        """,
        "#FFF6EC",
    ),
}

# 料理名に含まれるキーワードから、土台のイラストを選ぶ
DISH_ILLUSTRATION_RULES = [
    ("パスタ", "noodle"), ("そば", "noodle"), ("うどん", "noodle"),
    ("焼きそば", "noodle"), ("春雨", "noodle"), ("そうめん", "noodle"),
    ("トースト", "bread"), ("食パン", "bread"),
    ("カレー", "rice"), ("丼", "rice"), ("チャーハン", "rice"),
    ("雑炊", "rice"), ("餅", "rice"), ("ご飯", "rice"),
    ("スープ", "soup"), ("汁", "soup"),
    ("サラダ", "salad"), ("和え", "salad"), ("ナムル", "salad"),
    ("マリネ", "salad"), ("酢の物", "salad"), ("ごぼう", "salad"),
    ("かぶ", "salad"), ("チンゲン菜", "salad"), ("枝豆", "salad"),
    ("コーン", "salad"), ("水菜", "salad"),
    ("里芋", "default"),
    ("鮭", "fish"), ("さば", "fish"), ("えび", "fish"), ("あさり", "fish"),
    ("たら", "fish"), ("いか", "fish"), ("いわし", "fish"),
    ("はんぺん", "fish"), ("しらす", "fish"), ("ちくわ", "fish"),
    ("卵", "egg"), ("オムレツ", "egg"),
    ("豆腐", "tofu"), ("厚揚げ", "tofu"), ("納豆", "tofu"), ("がんもどき", "tofu"),
    ("鶏", "meat"), ("豚", "meat"), ("牛", "meat"),
    ("ベーコン", "meat"), ("ウインナー", "meat"), ("手羽元", "meat"),
]


def _dish_key(recipe: dict) -> str:
    title = recipe["title"]
    for keyword, key in DISH_ILLUSTRATION_RULES:
        if keyword in title:
            return key
    return "default"


# ---------------------------------------------------------------------------
# 2. レシピIDから決まる、色合いのバリエーション
# ---------------------------------------------------------------------------
# 色相をこの角度だけ回転させることで、同じ土台イラストでも色違いに見せる
_HUE_SHIFTS = [0, 18, -18, 34, -34, 50, -50]


def _hue_shift_for(recipe_id: str) -> int:
    return _HUE_SHIFTS[sum(recipe_id.encode("utf-8")) % len(_HUE_SHIFTS)]


# ---------------------------------------------------------------------------
# 3. 実際の材料から選ぶ、小さな食材アイコン
# ---------------------------------------------------------------------------
def _tomato(x: int, y: int) -> str:
    return (
        f'<circle cx="{x}" cy="{y}" r="8" fill="#E76F51"/>'
        f'<path d="M{x - 4} {y - 7} Q{x} {y - 13} {x + 4} {y - 7}" '
        f'stroke="#5B8C5A" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
    )


def _carrot(x: int, y: int) -> str:
    return (
        f'<path d="M{x - 7} {y - 6} L{x + 7} {y - 6} L{x} {y + 9} Z" fill="#F4A24C"/>'
        f'<path d="M{x - 2} {y - 9} L{x} {y - 15} M{x + 2} {y - 9} L{x + 4} {y - 14}" '
        f'stroke="#7FB77E" stroke-width="2" stroke-linecap="round"/>'
    )


def _leaf(x: int, y: int) -> str:
    return (
        f'<path d="M{x - 8} {y + 6} Q{x - 8} {y - 10} {x + 8} {y - 8} '
        f'Q{x + 6} {y + 8} {x - 8} {y + 6} Z" fill="#7FB77E"/>'
        f'<path d="M{x - 6} {y + 3} Q{x} {y - 2} {x + 5} {y - 5}" '
        f'stroke="#5B8C5A" stroke-width="1.5" fill="none"/>'
    )


def _cheese(x: int, y: int) -> str:
    return (
        f'<path d="M{x - 8} {y + 6} L{x + 8} {y + 6} L{x} {y - 8} Z" fill="#FFC107"/>'
        f'<circle cx="{x - 2}" cy="{y + 2}" r="1.4" fill="#FFF3C4"/>'
        f'<circle cx="{x + 3}" cy="{y + 4}" r="1.4" fill="#FFF3C4"/>'
    )


def _pepper(x: int, y: int) -> str:
    return (
        f'<path d="M{x - 7} {y - 5} Q{x - 9} {y + 8} {x} {y + 9} '
        f'Q{x + 9} {y + 8} {x + 7} {y - 5} Q{x} {y - 1} {x - 7} {y - 5} Z" fill="#7FB77E"/>'
        f'<line x1="{x}" y1="{y - 5}" x2="{x}" y2="{y - 11}" stroke="#5B8C5A" stroke-width="2" stroke-linecap="round"/>'
    )


def _shrimp(x: int, y: int) -> str:
    return (
        f'<path d="M{x - 8} {y} Q{x - 6} {y - 10} {x + 6} {y - 6} '
        f'Q{x + 10} {y - 2} {x + 4} {y + 6} Q{x - 4} {y + 8} {x - 8} {y} Z" fill="#F4A0A0"/>'
    )


def _corn(x: int, y: int) -> str:
    dots = "".join(
        f'<circle cx="{x - 6 + (i % 3) * 6}" cy="{y - 6 + (i // 3) * 6}" r="2" fill="#FFC107"/>'
        for i in range(6)
    )
    return f'<rect x="{x - 9}" y="{y - 9}" width="18" height="18" rx="4" fill="#FFF3C4"/>{dots}'


def _chili(x: int, y: int) -> str:
    return (
        f'<path d="M{x - 7} {y - 6} Q{x + 6} {y - 8} {x + 8} {y + 2} '
        f'Q{x + 6} {y + 9} {x - 2} {y + 6} Q{x - 9} {y + 2} {x - 7} {y - 6} Z" fill="#D62828"/>'
        f'<path d="M{x - 7} {y - 6} L{x - 10} {y - 11}" stroke="#5B8C5A" stroke-width="2" stroke-linecap="round"/>'
    )


_ACCENT_RULES: list[tuple[list[str], object]] = [
    (["トマト", "ケチャップ"], _tomato),
    (["にんじん"], _carrot),
    (["ほうれん草", "小松菜", "チンゲン菜", "水菜", "レタス", "キャベツ", "白菜"], _leaf),
    (["チーズ"], _cheese),
    (["ピーマン", "パプリカ", "アスパラ"], _pepper),
    (["えび"], _shrimp),
    (["コーン"], _corn),
    (["キムチ"], _chili),
]

_ACCENT_POSITIONS = [(266, 48), (34, 74)]



def _accent_icons_for(recipe: dict) -> str:
    """レシピの材料から、飾りになる小さな食材アイコンを最大2つ選ぶ。"""
    ingredient_names = [i["name"] for i in recipe["ingredients"]]
    dish_key = _dish_key(recipe)

    chosen = []
    for keywords, icon_fn in _ACCENT_RULES:
        if any(any(k in name for k in keywords) for name in ingredient_names):
            # 土台イラストと同じ食材の重複描画は避ける(例: 魚料理にえびアイコンは付けない)
            if dish_key == "fish" and icon_fn is _shrimp:
                continue
            if dish_key == "salad" and icon_fn is _leaf:
                continue
            chosen.append(icon_fn)
        if len(chosen) >= 2:
            break

    svg_parts = []
    for icon_fn, (x, y) in zip(chosen, _ACCENT_POSITIONS):
        svg_parts.append(
            f'<circle cx="{x}" cy="{y}" r="13" fill="#FFFFFF" opacity="0.9"/>{icon_fn(x, y)}'
        )
    return "".join(svg_parts)


# ---------------------------------------------------------------------------
# 組み立て
# ---------------------------------------------------------------------------
def _render(inner: str, bg: str, hue_shift: int, accents: str) -> str:
    filter_id = f"hue{hue_shift}".replace("-", "m")
    return (
        f'<svg viewBox="{_VIEWBOX}" xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" height="100%" preserveAspectRatio="xMidYMid slice">'
        f"<defs>"
        f'<radialGradient id="bg{filter_id}" cx="50%" cy="35%" r="75%">'
        f'<stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.55"/>'
        f'<stop offset="100%" stop-color="{bg}" stop-opacity="0"/>'
        f"</radialGradient>"
        f'<filter id="{filter_id}">'
        f'<feColorMatrix type="hueRotate" values="{hue_shift}"/>'
        f"</filter>"
        f"</defs>"
        f'<rect width="300" height="120" fill="{bg}"/>'
        f'<g filter="url(#{filter_id})">{inner}</g>'
        f'<rect width="300" height="120" fill="url(#bg{filter_id})"/>'
        f"{accents}"
        f"</svg>"
    )


def get_recipe_illustration(recipe: dict) -> str:
    """レシピごとに見た目が変わる、料理イラスト(SVG文字列)を作る。"""
    key = _dish_key(recipe)
    inner, bg = TEMPLATES[key]
    hue_shift = _hue_shift_for(recipe["id"])
    accents = _accent_icons_for(recipe)
    return _render(inner, bg, hue_shift, accents)


# 検索前のトップ画面などで使う、装飾用の固定イラスト（色変化なし）
ILLUSTRATIONS = {key: _render(inner, bg, 0, "") for key, (inner, bg) in TEMPLATES.items()}
