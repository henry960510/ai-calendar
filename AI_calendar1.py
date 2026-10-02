import asyncio
import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

import flet as ft
from dotenv import load_dotenv
from groq import Groq

from data_manager import save_data, load_data

load_dotenv()

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
MAX_HISTORY = 20  # 只保留最近 20 則對話

# ── 配色（沿用原本設計）──
ACCENT = "#4f8ef7"
CARD = "#2d2d44"   # 今天的日期底色、新增對話框欄位
TEXT = "white"

# ── API Key 本機設定（存在使用者自己的電腦，不在專案資料夾內）──
CONFIG_PATH = Path.home() / ".ai_calendar" / "config.json"
KEY_URL = "https://console.groq.com/keys"


def load_api_key() -> str:
    """優先讀取介面存的 key，其次才讀 .env。"""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        key = str(data.get("groq_api_key", "")).strip()
        if key:
            return key
    except (OSError, ValueError, AttributeError):
        pass
    return os.environ.get("GROQ_API_KEY", "").strip()


def save_api_key(key: str):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"groq_api_key": key}), encoding="utf-8")
    try:
        CONFIG_PATH.chmod(0o600)  # 只有自己能讀
    except OSError:
        pass


# =====================
# 工具函式
# =====================
def parse_reply(full_response: str):
    """把模型回覆拆成 (文字, 行程動作列表)，容忍 ```json 包裹與格式錯誤。"""
    text, _, rest = full_response.partition("---JSON---")
    rest = rest.split("---JSON---")[0]
    rest = re.sub(r"```(?:json)?", "", rest).strip()
    try:
        data = json.loads(rest) if rest else []
    except json.JSONDecodeError:
        return text.strip(), []
    if not isinstance(data, list):
        return text.strip(), []
    return text.strip(), [d for d in data if isinstance(d, dict)]


def is_valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def is_valid_time(s: str) -> bool:
    try:
        datetime.strptime(s, "%H:%M")
        return True
    except (TypeError, ValueError):
        return False


def make_event(data: dict):
    """驗證並建立行程 dict；欄位不合法回傳 None。"""
    name = str(data.get("event", "")).strip()
    date = str(data.get("date", "")).strip()
    time = str(data.get("time", "09:00")).strip() or "09:00"
    try:
        reminder = int(data.get("reminder", 30))
    except (TypeError, ValueError):
        reminder = 30
    if not name or not is_valid_date(date) or not is_valid_time(time):
        return None
    return {"event": name, "date": date, "time": time, "reminder": reminder}


def remove_event(events: list, name: str, date: str = ""):
    """有日期就用「名稱＋日期」比對，否則只刪第一個同名行程。"""
    for ev in events:
        if ev.get("event") == name and (not date or ev.get("date") == date):
            events.remove(ev)
            return True
    return False


def apply_actions(events: list, actions: list):
    """套用 AI 回傳的動作，回傳 (是否有變動, 最後新增/修改的日期)。"""
    changed = False
    jump_date = None

    for act in actions:
        kind = act.get("action")

        if kind == "delete":
            if remove_event(events, act.get("event", ""), act.get("date", "")):
                changed = True

        elif kind == "update":
            new_ev = make_event(act)
            if new_ev is None:
                continue
            remove_event(events, act.get("old_event", ""), act.get("old_date", ""))
            events.append(new_ev)
            changed, jump_date = True, new_ev["date"]

        elif kind == "add":
            new_ev = make_event(act)
            if new_ev is None:
                continue
            # 避免重複新增完全相同的行程
            if any(ev == new_ev for ev in events):
                continue
            events.append(new_ev)
            changed, jump_date = True, new_ev["date"]

    return changed, jump_date


# =====================
# AI 引擎
# =====================
class AIEngine:
    def __init__(self):
        self.history = []
        self.client = None
        self.api_key = ""
        self.model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.set_api_key(load_api_key())

    def set_api_key(self, key: str):
        self.api_key = key
        self.client = Groq(api_key=key) if key else None

    def has_key(self) -> bool:
        return self.client is not None

    def chat(self, user_input, events=None):
        events = events or []
        if not self.client:
            return "尚未設定 API Key，請按左上角的鑰匙圖示設定。", []
        now = datetime.now()
        today = f"{now:%Y-%m-%d}（週{WEEKDAYS[now.weekday()]}）"
        events_str = json.dumps(events, ensure_ascii=False)

        system_prompt = f"""You are a Traditional Chinese AI schedule assistant named AI Calendar. Today is {today}. Always reply in Traditional Chinese.
When the user says things like「下週五」, compute the date from today's date and weekday above.

目前使用者已有的行程：
{events_str}

你的個性：
- 冷淡、自然，像真人助理一樣對話
- 如果使用者打招呼，回招呼並問他今天有什麼行程需要安排
- 如果使用者問哪幾天有行程，從上面的行程列表回答他
- 如果使用者說的話不含行程資訊，就正常聊天或追問細節

重要規則：
- 只有使用者明確說要新增時才新增
- 確認或查詢現有行程時 action 陣列回傳空的
- 不要重複新增已存在的行程
- 以「目前使用者已有的行程」列表為準，不要根據對話歷史判斷行程是否存在
- 如果使用者說的話包含明確的事件、日期、時間，直接新增，不需要再次確認
- JSON 區塊直接輸出，不要用 ``` 包起來

當你偵測到行程操作時，回應必須包含這個 JSON 區塊：
---JSON---
[
  {{
    "action": "add",
    "event": "事件名稱",
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "reminder": 30
  }}
]
---JSON---

刪除（必須帶上該行程的日期）：
---JSON---
[{{"action": "delete", "event": "事件名稱", "date": "YYYY-MM-DD"}}]
---JSON---

修改：
---JSON---
[{{
  "action": "update",
  "old_event": "舊名稱",
  "old_date": "舊日期",
  "event": "新名稱",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "reminder": 30
}}]
---JSON---

沒有行程操作：
---JSON---
[]
---JSON---
"""

        self.history.append({"role": "user", "content": user_input})
        self.history = self.history[-MAX_HISTORY:]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, *self.history],
            )
            full_response = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": full_response})
            self.history = self.history[-MAX_HISTORY:]
            return parse_reply(full_response)

        except Exception as e:
            self.history.pop()  # 失敗時移除這則使用者訊息，避免歷史錯亂
            msg = str(e)
            if "401" in msg or "invalid_api_key" in msg:
                return "API Key 無效或已被停用，請按左上角的鑰匙圖示重新設定。", []
            return f"發生錯誤：{msg}", []


# =====================
# 主程式
# =====================
def main(page: ft.Page):
    page.title = "行程助理"
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER_50)
    page.bgcolor = "#2b2b2b"
    page.padding = 0

    ai = AIEngine()
    events = load_data()
    selected_date_ref = [datetime.now()]

    # ── API Key 設定對話框 ──
    def open_key_dialog(e=None):
        current = ai.api_key
        status = f"目前已設定：{current[:4]}…{current[-4:]}" if len(current) > 8 else "目前尚未設定"

        key_field = ft.TextField(
            label="Groq API Key",
            hint_text="gsk_...",
            password=True,
            can_reveal_password=True,
            bgcolor=CARD,
            color=TEXT,
            autofocus=True,
        )

        def save(e):
            key = key_field.value.strip()
            if not key or any(c.isspace() for c in key):
                key_field.error_text = "請貼上完整的 API Key（不含空白）"
                page.update()
                return
            try:
                save_api_key(key)
            except OSError as err:
                key_field.error_text = f"無法儲存：{err}"
                page.update()
                return
            ai.set_api_key(key)
            page.pop_dialog()
            add_chat_bubble("AI", "✅ API Key 已儲存，可以開始聊天了。")

        dialog = ft.AlertDialog(
            title=ft.Text("設定 API Key", color=TEXT),
            bgcolor="#1a1a2e",
            content=ft.Column(
                [
                    ft.Text(
                        "AI 功能需要你自己的 Groq API Key（免費）：\n"
                        "1. 點下方按鈕，用 Google 帳號登入 Groq\n"
                        "2. 建立一把 API Key 並複製\n"
                        "3. 貼在下面的欄位",
                        size=13,
                        color="#aaaaaa",
                    ),
                    ft.TextButton("開啟 Groq 申請頁面", icon=ft.Icons.OPEN_IN_NEW, url=KEY_URL),
                    key_field,
                    ft.Text(status, size=11, color="#aaaaaa"),
                    ft.Text("Key 只會存在你這台電腦上，不會上傳。", size=11, color="#aaaaaa"),
                ],
                spacing=10,
                tight=True,
                width=380,
            ),
            actions=[
                ft.TextButton("稍後再說", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("儲存", on_click=save),
            ],
        )
        page.show_dialog(dialog)

    # ── 聊天區 ──
    chat_messages = ft.ListView(expand=True, spacing=10, padding=10, auto_scroll=True)

    def add_chat_bubble(sender, message, is_user=False):
        bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Text(sender, size=11, color="#888888"),
                    ft.Text(message, size=15, color="black", selectable=True),
                ],
                spacing=3,
            ),
            bgcolor="#e2e2e2" if is_user else "#c8c8c8",
            border_radius=12,
            padding=12,
            # 使用者靠右、AI 靠左
            margin=ft.Margin.only(left=40 if is_user else 0, right=0 if is_user else 40),
        )
        chat_messages.controls.append(bubble)
        page.update()

    async def send_message(e):
        user_text = input_field.value.strip()
        if not user_text:
            return
        if not ai.has_key():
            add_chat_bubble("AI", "請先設定 Groq API Key（按左上角的鑰匙圖示）。")
            open_key_dialog()
            return

        input_field.value = ""
        input_field.disabled = True
        page.update()

        add_chat_bubble("你", user_text, is_user=True)
        add_chat_bubble("AI", "⏳ 思考中...", is_user=False)

        # 在背景執行緒呼叫 AI，介面不會卡住
        text_reply, actions = await asyncio.to_thread(ai.chat, user_text, list(events))

        chat_messages.controls.pop()
        add_chat_bubble("AI", text_reply or "（沒有回應）", is_user=False)

        changed, jump_date = apply_actions(events, actions)
        if changed:
            save_data(events)
            if jump_date:  # 週曆自動跳到剛新增的日期
                selected_date_ref[0] = datetime.strptime(jump_date, "%Y-%m-%d")
            refresh_calendar()

        input_field.disabled = False
        page.update()
        await input_field.focus()

    input_field = ft.TextField(
        hint_text="輸入事件...",
        bgcolor="#e2e2e2",
        color="black",
        expand=True,
        on_submit=send_message,
    )
    send_button = ft.IconButton(icon=ft.Icons.SEND, icon_color="#000000", on_click=send_message)

    left_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("💬 行程助理", size=18, weight=ft.FontWeight.BOLD, color="black"),
                        ft.IconButton(
                            icon=ft.Icons.KEY, icon_color="#000000",
                            tooltip="設定 API Key", on_click=open_key_dialog,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color="#c8c8c8"),
                chat_messages,
                ft.Row([input_field, send_button], spacing=8),
            ],
            spacing=8,
        ),
        width=420,
        bgcolor="#c8c8c8",
        padding=15,
    )

    # ── 週曆 ──
    def get_week_dates(base_date):
        monday = base_date - timedelta(days=base_date.weekday())
        return [monday + timedelta(days=i) for i in range(7)]

    def refresh_calendar():
        right_panel.content = build_calendar()
        page.update()

    def select_date(date_str):
        selected_date_ref[0] = datetime.strptime(date_str, "%Y-%m-%d")
        refresh_calendar()

    def change_week(days):
        selected_date_ref[0] += timedelta(days=days)
        refresh_calendar()

    def open_add_dialog(default_date):
        event_field = ft.TextField(label="事件名稱", bgcolor=CARD, color=TEXT)
        date_field = ft.TextField(label="日期 (YYYY-MM-DD)", bgcolor=CARD, color=TEXT, value=default_date)
        time_field = ft.TextField(label="時間 (HH:MM)", bgcolor=CARD, color=TEXT, value="09:00")
        reminder_field = ft.TextField(
            label="提醒（分鐘前）", bgcolor=CARD, color=TEXT, value="30",
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def confirm(e):
            # 逐欄驗證，錯誤顯示在欄位上而不是當掉
            ok = True
            event_field.error_text = None if event_field.value.strip() else "請輸入事件名稱"
            date_field.error_text = None if is_valid_date(date_field.value.strip()) else "日期格式錯誤"
            time_field.error_text = None if is_valid_time(time_field.value.strip()) else "時間格式錯誤"
            reminder_field.error_text = None if reminder_field.value.strip().isdigit() else "請輸入數字"
            for f in (event_field, date_field, time_field, reminder_field):
                if f.error_text:
                    ok = False
            if not ok:
                page.update()
                return

            events.append(
                {
                    "event": event_field.value.strip(),
                    "date": date_field.value.strip(),
                    "time": time_field.value.strip(),
                    "reminder": int(reminder_field.value.strip()),
                }
            )
            save_data(events)
            page.pop_dialog()
            refresh_calendar()

        dialog = ft.AlertDialog(
            title=ft.Text("新增行程", color=TEXT),
            bgcolor="#1a1a2e",
            content=ft.Column(
                [event_field, date_field, time_field, reminder_field], spacing=10, tight=True
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("新增", on_click=confirm),
            ],
        )
        page.show_dialog(dialog)

    def build_calendar():
        week_dates = get_week_dates(selected_date_ref[0])
        today = datetime.now().date()
        sel = selected_date_ref[0].date()
        sel_str = sel.strftime("%Y-%m-%d")

        # 日期列
        day_row = ft.Row(spacing=4, alignment=ft.MainAxisAlignment.CENTER)
        for i, d in enumerate(week_dates):
            is_today = d.date() == today
            is_selected = d.date() == sel
            date_str = d.strftime("%Y-%m-%d")
            has_events = any(ev.get("date") == date_str for ev in events)

            day_row.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(WEEKDAYS[i], size=11, color="#888888", text_align=ft.TextAlign.CENTER),
                            ft.Text(
                                str(d.day),
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT if is_selected else (ACCENT if is_today else "#898989"),
                                text_align=ft.TextAlign.CENTER,
                            ),
                            # 有行程的日子下方顯示小圓點
                            ft.Container(
                                width=5, height=5, border_radius=3,
                                bgcolor=(TEXT if is_selected else ACCENT) if has_events else "transparent",
                            ),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=44,
                    height=64,
                    bgcolor=ACCENT if is_selected else (CARD if is_today else "transparent"),
                    border_radius=10,
                    alignment=ft.Alignment(0, 0),
                    on_click=lambda e, ds=date_str: select_date(ds),
                )
            )

        # 當天行程（依時間排序）
        day_events = sorted(
            (ev for ev in events if ev.get("date") == sel_str),
            key=lambda x: x.get("time", ""),
        )

        event_list = ft.ListView(expand=True, spacing=6, padding=ft.Padding(top=10, left=0, right=0, bottom=0))
        if day_events:
            for ev in day_events:

                def delete_event(e, target=ev):
                    # 直接刪該物件，不會誤刪同名行程
                    if target in events:
                        events.remove(target)
                        save_data(events)
                    refresh_calendar()

                event_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(f"📌 {ev['event']}", size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                                        ft.Text(
                                            f"⏰ {ev['time']}　🔔 {ev['reminder']} 分鐘前",
                                            size=11, color="#aaaaaa",
                                        ),
                                    ],
                                    spacing=3,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color="#ff6b6b",
                                    icon_size=18,
                                    on_click=delete_event,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        bgcolor="#16213e",
                        border_radius=8,
                        padding=10,
                        border=ft.Border.all(1, "#212142"),
                    )
                )
        else:
            event_list.controls.append(ft.Text("這天沒有行程", size=12, color="#555555"))

        nav_row = ft.Row(
            [
                ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_color="#000000", on_click=lambda e: change_week(-7)),
                ft.Text(
                    f"{week_dates[0]:%m/%d} – {week_dates[6]:%m/%d}", size=12, color="#888888"
                ),
                ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color="#000000", on_click=lambda e: change_week(7)),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
        )

        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("📅 週曆", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.IconButton(
                            icon=ft.Icons.ADD, icon_color=ACCENT,
                            on_click=lambda e: open_add_dialog(sel_str),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color="#2d2d44"),
                nav_row,
                day_row,
                ft.Divider(color="#2d2d44"),
                ft.Text(f"{sel:%m月%d日} 的行程", size=13, color="#aaaaaa"),
                event_list,
            ],
            spacing=8,
            expand=True,
        )

    right_panel = ft.Container(content=build_calendar(), expand=True, bgcolor="#c8c8c8", padding=15)

    page.add(ft.Row([left_panel, right_panel], expand=True, spacing=0))

    # 歡迎訊息：依是否已有行程調整
    if events:
        add_chat_bubble("AI", "👋 歡迎回來！之前的行程已經幫你準備好囉。")
    else:
        add_chat_bubble("AI", "👋 你好！目前還沒有行程，想安排什麼可以直接跟我說。")

    if not ai.has_key():  # 第一次使用，自動跳出 API Key 設定
        open_key_dialog()


ft.run(main)