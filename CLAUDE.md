# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Star Office UI は、マルチエージェント協業のためのピクセルアートオフィスダッシュボード。AI アシスタントの作業状態をリアルタイムで可視化する。

- **バックエンド**: Python 3 + Flask（`backend/app.py` 単一ファイル）
- **フロントエンド**: Vanilla JavaScript + Phaser 3（ゲームエンジン）
- **データ永続化**: JSON ファイル（DB不使用）
- **ビルドステップ不要**: バンドラー/webpack なし

## 起動・開発コマンド

```bash
# 依存関係インストール（uv が未導入の場合: curl -LsSf https://astral.sh/uv/install.sh | sh）
uv sync

# オプション依存（画像処理 / エージェント通信）が必要な場合
uv sync --extra images   # Pillow
uv sync --extra agent    # requests
uv sync --extra all      # 両方

# 初回のみ: 状態ファイル初期化
cp state.sample.json state.json

# サーバー起動（http://127.0.0.1:18791）
uv run python backend/app.py

# 主エージェントの状態変更（プロジェクトルートから実行）
uv run python set_state.py <state> "<detail>"
# state: idle | writing | researching | executing | syncing | error
```

## アーキテクチャ

### バックエンド（`backend/app.py`）

Flask サーバー（ポート 18791）。主要エンドポイント:
- `GET /status`, `POST /set_state` — 主エージェント状態の取得・設定
- `GET /agents`, `POST /join-agent`, `POST /agent-push`, `POST /leave-agent` — マルチエージェント管理
- `GET /yesterday-memo` — `memory/YYYY-MM-DD.md` から昨日の記録を読み取り、プライバシー脱敏して返却

状態は `state.json`（主エージェント）と `agents-state.json`（ゲスト）に保存。ゲスト参加には `join-keys.json` の join key が必要（`threading.Lock` で同時参加の排他制御あり）。

### フロントエンド

- **`frontend/layout.js`** — 全座標・depth・アセットパスの一元管理（magic number 排除）。変更時はここを最初に確認
- **`frontend/game.js`** — Phaser 3 ゲームループ（preload → create → update）。状態に応じたキャラ移動・アニメーション・バブルテキスト制御
- **`frontend/index.html`** — UI 構造・CSS・テンプレート（`{{VERSION_TIMESTAMP}}` はサーバーが実行時に置換）

### 状態システム

6つの状態がオフィスの物理エリアにマッピングされる:
- `idle` → 休憩エリア（breakroom）
- `writing`, `researching`, `executing`, `syncing` → デスクエリア（writing）
- `error` → バグゾーン（error）

ゲストエージェントは5分間更新がないと自動 offline。主エージェントは `ttl_seconds`（デフォルト300秒）で自動 idle に戻る。

### アセット戦略

- WebP 優先、透過が必要な素材は PNG 強制（layout.js の `forcePng` フラグ）
- ブラウザ側で Canvas ベースの WebP サポート検出を実施
- スプライトシートによるフレームアニメーション（通常 12fps）

## 命名規則

- JavaScript: camelCase（関数・変数）
- Python: snake_case（関数・変数）
- 状態名: 小文字英語（`idle`, `writing`, `error` 等）
- エージェントID: `agent_[timestamp]_[random]` 形式

## ポーリング間隔（`game.js`）

- 主エージェント状態取得: 2000ms
- ゲストエージェント一覧取得: 2500ms
- バブルテキスト: 8000ms

## ライセンス注意事項

- **コード**: MIT
- **美術アセット**: 非商用のみ（主キャラは任天堂/ポケモンの IP）。商用利用時は独自アセットへの差し替えが必須
- ゲストキャラアセットは LimeZu の無料素材（出典表記必要）
