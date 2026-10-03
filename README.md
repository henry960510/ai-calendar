AI Calendar 行程助理

用聊天的方式安排行程的小程式。左邊跟 AI 說話，右邊是週曆。

直接打「下週五下午三點開會」，它就會幫你加進行事曆。

它可以做什麼
用日常說話的方式新增、修改、刪除行程
右邊有週曆，有行程的日子下面會有一個小圓點
也可以自己按右上角的 + 手動新增
行程存在你自己的電腦裡，不用註冊帳號
開始使用
----第一步：安裝 Python（已經有的人可以跳過）---

到 python.org 下載並安裝 Python（3.10 以上）。

Windows 使用者安裝時，請勾選畫面下方的 Add Python to PATH。

---第二步：下載這個程式---
回到這個頁面最上面，點綠色的 Code 按鈕
選 Download ZIP
下載完成後，點兩下解壓縮，會得到一個叫 ai-calendar-main 的資料夾

---第三步：打開終端機，貼上指令---

---Mac：按 Command + 空白鍵，搜尋「終端機」並打開。 把下面整段複製貼上，按 Enter：


bash

cd ~/Downloads/ai-calendar-main

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python AI_calendar1.py



---Windows：按 Windows 鍵，搜尋「cmd」並打開「命令提示字元」。 把下面整段複製貼上，按 Enter：

bash

cd %USERPROFILE%\Downloads\ai-calendar-main

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

python AI_calendar1.py


等它跑完，會跳出行事曆的視窗。

資料夾不在「下載」裡的話，把第一行的路徑換成你放的位置就好。

---第四步：設定 API Key（只有第一次要做）----

這個程式的 AI 是用 Groq 的服務，需要一把你自己的 API Key（免費額度夠一般使用）。第一次打開會自動跳出「設定 API Key」視窗：

點視窗裡的「開啟 Groq 申請頁面」
用 Google 帳號登入 Groq
建立一把新的 API Key，按複製
回到程式，貼在欄位裡，按「儲存」

完成後就可以開始聊天了。想換 Key 的時候，按左上角「行程助理」旁邊的鑰匙圖示。

Key 會不會外流？ 不會。它只存在你這台電腦裡，不會上傳到任何地方。

下次要再打開

每次想用，都要重新開終端機，貼這幾行：

---Mac---

cd ~/Downloads/ai-calendar-main

source venv/bin/activate

python AI_calendar1.py


---Windows---

cd %USERPROFILE%\Downloads\ai-calendar-main

venv\Scripts\activate

python AI_calendar1.py


這次不用再安裝，也不用再設定 Key。

我的資料存在哪裡？

你的行程和 API Key 都存在電腦的 .ai_calendar 資料夾裡：

Mac：/Users/你的名字/.ai_calendar/

Windows：C:\Users\你的名字\.ai_calendar\

這個資料夾是隱藏的（Mac 在 Finder 按 Command + Shift + . 可以顯示）。因為資料不在程式資料夾裡，所以更新或刪除程式不會讓行程消失。想備份的話，複製這個資料夾就好。

隱私說明

你跟 AI 說的話，還有目前行事曆上的行程，會被送到 Groq 處理。請不要在對話裡輸入密碼、身分證字號等敏感資料。

遇到問題怎麼辦

終端機說找不到資料夾（No such file or directory） 資料夾的位置或名字不對。解壓縮後有時會多包一層，輸入 ls（Windows 輸入 dir）看看裡面有什麼，如果只看到另一個 ai-calendar-main，再多打一次 cd ai-calendar-main。

終端機說找不到 python3 或 pip Python 沒有裝好。回到第一步重裝，Windows 記得勾選 Add Python to PATH。Windows 如果 python 不能用，可以試試把指令裡的 python 換成 py。

畫面出現 model_not_found 或 404 Groq 偶爾會把舊模型下架。在專案資料夾裡建立一個叫 .env 的文字檔，寫上 GROQ_MODEL=新的模型名稱，可用的模型名稱請看 Groq 文件。

說 API Key 無效 按左上角的鑰匙圖示重新貼一次，確認前後沒有多餘的空白。

AI 沒有照我說的新增行程 講得具體一點，例如「10 月 15 日下午 2 點看牙醫」。日期和時間都說清楚，它比較不會誤會。

授權

請見 LICENSE 檔案。
