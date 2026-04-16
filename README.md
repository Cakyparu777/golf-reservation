# ⛳ Golf Reservation Chatbot

[English README](README.en.md)

ゴルフ予約向けの会話型アシスタントです。**MCP (Model Context Protocol)** を実際のプロダクトフローにどう組み込むかを見せるために作っています。

このプロジェクトでは、以下を明確に分離しています。

- **LLM Host**: 会話状態、確認フロー、ツール実行の制御
- **MCP Server**: ゴルフ予約ドメインのツール群
- **Supabase**: Auth / Postgres / RLS / RPC を使った本番向けデータ基盤

## このプロジェクトで見せたいこと

- LLM をデータの正解源にしない設計
- 予約・検索・天気確認を **MCP ツール**に切り出す実装
- Host が MCP サーバーから **ネイティブにツール定義を discover** する構成
- `that day` / `there` / `book the second one` のような follow-up を解決する**構造化メモリ**
- Supabase Auth と Postgres を使った、会話 UI から予約データまで一貫したバックエンド設計

## 技術スタック

- **Backend:** FastAPI, Python, MCP, OpenAI
- **Frontend:** React, TypeScript, Vite
- **Data:** Supabase Postgres
- **Auth:** Supabase Auth
- **Conversation state:** memory（デフォルト） / Redis（任意）
- **Local test fallback:** SQLite fixtures

## アーキテクチャ

```text
User -> FastAPI Host -> OpenAI LLM -> MCP Client -> MCP Server -> Supabase Postgres
                         |                              |
                         +-> conversation state -> Memory or Redis
                         +-> Supabase Auth JWT verification / profile sync
```

- **Host (FastAPI)**
  - 会話状態管理
  - 確認フロー
  - follow-up 解決
  - MCP ツール discovery と tool orchestration
  - Supabase JWT 検証
- **MCP Server (FastMCP)**
  - ティータイム検索
  - コース情報取得
  - 代替案提示
  - レコメンド
  - 予約作成 / 確認 / キャンセル
  - 天気確認
- **Supabase**
  - Auth
  - Postgres tables / views / RLS
  - transactional RPC for reservation writes

## MCP の使い方

- ゴルフ予約ドメインの操作は **MCP ツール**として分離
- Host 側で確認・文脈解決・メモリ管理を担当
- LLM は自然な会話とツール選択に集中
- OpenAI へ渡す tool schema は **MCP サーバーから動的に取得**

つまり、**自然言語の柔軟さ**と **業務ロジックの決定性** を分けています。

## Supabase 方針

- 認証は Supabase Auth を使用
- 予約系の書き込みは Postgres RPC でトランザクション化
- public read 用 view は `security_invoker` を使用
- RLS は `auth.uid()` を `select auth.uid()` 形式で最適化
- SQLite はローカル test fixture 用にのみ残し、実運用パスは Supabase に統一

## 主な機能

- ティータイム検索
- 天候を考慮したおすすめ提案
- 雨天・強風（20 km/h 超）を避けるデフォルトロジック
- ホームエリア / 移動手段 / 最大移動時間を使った提案
- 予約作成 / 仮押さえ / 確認 / キャンセル
- 文脈を引き継ぐ会話メモリ
- 日本向けの JPY 価格表示

## ローカル実行

### 1. 依存関係のインストール

```bash
python3 -m venv .venv
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
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

共有前に、少なくとも以下も設定してください。

- `CORS_ALLOW_ORIGINS`

Redis を使う場合のみ追加で設定します。

- `CONVERSATION_BACKEND=redis`
- `REDIS_URL=redis://localhost:6379/0`

開発中に MCP ツール定義キャッシュを無効化したい場合のみ設定します。

- `MCP_DISABLE_TOOL_CACHE=1`

### 3. Supabase schema の反映

```bash
supabase db push
```

### 4. 起動

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
- Redis: `redis://localhost:6379`

## Supabase マイグレーション

- `supabase/migrations/20260416183000_init_golf_reservation.sql`
- `supabase/migrations/20260416190000_runtime_views_and_rls.sql`
- `supabase/migrations/20260416210000_complete_supabase_cutover.sql`

最後の migration では以下を行っています。

- `security_invoker` view への修正
- `reservation_details` view の追加
- performance advisor に合わせた RLS policy 修正
- 予約書き込み用 RPC の追加
- サンプルコース / ティータイム seed

## 設計上のトレードオフ

- public read は Supabase view + RLS
- 複数テーブル更新が必要な予約処理は RPC で Postgres 側に寄せる
- conversation state は backend 側で持ち、認証と予約データは Supabase に任せる
- SQLite はテストとオフライン fixture に限定
- `/chat` は認証必須にして OpenAI 利用を保護
- MCP サーバー接続は FastAPI 起動時に 1 本だけ確立して再利用し、tool 呼び出しは lock で直列化している。高い並列性が必要なら次は small pool 化が候補

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
