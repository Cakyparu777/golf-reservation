# ⛳ Golf Reservation Chatbot

[English README](README.en.md)

ゴルフ予約向けの会話型アシスタントです。**MCP (Model Context Protocol)** を実際のプロダクトフローにどう組み込むかを見せるために作っています。

このプロジェクトでは、単に LLM に自然文を返させるだけではなく、以下を明確に分離しています。

- **LLM Host**: 会話状態、確認フロー、ツール実行の制御
- **MCP Server**: ゴルフ予約ドメインのツール群
- **Supabase 連携**: Auth / Postgres / RLS への段階的移行

採用担当者向けに言うと、このリポジトリで見せたいのは「AI チャットが作れること」だけではなく、**MCP を使って業務ロジックを安全に扱える設計ができること**です。

## このプロジェクトで見せたいこと

- LLM をデータの正解源にしない設計
- 予約・検索・天気確認を **MCP ツール**に切り出す実装
- `that day` / `there` / `book the second one` のような follow-up を解決する**構造化メモリ**
- SQLite から Supabase/Postgres に移る**段階的なマイグレーション設計**
- フロントエンド、バックエンド、Auth、RLS まで含めた**実務寄りの統合**

## 技術スタック

- **Backend:** FastAPI, Python, MCP, OpenAI
- **Frontend:** React, TypeScript, Vite
- **Data:** SQLite（現行） / Supabase Postgres（移行中）
- **Auth:** ローカル JWT + Supabase Auth 対応
- **Infra direction:** Supabase, RLS, MCP-connected tooling

## アーキテクチャ

```text
User -> FastAPI Host -> OpenAI LLM -> MCP Client -> MCP Server -> SQLite / Supabase-ready Postgres
```

- **Host (FastAPI)**
  - 会話状態管理
  - 確認フロー
  - follow-up 解決
  - ツール呼び出し制御
- **MCP Server (FastMCP)**
  - ティータイム検索
  - コース情報取得
  - 代替案提示
  - レコメンド
  - 予約作成 / 確認 / キャンセル
  - 天気確認
- **LLM (OpenAI)**
  - 意図解釈
  - 応答生成
  - どのツールを呼ぶかの判断

## MCP の使い方

このプロジェクトでは、LLM に予約データを「それっぽく推測」させていません。

- ゴルフ予約ドメインの操作は **MCP ツール**として分離
- Host 側で確認・文脈解決・メモリ管理を担当
- LLM は自然な会話とツール選択に集中

つまり、**自然言語の柔軟さ**と **業務ロジックの決定性** を分けています。

## 主な機能

- ティータイム検索
- 天候を考慮したおすすめ提案
- 雨天・強風（20 km/h 超）を避けるデフォルトロジック
- ホームエリア / 移動手段 / 最大移動時間を使った提案
- 予約作成 / 仮押さえ / 確認 / キャンセル
- 文脈を引き継ぐ会話メモリ
- Supabase Auth 対応
- Supabase Postgres / RLS への段階的移行

## 会話体験の例

```text
User: nearest to adachi ku
Assistant: The nearest full course is Wakasu Golf Links.

User: tomorrow 12:00 3-4 players
Assistant: 日付・時間・人数・コース・天気をまとめて確認

User: how will be the weather that day
Assistant: 直前の course/date/time を引き継いで回答

User: book the second one
Assistant: 直前に提示した候補の 2 番目を解決して予約フローへ進む
```

この動きは意図的です。ステートレスなデモチャットではなく、**コールセンターの担当者に近い振る舞い**を目指しています。

## URL ルーティング

フロントエンドは URL ベースで各画面に遷移できます。

- `/login`
- `/signup`
- `/assistant`
- `/tee-times`
- `/my-golf`
- `/settings`

## ローカル実行

### 1. 依存関係のインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd frontend
npm install
```

### 2. 環境変数

```bash
cp .env.example .env
```

最低限、以下を設定します。

- `OPENAI_API_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

### 3. 起動

バックエンド:

```bash
./scripts/start_server.sh --reload
```

フロントエンド:

```bash
cd frontend
npm run dev
```

## Docker 実行

フロントエンド・バックエンド両方の Dockerfile を追加しています。

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

起動方法:

```bash
docker compose up --build
```

公開ポート:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

補足:

- フロントエンドは Nginx で配信し、`/chat`, `/auth`, `/api`, `/health` を backend に proxy します
- フロントエンドの Supabase 公開キーは build 時に埋め込まれるため、`.env` に `NEXT_PUBLIC_...` 系を入れてから build してください

## Supabase 移行状況

- `supabase/` は初期化済み
- 初期スキーマ:
  - `supabase/migrations/20260416183000_init_golf_reservation.sql`
- ランタイム向け追加:
  - `supabase/migrations/20260416190000_runtime_views_and_rls.sql`
- フロントエンドは Supabase Auth を利用
- バックエンドは Supabase JWT を受け取れる
- 一部の public read API は Supabase REST を優先利用

ただし、現時点ではまだ **完全な Supabase 切り替え**ではありません。予約系・MCP クエリの多くはまだ SQLite ベースです。

## 設計上のトレードオフ

- ローカル開発とテスト速度のために SQLite を残している
- 一方で Supabase Auth / Postgres / RLS を先に入れ、移行経路を可視化している
- プロンプトだけに頼らず、会話メモリは明示的な構造化 state で扱っている
- 一気に書き換えるのではなく、壊さず段階的に移す方針を取っている

## 本番化するなら次にやること

1. 予約作成・更新・キャンセルを Supabase Postgres に完全移行
2. SQLite 依存の MCP クエリを Postgres 向けに書き換え
3. ダミーデータではなく実データ連携に置き換え
4. in-memory の会話状態を永続化
5. ログ、監視、rate limit、バックグラウンドジョブを追加

## ディレクトリ構成

```text
golf-reservation/
├── backend/
│   ├── host/                # FastAPI host
│   ├── mcp_server/          # MCP server
│   ├── services/            # weather / location / supabase helpers
│   └── db/
├── frontend/
├── supabase/
├── scripts/
├── tests/
└── docker-compose.yml
```

## ライセンス

MIT
