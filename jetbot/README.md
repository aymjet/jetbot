# jetbot

Discordサーバーで受信したメッセージをSQLiteに保存し、保存記録をOpenAI APIへ送って質問回答と日本語要約を行うBotです。

## 実装されている機能

| 操作 | コードの処理 |
| --- | --- |
| サーバー内の投稿 | Bot以外の投稿をSQLiteへ保存。コマンドの投稿も保存する |
| `!sync` | 実行したサーバーのテキストチャンネルを順に処理し、取得できる過去メッセージを件数上限なしで保存。Botの投稿は除外 |
| `!ask 質問` | 質問を空白で分割し、語ごとに同じサーバーの保存済み本文をSQLの `LIKE` で検索。各語の最新50件を取得し、重複除去後の先頭100件までをAPIへ送る |
| `!summary` | 現在のチャンネルの保存済み最新100件を取得し、日時の昇順に並べてAPIへ送り、日本語での要約を要求する |

`!sync` と `!summary` はメッセージ本文が完全一致した場合、`!ask` は本文が `!ask ` で始まる場合に処理します。
DMとBotによる投稿は処理しません。保存には `INSERT OR IGNORE` を使い、同じメッセージIDの記録は追加・更新しません。
同期完了時の件数は確認した投稿数で、DBへの追加件数ではありません。チャンネル取得中のエラーは標準出力に記録され、他のチャンネルの処理を続けます。

質問回答・要約にはOpenAIのResponses APIを使用します。API応答の `output_text` を2000文字ごとに分割してDiscordへ送信します。
質問回答のプロンプトには、記録に基づいて回答し、記録にないことは推測しないよう指示しています。回答内容の正確性を別途検証する処理はありません。

## ファイル構成

リポジトリ内では、以下のファイルが `jetbot/` 配下にあります。

```text
jetbot/
├── README.md
├── jetbot.py                 Bot本体
├── requirements.txt          Python依存関係
├── .env.example              環境変数の設定例
├── .gitignore                ローカル設定・DB等の除外設定
└── scripts/
    └── check_openai.py       OpenAI APIへの手動接続確認
```

依存関係の指定は `discord.py>=2.3,<3` と `openai>=1.66,<3` です。
リポジトリ内にテストコード、Pythonバージョン指定、常駐運用・デプロイ用設定はありません。

## セットアップ

以下はmacOS/Linuxでのセットアップ手順です。PythonとGitを用意し、リポジトリを取得して `jetbot/` に移動します。

```sh
git clone https://github.com/aymjet/jetbot.git
cd jetbot/jetbot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

`.env` を編集してDiscord Bot TokenとOpenAI APIキーを設定します。
コードは `.env` を自動読み込みせず、環境変数を参照します。以下の方法では `.env` をシェルで実行するため、信頼できる設定だけを書き、必要に応じて値を引用符で囲んでください。

```sh
set -a
source .env
set +a
python jetbot.py
```

コードでは `message_content` Intentを有効にしています。Discord Developer PortalでもMessage Content Intentを有効にし、Botを対象サーバーへ招待してください。
対象チャンネルの閲覧・メッセージ送信・メッセージ履歴閲覧権限が必要です。

## 環境変数

| 名前 | 必須 | コードでの扱い |
| --- | --- | --- |
| `DISCORD_TOKEN` | 必須 | 未設定・空の場合、本体は起動時にエラーを出す |
| `OPENAI_API_KEY` | 必須 | 未設定・空の場合、本体は起動時にエラーを出す |
| `OPENAI_MODEL` | 任意 | 未指定時は `gpt-6-astra`。本体とAPI確認スクリプトの両方で使用 |
| `JETBOT_DB_PATH` | 任意 | 未指定時は `jetbot.py` と同じディレクトリの `jetbot.db` |

`gpt-6-astra` はコード内の既定値です。このREADMEの照合では、APIでの利用可否を確認していません。利用できるモデルを `OPENAI_MODEL` に設定してください。
既存DBを利用する場合は `JETBOT_DB_PATH` にそのパスを指定します。相対パスは起動時の作業ディレクトリを基準に扱われます。

環境変数を読み込んだ後、以下でOpenAI APIへの接続を手動確認できます。

```sh
python scripts/check_openai.py
```

このスクリプトは固定の挨拶文をAPIへ送って応答を表示します。DiscordとDBの動作確認は行いません。

## 保存データと制約

SQLiteの `messages` テーブルに、メッセージID、サーバーID、チャンネルID・名前、投稿者の文字列表現、本文、投稿日時を保存します。
質問・要約では選択した記録をOpenAI APIへ送信します。

- コマンド実行者の利用権限・役職を確認する処理はありません。`!ask` はサーバーIDだけで検索範囲を絞り、実行者のチャンネル閲覧権限を確認しません。
- `!ask` は語ごとの検索結果を連結するため、全体の最新100件を選ぶ処理ではありません。`LIKE` の `%` と `_` をエスケープする処理もありません。
- `!summary` の対象には、そのコマンドの投稿も含まれます。
- 投稿の編集・削除をDBへ反映する処理、保存期間制限、DBバックアップ処理はありません。
- `!sync` は `guild.text_channels` を巡回し、スレッドの過去ログを個別に取得する処理はありません。スレッド内でも `on_message` に届くサーバー投稿は保存対象です。
- API入力の文字数・トークン数・費用・同時実行数を制限する処理はありません。
- ChatGPTの会話履歴・プロジェクトの取得、GitHub API連携、X連携、Ableton操作は実装されていません。

`.gitignore` は `.env`、DB、ログ、ローカル環境などを除外し、`.env.example` は追跡対象にしています。
既に追跡されているファイルやコード中の秘密情報は `.gitignore` では除去されません。

## 確認範囲

2026-10-07にGitHubの `main` ブランチのファイル構成と上記コードを読み、READMEの記載を照合しました。
依存関係のインストール、Discordへの接続、OpenAI API呼び出し、実際の運用状況は今回確認していません。
