# ✨ AI Multi-Bot Arena (手機優化版多 AI 同時聊天室)

這是一個專門為**行動端手機**以及**高質感網頁體驗**設計的多 AI 機器人同時聊天網頁，採用 **Python + Streamlit** 框架開發，完美解決了前端跨來源資源共用 (CORS) 限制，並極致優化了手機手勢操作。

本專案完全相容於 **Streamlit Cloud** 免費託管服務，您可以一鍵部署並安全儲存 API Key 至雲端 Secrets 後台。

---

## 🌟 核心特色

1. **並行多機串流 (Concurrent Multi-Stream Engine)**
   - 採用多執行緒 (Threading) 消費者隊列模式，輸入一條訊息，同時觸發多個 AI 進行串流 (Streaming)。
   - **Gemini、Nvidia NIM、OpenRouter** 串流回覆同時吐字，畫面生動且完全不阻塞、不卡頓。

2. **高質感毛玻璃風 (Glassmorphism & Dark Aurora Theme)**
   - 墨黑極光深色主題，搭配高度半透明、带細微邊框發光的玻璃質感卡片 (`style.css`)。
   - 專門針對各家 AI 繪製專屬的光暈色彩（Gemini 藍色、Nvidia 綠色、OpenRouter 橘色）。
   - 微滑入動畫、打字骨架屏載入 (Shimmer Effect)、漂亮的客製化按鈕與字型。

3. **動態機器人管理與自訂個性**
   - 隨時可以**新增、修改、移除**對話中的 AI 機器人。
   - 自訂機器人名稱、底層 API Provider (Gemini / Nvidia NIM / OpenRouter)、指定特定模型 ID。
   - 自由定義每個機器人的**個性與角色設定 (System Prompt)**，並配置其代表頭像 Emoji。
   - 內建配置 **JSON 備份與一鍵還原**，徹底解決 Streamlit 頁面重設導致自訂機器人遺失的痛點。

4. **手機端體驗深度優化 (Mobile-First Layout)**
   - 手機專屬**分頁滑動 (Tabs)** 體驗，單手即可迅速在不同 AI 答案間滑動切換。
   - 大螢幕或「全能比較 (Compare)」模式下自動以並排欄位 (Columns) 呈現，直觀對比回答品質。
   - 手機側邊欄整合金鑰管理，如同從左側滑出的設定抽屜 (Settings Drawer)，整潔不佔空間。

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

3. **啟動 Streamlit 服務：**
   ```bash
   streamlit run app.py
   ```

4. **在手機上測試：**
   - 啟動後，終端機會顯示 `Network URL: http://<您的區域網路IP>:8501`。
   - 確保手機與電腦連線至同一個 Wi-Fi，在手機瀏覽器輸入該網址，即可在手機上流暢體驗！

---

## ☁️ 部署到 Streamlit Cloud 教學

您可以完全免費將此網頁部署至 **Streamlit Cloud**：

1. 將本專案上傳至您的 **GitHub** 儲存庫。
2. 前往 [Streamlit Community Cloud](https://share.streamlit.io/) 並使用 GitHub 登入。
3. 點選 **New app**，選擇您上傳的專案儲存庫、分支（通常為 `main`），並將 Main file path 設定為 `app.py`。
4. **設定背景金鑰 (Secrets)**：
   - 在部署設定頁面，找到 **Advanced settings...** 中的 **Secrets**。
   - 填入您的 API Keys（系統會自動讀取，安全隱密且每次開網頁免重新輸入）：
     ```toml
     GEMINI_API_KEY = "您的_Gemini_API_Key"
     NVIDIA_API_KEY = "您的_Nvidia_NIM_API_Key"
     OPENROUTER_API_KEY = "您的_OpenRouter_API_Key"
     ```
5. 點擊 **Deploy!**，約一分鐘後，您的專屬手機 AI 聊天網頁便大功告成！

---

## 📂 專案檔案結構說明

- 📁 `.streamlit/`
  - `config.toml` — 設定客製化深色主題、主色調與安全選項。
- 📁 `assets/`
  - `style.css` — 全網頁的毛玻璃風、光暈邊框、打字動畫、響應式佈局等 Vanilla CSS 樣式。
- 📄 `app.py` — 主程式，控制機器人狀態、多執行緒 API 發送與 UI 控制。
- 📄 `requirements.txt` — 必要的 Python 相依庫清單。
- 📄 `README.md` — 專案說明與部署指南。
