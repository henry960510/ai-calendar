import json
import os
import shutil

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule_data.json")


def save_data(events):
    """先寫到暫存檔再替換，避免寫到一半當機而毀掉原本的資料。"""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=4)
    os.replace(tmp, DATA_FILE)


def load_data():
    """檔案不存在（第一次使用）回傳空列表；檔案損毀則先備份再回傳空列表。"""
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