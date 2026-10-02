AI Calendar 行程助理

中文 | English

中文

用聊天的方式管理行程的桌面 App。左邊跟 AI 對話，右邊是週曆，直接說「下週五下午三點開會」就會自動新增。

功能
用自然語言新增、修改、刪除行程
週曆檢視，有行程的日期會顯示小圓點
也可以手動按 + 新增行程
行程儲存在本機，不需要註冊帳號
安裝

需要 Python 3.10 以上。

bash
git clone https://github.com/henry960510/ai-calendar.git
cd ai-calendar
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
執行
bash
python AI_calendar1.py
設定 API Key（第一次使用）

AI 功能使用 Groq 的模型，需要你自己的 API Key（有免費額度）：

第一次開啟會自動跳出「設定 API Key」視窗，點「開啟 Groq 申請頁面」
用 Google 帳號登入 Groq，建立一把 API Key 並複製
貼回視窗並按「儲存」

之後要更換，按左上角「行程助理」旁的鑰匙圖示。

Key 存在哪？ 存在你電腦的 ~/.ai_calendar/config.json（Windows 是 C:\Users\你的名稱\.ai_calendar\config.json），不在專案資料夾裡，不會被上傳到 GitHub。

進階：也可以在專案資料夾建立 .env 檔，寫入 GROQ_API_KEY=你的key。介面設定的 key 優先於 .env。

資料與隱私
行程存在專案資料夾的 schedule_data.json（第一次使用時自動建立）。
你傳給 AI 的訊息，以及目前的行程清單，會被送到 Groq 處理，請不要在對話中輸入敏感資訊。
常見問題
顯示 model_not_found / 404：Groq 的模型會更換或下架。預設模型是 openai/gpt-oss-120b，可以在 .env 加上 GROQ_MODEL=其他模型名稱 來換，可用模型請看 Groq 文件。
顯示 API Key 無效：按鑰匙圖示重新貼上 key，確認沒有多餘空白。
行程不見了：行程跟著程式資料夾走，刪除資料夾就會一起刪掉。檔案損毀時程式會自動備份成 schedule_data.json.bak。
授權

請見 LICENSE。

English

A desktop app for managing your schedule by chatting. Talk to the AI on the left, see your week on the right. Just say something like "meeting next Friday at 3pm" and it gets added.

Features
Add, edit, and delete events with natural language
Weekly calendar view, with a dot under days that have events
Add events manually with the + button
Everything is stored locally, no account needed
Installation

Requires Python 3.10 or later.

bash
git clone https://github.com/henry960510/ai-calendar.git
cd ai-calendar
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
Run
bash
python AI_calendar1.py
Setting up your API key (first launch)

The AI runs on models from Groq and needs your own API key (a free tier is available):

On first launch, a "Set API Key" window appears. Click the button to open the Groq key page.
Sign in to Groq with your Google account, create an API key, and copy it.
Paste it into the window and click Save.

To change it later, click the key icon next to the title in the top left.

Where is the key stored? In ~/.ai_calendar/config.json on your computer (on Windows: C:\Users\<you>\.ai_calendar\config.json). It is outside the project folder, so it never gets uploaded to GitHub.

Advanced: you can also create a .env file in the project folder containing GROQ_API_KEY=your_key. A key saved in the app takes priority over .env.

Data and privacy
Events are saved in schedule_data.json inside the project folder (created automatically on first use).
The messages you send and your current event list are sent to Groq for processing. Don't put sensitive information in the chat.
Troubleshooting
model_not_found / 404: Groq retires models from time to time. The default is openai/gpt-oss-120b. Add GROQ_MODEL=another-model to .env to switch; see the Groq docs for available models.
Invalid API key message: click the key icon and paste the key again, making sure there are no extra spaces.
Events disappeared: data lives with the project folder, so deleting the folder deletes the events. If the data file gets corrupted, it is backed up as schedule_data.json.bak.
License

See LICENSE.
