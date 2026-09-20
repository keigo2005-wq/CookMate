"""data/recipes.json の価格目安・栄養タグを、最新のingredient_reference.jsonを
もとに作り直すスクリプト。

食材データ(ingredient_reference.json)を更新したときに、一度だけ実行する。
"""

import json

from search import (
    ALWAYS_AVAILABLE,
    RECIPES_PATH,
    calculate_nutrition,
    classify_nutrition_tags,
    estimate_shopping_cost,
)

MANUAL_ONLY_TAGS = {"ダイエット向き", "美容"}  # これらは自動判定に置き換える対象


def main() -> None:
    with open(RECIPES_PATH, encoding="utf-8") as f:
        recipes = json.load(f)

    for recipe in recipes:
        priced_ingredients = [i for i in recipe["ingredients"] if i["name"] not in ALWAYS_AVAILABLE]
        recipe["price_yen"] = estimate_shopping_cost(priced_ingredients)

        nutrition = calculate_nutrition(recipe)
        auto_tags = classify_nutrition_tags(nutrition)
        kept_tags = [t for t in recipe["tags"] if t not in MANUAL_ONLY_TAGS]
        recipe["tags"] = kept_tags + [t for t in auto_tags if t not in kept_tags]

    with open(RECIPES_PATH, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    prices = [r["price_yen"] for r in recipes]
    diet_count = sum(1 for r in recipes if "ダイエット向き" in r["tags"])
    beauty_count = sum(1 for r in recipes if "美容" in r["tags"])
    print(f"{len(recipes)}件のレシピを更新しました。")
    print(f"価格目安: 最小{min(prices)}円 / 最大{max(prices)}円 / 平均{sum(prices)/len(prices):.0f}円")
    print(f"ダイエット向きタグ: {diet_count}件 / 美容タグ: {beauty_count}件")


if __name__ == "__main__":
    main()
