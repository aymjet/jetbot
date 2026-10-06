import os
import sqlite3
from pathlib import Path
import discord
from openai import AsyncOpenAI

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN が設定されていません")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY が設定されていません")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# =========================
# SQLite DB
# =========================

DB_PATH = Path(os.environ.get("JETBOT_DB_PATH", str(Path(__file__).with_name("jetbot.db"))))
db = sqlite3.connect(DB_PATH)

db.execute("""
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    channel_name TEXT,
    author TEXT,
    content TEXT,
    created_at TEXT
)
""")

db.commit()


def save_message(message):
    if not message.guild:
        return

    db.execute("""
    INSERT OR IGNORE INTO messages (
        message_id,
        guild_id,
        channel_id,
        channel_name,
        author,
        content,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        message.id,
        message.guild.id,
        message.channel.id,
        str(message.channel),
        str(message.author),
        message.content,
        message.created_at.isoformat()
    ))

    db.commit()


# =========================
# 起動
# =========================

@client.event
async def on_ready():
    print("jetbot 起動成功")
    print(f"ログイン: {client.user}")


# =========================
# メッセージ処理
# =========================

@client.event
async def on_message(message):

    if message.author.bot or message.guild is None:
        return

    if message.guild:
        save_message(message)

    # -------------------------
    # 全チャンネル同期
    # -------------------------

    if message.content == "!sync":

        await message.channel.send(
            "Discord全チャンネルの過去ログ同期を開始します。"
        )

        count = 0

        for channel in message.guild.text_channels:

            try:
                print(f"同期中: #{channel.name}")

                async for msg in channel.history(
                    limit=None,
                    oldest_first=True
                ):
                    if msg.author.bot:
                        continue

                    save_message(msg)
                    count += 1

                print(f"完了: #{channel.name}")

            except discord.Forbidden:
                print(f"権限なし: #{channel.name}")

            except Exception as e:
                print(f"エラー #{channel.name}: {e}")

        await message.channel.send(
            f"同期完了：{count}件のメッセージを確認しました。"
        )

    # -------------------------
    # 全履歴から質問
    # -------------------------

    elif message.content.startswith("!ask "):

        question = message.content[5:].strip()

        if not question:
            await message.channel.send(
                "質問を入力してください。"
            )
            return

        words = question.split()

        rows = []

        for word in words:

            result = db.execute("""
            SELECT
                channel_name,
                author,
                content,
                created_at
            FROM messages
            WHERE guild_id = ?
              AND content LIKE ?
            ORDER BY created_at DESC
            LIMIT 50
            """, (
                message.guild.id,
                f"%{word}%"
            )).fetchall()

            rows.extend(result)

        # 重複除去
        rows = list(dict.fromkeys(rows))

        if not rows:
            await message.channel.send(
                "関連するDiscord記録が見つかりませんでした。"
            )
            return

        context = ""

        for row in rows[:100]:
            context += (
                f"\n"
                f"チャンネル: #{row[0]}\n"
                f"投稿者: {row[1]}\n"
                f"日時: {row[3]}\n"
                f"内容: {row[2]}\n"
            )

        prompt = f"""
あなたはDiscord運営支援AI「jetbot」です。

以下はDiscordサーバーから取得した記録です。

--- Discord記録 ---

{context}

--- 質問 ---

{question}

必ずDiscord記録に基づいて回答してください。

ルール:
- 記録にないことは推測しない
- 不明な場合は「記録からは確認できません」と答える
- 可能な限りチャンネル名を示す
- 決定事項、数値、担当、日付は具体的に整理する
"""

        async with message.channel.typing():

            try:
                response = await openai_client.responses.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-6-astra"),
                    input=prompt
                )

                answer = response.output_text

                for i in range(0, len(answer), 2000):
                    await message.channel.send(
                        answer[i:i+2000]
                    )

            except Exception as e:
                print(f"OpenAIエラー: {e}")

                await message.channel.send(
                    "OpenAI APIとの通信でエラーが発生しました。"
                )

    # -------------------------
    # 現在チャンネルの要約
    # -------------------------

    elif message.content == "!summary":

        rows = db.execute("""
        SELECT
            author,
            content,
            created_at
        FROM messages
        WHERE guild_id = ?
          AND channel_id = ?
        ORDER BY created_at DESC
        LIMIT 100
        """, (
            message.guild.id,
            message.channel.id
        )).fetchall()

        if not rows:
            await message.channel.send(
                "このチャンネルの記録がまだありません。"
            )
            return

        context = ""

        for row in reversed(rows):
            context += (
                f"{row[2]} "
                f"{row[0]}: "
                f"{row[1]}\n"
            )

        prompt = f"""
以下はDiscordチャンネル #{message.channel.name} の記録です。

--- 記録 ---

{context}

このチャンネルの内容を日本語で整理してください。

次の項目を優先してください。

- 重要事項
- 決定事項
- 数値
- 担当者
- 未解決事項
- 次に必要な対応

記録にないことは推測しないでください。
"""

        async with message.channel.typing():

            try:
                response = await openai_client.responses.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-6-astra"),
                    input=prompt
                )

                answer = response.output_text

                for i in range(0, len(answer), 2000):
                    await message.channel.send(
                        answer[i:i+2000]
                    )

            except Exception as e:
                print(f"OpenAIエラー: {e}")

                await message.channel.send(
                    "要約処理でエラーが発生しました。"
                )


client.run(DISCORD_TOKEN)
