"""利用者ごとのログイン処理（ニックネーム＋パスワード）。

Supabase（無料のデータベースサービス）の users テーブルに、
ニックネームとパスワードを保存する。パスワードはそのままではなく、
bcryptで一方向に変換した「ハッシュ」を保存する。ハッシュからは
元のパスワードを復元できないため、データベースの中身を見られても
パスワードそのものは分からない。
"""

import os

import bcrypt
import streamlit as st
import truststore
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# このパソコンのネットワーク環境によっては、Pythonが持つ証明書の
# リストだけではSupabaseへの接続がSSLエラーになることがある。
# truststoreを使うと、OS(Windows)が信頼している証明書をそのまま
# 使えるようになり、このエラーを避けられる。
truststore.inject_into_ssl()


@st.cache_resource
def get_supabase_client() -> Client:
    """Supabaseへの接続を作る（アプリ内で使い回す）。"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            ".env に SUPABASE_URL と SUPABASE_ANON_KEY が設定されていません。"
            ".env.example を参考に .env を作成してください。"
        )
    return create_client(url, key)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def sign_up(username: str, password: str) -> dict:
    """新しい利用者を登録する。

    戻り値: {"id": ..., "username": ...}
    同じニックネームがすでに使われている場合は ValueError を出す。
    """
    client = get_supabase_client()

    existing = client.table("users").select("id").eq("username", username).execute()
    if existing.data:
        raise ValueError("そのニックネームはすでに使われています。")

    password_hash = _hash_password(password)
    response = (
        client.table("users")
        .insert({"username": username, "password_hash": password_hash})
        .execute()
    )
    user = response.data[0]
    return {"id": user["id"], "username": user["username"]}


def log_in(username: str, password: str) -> dict | None:
    """ログインを試す。

    戻り値: 成功したら {"id": ..., "username": ...}、失敗したら None
    """
    client = get_supabase_client()
    response = (
        client.table("users")
        .select("id, username, password_hash")
        .eq("username", username)
        .execute()
    )
    if not response.data:
        return None

    user = response.data[0]
    if not _verify_password(password, user["password_hash"]):
        return None

    return {"id": user["id"], "username": user["username"]}
