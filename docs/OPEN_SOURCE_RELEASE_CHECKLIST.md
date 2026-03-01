# Star Office UI — オープンソース公開準備チェックリスト（準備のみ、アップロードはしない）

## 0. 現在の目標
- 本ドキュメントは「公開前の準備」用であり、実際のアップロードは行わない。
- すべての push 操作にはハイシンの最終的な明示的承認が必要。

## 1. プライバシーとセキュリティ審査結果（現在のリポジトリ）

### 高リスクファイルの発見（必ず除外すること）
- 実行ログ：
  - `cloudflared.out`
  - `cloudflared-named.out`
  - `cloudflared-quick.out`
  - `healthcheck.log`
  - `backend.log`
  - `backend/backend.out`
- 実行状態：
  - `state.json`
  - `agents-state.json`
  - `backend/backend.pid`
- バックアップ/履歴ファイル：
  - `index.html.backup.*`
  - `index.html.original`
  - `*.backup*` ディレクトリとファイル
- ローカル仮想環境とキャッシュ：
  - `.venv/`
  - `__pycache__/`

### 潜在的な機密コンテンツの発見
- コード内に絶対パス `/root/...` が含まれている（相対パスまたは環境変数への変更を推奨）
- ドキュメントとスクリプトにプライベートドメイン `office.example.com` が含まれている（サンプルとして残すことは可能だが、プレースホルダードメインへの変更を推奨）

## 2. 必須変更項目（コミット前）

### A. .gitignore（追加が必要）
追加推奨：
```
*.log
*.out
*.pid
state.json
agents-state.json
join-keys.json
*.backup*
*.original
__pycache__/
.venv/
venv/
```

### B. README 著作権表示（必ず追加）
「美術アセットの著作権と使用制限」セクションを新規追加：
- コードはオープンソースライセンス（MIT など）
- 美術素材は原作者/スタジオに帰属
- 素材は学習/デモ用途のみ、**商用利用禁止**

### C. 公開ディレクトリのスリム化
- 実行ログ、実行状態ファイル、バックアップファイルを整理
- 「実行可能な最小セット + 必要な素材 + ドキュメント」のみ保持

## 3. 準備中の公開パッケージ推奨構成
```
star-office-ui/
  backend/
    app.py
    requirements.txt
    run.sh
  frontend/
    index.html
    game.js （まだ必要な場合）
    layout.js
    assets/* （公開可能な素材のみ）
  office-agent-push.py
  set_state.py
  state.sample.json
  README.md
  LICENSE
  SKILL.md
  docs/
```

## 4. 公開前の最終確認（ハイシン確認用）
- [ ] プライベートドメインのサンプル（`office.example.com`）を残すかどうか
- [ ] どの美術リソースの公開を許可するか（項目ごとに確認）
- [ ] README の非商用声明が期待する文言を満たしているか
- [ ] 「アーウェンロブスター連携スクリプト」を examples ディレクトリに分離する必要があるか

## 5. 現在の状況
- ✅ ドキュメント準備完了（要約、機能説明、Skill v2、公開チェックリスト）
- ⏳ ハイシンの確認待ち「公開素材の範囲 + 声明文案 + パッケージ整理スクリプトの実行を開始するかどうか」
- ⛔ GitHub アップロードはまだ実行していない
