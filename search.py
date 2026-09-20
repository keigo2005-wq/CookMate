"""冷蔵庫の食材条件から、合うレシピを探す検索ロジック。"""

import json
import re
from pathlib import Path

from custom_recipes import load_custom_recipes

RECIPES_PATH = Path(__file__).parent / "data" / "recipes.json"
ALIASES_PATH = Path(__file__).parent / "data" / "ingredient_aliases.json"
CATEGORIES_PATH = Path(__file__).parent / "data" / "ingredient_categories.json"
REFERENCE_PATH = Path(__file__).parent / "data" / "ingredient_reference.json"

# カテゴリの表示順（食材を選びやすい、大まかな並び）
CATEGORY_ORDER = [
    "肉類", "魚介類", "卵・乳製品", "豆腐・大豆製品",
    "野菜", "きのこ類", "ご飯・麺・パン", "調味料",
]

DEFAULT_PRICE_PER_100G = 150  # 価格データが無い食材の、仮の目安価格（円／100g）
DEFAULT_UNKNOWN_AMOUNT_G = 5  # 分量の表記が読み取れない場合の、仮の重さ（g）
DEFAULT_TABLESPOON_G = 15  # 大さじ1の目安（g）
DEFAULT_TEASPOON_G = 5  # 小さじ1の目安（g）


def load_recipes(user_id: str) -> list[dict]:
    """data/recipes.json と、指定した利用者が登録したマイレシピを合わせて返す。"""
    with open(RECIPES_PATH, encoding="utf-8") as f:
        recipes = json.load(f)
    return recipes + load_custom_recipes(user_id)


def load_ingredient_reference() -> dict[str, dict]:
    """data/ingredient_reference.json を読み込む。

    食材ごとに、100gあたりの栄養価・価格・「1個」「大さじ1」のような
    分量表記をグラム数に変換するための目安をまとめたデータ。
    """
    with open(REFERENCE_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_ingredient_aliases() -> dict[str, list[str]]:
    """data/ingredient_aliases.json を読み込む。

    「豚肉」→「豚」のように、一般的な呼び方や、ひらがな・カタカナ違いを
    実際のレシピの食材名に結びつけるための言い換え辞書。
    """
    with open(ALIASES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_common_ingredient_options(user_id: str) -> list[str]:
    """入力欄の候補として出す、よく使われる食材名の一覧を作る。

    レシピデータに実際に登場する食材名と、言い換え辞書のキー（豚肉など
    分かりやすい一般的な呼び方）の両方を候補に含める。
    """
    recipe_names = {i["name"] for r in load_recipes(user_id) for i in r["ingredients"]}
    alias_names = set(load_ingredient_aliases().keys())
    return sorted((recipe_names | alias_names) - ALWAYS_AVAILABLE)


def load_ingredient_categories() -> dict[str, list[str]]:
    """data/ingredient_categories.json を読み込む。

    食材名を「肉類」「野菜」のようなカテゴリに分類したもの。
    選択肢を分けて表示し、食材を選びやすくするために使う。
    """
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_categorized_ingredient_options() -> list[tuple[str, list[str]]]:
    """カテゴリ名と、そのカテゴリに属する食材名リストのペアを、表示順で返す。"""
    categories = load_ingredient_categories()
    return [(name, sorted(categories[name])) for name in CATEGORY_ORDER if name in categories]


_FRACTIONS = {"1/2": 0.5, "1/3": 1 / 3, "1/4": 0.25, "1/8": 0.125}


def _parse_number(text: str) -> float:
    """"1/2" のような分数表記にも対応した数値変換。"""
    if "/" in text:
        num, den = text.split("/")
        return float(num) / float(den)
    return float(text)


def _parse_quantity_prefix(text: str) -> tuple[float, str]:
    """文字列の先頭にある数量（分数・整数）を取り出す。

    戻り値: (数量, 残りの文字列)。数量が無ければ (1.0, 元の文字列)。
    """
    for fraction_text, value in _FRACTIONS.items():
        if text.startswith(fraction_text):
            return value, text[len(fraction_text):]
    match = re.match(r"^(\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1)), text[match.end():]
    return 1.0, text


def amount_to_grams(ingredient_name: str, amount_text: str, reference: dict) -> float:
    """「200g」「大さじ1」「1/4個」のような分量の表記を、おおよそのグラム数に変換する。

    食材ごとに「1個」「1本」などが何gに相当するかは、ingredient_reference.json の
    unit_weights_g を参照する。大さじ・小さじ・少々などは、食材ごとの指定が
    無ければ共通の目安値を使う。
    """
    text = amount_text.strip()
    unit_weights = reference.get(ingredient_name, {}).get("unit_weights_g", {})

    # 「小1パック」のような、食材固有の特殊な表記がそのまま登録されている場合
    if text in unit_weights:
        return unit_weights[text]

    text = text.replace("あれば", "").replace("約", "").strip()
    if text in unit_weights:
        return unit_weights[text]

    if text in ("少々", "ひとつまみ"):
        return 1.0
    if text in ("適量", ""):
        return 5.0

    match = re.match(r"^(\d+(?:\.\d+)?)(g|ml)$", text)
    if match:
        return float(match.group(1))

    match = re.match(r"^大さじ(\d+(?:/\d+)?(?:\.\d+)?)$", text)
    if match:
        return _parse_number(match.group(1)) * unit_weights.get("tablespoon_g", DEFAULT_TABLESPOON_G)

    match = re.match(r"^小さじ(\d+(?:/\d+)?(?:\.\d+)?)$", text)
    if match:
        return _parse_number(match.group(1)) * unit_weights.get("teaspoon_g", DEFAULT_TEASPOON_G)

    match = re.match(r"^(\d+(?:\.\d+)?)cm$", text)
    if match:
        return float(match.group(1)) * unit_weights.get("cm", 10)

    quantity, rest = _parse_quantity_prefix(text)
    if rest in unit_weights:
        return quantity * unit_weights[rest]

    return DEFAULT_UNKNOWN_AMOUNT_G


def estimate_shopping_cost(ingredients: list[dict]) -> int:
    """材料（名前と分量）のリストから、買うのにだいたいいくらかかるかを合計する（円）。

    食材ごとの100gあたり価格 × 実際に使う分量(g) で計算するため、
    同じ食材でもレシピによって必要な量が違えば、金額も変わる。
    """
    reference = load_ingredient_reference()
    total = 0.0
    for ingredient in ingredients:
        name = ingredient["name"]
        amount_text = ingredient.get("amount", "")
        grams = amount_to_grams(name, amount_text, reference) if amount_text else 100.0
        price_per_100g = reference.get(name, {}).get("price_per_100g_yen", DEFAULT_PRICE_PER_100G)
        total += price_per_100g * grams / 100
    return round(total)


NUTRITION_KEYS = ["kcal", "protein", "fat", "carbs", "vitamin_c", "vitamin_e", "calcium", "iron"]


def calculate_nutrition(recipe: dict) -> dict[str, float]:
    """レシピ全体のカロリー・PFC・主なビタミン/ミネラルを合計する。

    食材ごとの100gあたりの栄養価に、実際にレシピで使う分量(g)を掛けて
    合計する。栄養成分表のような厳密な分析値ではなく、「だいたいの目安」
    として扱う。
    """
    reference = load_ingredient_reference()

    totals = {key: 0.0 for key in NUTRITION_KEYS}
    for ingredient in recipe["ingredients"]:
        name = ingredient["name"]
        entry = reference.get(name)
        if entry is None:
            continue
        grams = amount_to_grams(name, ingredient["amount"], reference)
        per_100g = entry["per_100g"]
        for key in NUTRITION_KEYS:
            totals[key] += per_100g.get(key, 0.0) * grams / 100

    # PFCバランス：3大栄養素のうち、それぞれ何%のカロリーを占めるか
    # (たんぱく質・炭水化物は1gあたり4kcal、脂質は1gあたり9kcal)
    protein_kcal = totals["protein"] * 4
    fat_kcal = totals["fat"] * 9
    carbs_kcal = totals["carbs"] * 4
    pfc_kcal_total = protein_kcal + fat_kcal + carbs_kcal

    if pfc_kcal_total > 0:
        totals["protein_ratio"] = round(protein_kcal / pfc_kcal_total * 100)
        totals["fat_ratio"] = round(fat_kcal / pfc_kcal_total * 100)
        totals["carbs_ratio"] = round(carbs_kcal / pfc_kcal_total * 100)
    else:
        totals["protein_ratio"] = totals["fat_ratio"] = totals["carbs_ratio"] = 0

    return totals


# 厚生労働省「日本人の食事摂取基準」で、脂質由来エネルギー比率の目標量は
# 20〜30%とされている。この上限に収まる料理を「ダイエット向き」の目安とする。
DIET_FAT_RATIO_MAX = 30
DIET_KCAL_MAX = 450  # 1品あたりのカロリーが控えめな目安（kcal）

# ビタミンC・ビタミンEを、他のレシピと比べて特に多く含む料理を
# 「美容」に役立つ料理とみなす（全レシピの上位25%程度が目安に収まるよう、
# 実際の分布を確認したうえで基準値を決めた）
BEAUTY_VITAMIN_C_MIN = 40
BEAUTY_VITAMIN_E_MIN = 2.2


def classify_nutrition_tags(nutrition: dict[str, float]) -> list[str]:
    """計算した栄養価から、「ダイエット向き」「美容」のタグを自動で判定する。

    数値による判定なので、実際の栄養価が変わればタグも自動的に更新される。
    """
    tags = []
    if nutrition["kcal"] <= DIET_KCAL_MAX and nutrition["fat_ratio"] <= DIET_FAT_RATIO_MAX:
        tags.append("ダイエット向き")
    if nutrition.get("vitamin_c", 0) >= BEAUTY_VITAMIN_C_MIN or nutrition.get("vitamin_e", 0) >= BEAUTY_VITAMIN_E_MIN:
        tags.append("美容")
    return tags


ALWAYS_AVAILABLE = {"水"}  # 誰の家にもあるとみなし、「追加で必要な食材」に含めない


def _expand_with_aliases(owned_name: str, aliases: dict[str, list[str]]) -> list[str]:
    """入力された食材名を、比較に使うキーワードのリストに展開する。

    「豚肉」なら ["豚肉", "豚"] のように、言い換え辞書にある分かりやすい
    キーワードも合わせて返す。辞書に無ければ、入力そのものだけを返す。
    """
    return [owned_name] + aliases.get(owned_name, [])


def match_ingredients(recipe: dict, ingredients: list[str]) -> tuple[list[str], list[str]]:
    """レシピの材料を、手持ちの食材で「使える」ものと「足りない」ものに分ける。

    「豚肉」という入力が「豚こま肉」という材料に一致する、というように、
    表記のゆれや一般的な呼び方も、言い換え辞書を通して吸収する。

    戻り値: (使える材料名のリスト, 足りない材料名のリスト)
    """
    aliases = load_ingredient_aliases()
    recipe_ingredient_names = [i["name"] for i in recipe["ingredients"]]

    have = []
    for name in recipe_ingredient_names:
        if name in ALWAYS_AVAILABLE:
            have.append(name)
            continue
        for owned in ingredients:
            keywords = _expand_with_aliases(owned, aliases)
            if any(k in name or name in k for k in keywords):
                have.append(name)
                break

    missing = [name for name in recipe_ingredient_names if name not in have]

    return have, missing


def _score_recipe(recipe: dict, ingredients: list[str], tags: list[str]) -> float:
    """1件のレシピについて、入力条件とどれだけ合うか点数をつける。

    - 食材の一致数が多いほど加点する
    - 指定タグ（例：野菜多め）に一致すると加点する
    """
    have, _missing = match_ingredients(recipe, ingredients)
    # 「水」のような、常備品とみなす食材は加点の対象にしない
    # （買い出しの手間が減るわけではないため、実際に入力された食材だけを評価する）
    ingredient_score = len([name for name in have if name not in ALWAYS_AVAILABLE])

    tag_score = sum(1 for tag in tags if tag in recipe["tags"])

    return ingredient_score * 2 + tag_score


# 意味検索のスコア(-1〜1)を、食材一致スコア(0〜数点)と足し合わせるための倍率
SEMANTIC_SCORE_WEIGHT = 5


def search_recipes(
    user_id: str,
    ingredients: list[str],
    max_time_minutes: int | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
    query_text: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    """条件に合うレシピを、点数の高い順に top_k 件返す。

    Args:
        user_id: 検索する利用者のID（本人のマイレシピも検索対象に含める）
        ingredients: 手持ちの食材名のリスト（例：["鶏むね肉", "キャベツ"]）
        max_time_minutes: この時間以内で作れるレシピに絞る（Noneなら絞らない）
        tags: 欲しい条件のタグ（例：["野菜多め", "時短"]）
        category: 絞り込みたいカテゴリ（例："主菜"、Noneなら絞らない）
        query_text: 「こんな料理が食べたい」という自由記述。指定すると、
            埋め込みベクトルによる意味の近さも点数に加える
        top_k: 返すレシピの件数
    """
    tags = tags or []
    recipes = load_recipes(user_id)

    if max_time_minutes is not None:
        recipes = [r for r in recipes if r["time_minutes"] <= max_time_minutes]

    if category:
        recipes = [r for r in recipes if r["category"] == category]

    semantic = {}
    if query_text:
        from vector_store import query_similar  # 使う時だけ読み込む(モデルの読み込みに時間がかかるため)

        semantic = query_similar(query_text, top_k=len(recipes) or 1)

    scored = []
    for recipe in recipes:
        structured_score = _score_recipe(recipe, ingredients, tags)
        semantic_score = semantic.get(recipe["id"], 0.0) * SEMANTIC_SCORE_WEIGHT
        scored.append((recipe, structured_score + semantic_score))

    if not query_text:
        # 自由記述が無いときは、これまで通り食材が1つも合わないレシピは除く
        scored = [pair for pair in scored if pair[1] > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [recipe for recipe, _score in scored[:top_k]]


def find_near_miss_recipes(
    user_id: str,
    ingredients: list[str],
    exclude_ids: set[str],
    max_time_minutes: int | None = None,
    category: str | None = None,
    max_missing: int = 2,
    top_k: int = 2,
) -> list[dict]:
    """あと少し食材を買い足せば作れる、というレシピを探す。

    「検索結果には入らなかったが、足りない材料が少ないレシピ」を見つけることで、
    「これも買えば作れます」という提案ができるようにする。
    """
    recipes = load_recipes(user_id)
    recipes = [r for r in recipes if r["id"] not in exclude_ids]

    if max_time_minutes is not None:
        recipes = [r for r in recipes if r["time_minutes"] <= max_time_minutes]

    if category:
        recipes = [r for r in recipes if r["category"] == category]

    candidates = []
    for recipe in recipes:
        have, missing = match_ingredients(recipe, ingredients)
        # 「水」だけ一致していても、実際には何も使えていないので対象にしない
        real_have = [name for name in have if name not in ALWAYS_AVAILABLE]
        if real_have and 1 <= len(missing) <= max_missing:
            candidates.append((recipe, len(missing), len(real_have)))

    candidates.sort(key=lambda triple: (triple[1], -triple[2]))
    return [recipe for recipe, _missing_n, _have_n in candidates[:top_k]]
