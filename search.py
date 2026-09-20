"""冷蔵庫の食材条件から、合うレシピを探す検索ロジック。"""

import json
from pathlib import Path

from custom_recipes import load_custom_recipes

RECIPES_PATH = Path(__file__).parent / "data" / "recipes.json"
PRICES_PATH = Path(__file__).parent / "data" / "ingredient_prices.json"
ALIASES_PATH = Path(__file__).parent / "data" / "ingredient_aliases.json"
CATEGORIES_PATH = Path(__file__).parent / "data" / "ingredient_categories.json"
NUTRITION_PATH = Path(__file__).parent / "data" / "ingredient_nutrition.json"

# カテゴリの表示順（食材を選びやすい、大まかな並び）
CATEGORY_ORDER = [
    "肉類", "魚介類", "卵・乳製品", "豆腐・大豆製品",
    "野菜", "きのこ類", "ご飯・麺・パン", "調味料",
]

DEFAULT_INGREDIENT_PRICE = 100  # 価格が分からない食材の、仮の目安価格（円）


def load_recipes(user_id: str) -> list[dict]:
    """data/recipes.json と、指定した利用者が登録したマイレシピを合わせて返す。"""
    with open(RECIPES_PATH, encoding="utf-8") as f:
        recipes = json.load(f)
    return recipes + load_custom_recipes(user_id)


def load_ingredient_prices() -> dict[str, int]:
    """data/ingredient_prices.json を読み込んで、食材ごとの目安価格を返す。"""
    with open(PRICES_PATH, encoding="utf-8") as f:
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


def estimate_shopping_cost(missing_ingredients: list[str]) -> int:
    """足りない食材を買うのに、だいたいいくらかかるかを合計する（円）。"""
    prices = load_ingredient_prices()
    return sum(prices.get(name, DEFAULT_INGREDIENT_PRICE) for name in missing_ingredients)


def load_ingredient_nutrition() -> dict[str, dict[str, float]]:
    """data/ingredient_nutrition.json を読み込んで、食材ごとの栄養価の目安を返す。"""
    with open(NUTRITION_PATH, encoding="utf-8") as f:
        return json.load(f)


def calculate_nutrition(recipe: dict) -> dict[str, float]:
    """レシピ全体のカロリーとPFC（たんぱく質・脂質・炭水化物）を合計する。

    食材ごとの目安値を足し合わせるだけの、簡易的な計算方法。
    栄養成分表のような厳密な分析値ではなく、「だいたいの目安」として扱う。
    """
    nutrition_table = load_ingredient_nutrition()

    totals = {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    for ingredient in recipe["ingredients"]:
        values = nutrition_table.get(ingredient["name"])
        if values is None:
            continue
        for key in totals:
            totals[key] += values[key]

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
