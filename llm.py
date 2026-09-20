"""検索で見つけたレシピを、Claude APIで分かりやすい回答文にする処理。"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

from search import calculate_nutrition

load_dotenv()

MODEL_NAME = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """あなたは、一人暮らしの大学生向けの料理アドバイザーです。
渡された「候補レシピ」「あと少しで作れるレシピ」の中からのみ話してください。
そこに無い料理を、勝手に作り出してはいけません。

材料・調理時間・値段・栄養の詳しい情報は、この後の画面にカードとして
表示されるので、あなたはそれを繰り返してはいけません。

「一番のおすすめ」として指定されたレシピが必ず渡されます。
画面上にも同じレシピが「⭐一番のおすすめ」として表示されるので、
あなたはそれ以外のレシピを一番のおすすめとして紹介してはいけません。

あなたの役割は、次の内容を2〜3文の短いコメントとして伝えることだけです。
- 指定された「一番のおすすめ」のレシピが、なぜこの中で良い選択なのか
- 「あと少しで作れるレシピ」がある場合、何を買い足すとどんな料理が
  作れるようになるかを、一言で前向きに伝える

日本語で、親しみやすく簡潔に、見出しや箇条書きを使わずに答えてください。"""


def _format_recipe(recipe: dict) -> str:
    """1件のレシピを、LLMに渡すためのテキストに変換する。"""
    ingredients = "、".join(
        f"{i['name']}{i['amount']}" for i in recipe["ingredients"]
    )
    steps = "\n".join(f"{n}. {s}" for n, s in enumerate(recipe["steps"], start=1))
    return (
        f"【{recipe['title']}】\n"
        f"カテゴリ: {recipe['category']} / 調理時間: {recipe['time_minutes']}分 "
        f"/ 難易度: {recipe['difficulty']} / 価格目安: 約{recipe['price_yen']}円\n"
        f"材料: {ingredients}\n"
        f"作り方:\n{steps}\n"
        f"栄養の特徴: {recipe['nutrition_note']}\n"
        f"保存: {recipe['storage']}\n"
        f"出典: {recipe['source']}"
    )


def _format_near_miss(recipe: dict, missing: list[str], cost: int) -> str:
    """あと少しで作れるレシピを、買い足す食材と費用つきでテキストにする。"""
    missing_text = "、".join(missing)
    return (
        f"【{recipe['title']}】\n"
        f"調理時間: {recipe['time_minutes']}分 / 難易度: {recipe['difficulty']}\n"
        f"買い足す食材: {missing_text}（合計 約{cost}円）"
    )


def build_user_message(
    user_query: str,
    recipes: list[dict],
    near_miss: list[tuple[dict, list[str], int]] | None = None,
) -> str:
    """ユーザーの質問、候補レシピ、あと少しで作れるレシピをまとめる。"""
    near_miss = near_miss or []

    if not recipes:
        return (
            f"ユーザーの希望: {user_query}\n\n"
            "候補レシピが見つかりませんでした。"
            "条件に合うレシピが無いことを、ユーザーに伝えてください。"
        )

    recipes_text = "\n\n".join(_format_recipe(r) for r in recipes)
    best_title = recipes[0]["title"]
    message = (
        f"ユーザーの希望: {user_query}\n\n候補レシピ:\n{recipes_text}\n\n"
        f"一番のおすすめとして指定されたレシピ: {best_title}"
    )

    if near_miss:
        near_miss_text = "\n\n".join(
            _format_near_miss(r, missing, cost) for r, missing, cost in near_miss
        )
        message += f"\n\nあと少しで作れるレシピ:\n{near_miss_text}"

    return message


def generate_answer(
    user_query: str,
    recipes: list[dict],
    near_miss: list[tuple[dict, list[str], int]] | None = None,
) -> str:
    """検索結果を渡して、Claude APIに回答文を作らせる。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            ".env に ANTHROPIC_API_KEY が設定されていません。"
            ".env.example を参考に .env を作成してください。"
        )

    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_user_message(user_query, recipes, near_miss)}
        ],
    )
    return message.content[0].text


WEEKLY_PLAN_SYSTEM_PROMPT = """あなたは、一人暮らしの大学生向けの栄養アドバイザーです。
大学生は、栄養バランスの良い献立の組み方が分からないことが多いので、
あなたが代わりに1週間分の献立を設計します。

渡された「候補レシピ一覧」の中から、月・火・水・木・金・土・日の7日分、
1日1品ずつ、主に夕食として食べる料理を選んでください。

選ぶときのルール:
- 同じレシピを2つ以上の曜日に選んではいけません
- 候補一覧に無いレシピを選んではいけません
- 「今週の要望」が伝えられた場合は、下のバランス重視のルールより
  その要望を優先してください（例:「高たんぱく重視」→ たんぱく質が
  多いレシピを中心に選ぶ。「カロリー控えめ」→ 1品あたりのカロリーが
  低めのレシピを中心に選ぶ。「野菜多め」→ 野菜多めタグのレシピを
  中心に選ぶ）
- 要望が無い場合は、次のバランス重視のルールで選ぶ:
  - 1週間を通して、たんぱく質・脂質・炭水化物のバランスが偏らないようにする
    （揚げ物や脂質の多い日が続いたら、次は野菜中心の日を入れる、など）
  - 同じ主な食材（鶏肉ばかり、麺類ばかり、など）が連続しないようにする
- 要望の有無に関わらず、1品あたりのカロリーが極端に低いレシピ
  （汁物や副菜など）だけが何日も続かないよう、主菜・主食を中心にしつつ
  変化をつける

選び終えたら、必ず assign_weekly_plan ツールを使って回答してください。
reasoningには、なぜこの組み合わせにしたのか（要望があれば、それに
どう応えたか）を、大学生に向けて分かりやすい日本語で3〜5文で
説明してください。

重要: reasoningの中で具体的なレシピ名を挙げるときは、必ず
assignmentsで実際に選んだレシピの正式なタイトルだけを使ってください。
選ばなかったレシピの名前を書いてはいけません。書き終える前に、
reasoningに書いたレシピ名が、すべてassignmentsに含まれているか
必ず見直してください。"""

WEEKLY_PLAN_TOOL = {
    "name": "assign_weekly_plan",
    "description": "1週間分（月〜日）の献立を、レシピIDで割り当てる",
    "input_schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "object",
                "description": "曜日をキー、レシピIDを値とするオブジェクト",
                "properties": {
                    "月": {"type": "string", "description": "月曜日に割り当てるレシピID"},
                    "火": {"type": "string", "description": "火曜日に割り当てるレシピID"},
                    "水": {"type": "string", "description": "水曜日に割り当てるレシピID"},
                    "木": {"type": "string", "description": "木曜日に割り当てるレシピID"},
                    "金": {"type": "string", "description": "金曜日に割り当てるレシピID"},
                    "土": {"type": "string", "description": "土曜日に割り当てるレシピID"},
                    "日": {"type": "string", "description": "日曜日に割り当てるレシピID"},
                },
                "required": ["月", "火", "水", "木", "金", "土", "日"],
            },
            "reasoning": {
                "type": "string",
                "description": "栄養バランスの観点から見た、この組み合わせの意図の説明（日本語）",
            },
        },
        "required": ["assignments", "reasoning"],
    },
}


def _format_recipe_for_planning(recipe: dict) -> str:
    """1件のレシピを、献立設計用の1行データに変換する。"""
    n = calculate_nutrition(recipe)
    tags = "、".join(recipe["tags"])
    return (
        f"{recipe['id']} | {recipe['title']} | {recipe['category']} | "
        f"{n['kcal']:.0f}kcal (P{n['protein']:.0f}g/F{n['fat']:.0f}g/C{n['carbs']:.0f}g) | "
        f"タグ: {tags}"
    )


def generate_weekly_plan(recipes: list[dict], user_goal: str | None = None) -> dict:
    """候補レシピ一覧から、AIに1週間分の献立を設計してもらう。

    Tool Use（Function Calling）を使い、AIに自由な文章ではなく、
    決まった形（曜日→レシピID）のデータで回答させる。

    Args:
        recipes: 候補にするレシピの一覧
        user_goal: 「高たんぱく重視」「カロリー控えめ」などの今週の要望。
            指定しない場合は、栄養バランス重視で選ばせる

    戻り値: {"assignments": {"月": "r001", ...}, "reasoning": "..."}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            ".env に ANTHROPIC_API_KEY が設定されていません。"
            ".env.example を参考に .env を作成してください。"
        )

    recipe_list_text = "\n".join(_format_recipe_for_planning(r) for r in recipes)
    user_content = f"候補レシピ一覧:\n{recipe_list_text}"
    if user_goal:
        user_content += f"\n\n今週の要望: {user_goal}"

    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=1024,
        system=WEEKLY_PLAN_SYSTEM_PROMPT,
        tools=[WEEKLY_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "assign_weekly_plan"},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in message.content:
        if block.type == "tool_use":
            return block.input

    raise RuntimeError("AIから献立の提案を受け取れませんでした。もう一度お試しください。")


if __name__ == "__main__":
    from search import search_recipes

    query = "鶏むね肉とキャベツと卵が余っていて、20分以内で野菜多めの料理が作りたい"
    found = search_recipes(
        ingredients=["鶏むね肉", "キャベツ", "卵"],
        max_time_minutes=20,
        tags=["野菜多め"],
    )
    print(generate_answer(query, found))
