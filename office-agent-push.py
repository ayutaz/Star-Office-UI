#!/usr/bin/env python3
"""
Starオフィス - Agent ステータス自動プッシュスクリプト

使用法:
1. 下記の JOIN_KEY を入力（Starオフィスから取得したワンタイム join key）
2. AGENT_NAME を入力（オフィスに表示したい名前）
3. 実行: python office-agent-push.py
4. スクリプトが自動的に join（初回実行時）し、その後15秒ごとにStarオフィスへ現在のステータスをプッシュ
"""

import json
import os
import time
import sys
from datetime import datetime

# === 入力が必要な情報 ===
JOIN_KEY = ""   # 必須: ワンタイム join key
AGENT_NAME = "" # 必須: オフィスに表示する名前
OFFICE_URL = "https://office.example.com"  # Starオフィスのアドレス（通常変更不要）

# === プッシュ設定 ===
PUSH_INTERVAL_SECONDS = 15  # プッシュ間隔（秒）
STATUS_ENDPOINT = "/status"
JOIN_ENDPOINT = "/join-agent"
PUSH_ENDPOINT = "/agent-push"

# ローカルステータス保存（前回 join で取得した agentId を記憶）
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "office-agent-state.json")

# ローカル OpenClaw ワークスペースのステータスファイルを優先読み取り（AGENTS.md のワークフローに準拠）
# 自動検出対応。手動設定の手間を削減。
DEFAULT_STATE_CANDIDATES = [
    "/root/.openclaw/workspace/star-office-ui/state.json",
    "/root/.openclaw/workspace/state.json",
    os.path.join(os.getcwd(), "state.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json"),
]

# ローカル /status に認証が必要な場合、ここに token を設定（または環境変数 OFFICE_LOCAL_STATUS_TOKEN を使用）
LOCAL_STATUS_TOKEN = os.environ.get("OFFICE_LOCAL_STATUS_TOKEN", "")
LOCAL_STATUS_URL = os.environ.get("OFFICE_LOCAL_STATUS_URL", "http://127.0.0.1:18791/status")
# 任意: ローカルステータスファイルパスを直接指定（最もシンプルな方法: /status 認証をバイパス）
LOCAL_STATE_FILE = os.environ.get("OFFICE_LOCAL_STATE_FILE", "")
VERBOSE = os.environ.get("OFFICE_VERBOSE", "0") in {"1", "true", "TRUE", "yes", "YES"}


def load_local_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "agentId": None,
        "joined": False,
        "joinKey": JOIN_KEY,
        "agentName": AGENT_NAME
    }


def save_local_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_state(s):
    """異なるローカルステータス用語を互換し、オフィスが認識するステータスにマッピング。"""
    s = (s or "").strip().lower()
    if s in {"writing", "researching", "executing", "syncing", "error", "idle"}:
        return s
    if s in {"working", "busy", "write"}:
        return "writing"
    if s in {"run", "running", "execute", "exec"}:
        return "executing"
    if s in {"research", "search"}:
        return "researching"
    if s in {"sync"}:
        return "syncing"
    return "idle"


def map_detail_to_state(detail, fallback_state="idle"):
    """detail のみの場合、キーワードからステータスを推定（AGENTS.md のオフィスエリアロジックに準拠）。"""
    d = (detail or "").lower()
    if any(k in d for k in ["报错", "error", "bug", "异常", "报警", "エラー"]):
        return "error"
    if any(k in d for k in ["同步", "sync", "备份", "同期"]):
        return "syncing"
    if any(k in d for k in ["调研", "research", "搜索", "查资料", "調査"]):
        return "researching"
    if any(k in d for k in ["执行", "run", "推进", "处理任务", "工作中", "writing", "実行"]):
        return "writing"
    if any(k in d for k in ["待命", "休息", "idle", "完成", "done", "待機"]):
        return "idle"
    return fallback_state


def fetch_local_status():
    """ローカルステータスを読み取り:
    1) state.json を優先（AGENTS.md 準拠: タスク前に writing、完了後に idle に切替）
    2) 次にローカル HTTP /status を試行
    3) 最後に fallback idle
    """
    # 1) ローカル state.json を読み取り（明示指定パスを優先、次に自動検出）
    candidate_files = []
    if LOCAL_STATE_FILE:
        candidate_files.append(LOCAL_STATE_FILE)
    for fp in DEFAULT_STATE_CANDIDATES:
        if fp not in candidate_files:
            candidate_files.append(fp)

    for fp in candidate_files:
        try:
            if fp and os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # 「ステータスファイル」構造のみ受け入れ; office-agent-state.json（agentId キャッシュ専用）を誤ってステータスソースとして使用しない
                    if not isinstance(data, dict):
                        continue
                    has_state = "state" in data
                    has_detail = "detail" in data
                    if (not has_state) and (not has_detail):
                        continue

                    state = normalize_state(data.get("state", "idle"))
                    detail = data.get("detail", "") or ""
                    # detail でフォールバック補正、「作業/休憩/異常」が正しいエリアに割り当てられることを保証
                    state = map_detail_to_state(detail, fallback_state=state)
                    if VERBOSE:
                        print(f"[status-source:file] path={fp} state={state} detail={detail[:60]}")
                    return {"state": state, "detail": detail}
        except Exception:
            pass

    # 2) ローカル /status を試行（認証が必要な場合あり）
    try:
        import requests
        headers = {}
        if LOCAL_STATUS_TOKEN:
            headers["Authorization"] = f"Bearer {LOCAL_STATUS_TOKEN}"
        r = requests.get(LOCAL_STATUS_URL, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            state = normalize_state(data.get("state", "idle"))
            detail = data.get("detail", "") or ""
            state = map_detail_to_state(detail, fallback_state=state)
            if VERBOSE:
                print(f"[status-source:http] url={LOCAL_STATUS_URL} state={state} detail={detail[:60]}")
            return {"state": state, "detail": detail}
        # 401 の場合、token が必要
        if r.status_code == 401:
            return {"state": "idle", "detail": "ローカル /status に認証が必要（401）、OFFICE_LOCAL_STATUS_TOKEN を設定してください"}
    except Exception:
        pass

    # 3) デフォルト fallback
    if VERBOSE:
        print("[status-source:fallback] state=idle detail=待機中")
    return {"state": "idle", "detail": "待機中"}


def do_join(local):
    import requests
    payload = {
        "name": local.get("agentName", AGENT_NAME),
        "joinKey": local.get("joinKey", JOIN_KEY),
        "state": "idle",
        "detail": "参加しました"
    }
    r = requests.post(f"{OFFICE_URL}{JOIN_ENDPOINT}", json=payload, timeout=10)
    if r.status_code in (200, 201):
        data = r.json()
        if data.get("ok"):
            local["joined"] = True
            local["agentId"] = data.get("agentId")
            save_local_state(local)
            print(f"Starオフィスに参加しました、agentId={local['agentId']}")
            return True
    print(f"参加失敗: {r.text}")
    return False


def do_push(local, status_data):
    import requests
    payload = {
        "agentId": local.get("agentId"),
        "joinKey": local.get("joinKey", JOIN_KEY),
        "state": status_data.get("state", "idle"),
        "detail": status_data.get("detail", ""),
        "name": local.get("agentName", AGENT_NAME)
    }
    r = requests.post(f"{OFFICE_URL}{PUSH_ENDPOINT}", json=payload, timeout=10)
    if r.status_code in (200, 201):
        data = r.json()
        if data.get("ok"):
            area = data.get("area", "breakroom")
            print(f"ステータス同期完了、現在のエリア={area}")
            return True

    # 403/404: 拒否/削除 → プッシュ停止
    if r.status_code in (403, 404):
        msg = ""
        try:
            msg = (r.json() or {}).get("msg", "")
        except Exception:
            msg = r.text
        print(f"アクセス拒否またはルームから退出済み（{r.status_code}）、プッシュ停止: {msg}")
        local["joined"] = False
        local["agentId"] = None
        save_local_state(local)
        sys.exit(1)

    print(f"プッシュ失敗: {r.text}")
    return False


def main():
    local = load_local_state()

    # 設定が完了しているか確認
    if not JOIN_KEY or not AGENT_NAME:
        print("スクリプト冒頭の JOIN_KEY と AGENT_NAME を先に入力してください")
        sys.exit(1)

    # 未参加の場合、先に join
    if not local.get("joined") or not local.get("agentId"):
        ok = do_join(local)
        if not ok:
            sys.exit(1)

    # 継続プッシュ
    print(f"ステータスの継続プッシュを開始、間隔={PUSH_INTERVAL_SECONDS}秒")
    print("ステータスロジック: タスク中→作業エリア; 待機/完了→休憩エリア; 異常→bugエリア")
    print("ローカル /status が Unauthorized(401) を返す場合、環境変数を設定: OFFICE_LOCAL_STATUS_TOKEN または OFFICE_LOCAL_STATUS_URL")
    try:
        while True:
            try:
                status_data = fetch_local_status()
                do_push(local, status_data)
            except Exception as e:
                print(f"プッシュ例外: {e}")
            time.sleep(PUSH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nプッシュを停止しました")
        sys.exit(0)


if __name__ == "__main__":
    main()
