"""文章を埋め込みベクトルに変換するための、基本となる処理。

埋め込みベクトルとは、文章を「意味を表す数字の列」に変換したもの。
似た意味の文章ほど、数字の列同士が近くなる。これを使うと、
同じ単語が入っていなくても、意味が近いレシピを探せるようになる。

Claude APIには埋め込み機能が無いため、無料で使えるモデルを
パソコンの中だけで動かして計算する(追加のAPIキーや料金は不要)。

計算した埋め込みベクトルの保存・検索は、この上に構築した
vector_store.py（ベクトルデータベース）が担当する。
"""

import truststore

# モデルのダウンロード時に、ネットワーク環境によっては証明書エラーに
# なることがある(この学校のネットワークで発生した)。OSが信頼している
# 証明書をそのまま使うことで、この問題を避ける。Supabaseへの接続でも
# 同じ仕組みを使っている(auth.py参照)。何度呼び出しても安全な処理なので、
# ここでも呼び出しておくことで、embeddings.pyだけを使う場合にも対応する。
truststore.inject_into_ssl()

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"

_model: SentenceTransformer | None = None


def load_model() -> SentenceTransformer:
    """埋め込みモデルを読み込む。

    初回はモデルファイルをダウンロードするため少し時間がかかるが、
    2回目以降はパソコンに保存されたファイルを使うので速い。
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def recipe_to_text(recipe: dict) -> str:
    """レシピを、意味検索用の1つの文章にまとめる。"""
    tags = "、".join(recipe["tags"])
    return (
        f"{recipe['title']}。カテゴリ:{recipe['category']}。"
        f"特徴:{tags}。{recipe['nutrition_note']}"
    )


def embed_texts(texts: list[str]) -> np.ndarray:
    """複数の文章を、まとめて埋め込みベクトルに変換する(レシピ側で使う)。"""
    model = load_model()
    # 使用しているモデル(e5系)は、検索される側の文章に"passage: "、
    # 検索する側の文章に"query: "を付けると精度が上がる決まりになっている
    prefixed = [f"passage: {t}" for t in texts]
    return model.encode(prefixed, normalize_embeddings=True)


def embed_query(text: str) -> np.ndarray:
    """検索クエリ(ユーザーが入力した文章)を埋め込みベクトルに変換する。"""
    model = load_model()
    return model.encode([f"query: {text}"], normalize_embeddings=True)[0]
