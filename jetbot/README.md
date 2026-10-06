# jetbot

Discordの会話をSQLiteに保存し、OpenAI APIを使って質問回答と日本語要約を行う運営支援Bot。
優先する範囲はjetbot本体・要約・ChatGPT/OpenAI連携・GitHubでのコード管理。X連携は今回の対象外。

## 現状機能

| 操作 | 動作 |
| --- | --- |
| 通常の投稿 | Bot以外のサーバー投稿をSQLiteへ保存 |
| `!sync` | Botが読めるサーバー内のテキストチャンネルの過去ログを同期。件数は確認件数で、追加件数ではない |
| `!ask 質問` | 同じサーバーの保存済みログを空白区切りの語で部分一致検索し、最大100件を使って回答 |
| `!summary` | 現在のチャンネルの保存済みログ最新100件を日本語で要約 |

回答はDiscordの文字数制限に合わせて2000文字ごとに分割。DMは処理しない。
ChatGPTとの連携はOpenAI API呼び出しとして実装されており、ChatGPTの会話履歴やプロジェクトを読み込む機能はない。
GitHub API連携は未実装で、まずこのコードをGitHubで管理する。

## ファイル構成と元ファイル

```text
jetbot.py                 Bot本体
scripts/check_openai.py    OpenAI API接続の手動確認（API利用料金が発生）
requirements.txt          Python依存関係
.env.example              値を含まない設定例
.gitignore                秘密情報・会話DB・ローカル環境の除外設定
```

2026-10-06にローカルの `~/jetbot.py` を元に整理。
`~/jetbot_sync_backup.py` は本体と同一、`~/jetbot_backup.py` は `!ai` の旧版のため含めていない。
`~/jetbot_test.py` は手動API確認スクリプトとして整理した。
`~/jetbot.db` と元ファイルはそのまま保持し、この配布用フォルダへDBはコピーしていない。

## セットアップ

Python 3.10以上、Discord Bot、OpenAI APIキー、インターネット接続が必要。
macOS/Linuxの例（このフォルダ内で実行）:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

`.env` をローカルで編集してキーを設定する。ファイル自体の自動読み込みは行わない。
次の方法で環境変数へ読み込むため、`.env` には信頼できる設定だけを書き、値に空白等がある場合は引用符で囲む。

```sh
set -a
source .env
set +a
python jetbot.py
```

Discord Developer PortalでBotのMessage Content Intentを有効にし、対象サーバーに招待する。
対象チャンネルの閲覧・メッセージ送信・メッセージ履歴閲覧権限を付与する。
依存関係のバージョン範囲は整理時点の指定で、インストール・実接続による動作確認は未実施。

## 環境変数

| 名前 | 必須 | 説明 |
| --- | --- | --- |
| `DISCORD_TOKEN` | 必須 | Discord Bot Token |
| `OPENAI_API_KEY` | 必須 | OpenAI APIキー |
| `OPENAI_MODEL` | 任意 | APIで利用するモデル。未指定時は元コードの `gpt-6-astra`。利用可否は未検証のため、アカウントで使えるモデルを指定する |
| `JETBOT_DB_PATH` | 任意 | SQLiteファイルの場所。未指定時は本体と同じフォルダの `jetbot.db` |

既存記録を利用する場合は、`JETBOT_DB_PATH` に既存DBの絶対パスを設定する。同じDBを使うBotを同時に複数起動しない。
API接続だけを確認する場合は、環境変数を読み込んだ後に `python scripts/check_openai.py` を実行する。

## データと利用上の制約

会話本文・投稿者・サーバー/チャンネルID・日時をSQLiteへ保存する。
質問・要約では選択した会話をOpenAI APIへ送信する。
現状、コマンド実行者の役職制限はなく、`!ask` は実行者が閲覧できないチャンネルの保存記録も検索対象にする。
アクセス範囲を共有できる運営用サーバーで利用し、権限の異なる利用者へ展開する前に閲覧権限チェックを実装する。
ログの編集・削除同期、スレッド同期、保存期間制限、API入力長の制限は未実装。

秘密情報・Webhook・`.env`・DB・ログはGitHubに登録しない。
`.gitignore` はコード内の秘密情報や既に追跡されているファイルを除去しないため、公開前には変更内容と履歴を確認する。
整理時のコピー対象コードでは既知の秘密情報パターンと資格情報の直接代入を検査し、候補は検出されなかった。

## GitHubへ登録

接続済みGitHubで `jetbot` という名前のリポジトリは見つからなかった。接続範囲外のリポジトリの有無は未確認。
既存リポジトリがある場合は、そちらを取得して、この一式の変更を確認してから反映する。
新規の場合はGitHubで空のリポジトリを作成し、このフォルダで以下を実行する:

```sh
git init -b main
git add .
git diff --cached --stat
git diff --cached
git commit -m "Organize jetbot source and setup documentation"
git remote add origin <作成したリポジトリのURL>
git push -u origin main
```

## 今後のTODO

- コマンドの利用者・役職制限と、質問回答時のチャンネル閲覧権限チェック
- 同期・質問・要約の動作テストと依存バージョンの固定
- API入力長・費用・同時実行の制限、長いログの段階的要約
- `!ask` の日本語検索改善と検索結果の時系列整理
- 投稿の編集・削除同期、保存期間とDBバックアップ方針
- 一般的なAI質問機能（旧版の `!ai`）を本体へ統合するか検討
- GitHub連携の用途・権限を決定し、必要な機能を実装
- X連携は今回の作業対象外
