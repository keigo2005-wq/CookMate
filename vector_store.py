"""ベクトルデータベース(Chroma)を使った、レシピの意味検索。

以前は埋め込みベクトルをJSONファイルに保存し、Pythonで自分で
コサイン類似度を計算していた。ここでは専用のベクトルデータベースに
保存し、似ているレシピを探す処理そのものをデータベース側に任せる。

Chromaは無料で、パソコンの中だけで動く(サーバーもAPIキーも不要)。
"""

import json
import os
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")  # 利用状況の外部送信をしない

import chromadb
import streamlit as st
from chromadb.config import Settings

from embeddings import embed_query, embed_texts, recipe_to_text

CHROMA_PATH = Path(__file__).parent / "data" / "chroma_db"
COLLECTION_NAME = "recipes"
RECIPES_PATH = Path(__file__).parent / "data" / "recipes.json"


@st.cache_resource
def _get_client():
    """Chromaへの接続を作る。

    Streamlitは利用者ごとに別スレッドでアプリを動かすため、単純な
    グローバル変数でキャッシュすると、複数の利用者が同時にアクセスした
    ときに接続の作成が重なってしまうことがある。st.cache_resourceを使うと、
    Streamlit自身が「全体で1つだけ作る」ことを保証してくれる。
    """
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False),
    )


def _get_collection():
    """Chromaのコレクション(表のようなもの)を取得する。無ければ作る。"""
    client = _get_client()
    # "hnsw:space": "cosine" は、意味の近さを測る方法にコサイン類似度を使う指定
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(recipes: list[dict]) -> None:
    """全レシピをベクトルデータベースに登録し直す。

    レシピが追加・変更されたときは、この関数を実行して
    データベースの中身を作り直す。
    """
    collection = _get_collection()

    existing_ids = collection.get()["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)

    texts = [recipe_to_text(r) for r in recipes]
    vectors = embed_texts(texts)

    collection.add(
        ids=[r["id"] for r in recipes],
        embeddings=[v.tolist() for v in vectors],
        documents=texts,
        metadatas=[{"title": r["title"], "category": r["category"]} for r in recipes],
    )


def add_recipe_to_index(recipe: dict) -> None:
    """レシピを1件だけ、ベクトルデータベースに追加(または上書き)する。

    ユーザーが「マイレシピ」を登録したときに、全件を作り直さなくても
    その場で意味検索の対象に加えられるようにするための関数。
    """
    collection = _get_collection()
    text = recipe_to_text(recipe)
    vector = embed_texts([text])[0]
    collection.upsert(
        ids=[recipe["id"]],
        embeddings=[vector.tolist()],
        documents=[text],
        metadatas=[{"title": recipe["title"], "category": recipe["category"]}],
    )


def delete_recipe_from_index(recipe_id: str) -> None:
    """レシピを1件、ベクトルデータベースから削除する。"""
    collection = _get_collection()
    collection.delete(ids=[recipe_id])


def load_all_recipes_for_index() -> list[dict]:
    """本体レシピ＋全利用者分のマイレシピを、ベクトルDB作成用に読み込む。

    search.pyを経由すると循環インポートになるため、ここでは
    直接ファイルとcustom_recipesを読み込む。
    """
    from custom_recipes import load_all_custom_recipes

    with open(RECIPES_PATH, encoding="utf-8") as f:
        base_recipes = json.load(f)
    return base_recipes + load_all_custom_recipes()


def query_similar(query_text: str, top_k: int = 100) -> dict[str, float]:
    """検索文と意味が近いレシピを探し、レシピIDと類似度のペアで返す。

    類似度は -1〜1 の数値で、1に近いほど意味が近い。
    """
    collection = _get_collection()
    if collection.count() == 0:
        # Streamlit Cloudなど、パソコンを再起動するとベクトルデータベースが
        # 空になってしまう環境向けに、空だった場合はここで自動的に作り直す
        build_index(load_all_recipes_for_index())
        collection = _get_collection()
        if collection.count() == 0:
            return {}

    query_vector = embed_query(query_text)
    result = collection.query(
        query_embeddings=[query_vector.tolist()],
        n_results=min(top_k, collection.count()),
    )

    ids = result["ids"][0]
    distances = result["distances"][0]
    # コサイン距離(0に近いほど似ている)を、類似度(1に近いほど似ている)に変換する
    return {recipe_id: 1 - distance for recipe_id, distance in zip(ids, distances)}


if __name__ == "__main__":
    all_recipes = load_all_recipes_for_index()
    print(f"{len(all_recipes)}件のレシピをベクトルデータベースに登録しています...")
    build_index(all_recipes)
    print("登録しました:", CHROMA_PATH)

    print("\n試しに検索してみます:「さっぱりした野菜多めの一品」")
    scores = query_similar("さっぱりした野菜多めの一品", top_k=5)
    recipes_by_id = {r["id"]: r for r in all_recipes}
    for recipe_id, score in scores.items():
        print(f"{score:.3f}  {recipes_by_id[recipe_id]['title']}")
