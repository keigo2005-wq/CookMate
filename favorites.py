"""お気に入りレシピの保存・読み込み（Supabase版）。

以前は1つのJSONファイルに保存していたが、利用者ごとに別々の
お気に入りを持てるように、Supabaseのfavoritesテーブルに
「誰の（user_id）」「どのレシピ（recipe_id）」かをセットで保存する形に変更した。
"""

from auth import get_supabase_client


def load_favorite_ids(user_id: str) -> list[str]:
    """指定した利用者が、お気に入りに入れたレシピIDのリストを読み込む。"""
    client = get_supabase_client()
    response = client.table("favorites").select("recipe_id").eq("user_id", user_id).execute()
    return [row["recipe_id"] for row in response.data]


def is_favorite(user_id: str, recipe_id: str) -> bool:
    """指定したレシピが、お気に入りに入っているかを返す。"""
    return recipe_id in load_favorite_ids(user_id)


def toggle_favorite(user_id: str, recipe_id: str) -> bool:
    """お気に入りへの追加・解除を切り替える。

    戻り値: 切り替え後に「お気に入りに入っている」状態なら True
    """
    client = get_supabase_client()
    if is_favorite(user_id, recipe_id):
        client.table("favorites").delete().eq("user_id", user_id).eq(
            "recipe_id", recipe_id
        ).execute()
        return False

    client.table("favorites").insert({"user_id": user_id, "recipe_id": recipe_id}).execute()
    return True
