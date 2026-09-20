"""ユーザーが自分で作ったレシピを保存する処理（Supabase版）。

以前はJSONファイルに保存していたが、利用者ごとに別々のマイレシピを
持てるように、Supabaseのcustom_recipesテーブルに保存する形に変更した。
データの形（項目）は本体のレシピと同じにしているので、検索・お気に入り・
週間献立プランナーなど、アプリの他の機能からも同じように扱える。
"""

import uuid

from auth import get_supabase_client

SOURCE_LABEL = "マイレシピ（自分で登録）"


def load_custom_recipes(user_id: str) -> list[dict]:
    """指定した利用者が追加したレシピの一覧を読み込む。"""
    client = get_supabase_client()
    response = client.table("custom_recipes").select("*").eq("user_id", user_id).execute()
    return [_row_to_recipe(row) for row in response.data]


def load_all_custom_recipes() -> list[dict]:
    """全利用者分のマイレシピを読み込む（ベクトルDBの一括作り直し専用）。"""
    client = get_supabase_client()
    response = client.table("custom_recipes").select("*").execute()
    return [_row_to_recipe(row) for row in response.data]


def add_custom_recipe(user_id: str, recipe: dict) -> dict:
    """新しいレシピを1件追加する。

    他のレシピと重ならない専用のID（例: custom_xxxxxxxx）を振ってから保存する。
    戻り値: IDが振られた後のレシピの中身
    """
    recipe = dict(recipe)
    recipe["id"] = f"custom_{uuid.uuid4().hex[:8]}"

    client = get_supabase_client()
    client.table("custom_recipes").insert(_recipe_to_row(user_id, recipe)).execute()
    return recipe


def delete_custom_recipe(user_id: str, recipe_id: str) -> None:
    """指定したIDのレシピを削除する。"""
    client = get_supabase_client()
    client.table("custom_recipes").delete().eq("user_id", user_id).eq("id", recipe_id).execute()


def _recipe_to_row(user_id: str, recipe: dict) -> dict:
    return {
        "id": recipe["id"],
        "user_id": user_id,
        "title": recipe["title"],
        "category": recipe["category"],
        "time_minutes": recipe["time_minutes"],
        "difficulty": recipe["difficulty"],
        "price_yen": recipe["price_yen"],
        "ingredients": recipe["ingredients"],
        "steps": recipe["steps"],
        "tags": recipe.get("tags", []),
        "storage": recipe.get("storage", ""),
        "arrange_tip": recipe.get("arrange_tip", ""),
        "nutrition_note": recipe.get("nutrition_note", ""),
    }


def _row_to_recipe(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "time_minutes": row["time_minutes"],
        "difficulty": row["difficulty"],
        "price_yen": row["price_yen"],
        "ingredients": row["ingredients"],
        "steps": row["steps"],
        "tags": row.get("tags") or [],
        "storage": row.get("storage") or "",
        "arrange_tip": row.get("arrange_tip") or "",
        "nutrition_note": row.get("nutrition_note") or "",
        "source": SOURCE_LABEL,
    }
