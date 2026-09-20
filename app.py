"""CookMate: 冷蔵庫の食材から、合うレシピをAIが提案するWeb画面。"""

import streamlit as st

from auth import log_in, sign_up
from custom_recipes import add_custom_recipe, delete_custom_recipe, load_custom_recipes
from favorites import load_favorite_ids, toggle_favorite
from icons import icon
from illustrations import ILLUSTRATIONS, get_recipe_illustration
from llm import generate_answer, generate_weekly_plan
from meal_plan import DAYS, build_shopping_list, load_plan, set_meal
from search import (
    calculate_nutrition,
    classify_nutrition_tags,
    estimate_shopping_cost,
    find_near_miss_recipes,
    load_categorized_ingredient_options,
    load_recipes,
    match_ingredients,
    search_recipes,
)

st.set_page_config(page_title="CookMate", page_icon="assets/icon.png", layout="centered")

# タグごとの配色（背景は淡いトーン、文字はその濃いトーンにする
# 「トーナルカラー」の考え方。Material Design 3 のchipの配色にならった）
TAG_COLORS = {
    "時短": ("#FFE7C2", "#7A4A00"),
    "野菜多め": ("#DCEFCE", "#33591C"),
    "高たんぱく": ("#FFDBC9", "#7A2E0E"),
    "節約": ("#D3E8EC", "#0B4650"),
    "作り置き向き": ("#E8DEFA", "#4B2E82"),
    "定番": ("#F0E4D4", "#5C4630"),
    "ダイエット向き": ("#D7ECDD", "#1E5631"),
    "美容": ("#FBDCE6", "#7D2350"),
}
DEFAULT_TAG_COLOR = ("#EEE6E0", "#4A3B34")

SORT_OPTIONS = {
    "おすすめ順": None,
    "時間が短い順": ("time_minutes", False),
    "費用が安い順": ("price_yen", False),
    "難易度が易しい順": ("difficulty", False),
}

PFC_COLORS = {"protein": "#B3401D", "fat": "#B8860B", "carbs": "#3E7CB1"}

PAGE_CSS = """
<style>
/* ---- Material Design 3 に沿ったカラートークン ----
   温かみのあるオレンジを基準に、明るいトーン(コンテナ)と
   濃いトーン(オンコンテナ)のペアで配色を統一している。 */
:root {
    --md-primary: #B3401D;
    --md-on-primary: #FFFFFF;
    --md-primary-container: #FFDBC9;
    --md-on-primary-container: #3A0F00;
    --md-secondary-container: #F4E0D6;
    --md-on-secondary-container: #2B1D15;
    --md-surface: #FFF8F5;
    --md-surface-container: #FFFFFF;
    --md-surface-container-high: #FBEEE7;
    --md-on-surface: #271A13;
    --md-on-surface-variant: #6B5A50;
    --md-outline: #85736A;
    --md-outline-variant: #E4D4C9;
    --md-elevation-1: 0px 1px 2px rgba(0,0,0,0.20), 0px 1px 3px 1px rgba(60,30,10,0.12);
    --md-elevation-2: 0px 1px 2px rgba(0,0,0,0.22), 0px 2px 8px 1px rgba(60,30,10,0.16);
}

/* 画面幅より横に広がってしまう要素があっても、横スクロールが
   出ないようにする保険 */
body { overflow-x: hidden; }
body, [class*="st-emotion-cache"] { color: var(--md-on-surface); }

.recipe-card h3 {
    overflow-wrap: break-word;
    word-break: break-word;
}

.brand-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 2px;
}
.brand-row h1 {
    margin: 0;
    font-size: 2rem;
}
.subtitle {
    color: var(--md-on-surface-variant);
    font-size: 0.95em;
    margin-top: 0;
    margin-bottom: 14px;
}
.hero-strip {
    display: flex;
    gap: 8px;
    border-radius: 20px;
    overflow: hidden;
    height: 90px;
    margin-bottom: 18px;
    box-shadow: var(--md-elevation-1);
}
.hero-strip > div { flex: 1; min-width: 0; }
.hero-strip svg { display: block; }

.recipe-card {
    background: var(--md-surface-container);
    border: 1px solid var(--md-outline-variant);
    border-radius: 20px;
    overflow: hidden;
    margin-bottom: 4px;
    box-shadow: var(--md-elevation-1);
}
.recipe-card.best {
    border: 1.5px solid var(--md-primary);
    box-shadow: var(--md-elevation-2);
}
.illustration-banner { height: 110px; }
.illustration-banner svg { display: block; }
.card-body { padding: 18px 20px; }
.best-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--md-primary-container);
    color: var(--md-on-primary-container);
    font-size: 0.78em;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 999px;
    margin-bottom: 8px;
}
.recipe-card h3 { margin: 0 0 8px 0; }
.recipe-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px 14px;
    color: var(--md-on-surface-variant);
    font-size: 0.9em;
    margin-bottom: 10px;
}
.recipe-meta .meta-item { display: inline-flex; align-items: center; gap: 4px; }
.tag-chip {
    display: inline-flex;
    align-items: center;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.78em;
    font-weight: 500;
    margin-right: 6px;
    margin-bottom: 4px;
}
.ingredient-ok, .ingredient-need {
    display: flex;
    align-items: flex-start;
    gap: 6px;
}
.ingredient-ok { color: #2E6B2E; }
.ingredient-need { color: #A03E1A; }
.ingredient-ok svg, .ingredient-need svg { margin-top: 3px; flex-shrink: 0; }

.nutrition-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 10px 0;
    padding: 12px 14px;
    background: var(--md-surface-container-high);
    border-radius: 14px;
}
.nutrition-text {
    flex: 1;
    min-width: 0;
    color: var(--md-on-surface);
    font-size: 0.88em;
}
.pfc-pie {
    width: 52px;
    height: 52px;
    min-width: 52px;
    border-radius: 50%;
    border: 2px solid var(--md-surface-container);
    box-shadow: 0 0 0 1px var(--md-outline-variant);
}
.pfc-legend {
    font-size: 0.78em;
    color: var(--md-on-surface-variant);
    margin-top: 4px;
    line-height: 1.6;
}
.pfc-legend .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 4px;
}
.vitamin-line {
    font-size: 0.76em;
    color: var(--md-on-surface-variant);
    margin-top: 6px;
}

.near-miss-card {
    background: var(--md-surface-container);
    border: 1.5px dashed var(--md-outline);
    border-radius: 20px;
    overflow: hidden;
    margin-bottom: 16px;
}
.near-miss-card .illustration-banner { height: 80px; opacity: 0.9; }
.cost-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--md-primary);
    color: var(--md-on-primary);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 0.85em;
    margin-left: 8px;
}

.ai-comment {
    display: flex;
    gap: 10px;
    background: var(--md-secondary-container);
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 20px;
    font-size: 0.95em;
    color: var(--md-on-secondary-container);
}
.ai-comment svg { flex-shrink: 0; margin-top: 2px; }

.fav-button-row {
    margin-bottom: 20px;
    margin-top: -8px;
}

.section-heading {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--md-on-surface);
}

/* ---- Streamlit標準ウィジェットを、Material Design 3ふうに整える ---- */
.stButton button, .stFormSubmitButton button {
    min-height: 44px;
    padding: 10px 20px;
    font-size: 1rem;
    border-radius: 999px;
    border: 1px solid var(--md-outline-variant);
    box-shadow: none;
    transition: box-shadow 0.15s ease;
}
.stButton button:hover, .stFormSubmitButton button:hover {
    box-shadow: var(--md-elevation-1);
    border-color: var(--md-primary);
}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
    border: none;
    box-shadow: var(--md-elevation-1);
}
.stTabs [data-baseweb="tab"] {
    min-height: 44px;
    padding: 10px 14px;
    border-radius: 12px 12px 0 0;
}
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
    min-height: 44px;
    border-radius: 14px;
}
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    border-radius: 14px;
}
[data-testid="stExpander"] {
    border-radius: 16px;
    border: 1px solid var(--md-outline-variant);
    overflow: hidden;
}
[data-testid="stForm"] {
    border-radius: 20px;
    border: 1px solid var(--md-outline-variant);
    box-shadow: var(--md-elevation-1);
}

/* スマホなど幅の狭い画面では、文字が小さくなりすぎないよう
   細かい表示部分のフォントサイズを少し大きくする */
@media (max-width: 640px) {
    .recipe-meta { font-size: 1em; }
    .tag-chip { font-size: 0.9em; padding: 4px 12px; }
    .nutrition-text { font-size: 1em; }
    .pfc-legend { font-size: 0.9em; }
    .cost-badge { font-size: 0.95em; }
    .best-badge { font-size: 0.9em; }
    .ai-comment { font-size: 1em; }
    .hero-strip { height: 70px; }
    .illustration-banner { height: 90px; }
    .near-miss-card .illustration-banner { height: 70px; }
}
</style>
"""

st.markdown(PAGE_CSS, unsafe_allow_html=True)

st.markdown(
    f'<div class="brand-row">{icon("chef-hat", size=34, color="var(--md-primary)")}<h1>CookMate</h1></div>',
    unsafe_allow_html=True,
)
st.markdown('<p class="subtitle">〜 あなたの冷蔵庫の、料理の相棒 〜</p>', unsafe_allow_html=True)

hero_keys = ["meat", "salad", "soup", "rice"]
hero_html = '<div class="hero-strip">' + "".join(
    f"<div>{ILLUSTRATIONS[k]}</div>" for k in hero_keys
) + "</div>"
st.markdown(hero_html, unsafe_allow_html=True)

if "user" not in st.session_state:
    st.write("ログインすると、あなた専用のお気に入り・週間献立・マイレシピが使えます。")

    login_tab, signup_tab = st.tabs([":material/login: ログイン", ":material/person_add: 新規登録"])

    with login_tab:
        with st.form("login_form"):
            login_username = st.text_input("ニックネーム", key="login_username")
            login_password = st.text_input("パスワード", type="password", key="login_password")
            login_submitted = st.form_submit_button(":material/login: ログイン")
        if login_submitted:
            if not login_username.strip() or not login_password:
                st.error("ニックネームとパスワードを入力してください。")
            else:
                user = log_in(login_username.strip(), login_password)
                if user is None:
                    st.error("ニックネームまたはパスワードが違います。")
                else:
                    st.session_state["user"] = user
                    st.rerun()

    with signup_tab:
        with st.form("signup_form"):
            signup_username = st.text_input("ニックネーム", key="signup_username")
            signup_password = st.text_input("パスワード", type="password", key="signup_password")
            signup_password2 = st.text_input(
                "パスワード（確認）", type="password", key="signup_password2"
            )
            signup_submitted = st.form_submit_button(":material/person_add: 新規登録")
        if signup_submitted:
            if not signup_username.strip() or not signup_password:
                st.error("ニックネームとパスワードを入力してください。")
            elif len(signup_password) < 4:
                st.error("パスワードは4文字以上にしてください。")
            elif signup_password != signup_password2:
                st.error("パスワード（確認）が一致していません。")
            else:
                try:
                    user = sign_up(signup_username.strip(), signup_password)
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.session_state["user"] = user
                    st.rerun()

    st.stop()

current_user = st.session_state["user"]
user_id = current_user["id"]

with st.sidebar:
    st.write(f":material/person: {current_user['username']} さん")
    if st.button(":material/logout: ログアウト"):
        del st.session_state["user"]
        st.rerun()

all_recipes = load_recipes(user_id)
recipes_by_id = {r["id"]: r for r in all_recipes}
all_tags = sorted({tag for r in all_recipes for tag in r["tags"]})
all_categories = sorted({r["category"] for r in all_recipes})
categorized_options = load_categorized_ingredient_options()


def format_ingredient_list(recipe: dict, names: list[str]) -> str:
    """食材名のリストを、分量つきの読みやすい文章にする。"""
    amount_by_name = {i["name"]: i["amount"] for i in recipe["ingredients"]}
    return "、".join(f"{name} {amount_by_name.get(name, '')}".strip() for name in names)


def render_favorite_button(recipe_id: str, key_prefix: str) -> None:
    """お気に入りの追加・解除ボタンを表示する。"""
    is_fav = recipe_id in load_favorite_ids(user_id)
    label = ":material/heart_minus: お気に入りから外す" if is_fav else ":material/favorite: お気に入りに追加"
    st.markdown('<div class="fav-button-row"></div>', unsafe_allow_html=True)
    if st.button(label, key=f"fav_{key_prefix}_{recipe_id}"):
        toggle_favorite(user_id, recipe_id)
        st.rerun()


def build_nutrition_html(recipe: dict) -> str:
    """カロリー・PFCバランスを表す、テキストと円グラフのHTMLを作る。"""
    n = calculate_nutrition(recipe)
    p, f, c = n["protein_ratio"], n["fat_ratio"], n["carbs_ratio"]

    if p + f + c == 0:
        pie_style = "background:#E5DED6;"
    else:
        p_end = p
        f_end = p + f
        pie_style = (
            f'background: conic-gradient('
            f'{PFC_COLORS["protein"]} 0% {p_end}%, '
            f'{PFC_COLORS["fat"]} {p_end}% {f_end}%, '
            f'{PFC_COLORS["carbs"]} {f_end}% 100%);'
        )

    legend = (
        f'<div class="pfc-legend">'
        f'<span class="dot" style="background:{PFC_COLORS["protein"]}"></span>たんぱく質 {p}%<br>'
        f'<span class="dot" style="background:{PFC_COLORS["fat"]}"></span>脂質 {f}%<br>'
        f'<span class="dot" style="background:{PFC_COLORS["carbs"]}"></span>炭水化物 {c}%'
        f"</div>"
    )

    vitamin_line = (
        f'<div class="vitamin-line">'
        f'ビタミンC {n.get("vitamin_c", 0):.0f}mg／'
        f'ビタミンE {n.get("vitamin_e", 0):.1f}mg／'
        f'カルシウム {n.get("calcium", 0):.0f}mg／'
        f'鉄 {n.get("iron", 0):.1f}mg'
        f"</div>"
    )

    return (
        f'<div class="nutrition-row">'
        f'<div class="nutrition-text">{icon("flame", size=16, color=PFC_COLORS["fat"])} 目安 約{n["kcal"]:.0f}kcal　'
        f'（P {n["protein"]:.0f}g ／ F {n["fat"]:.0f}g ／ C {n["carbs"]:.0f}g）'
        f"{legend}"
        f"{vitamin_line}"
        f"</div>"
        f'<div class="pfc-pie" style="{pie_style}"></div>'
        f"</div>"
    )


def render_recipe_card(
    recipe: dict,
    have: list[str] | None,
    missing: list[str] | None,
    is_best: bool,
    key_prefix: str,
) -> None:
    """レシピカードを表示する。have/missing が None のときは、食材の一致状況を表示しない。"""
    stars = "★" * recipe["difficulty"] + "☆" * (3 - recipe["difficulty"])
    tag_chips = "".join(
        f'<span class="tag-chip" style="background:{TAG_COLORS.get(t, DEFAULT_TAG_COLOR)[0]};'
        f'color:{TAG_COLORS.get(t, DEFAULT_TAG_COLOR)[1]}">{t}</span>'
        for t in recipe["tags"]
    )

    ingredient_lines = ""
    if have is not None:
        have_text = format_ingredient_list(recipe, have) if have else "なし"
        if missing:
            missing_dicts = [i for i in recipe["ingredients"] if i["name"] in missing]
            cost = estimate_shopping_cost(missing_dicts)
            missing_text = f"{format_ingredient_list(recipe, missing)}（合計 約{cost}円）"
        else:
            missing_text = "なし(今の食材だけで作れます)"
        ok_icon = icon("check-circle-2", size=16, color="#2E6B2E")
        need_icon = icon("shopping-cart", size=16, color="#A03E1A")
        ingredient_lines = (
            f'<p class="ingredient-ok">{ok_icon} 使える食材: {have_text}</p>'
            f'<p class="ingredient-need">{need_icon} 追加で必要: {missing_text}</p>'
        )

    card_class = "recipe-card best" if is_best else "recipe-card"
    best_badge = (
        f'<span class="best-badge">{icon("star", size=14)} 一番のおすすめ</span>' if is_best else ""
    )

    card_html = (
        f'<div class="{card_class}">'
        f'<div class="illustration-banner">{get_recipe_illustration(recipe)}</div>'
        f'<div class="card-body">{best_badge}'
        f'<h3>{recipe["title"]}</h3>'
        f'<div class="recipe-meta">'
        f'<span class="meta-item">{icon("clock", size=15)} {recipe["time_minutes"]}分</span>'
        f'<span class="meta-item">難易度: {stars}</span>'
        f'<span class="meta-item">{icon("japanese_yen", size=15)} 目安 約{recipe["price_yen"]}円</span>'
        f'</div>'
        f'<div>{tag_chips}</div>'
        f"{build_nutrition_html(recipe)}"
        f"{ingredient_lines}"
        f'</div></div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
    render_favorite_button(recipe["id"], key_prefix)

    with st.expander(":material/menu_book: 作り方を見る"):
        for n, step in enumerate(recipe["steps"], start=1):
            st.write(f"{n}. {step}")
        if recipe.get("arrange_tip"):
            st.info(f"アレンジ: {recipe['arrange_tip']}", icon=":material/lightbulb:")
        st.caption(f"栄養の特徴: {recipe['nutrition_note']}")
        st.caption(f"保存: {recipe['storage']} / 出典: {recipe['source']}")


def render_near_miss_card(recipe: dict, missing: list[str], cost: int) -> None:
    stars = "★" * recipe["difficulty"] + "☆" * (3 - recipe["difficulty"])
    missing_text = format_ingredient_list(recipe, missing)

    card_html = (
        f'<div class="near-miss-card">'
        f'<div class="illustration-banner">{get_recipe_illustration(recipe)}</div>'
        f'<div class="card-body">'
        f'<h3>{recipe["title"]} <span class="cost-badge">あと約{cost}円</span></h3>'
        f'<div class="recipe-meta">'
        f'<span class="meta-item">{icon("clock", size=15)} {recipe["time_minutes"]}分</span>'
        f'<span class="meta-item">難易度: {stars}</span>'
        f'</div>'
        f'<p>{icon("shopping-cart", size=16, color="#A03E1A")} 買い足す食材: {missing_text}</p>'
        f'</div></div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
    render_favorite_button(recipe["id"], "nearmiss")


tab_search, tab_favorites, tab_planner, tab_myrecipes = st.tabs(
    [
        ":material/search: レシピを探す",
        f":material/favorite: お気に入り（{len(load_favorite_ids(user_id))}件）",
        ":material/calendar_month: 週間献立",
        f":material/edit_note: マイレシピ（{len(load_custom_recipes(user_id))}件）",
    ]
)

with tab_search:
    st.write("冷蔵庫にある食材を入れると、条件に合うレシピをAIが提案します。")
    st.caption("条件を選ぶと、候補レシピがすぐに切り替わります。")

    def reset_search_filters() -> None:
        """検索条件を、すべて選んでいない状態に戻す。"""
        for category_name, _ in categorized_options:
            st.session_state.pop(f"ing_{category_name}", None)
        st.session_state.pop("other_ingredients_text", None)
        st.session_state.pop("query_text_area", None)
        st.session_state.pop("max_time_slider", None)
        st.session_state.pop("category_select", None)
        st.session_state.pop("tags_select", None)
        st.session_state.pop("ai_comment", None)

    st.button(":material/restart_alt: 条件をリセット", on_click=reset_search_filters)

    st.write("**使いたい食材**（カテゴリごとに選べます）")
    ingredients: list[str] = []
    columns = st.columns(2)
    for i, (category_name, options) in enumerate(categorized_options):
        with columns[i % 2]:
            selected = st.multiselect(category_name, options=options, key=f"ing_{category_name}")
            ingredients.extend(selected)

    other_text = st.text_input(
        "その他の食材（一覧に無い場合はこちらに入力）",
        placeholder="例：柚子胡椒、パクチー",
        key="other_ingredients_text",
    )
    delimiter = "、" if "、" in other_text else ","
    ingredients.extend([t.strip() for t in other_text.split(delimiter) if t.strip()])

    st.divider()
    query_text = st.text_area(
        "こんな料理が食べたい（自由に書いてください・任意）",
        placeholder="例：さっぱりした野菜多めの一品 / 疲れた日に食べたい元気が出る料理",
        help=(
            "食材名でなく、文章のまま入力できます。意味の近いレシピを"
            "AIが探します。空欄でも検索できます。"
        ),
        key="query_text_area",
    )

    st.divider()
    max_time = st.slider(
        "調理時間の上限（分）", min_value=5, max_value=60, value=20, step=5, key="max_time_slider"
    )
    selected_category = st.selectbox(
        "カテゴリ", options=["すべて"] + all_categories, key="category_select"
    )
    selected_tags = st.multiselect("こだわりたい条件", options=all_tags, key="tags_select")

    category_filter = None if selected_category == "すべて" else selected_category

    st.divider()

    if not ingredients and not query_text.strip():
        st.info("食材を選ぶか、食べたい料理を文章で入力すると、レシピが表示されます。")
    else:
        with st.spinner("レシピを検索しています..."):
            results = search_recipes(
                user_id=user_id,
                ingredients=ingredients,
                max_time_minutes=max_time,
                tags=selected_tags,
                category=category_filter,
                query_text=query_text.strip() or None,
                top_k=6,
            )

        if not results:
            st.warning("条件に合うレシピが見つかりませんでした。食材や条件を変えてみてください。")
        else:
            near_miss_recipes = find_near_miss_recipes(
                user_id=user_id,
                ingredients=ingredients,
                exclude_ids={r["id"] for r in results},
                max_time_minutes=max_time,
                category=category_filter,
            )
            near_miss_info = []
            for r in near_miss_recipes:
                _have, missing = match_ingredients(r, ingredients)
                missing_dicts = [i for i in r["ingredients"] if i["name"] in missing]
                cost = estimate_shopping_cost(missing_dicts)
                near_miss_info.append((r, missing, cost))

            best_id = results[0]["id"]

            st.subheader("候補レシピ")
            sort_choice = st.selectbox("並び替え", options=list(SORT_OPTIONS.keys()))

            results_to_show = list(results)
            sort_key = SORT_OPTIONS[sort_choice]
            if sort_key is not None:
                field, _reverse = sort_key
                results_to_show.sort(key=lambda r: r[field])

            for r in results_to_show:
                have, missing = match_ingredients(r, ingredients)
                render_recipe_card(r, have, missing, is_best=(r["id"] == best_id), key_prefix="result")

            if near_miss_info:
                st.subheader(":material/shopping_cart: あと少しで作れるレシピ")
                for r, missing, cost in near_miss_info:
                    render_near_miss_card(r, missing, cost)

            # AIのコメントは、Claude APIを呼ぶため費用がかかる。
            # 条件を変えるたびに毎回呼ぶと無駄が多いので、ボタンを押した
            # ときだけ生成する。今の検索条件を指紋(フィンガープリント)として
            # 保存しておき、条件が変わったら古いコメントは表示しない。
            current_fingerprint = (
                tuple(sorted(ingredients)),
                query_text.strip(),
                max_time,
                category_filter,
                tuple(sorted(selected_tags)),
                tuple(r["id"] for r in results_to_show),
            )

            if st.button(":material/auto_awesome: AIのおすすめコメントをもらう"):
                query_desc = (
                    f"手持ちの食材: {'、'.join(ingredients) or 'なし'} / "
                    f"食べたいものの説明: {query_text.strip() or 'なし'} / "
                    f"{max_time}分以内 / カテゴリ: {selected_category} / "
                    f"こだわり条件: {'、'.join(selected_tags) or 'なし'}"
                )
                with st.spinner("AIがコメントを作成しています..."):
                    answer = generate_answer(query_desc, results, near_miss_info)
                st.session_state["ai_comment"] = {
                    "fingerprint": current_fingerprint,
                    "answer": answer,
                }

            stored_comment = st.session_state.get("ai_comment")
            if stored_comment and stored_comment["fingerprint"] == current_fingerprint:
                st.markdown(
                    f'<div class="ai-comment">{icon("sparkles", size=18)}'
                    f'<span>{stored_comment["answer"]}</span></div>',
                    unsafe_allow_html=True,
                )
            elif stored_comment:
                st.caption("条件が変わりました。もう一度ボタンを押すと最新のコメントがもらえます。")

with tab_favorites:
    favorite_ids = load_favorite_ids(user_id)
    if not favorite_ids:
        st.info(
            "まだお気に入りがありません。「レシピを探す」タブでカードのボタンから追加できます。",
            icon=":material/favorite:",
        )
    else:
        favorite_recipes = [recipes_by_id[fid] for fid in favorite_ids if fid in recipes_by_id]
        st.write(f"{len(favorite_recipes)}件のお気に入りレシピです。")
        for r in favorite_recipes:
            render_recipe_card(r, have=None, missing=None, is_best=False, key_prefix="favtab")

with tab_planner:
    st.write("曜日ごとにレシピを割り当てると、1週間分の献立と買い物リストが作れます。")

    st.markdown("**:material/auto_awesome: 栄養バランスの組み方が分からない場合は、AIにおまかせできます**")

    goal_presets = st.multiselect(
        "今週の目標（選ぶだけでもOK・複数選択可）",
        options=["高たんぱく重視", "カロリー控えめ（ダイエット向き）", "野菜多め", "時短重視", "節約重視"],
        key="goal_presets_select",
    )
    goal_text = st.text_input(
        "その他の要望（自由記述・任意）",
        placeholder="例：揚げ物は控えたい、魚を多めにしたい",
        key="goal_text_input",
    )
    user_goal = "、".join(goal_presets + ([goal_text.strip()] if goal_text.strip() else []))

    if st.button(":material/auto_awesome: AIに1週間分の献立を設計してもらう"):
        with st.spinner("AIが栄養バランスを考えながら、1週間分の献立を設計しています..."):
            try:
                plan_result = generate_weekly_plan(all_recipes, user_goal=user_goal or None)
            except RuntimeError as e:
                st.error(str(e))
                plan_result = None

        if plan_result is not None:
            assignments = plan_result.get("assignments", {})
            recipe_ids = list(assignments.values())
            is_valid = (
                set(assignments.keys()) == set(DAYS)
                and all(rid in recipes_by_id for rid in recipe_ids)
                and len(set(recipe_ids)) == len(recipe_ids)
            )
            if not is_valid:
                st.error(
                    "AIの提案内容が正しい形式ではなかったため、反映しませんでした。"
                    "もう一度お試しください。"
                )
            else:
                for day, recipe_id in assignments.items():
                    set_meal(user_id, day, recipe_id)
                    # 曜日の選択欄(selectbox)は、一度表示されるとキーごとに
                    # 自分の状態を持ち続け、次の実行でもそちらが優先されてしまう。
                    # そのままだとAIが決めた内容が画面に反映されないため、
                    # 選択欄の状態も合わせて書き換えておく。
                    st.session_state[f"plan_{day}"] = recipe_id
                st.session_state["weekly_plan_reasoning"] = plan_result.get("reasoning", "")
                st.rerun()

    if st.session_state.get("weekly_plan_reasoning"):
        st.info(st.session_state["weekly_plan_reasoning"], icon=":material/auto_awesome:")

    st.divider()

    recipe_options = [r["id"] for r in all_recipes]

    def format_recipe_option(recipe_id: str) -> str:
        return recipes_by_id[recipe_id]["title"]

    def reset_weekly_plan() -> None:
        """1週間分すべてを未定に戻す。"""
        for day in DAYS:
            set_meal(user_id, day, None)
            st.session_state[f"plan_{day}"] = None
        st.session_state.pop("weekly_plan_reasoning", None)
        st.session_state.pop("goal_presets_select", None)
        st.session_state.pop("goal_text_input", None)

    st.button(":material/restart_alt: 献立をすべて未定に戻す", on_click=reset_weekly_plan)

    plan = load_plan(user_id)

    for day in DAYS:
        current_id = plan.get(day)
        state_key = f"plan_{day}"
        if state_key not in st.session_state:
            st.session_state[state_key] = current_id

        # index=Noneを毎回渡すことで、選択済みでも右端に✕(クリア)ボタンが
        # 常に出る状態を保つ。実際の表示値はst.session_state側が優先される。
        selected_id = st.selectbox(
            f"{day}曜日",
            options=recipe_options,
            index=None,
            format_func=format_recipe_option,
            key=state_key,
        )

        if selected_id != current_id:
            set_meal(user_id, day, selected_id)
            st.rerun()

    st.divider()

    assigned_recipes = [recipes_by_id[rid] for rid in plan.values() if rid in recipes_by_id]
    if not assigned_recipes:
        st.info("レシピを割り当てると、ここに献立の詳細と買い物リストが表示されます。")
    else:
        st.subheader(":material/checklist: 献立の詳細")
        for day in DAYS:
            rid = plan.get(day)
            if rid in recipes_by_id:
                st.markdown(f"**{day}曜日**")
                render_recipe_card(
                    recipes_by_id[rid], have=None, missing=None, is_best=False, key_prefix=f"planner_{day}"
                )

        st.subheader(":material/shopping_cart: 今週の買い物リスト")
        shopping_list = build_shopping_list(plan, recipes_by_id)
        flattened_amounts = [
            {"name": item["name"], "amount": amount}
            for item in shopping_list
            for amount in item["amounts"]
        ]
        total_cost = estimate_shopping_cost(flattened_amounts)
        total_kcal = sum(calculate_nutrition(r)["kcal"] for r in assigned_recipes)

        st.write(
            f"献立 {len(assigned_recipes)}食　"
            f"食材 {len(shopping_list)}種類　"
            f"買い物目安 約{total_cost}円　"
            f"合計 約{total_kcal:.0f}kcal"
        )
        for item in shopping_list:
            st.write(f"- {item['name']}（{'、'.join(item['amounts'])}）")

with tab_myrecipes:
    st.write(
        "自分でアレンジしたレシピを登録できます。登録すると、"
        "検索・お気に入り・週間献立プランナーからも使えるようになります。"
    )

    with st.form("add_custom_recipe_form", clear_on_submit=True):
        title = st.text_input("レシピ名 *")

        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("カテゴリ", options=all_categories)
        with col2:
            time_minutes = st.number_input("調理時間（分）", min_value=1, max_value=180, value=15)
        with col3:
            difficulty = st.selectbox(
                "難易度", options=[1, 2, 3], format_func=lambda d: "★" * d + "☆" * (3 - d)
            )

        price_yen = st.number_input(
            "費用目安（円）",
            min_value=0,
            max_value=5000,
            value=0,
            step=10,
            help="0のままにすると、材料から自動で見積もります。",
        )

        ingredients_text = st.text_area(
            "材料 *（1行に1つ、「食材名,分量」の形で入力）",
            placeholder="鶏むね肉,200g\nキャベツ,1/4個\n塩,少々",
            height=120,
        )
        steps_text = st.text_area(
            "作り方 *（1行に1手順）",
            placeholder="鶏むね肉を一口大に切る\nフライパンで両面焼く\n塩で味を整えて完成",
            height=120,
        )

        custom_tags = st.multiselect("タグ（任意）", options=all_tags)
        storage = st.text_input("保存（任意）", placeholder="例：冷蔵で2日保存可")
        arrange_tip = st.text_input("アレンジ方法（任意）", placeholder="例：チーズをのせても美味しい")
        nutrition_note = st.text_input(
            "栄養の特徴（任意）", placeholder="例：高たんぱくで野菜も摂れる一品"
        )

        submitted_recipe = st.form_submit_button(":material/add: レシピを登録する")

    if submitted_recipe:
        errors = []
        if not title.strip():
            errors.append("レシピ名を入力してください。")

        parsed_ingredients = []
        for line in ingredients_text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 1)
            name = parts[0].strip()
            amount = parts[1].strip() if len(parts) > 1 else ""
            if name:
                parsed_ingredients.append({"name": name, "amount": amount})
        if not parsed_ingredients:
            errors.append("材料を1つ以上、「食材名,分量」の形で入力してください。")

        parsed_steps = [line.strip() for line in steps_text.splitlines() if line.strip()]
        if not parsed_steps:
            errors.append("作り方を1つ以上入力してください。")

        if errors:
            for e in errors:
                st.error(e)
        else:
            auto_nutrition_tags = classify_nutrition_tags(
                calculate_nutrition({"ingredients": parsed_ingredients})
            )
            combined_tags = custom_tags + [t for t in auto_nutrition_tags if t not in custom_tags]
            new_recipe = {
                "title": title.strip(),
                "servings": "1人分",
                "time_minutes": int(time_minutes),
                "category": category,
                "tags": combined_tags,
                "ingredients": parsed_ingredients,
                "steps": parsed_steps,
                "nutrition_note": nutrition_note.strip() or "ユーザーが登録したオリジナルレシピです。",
                "price_yen": int(price_yen) if price_yen else estimate_shopping_cost(parsed_ingredients),
                "difficulty": int(difficulty),
                "storage": storage.strip() or "お早めにお召し上がりください",
                "source": "マイレシピ（自分で登録）",
                "arrange_tip": arrange_tip.strip() or "自分好みに自由にアレンジしてみましょう。",
            }
            saved_recipe = add_custom_recipe(user_id, new_recipe)

            with st.spinner("意味検索でも探せるように登録しています..."):
                try:
                    from vector_store import add_recipe_to_index

                    add_recipe_to_index(saved_recipe)
                except Exception as e:
                    st.warning(
                        f"意味検索への登録に失敗しました（食材での検索は通常通り使えます）: {e}"
                    )

            st.success(f"「{saved_recipe['title']}」を登録しました！")
            st.rerun()

    custom_recipes = load_custom_recipes(user_id)
    if custom_recipes:
        st.divider()
        st.subheader(f":material/edit_note: マイレシピ一覧（{len(custom_recipes)}件）")
        for r in custom_recipes:
            render_recipe_card(r, have=None, missing=None, is_best=False, key_prefix="myrecipe")
            if st.button(f":material/delete: 「{r['title']}」を削除する", key=f"delete_{r['id']}"):
                delete_custom_recipe(user_id, r["id"])
                try:
                    from vector_store import delete_recipe_from_index

                    delete_recipe_from_index(r["id"])
                except Exception:
                    pass
                st.rerun()
