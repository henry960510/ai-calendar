import json
import os
import shutil

# 行程存在使用者家目錄的 .ai_calendar 資料夾（與 API Key 設定同一處）
DATA_DIR = os.path.join(os.path.expanduser("~"), ".ai_calendar")
DATA_FILE = os.path.join(DATA_DIR, "schedule_data.json")

# 舊版把行程存在程式旁邊，第一次執行時會自動搬過來
LEGACY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule_data.json")


def _migrate_legacy():
    """新位置還沒有資料、舊位置有的話，複製過來（保留舊檔不刪除）。"""
    if os.path.exists(DATA_FILE) or not os.path.exists(LEGACY_FILE):
        return
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        shutil.copy(LEGACY_FILE, DATA_FILE)
    except OSError:
        pass


def save_data(events):
    """先寫到暫存檔再替換，避免寫到一半當機而毀掉原本的資料。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=4)
    os.replace(tmp, DATA_FILE)


def load_data():
    """檔案不存在（第一次使用）回傳空列表；檔案損毀則先備份再回傳空列表。"""
    _migrate_legacy()
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [ev for ev in data if isinstance(ev, dict)]
    except (OSError, ValueError):
        pass
    # 內容壞掉：備份起來，避免下次儲存時被覆蓋掉
    try:
        shutil.copy(DATA_FILE, DATA_FILE + ".bak")
    except OSError:
        pass
    return []