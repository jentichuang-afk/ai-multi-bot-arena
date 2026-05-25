# ✨ AI Multi-Bot Arena (手機優化版多 AI 同時聊天室 + 雲端硬碟同步)

這是一個專門為**行動端手機**以及**高質感網頁體驗**設計的多 AI 機器人同時聊天網頁，採用 **Python + Streamlit** 框架開發，完美解決了前端跨來源資源共用 (CORS) 限制，並極致優化了手機手勢操作。

本專案完全相容於 **Streamlit Cloud** 免費託管服務，並整合了 **Google 帳號登入** 與 **Google Drive 雲端自動對話同步** 功能，讓您的設定與對話永不遺失！

---

## 🌟 核心特色

1. **並行多機串流 (Concurrent Multi-Stream Engine)**
   - 採用多執行緒 (Threading) 消費者隊列模式，輸入一條訊息，同時觸發多個 AI 進行串流 (Streaming)。
   - **Gemini、Nvidia NIM、OpenRouter** 串流回覆同時吐字，畫面生動且完全不阻塞、不卡頓。

2. **👤 Google 帳號登入與 Google Drive 自動備份同步 (全新升級！)**
   - **一鍵 Google 登入**：串接 Google OAuth 2.0，登入後側邊欄顯示您的 Google 頭像與姓名。
   - **Google Drive 雲端同步**：自動在您的雲端硬碟建立 `ai_multi_bot_arena_config.json` (自訂機器人) 與 `ai_multi_bot_arena_history.json` (完整對話紀錄)。
   - **自動雲端同步 (Auto-Sync)**：每次發送訊息或新增、移除、切換機器人時，背景自動同步寫入 Google Drive，換手機、換電腦也只需登入即可完美續接對話！
   - **極致隱私保護 (`drive.file` 權限)**：僅申請最小權限，程式**只對由自己建立的這兩個檔案有存取權限**，絕對無法讀取您雲端硬碟裡的其他私人相片或文件。

3. **高質感毛玻璃風 (Glassmorphism & Dark Aurora Theme)**
   - 墨黑極光深色主題，搭配高度半透明、带細微邊框發光的玻璃質感卡片 (`style.css`)。
   - 專門針對各家 AI 繪製專屬的光暈色彩（Gemini 藍色、Nvidia 綠色、OpenRouter 橘色）。
   - 微滑入動畫、打字骨架屏載入 (Shimmer Effect)、漂亮的客製化按鈕與字型。

4. **動態機器人管理與自訂個性**
   - 隨時可以**新增、修改、移除**對話中的 AI 機器人。
   - 自訂機器人名稱、底層 API Provider (Gemini / Nvidia NIM / OpenRouter)、指定特定模型 ID。
   - 自由定義每個機器人的**個性與角色設定 (System Prompt)**，並配置其代表頭像 Emoji。

---

## 🛠️ 本地快速啟動教學

請確保您的電腦已安裝 Python 3.8 或以上版本。

1. **複製本專案至本地並進入目錄：**
   ```bash
   cd "d:\AntiGravity\AI talk"
   ```

2. **安裝所需依賴套件：**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置本地 Secrets 金鑰 (選用)：**
   在 `d:\AntiGravity\AI talk` 目錄下建立 `.streamlit/secrets.toml`，並填入以下內容（若不建立，也可在啟動後的網頁側邊欄動態輸入）：
   ```toml
   GEMINI_API_KEY = "您的_Gemini_API_Key"
   NVIDIA_API_KEY = "您的_Nvidia_API_Key"
   OPENROUTER_API_KEY = "您的_OpenRouter_API_Key"
   
   # Google 登入用憑證 (選填，若要測試 Google 登入請填寫)
   GOOGLE_CLIENT_ID = "您的_Google_Client_ID"
   GOOGLE_CLIENT_SECRET = "您的_Google_Client_Secret"
   GOOGLE_REDIRECT_URI = "http://localhost:8501/"
   ```

4. **啟動 Streamlit 服務：**
   ```bash
   streamlit run app.py
   ```

5. **在手機上測試：**
   - 啟動後，終端機顯示 `Network URL: http://<您的區域網路IP>:8501`。
   - 確保手機與電腦連線至同一個 Wi-Fi，在手機瀏覽器輸入該網址，即可流暢體驗！

---

## 🛡️ 如何申請 Google OAuth 2.0 用戶端憑證？

若您想使用 Google 帳號登入與雲端硬碟同步功能，您需要取得一組 Google API 憑證：

1. 前往 **[Google Cloud Console](https://console.cloud.google.com/)**，點擊建立新專案。
2. 前往 **API 和服務 -> OAuth 同意畫面**：
   - 選擇 **External (外部)**，填寫基本資料。
   - 在 Scopes 中加入 `.../auth/userinfo.profile`, `.../auth/userinfo.email` 與 `.../auth/drive.file`。
   - 在 **測試使用者 (Test users)** 中，加入您自己的 Google 電子信箱。
3. 前往 **憑證 (Credentials) -> 建立憑證 -> OAuth 用戶端 ID**：
   - 應用程式類型：**網頁應用程式 (Web application)**
   - 在 **已授權的重新導向 URI** 中，填入：
     - 本地測試：`http://localhost:8501/`
     - 雲端網址（部署至 Streamlit Cloud 後）：`https://您的專案名稱.streamlit.app/`
4. 點選儲存後即可取得 **用戶端 ID (Client ID)** 與 **用戶端密鑰 (Client Secret)**！

---

## ☁️ 部署到 Streamlit Cloud 教學

您可以完全免費將此網頁部署至 **Streamlit Community Cloud**：

1. 將本專案上傳至您的 **GitHub** 儲存庫（只要我修改程式碼，都會自動為您 Push 更新！）。
2. 前往 [Streamlit Community Cloud](https://share.streamlit.io/) 並使用 GitHub 登入。
3. 點選 **New app**，選擇您的儲存庫與分支，並將 Main file path 設定為 `app.py`。
4. **設定背景金鑰 (Secrets)**：
   - 在部署設定頁面，找到 **Advanced settings...** 中的 **Secrets**。
   - 貼上並填寫以下完整內容：
     ```toml
     # 1. 您的 AI 平台 API 金鑰設定
     GEMINI_API_KEY = "您的_Gemini_API_Key"
     NVIDIA_API_KEY = "您的_Nvidia_NIM_API_Key"
     OPENROUTER_API_KEY = "您的_OpenRouter_API_Key"
     
     # 2. Google OAuth 2.0 用戶端憑證設定 (Redirect URI 請修改為雲端網址)
     GOOGLE_CLIENT_ID = "您的_Google_OAuth_Client_ID"
     GOOGLE_CLIENT_SECRET = "您的_Google_OAuth_Client_Secret"
     GOOGLE_REDIRECT_URI = "https://您的專案名稱.streamlit.app/"
     ```
5. 點擊 **Deploy!**，您的專屬手機多 AI 雲端聊天網頁即刻上線！
