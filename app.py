import streamlit as st
import threading
import queue
import time
import json
import os
import google_drive_sync

def fetch_api_models(provider, api_keys):
    """根據指定的 API 提供商與金鑰，動態拉取可用的模型清單"""
    cache_key = f"models_cache_{provider}"
    
    # 優先從 session_state 快取讀取，避免重覆呼叫 API 造成延遲
    if cache_key in st.session_state and st.session_state[cache_key]:
        return st.session_state[cache_key]
        
    api_key = api_keys.get(provider, "")
    
    # OpenRouter：免金鑰即可公開拉取所有最新模型列表，非常友善！
    if provider == "OpenRouter":
        try:
            import requests
            response = requests.get("https://openrouter.ai/api/v1/models", timeout=4)
            if response.status_code == 200:
                data = response.json()
                models = [m["id"] for m in data.get("data", [])]
                # 篩選並將免費模型 (:free) 與常規熱門模型排序
                free_models = sorted([m for m in models if ":free" in m])
                other_models = sorted([m for m in models if ":free" not in m])
                sorted_models = free_models + other_models
                if sorted_models:
                    st.session_state[cache_key] = sorted_models + ["自訂模型 ID..."]
                    return st.session_state[cache_key]
        except Exception:
            pass
            
    # Gemini 與 Nvidia NIM 必須有 API Key 才能執行偵測
    if not api_key:
        defaults = {
            "Google Gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp", "自訂模型 ID..."],
            "Nvidia NIM": ["meta/llama-3.1-70b-instruct", "nvidia/llama-3-1-nemotron-70b-instruct", "meta/llama-3.1-8b-instruct", "自訂模型 ID..."]
        }
        return defaults.get(provider, ["自訂模型 ID..."])
        
    try:
        if provider == "Google Gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            models = genai.list_models()
            gemini_list = []
            for m in models:
                if "generateContent" in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    gemini_list.append(name)
            if gemini_list:
                st.session_state[cache_key] = sorted(gemini_list) + ["自訂模型 ID..."]
                return st.session_state[cache_key]
                
        elif provider == "Nvidia NIM":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")
            models = client.models.list()
            nim_list = [m.id for m in models.data]
            if nim_list:
                st.session_state[cache_key] = sorted(nim_list) + ["自訂模型 ID..."]
                return st.session_state[cache_key]
                
    except Exception as e:
        st.toast(f"⚠️ 自動偵測 {provider} 模型失敗，使用預設清單: {str(e)}")
        
    # 失敗時的回退預設值
    defaults = {
        "Google Gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp", "自訂模型 ID..."],
        "Nvidia NIM": ["meta/llama-3.1-70b-instruct", "nvidia/llama-3-1-nemotron-70b-instruct", "meta/llama-3.1-8b-instruct", "自訂模型 ID..."],
        "OpenRouter": ["meta-llama/llama-3.1-8b-instruct:free", "google/gemma-2-9b-it:free", "自訂模型 ID..."]
    }
    return defaults.get(provider, ["自訂模型 ID..."])

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
if "conversation" not in st.session_state:
    st.session_state.conversation = []

# Google OAuth 驗證相關
if "google_credentials" not in st.session_state:
    st.session_state.google_credentials = None

if "google_auto_sync" not in st.session_state:
    st.session_state.google_auto_sync = True

# ---------------------------------------------------------
# 3. API Keys & Google OAuth 設定管理
# ---------------------------------------------------------
def get_api_keys():
    return {
        "Google Gemini": st.secrets.get("GEMINI_API_KEY", ""),
        "Nvidia NIM": st.secrets.get("NVIDIA_API_KEY", ""),
        "OpenRouter": st.secrets.get("OPENROUTER_API_KEY", "")
    }

def get_google_oauth_config():
    return {
        "client_id": st.secrets.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": st.secrets.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": st.secrets.get("GOOGLE_REDIRECT_URI", "")
    }

# ---------------------------------------------------------
# 4. Google Drive 雲端同步觸發器 (Cloud Sync Helpers)
# ---------------------------------------------------------
def sync_to_google_drive():
    """將目前的對話與機器人設定同步上傳至 Google Drive"""
    if st.session_state.google_credentials:
        try:
            creds = google_drive_sync.dict_to_credentials(st.session_state.google_credentials)
            # 同步設定檔
            google_drive_sync.save_data_to_drive(
                creds, "ai_multi_bot_arena_config.json", st.session_state.bots
            )
            # 同步對話紀錄
            google_drive_sync.save_data_to_drive(
                creds, "ai_multi_bot_arena_history.json", st.session_state.conversation
            )
            # 刷新憑證（若在過程中自動刷新了 Access Token）
            st.session_state.google_credentials = google_drive_sync.credentials_to_dict(creds)
        except Exception as e:
            pass

def sync_from_google_drive():
    """自 Google Drive 下載並還原配置與對話"""
    if st.session_state.google_credentials:
        try:
            creds = google_drive_sync.dict_to_credentials(st.session_state.google_credentials)
            # 載入自訂機器人
            cloud_bots, err = google_drive_sync.load_data_from_drive(creds, "ai_multi_bot_arena_config.json")
            if cloud_bots:
                st.session_state.bots = cloud_bots
            # 載入對話歷史
            cloud_conv, err = google_drive_sync.load_data_from_drive(creds, "ai_multi_bot_arena_history.json")
            if cloud_conv:
                st.session_state.conversation = cloud_conv
            st.session_state.google_credentials = google_drive_sync.credentials_to_dict(creds)
            return True, "雲端資料下載成功！"
        except Exception as e:
            return False, f"自雲端載入失敗: {str(e)}"
    return False, "尚未登入 Google 帳號。"

# ---------------------------------------------------------
# 5. 解析 Google OAuth2 重新導向回傳的 Authorization Code
# ---------------------------------------------------------
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    oauth_config = get_google_oauth_config()
    
    if oauth_config["client_id"] and oauth_config["client_secret"] and oauth_config["redirect_uri"]:
        try:
            flow = google_drive_sync.get_oauth_flow(
                oauth_config["client_id"],
                oauth_config["client_secret"],
                oauth_config["redirect_uri"]
            )
            flow.fetch_token(code=auth_code)
            st.session_state.google_credentials = google_drive_sync.credentials_to_dict(flow.credentials)
            st.toast("🎉 Google 帳號驗證成功！")
            
            # 清除網址列上的 query params，避免重複執行 Token 交換
            st.query_params.clear()
            
            # 登入成功後，預設執行一次自動下載還原
            success, msg = sync_from_google_drive()
            if success:
                st.toast("📥 已成功自動載入雲端對話與設定！")
            
            st.rerun()
        except Exception as e:
            st.error(f"❌ Google OAuth2 Token 交換失敗: {str(e)}")
            st.query_params.clear()
    else:
        st.error("❌ 偵測到 Google 回傳代碼，但系統尚未設定 Google Client ID/Secret 憑證資訊，無法完成登入！")
        st.query_params.clear()

# ---------------------------------------------------------
# 6. 側邊欄控制面板 (Settings Drawer)
# ---------------------------------------------------------
with st.sidebar:
    # 👤 A. Google 雲端同步區塊
    st.markdown("## 👤 Google 雲端同步")
    oauth_config = get_google_oauth_config()
    
    if st.session_state.google_credentials:
        # 已登入狀態
        try:
            creds = google_drive_sync.dict_to_credentials(st.session_state.google_credentials)
            user_info = google_drive_sync.get_user_info(creds)
            
            if user_info:
                # 圓形 glowing 頭像與使用者資訊
                st.markdown(f"""
                <div style="display: flex; gap: 0.85rem; align-items: center; background: rgba(255, 255, 255, 0.05); padding: 0.85rem; border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.2); margin-bottom: 1rem;">
                    <img src="{user_info.get('picture', '')}" style="width: 46px; height: 46px; border-radius: 50%; border: 2px solid #8b5cf6; box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);">
                    <div style="overflow: hidden;">
                        <div style="font-weight: 600; font-size: 0.95rem; color: #ffffff;">{user_info.get('name', '')}</div>
                        <div style="font-size: 0.75rem; color: #9ca3af; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{user_info.get('email', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 自動同步選項
                st.session_state.google_auto_sync = st.toggle("🔄 自動雲端同步", value=st.session_state.google_auto_sync)
                st.caption("開啟後，對話或機器人設定異動將自動上傳 Google Drive。")
                
                col_sync1, col_sync2 = st.columns(2)
                with col_sync1:
                    if st.button("📤 雲端備份", use_container_width=True):
                        sync_to_google_drive()
                        st.toast("✅ 備份成功！")
                with col_sync2:
                    if st.button("📥 雲端還原", use_container_width=True):
                        success, msg = sync_from_google_drive()
                        if success:
                            st.toast("✅ 還原成功！")
                            st.rerun()
                        else:
                            st.error(msg)
                
                if st.button("🚪 登出 Google 帳號", use_container_width=True, type="secondary"):
                    st.session_state.google_credentials = None
                    st.toast("已成功登出 Google 帳號！")
                    st.rerun()
            else:
                st.warning("⚠️ 無法讀取 Google 使用者資料，請嘗試重新登入。")
                if st.button("🚪 登出", use_container_width=True):
                    st.session_state.google_credentials = None
                    st.rerun()
        except Exception as e:
            st.error(f"還原 Google 連線失敗: {str(e)}")
            st.session_state.google_credentials = None
    else:
        # 未登入狀態
        if oauth_config["client_id"] and oauth_config["client_secret"] and oauth_config["redirect_uri"]:
            login_url, state = google_drive_sync.get_login_url(
                oauth_config["client_id"],
                oauth_config["client_secret"],
                oauth_config["redirect_uri"]
            )
            if login_url:
                st.markdown(f'<a href="{login_url}" target="_self"><button style="width: 100%; background: linear-gradient(135deg, #4285F4 0%, #357AE8 100%); color: white; border: none; padding: 0.6rem; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(66, 133, 244, 0.2);"><svg style="width:18px;height:18px;" viewBox="0 0 24 24"><path fill="currentColor" d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.114-5.136 4.114-3.513 0-6.386-2.873-6.386-6.386 0-3.513 2.873-6.386 6.386-6.386 1.632 0 3.12.617 4.26 1.628l3.056-3.056C19.43 2.416 16.05 1 12.24 1 5.58 1 0 6.58 0 13.24s5.58 12.24 12.24 12.24c6.82 0 11.23-4.79 11.23-11.23 0-.756-.067-1.333-.167-1.965h-11.07z"/></svg> 登入 Google 帳號</button></a>', unsafe_allow_html=True)
                st.caption("點擊登入後，系統將安全地與您的 Google Drive 進行同步。")
            else:
                st.error("登入連結產生失敗。")
        else:
            st.warning("⚠️ 請在 Streamlit Secrets 設定您的 Google 登入憑證 (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) 以啟用雲端同步！")

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
        if st.session_state.google_credentials and st.session_state.google_auto_sync:
            sync_to_google_drive()
        st.rerun()

# ---------------------------------------------------------
# 7. 併發多執行緒 API 串流處理器 (Concurrent Stream Engine)
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
            
            model = genai.GenerativeModel(
                model_name=model_id,
                system_instruction=system_prompt
            )
            
            gemini_history = []
            for turn in history[:-1]:
                role = "user" if turn["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [turn["content"]]})
                
            latest_prompt = history[-1]["content"]
            contents = gemini_history + [{"role": "user", "parts": [latest_prompt]}]
            
            response = model.generate_content(contents, stream=True)
            for chunk in response:
                if chunk.text:
                    token_queue.put((bot_id, chunk.text))
                    
        # B. Nvidia NIM 串接
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
                    
        # C. OpenRouter 串接
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
        
    token_queue.put((bot_id, None))

# ---------------------------------------------------------
# 8. 主頁面佈局與 UI 渲染
# ---------------------------------------------------------
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
            # 使用者訊息
            user_bubble = f"""
            <div class="chat-container">
                <div class="chat-bubble user-bubble">
                    <div class="message-content">{turn['user']}</div>
                    <div class="bot-avatar user-avatar">👤</div>
                </div>
            </div>
            """
            st.markdown(user_bubble, unsafe_allow_html=True)
            
            # AI 機器人回覆 (Tabs 分頁)
            bot_tabs = st.tabs([f"{b['emoji']} {b['name']}" for b in active_bots] + ["✨ 全能比較 (Compare)"])
            
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
            
            # 全能比較 Tab
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
            user_bubble = f"""
            <div class="chat-container">
                <div class="chat-bubble user-bubble">
                    <div class="message-content">{prompt}</div>
                    <div class="bot-avatar user-avatar">👤</div>
                </div>
            </div>
            """
            st.markdown(user_bubble, unsafe_allow_html=True)
            
            st.markdown("### 🤖 AI 即時並行串流中...")
            bot_tabs = st.tabs([f"{b['emoji']} {b['name']}" for b in active_bots] + ["✨ 全能比較 (Compare)"])
            
            placeholders = {}
            compare_placeholders = {}
            replies = {bot["id"]: "" for bot in active_bots}
            
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
            
            token_queue = queue.Queue()
            threads = []
            api_keys = get_api_keys()
            
            for bot in active_bots:
                bot_history = []
                for turn in st.session_state.conversation:
                    bot_history.append({"role": "user", "content": turn["user"]})
                    if bot["id"] in turn["replies"] and turn["replies"][bot["id"]]:
                        bot_history.append({"role": "assistant", "content": turn["replies"][bot["id"]]})
                
                bot_history.append({"role": "user", "content": prompt})
                
                t = threading.Thread(
                    target=stream_bot_worker,
                    args=(bot, bot_history, api_keys, token_queue)
                )
                t.start()
                threads.append(t)
                
            active_threads = len(active_bots)
            while active_threads > 0:
                try:
                    bot_id, token = token_queue.get(timeout=0.05)
                    if token is None:
                        active_threads -= 1
                    else:
                        replies[bot_id] += token
                        placeholders[bot_id].markdown(replies[bot_id] + " ▌")
                        compare_placeholders[bot_id].markdown(replies[bot_id] + " ▌")
                except queue.Empty:
                    if not any(t.is_alive() for t in threads) and token_queue.empty():
                        break
            
            for bot_id in replies:
                placeholders[bot_id].markdown(replies[bot_id])
                compare_placeholders[bot_id].markdown(replies[bot_id])
                
            st.session_state.conversation.append({
                "user": prompt,
                "replies": replies
            })
            
            # 若已登入且開啟自動雲端同步，則將新對話同步至 Google Drive
            if st.session_state.google_credentials and st.session_state.google_auto_sync:
                sync_to_google_drive()
                
            st.rerun()

# ==========================================
# 頁籤二：機器人自訂與管理
# ==========================================
with main_tab2:
    st.markdown("### 🤖 自訂您的 AI 機器人軍團")
    
    with st.expander("✨ ➕ 新增自訂 AI 機器人", expanded=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col2:
            new_provider = st.selectbox("API 提供商 (Provider)", ["Google Gemini", "Nvidia NIM", "OpenRouter"])
            new_emoji = st.text_input("代表頭像 (Emoji)", value="🤖", max_chars=2)
            
        # 動態偵測 API 金鑰下可用的模型清單
        api_keys = get_api_keys()
        model_options = fetch_api_models(new_provider, api_keys)
        
        with col1:
            new_name = st.text_input("機器人名稱", placeholder="例如：程式碼導師 🧙‍♂️")
            
            # 模型選擇下拉選單 (自動偵測可用模型)
            selected_model_option = st.selectbox("選擇模型 ID (Model ID)", model_options)
            
            # 若使用者選取「自訂模型 ID...」，則顯示文字輸入欄位讓使用者自行填寫
            if selected_model_option == "自訂模型 ID...":
                new_model = st.text_input("請輸入自訂模型 ID", placeholder="例如：meta-llama/llama-3.3-70b-instruct")
            else:
                new_model = selected_model_option
                
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if selected_model_option == "自訂模型 ID...":
                st.markdown("<br><br>", unsafe_allow_html=True)
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
                
                # 自動同步
                if st.session_state.google_credentials and st.session_state.google_auto_sync:
                    sync_to_google_drive()
                    st.toast("✅ 已自動同步新增的機器人至雲端！")
                    
                st.success(f"🎉 成功新增機器人：{new_name}！")
                st.rerun()

    # 顯示現有機器人清單
    st.markdown("### 📋 目前擁有的機器人清單")
    
    for i, bot in enumerate(st.session_state.bots):
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
            
            btn_col1, btn_col2, _ = st.columns([1, 1, 4])
            with btn_col1:
                # 狀態切換
                old_active = bot["active"]
                bot["active"] = st.toggle("在此啟用", value=bot["active"], key=f"toggle_{bot['id']}")
                if old_active != bot["active"] and st.session_state.google_credentials and st.session_state.google_auto_sync:
                    sync_to_google_drive()
            with btn_col2:
                if not bot.get("is_default", False):
                    if st.button("🗑️ 刪除機器人", key=f"del_{bot['id']}", use_container_width=True):
                        st.session_state.bots.remove(bot)
                        if st.session_state.google_credentials and st.session_state.google_auto_sync:
                            sync_to_google_drive()
                        st.success(f"已刪除 {bot['name']}！")
                        st.rerun()
                else:
                    st.caption("🔒 系統預設（不可刪除）")
            st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 頁籤三：配置備份與教學
# ==========================================
with main_tab3:
    st.markdown("### 💾 本地備份與還原機器人配置")
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
                    if st.session_state.google_credentials and st.session_state.google_auto_sync:
                        sync_to_google_drive()
                    st.success("🎉 機器人配置匯入成功！已覆蓋目前設定。")
                    st.rerun()
                else:
                    st.error("❌ 格式錯誤：請確保匯入的資料是有效的 JSON 陣列！")
            except Exception as e:
                st.error(f"❌ 匯入失敗，解析錯誤：{str(e)}")

    st.markdown("---")
    st.markdown("### ☁️ Streamlit Cloud 背景部署與 Secrets 設定教學")
    st.markdown("""
    本專案支援全自動背景 API 金鑰與 Google OAuth2 帳號登入對接。請前往 Streamlit Cloud 後台，在您的 App 設定中，點選 **Secrets** 並貼上填寫以下完整內容：
    
    ```toml
    # 1. 您的 AI 平台 API 金鑰設定
    GEMINI_API_KEY = "您的_Gemini_API_Key"
    NVIDIA_API_KEY = "您的_Nvidia_NIM_API_Key"
    OPENROUTER_API_KEY = "您的_OpenRouter_API_Key"
    
    # 2. Google OAuth 2.0 用戶端憑證設定
    GOOGLE_CLIENT_ID = "您的_Google_OAuth_Client_ID"
    GOOGLE_CLIENT_SECRET = "您的_Google_OAuth_Client_Secret"
    GOOGLE_REDIRECT_URI = "https://您的專案名稱.streamlit.app/"
    ```
    
    ### 🛡️ 如何取得 Google OAuth 憑證？
    1. 前往 **[Google Cloud Console](https://console.cloud.google.com/)**，點擊建立新專案。
    2. 前往 **API 和服務 -> OAuth 同意畫面**：選擇 **External (外部)**，填寫基本資料，並在 Scopes 中加入 `userinfo.profile`, `userinfo.email` 與 `drive.file`。並在測試使用者中加入您自己的 Google 信箱。
    3. 前往 **憑證 (Credentials) -> 建立憑證 -> OAuth 用戶端 ID**：
       - 應用程式類型：**網頁應用程式 (Web application)**
       - 在 **已授權的重新導向 URI** 中填入本地網址 `http://localhost:8501/`，部署至雲端後請加入您的 Streamlit 網頁網址（如 `https://ai-multi-bot-arena.streamlit.app/`）。
    4. 點選儲存後即可取得 **用戶端 ID (Client ID)** 與 **用戶端密鑰 (Client Secret)**！
    """)
