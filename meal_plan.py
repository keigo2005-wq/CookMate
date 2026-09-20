"""1週間分の献立プランと、そこから作る買い物リスト（Supabase版）。

以前は1つのJSONファイルに保存していたが、利用者ごとに別々の献立を
持てるように、Supabaseのmeal_plansテーブルに保存する形に変更した。
"""

from auth import get_supabase_client

DAYS = ["月", "火", "水", "木", "金", "土", "日"]


def load_plan(user_id: str) -> dict[str, str | None]:
    """指定した利用者の、曜日ごとに割り当てられているレシピIDを読み込む。"""
    client = get_supabase_client()
    response = client.table("meal_plans").select("day, recipe_id").eq("user_id", user_id).execute()
    plan: dict[str, str | None] = {day: None for day in DAYS}
    for row in response.data:
        plan[row["day"]] = row["recipe_id"]
    return plan


def set_meal(user_id: str, day: str, recipe_id: str | None) -> None:
    """指定した曜日に、レシピを割り当てる（Noneで未定に戻す）。"""
    client = get_supabase_client()
    if recipe_id is None:
        client.table("meal_plans").delete().eq("user_id", user_id).eq("day", day).execute()
    else:
        client.table("meal_plans").upsert(
            {"user_id": user_id, "day": day, "recipe_id": recipe_id},
            on_conflict="user_id,day",
        ).execute()


def build_shopping_list(
    plan: dict[str, str | None], recipes_by_id: dict[str, dict]
) -> list[dict]:
    """献立に登録した全レシピの材料をまとめて、買い物リストを作る。

    同じ食材が複数のレシピで使われる場合は、分量をまとめて表示する。
    「水」は誰の家にもあるとみなし、リストから除く。
    """
    amounts_by_ingredient: dict[str, list[str]] = {}

    for recipe_id in plan.values():
        if not recipe_id or recipe_id not in recipes_by_id:
            continue
        for ingredient in recipes_by_id[recipe_id]["ingredients"]:
            name = ingredient["name"]
            if name == "水":
                continue
            amounts_by_ingredient.setdefault(name, []).append(ingredient["amount"])

    return [
        {"name": name, "amounts": amounts}
        for name, amounts in sorted(amounts_by_ingredient.items())
    ]
