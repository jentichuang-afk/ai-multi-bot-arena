import streamlit as st
import threading
import queue
import time
import json
import os

# ---------------------------------------------------------
# 1. 頁面初始化與樣式載入
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Multi-Bot Arena",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 讀取並注入外部 CSS 樣式檔案
def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("找不到樣式檔案，採用預設樣式。")

load_css("assets/style.css")

# ---------------------------------------------------------
# 2. 初始化 Session State 狀態管理
# ---------------------------------------------------------

# 預設機器人配置
if "bots" not in st.session_state:
    st.session_state.bots = [
        {
            "id": "gemini-flash",
            "name": "Gemini Flash 🚀",
            "provider": "Google Gemini",
            "model": "gemini-1.5-flash",
            "system_prompt": "你是一個幽默、簡短且充滿創意的 AI 助手，請用繁體中文回答。",
            "emoji": "♊",
            "active": True,
            "is_default": True
        },
        {
            "id": "nvidia-llama",
            "name": "Nvidia Llama 🟢",
            "provider": "Nvidia NIM",
            "model": "meta/llama-3.1-70b-instruct",
            "system_prompt": "你是一個專業、嚴謹且善於邏輯推理的 AI 助手，由 Nvidia NIM 提供動力，請用繁體中文回答。",
            "emoji": "🟢",
            "active": True,
            "is_default": True
        },
        {
            "id": "openrouter-free",
            "name": "OpenRouter Llama 🧡",
            "provider": "OpenRouter",
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "system_prompt": "你是一個溫暖、親切、像朋友一樣聊天的 AI 助手，請用繁體中文回答。",
            "emoji": "🧡",
            "active": True,
            "is_default": True
        }
    ]

# 統一對話歷史紀錄
# 結構: [{"user": "哈囉", "replies": {"gemini-flash": "你好...", "nvidia-llama": "您好..."}}]
if "conversation" not in st.session_state:
    st.session_state.conversation = []

# 暫存輸入框的 Key，用於重設輸入
if "temp_input" not in st.session_state:
    st.session_state.temp_input = ""

# ---------------------------------------------------------
# 3. API Key 管理與環境設定
# ---------------------------------------------------------

# 優先讀取 Streamlit Secrets，其次讀取使用者在側邊欄輸入的值
def get_api_keys():
    keys = {
        "Google Gemini": st.secrets.get("GEMINI_API_KEY", ""),
        "Nvidia NIM": st.secrets.get("NVIDIA_API_KEY", ""),
        "OpenRouter": st.secrets.get("OPENROUTER_API_KEY", "")
    }
    
    # 若側邊欄有手動輸入，則覆蓋 Secrets
    if "sidebar_gemini_key" in st.session_state and st.session_state.sidebar_gemini_key:
        keys["Google Gemini"] = st.session_state.sidebar_gemini_key
    if "sidebar_nvidia_key" in st.session_state and st.session_state.sidebar_nvidia_key:
        keys["Nvidia NIM"] = st.session_state.sidebar_nvidia_key
    if "sidebar_openrouter_key" in st.session_state and st.session_state.sidebar_openrouter_key:
        keys["OpenRouter"] = st.session_state.sidebar_openrouter_key
        
    return keys

# ---------------------------------------------------------
# 4. 側邊欄控制面板 (Settings Drawer)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ AI 背景設定中心")
    st.markdown("在此輸入您的 API 金鑰。金鑰將安全地儲存在本機 Session 中，絕不上傳第三方伺服器。")
    
    # 讀取目前的預設/已儲存的金鑰
    keys = get_api_keys()
    
    # 展開摺疊面板：API Keys 設定
    with st.expander("🔑 API 金鑰配置 (API Keys)", expanded=True):
        st.session_state.sidebar_gemini_key = st.text_input(
            "Google Gemini API Key",
            value=st.session_state.get("sidebar_gemini_key", keys["Google Gemini"]),
            type="password",
            placeholder="請輸入 Gemini API Key..."
        )
        # 顯示目前的偵測狀態
        if keys["Google Gemini"]:
            st.caption("🟢 Gemini 金鑰：已設定")
        else:
            st.caption("🔴 Gemini 金鑰：尚未設定")
            
        st.session_state.sidebar_nvidia_key = st.text_input(
            "Nvidia NIM API Key",
            value=st.session_state.get("sidebar_nvidia_key", keys["Nvidia NIM"]),
            type="password",
            placeholder="請輸入 Nvidia NIM API Key..."
        )
        if keys["Nvidia NIM"]:
            st.caption("🟢 Nvidia NIM 金鑰：已設定")
        else:
            st.caption("🔴 Nvidia NIM 金鑰：尚未設定")
            
        st.session_state.sidebar_openrouter_key = st.text_input(
            "OpenRouter API Key",
            value=st.session_state.get("sidebar_openrouter_key", keys["OpenRouter"]),
            type="password",
            placeholder="請輸入 OpenRouter API Key..."
        )
        if keys["OpenRouter"]:
            st.caption("🟢 OpenRouter 金鑰：已設定")
        else:
            st.caption("🔴 OpenRouter 金鑰：尚未設定")

    # 快速勾選要啟用的機器人
    st.markdown("### 🤖 啟用對話的機器人")
    active_count = 0
    for bot in st.session_state.bots:
        # 在側邊欄為每個機器人產生一個核取方塊
        bot["active"] = st.checkbox(
            f"{bot['emoji']} {bot['name']}",
            value=bot["active"],
            key=f"active_check_{bot['id']}"
        )
        if bot["active"]:
            active_count += 1
            
    if active_count == 0:
        st.warning("⚠️ 請至少勾選一個機器人以開始聊天！")

    st.markdown("---")
    # 一鍵清除對話紀錄
    if st.button("🗑️ 清除對話紀錄", use_container_width=True):
        st.session_state.conversation = []
        st.rerun()

# ---------------------------------------------------------
# 5. 併發多執行緒 API 串流處理器 (Concurrent Stream Engine)
# ---------------------------------------------------------
def stream_bot_worker(bot, history, api_keys, token_queue):
    provider = bot["provider"]
    model_id = bot["model"]
    system_prompt = bot["system_prompt"]
    bot_id = bot["id"]
    
    api_key = api_keys.get(provider, "")
    if not api_key:
        token_queue.put((bot_id, f"⚠️ 未設定 {provider} API 金鑰，請在側邊欄填寫。"))
        token_queue.put((bot_id, None))
        return
        
    try:
        # A. Google Gemini 串接
        if provider == "Google Gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # 初始化模型，並帶入 System Prompt 個性設定
            model = genai.GenerativeModel(
                model_name=model_id,
                system_instruction=system_prompt
            )
            
            # 轉換歷史紀錄格式
            gemini_history = []
            for turn in history[:-1]:
                role = "user" if turn["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [turn["content"]]})
                
            # 最新一筆 Prompt
            latest_prompt = history[-1]["content"]
            contents = gemini_history + [{"role": "user", "parts": [latest_prompt]}]
            
            # 發起串流
            response = model.generate_content(contents, stream=True)
            for chunk in response:
                if chunk.text:
                    token_queue.put((bot_id, chunk.text))
                    
        # B. Nvidia NIM 串接 (相容 OpenAI 格式)
        elif provider == "Nvidia NIM":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")
            
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token_queue.put((bot_id, chunk.choices[0].delta.content))
                    
        # C. OpenRouter 串接 (相容 OpenAI 格式)
        elif provider == "OpenRouter":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                stream=True,
                extra_headers={
                    "HTTP-Referer": "https://streamlit.io",
                    "X-Title": "AI Multi-Bot Arena",
                }
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token_queue.put((bot_id, chunk.choices[0].delta.content))
                    
    except Exception as e:
        token_queue.put((bot_id, f"\n\n❌ **API 連線錯誤 ({provider})**: {str(e)}"))
        
    # 發送結束標誌 Sentinel
    token_queue.put((bot_id, None))

# ---------------------------------------------------------
# 6. 主頁面佈局與 UI 渲染
# ---------------------------------------------------------

# 炫彩頂部標題
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="background: linear-gradient(135deg, #a78bfa 0%, #3b82f6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.5rem; letter-spacing: -0.025em; margin-bottom: 0.5rem;">
        ✨ AI Multi-Bot Arena
    </h1>
    <p style="color: #9ca3af; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
        同一個輸入框，同時串流呼叫多個 AI 機器人！在手機上左右滑動分頁或並排比較，輕鬆探索最完美的解答。
    </p>
</div>
""", unsafe_allow_html=True)

# 定義主頁面三大頁籤
main_tab1, main_tab2, main_tab3 = st.tabs(["💬 聊天大廳 (Chat Room)", "🤖 機器人自訂與管理", "⚙️ 配置備份與教學"])

# ==========================================
# 頁籤一：聊天大廳 (Chat Room)
# ==========================================
with main_tab1:
    active_bots = [b for b in st.session_state.bots if b["active"]]
    
    if not active_bots:
        st.info("💡 請先在左側邊欄勾選啟用至少一個 AI 機器人以開始聊天。")
    else:
        # A. 渲染歷史訊息
        for turn_idx, turn in enumerate(st.session_state.conversation):
            # 1. 使用者訊息 (自訂精緻毛玻璃氣泡)
            user_bubble = f"""
            <div class="chat-container">
                <div class="chat-bubble user-bubble">
                    <div class="message-content">{turn['user']}</div>
                    <div class="bot-avatar user-avatar">👤</div>
                </div>
            </div>
            """
            st.markdown(user_bubble, unsafe_allow_html=True)
            
            # 2. AI 機器人回覆 (使用 Tabs / Columns 進行分頁比較呈現)
            bot_tabs = st.tabs([f"{b['emoji']} {b['name']}" for b in active_bots] + ["✨ 全能比較 (Compare)"])
            
            # 渲染個別機器人 Tab
            for idx, bot in enumerate(active_bots):
                with bot_tabs[idx]:
                    reply = turn["replies"].get(bot["id"], "")
                    bot_class = "gemini-bot" if bot["provider"] == "Google Gemini" else "nvidia-bot" if bot["provider"] == "Nvidia NIM" else "openrouter-bot"
                    avatar_class = "gemini-avatar" if bot["provider"] == "Google Gemini" else "nvidia-avatar" if bot["provider"] == "Nvidia NIM" else "openrouter-avatar"
                    name_class = "gemini-name" if bot["provider"] == "Google Gemini" else "nvidia-name" if bot["provider"] == "Nvidia NIM" else "openrouter-name"
                    
                    bot_html = f"""
                    <div class="chat-bubble bot-bubble {bot_class}" style="max-width: 100%;">
                        <div class="bot-avatar {avatar_class}">{bot['emoji']}</div>
                        <div class="message-content">
                            <div class="bot-name {name_class}">{bot['name']} ({bot['model']})</div>
                        </div>
                    </div>
                    """
                    st.markdown(bot_html, unsafe_allow_html=True)
                    st.markdown(reply if reply else "*機器人未回應*")
            
            # 渲染全能比較 Tab
            with bot_tabs[-1]:
                cols = st.columns(len(active_bots))
                for idx, bot in enumerate(active_bots):
                    with cols[idx]:
                        reply = turn["replies"].get(bot["id"], "")
                        bot_class = "gemini-bot" if bot["provider"] == "Google Gemini" else "nvidia-bot" if bot["provider"] == "Nvidia NIM" else "openrouter-bot"
                        avatar_class = "gemini-avatar" if bot["provider"] == "Google Gemini" else "nvidia-avatar" if bot["provider"] == "Nvidia NIM" else "openrouter-avatar"
                        name_class = "gemini-name" if bot["provider"] == "Google Gemini" else "nvidia-name" if bot["provider"] == "Nvidia NIM" else "openrouter-name"
                        
                        bot_html = f"""
                        <div class="chat-bubble bot-bubble {bot_class}" style="max-width: 100%;">
                            <div class="bot-avatar {avatar_class}">{bot['emoji']}</div>
                            <div class="message-content">
                                <div class="bot-name {name_class}">{bot['name']}</div>
                            </div>
                        </div>
                        """
                        st.markdown(bot_html, unsafe_allow_html=True)
                        st.markdown(reply if reply else "*機器人未回應*")

        # B. 處理輸入與即時併發串流
        prompt = st.chat_input("發送訊息給所有啟用的 AI 機器人...")
        
        if prompt:
            # 1. 立即渲染使用者的輸入
            user_bubble = f"""
            <div class="chat-container">
                <div class="chat-bubble user-bubble">
                    <div class="message-content">{prompt}</div>
                    <div class="bot-avatar user-avatar">👤</div>
                </div>
            </div>
            """
            st.markdown(user_bubble, unsafe_allow_html=True)
            
            # 2. 初始化本次回覆容器與串流佔位器
            st.markdown("### 🤖 AI 即時並行串流中...")
            bot_tabs = st.tabs([f"{b['emoji']} {b['name']}" for b in active_bots] + ["✨ 全能比較 (Compare)"])
            
            placeholders = {}
            compare_placeholders = {}
            replies = {bot["id"]: "" for bot in active_bots}
            
            # 建立個別 Tab 的 Placeholder
            for idx, bot in enumerate(active_bots):
                with bot_tabs[idx]:
                    bot_class = "gemini-bot" if bot["provider"] == "Google Gemini" else "nvidia-bot" if bot["provider"] == "Nvidia NIM" else "openrouter-bot"
                    avatar_class = "gemini-avatar" if bot["provider"] == "Google Gemini" else "nvidia-avatar" if bot["provider"] == "Nvidia NIM" else "openrouter-avatar"
                    name_class = "gemini-name" if bot["provider"] == "Google Gemini" else "nvidia-name" if bot["provider"] == "Nvidia NIM" else "openrouter-name"
                    
                    bot_html = f"""
                    <div class="chat-bubble bot-bubble {bot_class}" style="max-width: 100%;">
                        <div class="bot-avatar {avatar_class}">{bot['emoji']}</div>
                        <div class="message-content">
                            <div class="bot-name {name_class}">{bot['name']} ({bot['model']})</div>
                        </div>
                    </div>
                    """
                    st.markdown(bot_html, unsafe_allow_html=True)
                    placeholders[bot["id"]] = st.empty()
                    placeholders[bot["id"]].markdown("<span class='shimmer-text'>⚡ 正在連線中...</span>", unsafe_allow_html=True)
            
            # 建立全能比較 Tab 的 Placeholder (Columns 佈局)
            with bot_tabs[-1]:
                cols = st.columns(len(active_bots))
                for idx, bot in enumerate(active_bots):
                    with cols[idx]:
                        bot_class = "gemini-bot" if bot["provider"] == "Google Gemini" else "nvidia-bot" if bot["provider"] == "Nvidia NIM" else "openrouter-bot"
                        avatar_class = "gemini-avatar" if bot["provider"] == "Google Gemini" else "nvidia-avatar" if bot["provider"] == "Nvidia NIM" else "openrouter-avatar"
                        name_class = "gemini-name" if bot["provider"] == "Google Gemini" else "nvidia-name" if bot["provider"] == "Nvidia NIM" else "openrouter-name"
                        
                        bot_html = f"""
                        <div class="chat-bubble bot-bubble {bot_class}" style="max-width: 100%;">
                            <div class="bot-avatar {avatar_class}">{bot['emoji']}</div>
                            <div class="message-content">
                                <div class="bot-name {name_class}">{bot['name']}</div>
                            </div>
                        </div>
                        """
                        st.markdown(bot_html, unsafe_allow_html=True)
                        compare_placeholders[bot["id"]] = st.empty()
                        compare_placeholders[bot["id"]].markdown("<span class='shimmer-text'>⚡ 正在連線中...</span>", unsafe_allow_html=True)
            
            # 3. 啟動多執行緒併發串流
            token_queue = queue.Queue()
            threads = []
            api_keys = get_api_keys()
            
            for bot in active_bots:
                # 建立該機器人專屬的歷史紀錄（包含過去該機器人回答過的內容）
                bot_history = []
                for turn in st.session_state.conversation:
                    bot_history.append({"role": "user", "content": turn["user"]})
                    if bot["id"] in turn["replies"] and turn["replies"][bot["id"]]:
                        bot_history.append({"role": "assistant", "content": turn["replies"][bot["id"]]})
                
                # 追加目前使用者的最新輸入
                bot_history.append({"role": "user", "content": prompt})
                
                # 啟動 Thread
                t = threading.Thread(
                    target=stream_bot_worker,
                    args=(bot, bot_history, api_keys, token_queue)
                )
                t.start()
                threads.append(t)
                
            # 4. 主執行緒消費 Token 隊列，動態更新 UI
            active_threads = len(active_bots)
            while active_threads > 0:
                try:
                    # 從隊列取出 Token
                    bot_id, token = token_queue.get(timeout=0.05)
                    if token is None:
                        active_threads -= 1
                    else:
                        replies[bot_id] += token
                        # 更新單個機器人 Tab
                        placeholders[bot_id].markdown(replies[bot_id] + " ▌")
                        # 更新比較畫面
                        compare_placeholders[bot_id].markdown(replies[bot_id] + " ▌")
                except queue.Empty:
                    # 避免在 API 緩慢時卡死，檢測執行緒狀態
                    if not any(t.is_alive() for t in threads) and token_queue.empty():
                        break
            
            # 5. 去除光標，完成最終文字渲染
            for bot_id in replies:
                placeholders[bot_id].markdown(replies[bot_id])
                compare_placeholders[bot_id].markdown(replies[bot_id])
                
            # 6. 寫入全域 Session 歷史紀錄，並重新整理頁面以重繪聊天室
            st.session_state.conversation.append({
                "user": prompt,
                "replies": replies
            })
            st.rerun()

# ==========================================
# 頁籤二：機器人自訂與管理
# ==========================================
with main_tab2:
    st.markdown("### 🤖 自訂您的 AI 機器人軍團")
    st.markdown("在此新增、編輯或移除您的機器人。您可以自由設定其個性（System Prompt）、頭像與底層 API 模型。")
    
    # 建立新增機器人卡片
    with st.expander("✨ ➕ 新增自訂 AI 機器人", expanded=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_name = st.text_input("機器人名稱", placeholder="例如：程式碼導師 🧙‍♂️")
            new_model = st.text_input("模型 ID (Model ID)", placeholder="例如：gemini-1.5-pro 或 nvidia/llama-3-1-nemotron-70b-instruct")
        with col2:
            new_provider = st.selectbox("API 提供商 (Provider)", ["Google Gemini", "Nvidia NIM", "OpenRouter"])
            new_emoji = st.text_input("代表頭像 (Emoji)", value="🤖", max_chars=2)
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            add_submitted = st.button("➕ 新增機器人", use_container_width=True)
            
        new_prompt = st.text_area(
            "系統個性設定 (System Prompt)", 
            placeholder="底層大模型的個性設定，例如：'你是一個資深的 Python 專家，說話幽默風趣，請用繁體中文回答。'",
            height=80
        )
        
        if add_submitted:
            if not new_name or not new_model:
                st.error("❌ 請填寫機器人名稱與模型 ID！")
            else:
                # 產生唯一 ID
                new_id = f"custom-{int(time.time())}"
                new_bot = {
                    "id": new_id,
                    "name": new_name,
                    "provider": new_provider,
                    "model": new_model,
                    "system_prompt": new_prompt if new_prompt else "你是一個熱心的 AI 助手，請用繁體中文回答。",
                    "emoji": new_emoji if new_emoji else "🤖",
                    "active": True,
                    "is_default": False
                }
                st.session_state.bots.append(new_bot)
                st.success(f"🎉 成功新增機器人：{new_name}！")
                st.rerun()

    # 顯示現有機器人清單
    st.markdown("### 📋 目前擁有的機器人清單")
    
    # 使用網格排版顯示機器人
    for i, bot in enumerate(st.session_state.bots):
        # 建立精美的玻璃卡片背景
        with st.container():
            st.markdown(f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <span style="font-size: 2rem;">{bot['emoji']}</span>
                        <div>
                            <strong style="font-size: 1.1rem; color: #f3f4f6;">{bot['name']}</strong>
                            <span style="background: rgba(139, 92, 246, 0.2); color: #c084fc; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-left: 0.5rem; border: 1px solid rgba(139, 92, 246, 0.3);">
                                {bot['provider']}
                            </span>
                            <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.25rem;">模型 ID: <code>{bot['model']}</code></div>
                        </div>
                    </div>
                </div>
                <div style="margin-top: 0.85rem; font-size: 0.9rem; color: #d1d5db; background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03);">
                    <strong>🎭 個性設定:</strong><br>{bot['system_prompt']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 操作按鈕列
            btn_col1, btn_col2, _ = st.columns([1, 1, 4])
            with btn_col1:
                # 啟用狀態切換
                bot["active"] = st.toggle("在此啟用", value=bot["active"], key=f"toggle_{bot['id']}")
            with btn_col2:
                # 僅允許刪除自訂機器人，預設機器人不能刪除以防出錯
                if not bot.get("is_default", False):
                    if st.button("🗑️ 刪除機器人", key=f"del_{bot['id']}", use_container_width=True):
                        st.session_state.bots.remove(bot)
                        st.success(f"已刪除 {bot['name']}！")
                        st.rerun()
                else:
                    st.caption("🔒 系統預設（不可刪除）")
            
            st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 頁籤三：配置備份與教學
# ==========================================
with main_tab3:
    st.markdown("### 💾 備份與還原機器人配置")
    st.markdown("因為 Streamlit Cloud 在閒置或網頁重新整理時，`Session State` 狀態可能會重設。建議將您調教好的機器人配置匯出備份，隨時可以一鍵還原！")
    
    # 匯出配置
    bots_json_str = json.dumps(st.session_state.bots, ensure_ascii=False, indent=2)
    
    col_backup1, col_backup2 = st.columns(2)
    
    with col_backup1:
        st.markdown("#### 📤 匯出目前配置")
        st.text_area("複製下方 JSON 代碼保存至您的電腦中：", value=bots_json_str, height=200)
        
    with col_backup2:
        st.markdown("#### 📥 匯入已存配置")
        import_json_str = st.text_area("請在此貼上之前備份的 JSON 代碼：", placeholder="貼上 JSON 備份...", height=150)
        if st.button("📥 一鍵匯入與覆蓋", use_container_width=True):
            try:
                imported_bots = json.loads(import_json_str)
                if isinstance(imported_bots, list) and len(imported_bots) > 0:
                    st.session_state.bots = imported_bots
                    st.success("🎉 機器人配置匯入成功！已覆蓋目前設定。")
                    st.rerun()
                else:
                    st.error("❌ 格式錯誤：請確保匯入的資料是有效的 JSON 陣列！")
            except Exception as e:
                st.error(f"❌ 匯入失敗，解析錯誤：{str(e)}")

    st.markdown("---")
    st.markdown("### ☁️ Streamlit Cloud 背景部署與 Secrets 設定教學")
    st.markdown("""
    當您將本網頁部署至 **Streamlit Cloud** 後，為了方便每次開啟都能**免輸入 API Key** 直接聊天，您可以善用 Streamlit Cloud 的 **Secrets** 安全後台：
    
    1. 前往您的 Streamlit Cloud 管理後台 (Dashboard)。
    2. 找到本 App，點擊右側的 `...` 菜單，選擇 **Settings**。
    3. 點選 **Secrets** 標籤頁。
    4. 貼上並填寫以下設定格式，然後點擊 Save：
    
    ```toml
    # 您的 AI 平台金鑰設定
    GEMINI_API_KEY = "您的_Gemini_API_Key"
    NVIDIA_API_KEY = "您的_Nvidia_NIM_API_Key"
    OPENROUTER_API_KEY = "您的_OpenRouter_API_Key"
    ```
    
    5. 儲存後，網頁將會**全自動在背景讀取**這些金鑰，側邊欄會直接亮起綠燈 🟢，體驗超級完美！
    """)
