import json
import requests
import urllib.parse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import io
import streamlit as st

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive.file"
]

def get_oauth_flow(client_id, client_secret, redirect_uri):
    """建立並回傳 Google OAuth Flow 物件"""
    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": "ai-multi-bot-arena",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES
    )
    flow.redirect_uri = redirect_uri
    return flow

def get_login_url(client_id, client_secret, redirect_uri):
    """產生 Google OAuth 登入連結與 state 識別碼"""
    try:
        flow = get_oauth_flow(client_id, client_secret, redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # 強制再次同意以取得 Refresh Token
        )
        return auth_url, state
    except Exception as e:
        st.error(f"產生登入網址失敗: {str(e)}")
        return None, None

def credentials_to_dict(credentials):
    """將 Credentials 物件轉為字典形式以便儲存"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def dict_to_credentials(cred_dict):
    """將字典還原為 Credentials 物件，並在過期時自動 Refresh"""
    creds = Credentials(
        token=cred_dict['token'],
        refresh_token=cred_dict.get('refresh_token'),
        token_uri=cred_dict['token_uri'],
        client_id=cred_dict['client_id'],
        client_secret=cred_dict['client_secret'],
        scopes=cred_dict['scopes']
    )
    # 若 Access Token 已過期，嘗試自動刷新
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            st.error(f"更新 Google Token 失敗，可能需要重新登入: {str(e)}")
    return creds

def get_user_info(credentials):
    """獲取已登入使用者的名稱、Email 與頭像圖片網址"""
    try:
        # 使用 requests 直接呼叫 Userinfo API，最為輕量快速
        response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"獲取使用者資訊失敗: {str(e)}")
    return None

def save_data_to_drive(credentials, filename, json_data):
    """將 JSON 資料儲存至使用者的 Google Drive (覆寫或新建)"""
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        # 1. 搜尋雲端硬碟中是否已存在同名且未刪除的檔案
        results = service.files().list(
            q=f"name = '{filename}' and trashed = false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        
        # 準備上傳的二進位資料串流
        json_bytes = json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
        media = MediaIoBaseUpload(
            io.BytesIO(json_bytes),
            mimetype='application/json',
            resumable=True
        )
        
        if files:
            # 2. 檔案已存在：直接更新/覆寫內容
            file_id = files[0]['id']
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            return True, f"已成功更新雲端備份！(ID: {file_id})"
        else:
            # 3. 檔案不存在：建立新檔案
            file_metadata = {
                'name': filename,
                'mimeType': 'application/json'
            }
            new_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            return True, f"已成功在雲端硬碟建立備份！(ID: {new_file.get('id')})"
            
    except Exception as e:
        return False, f"儲存到 Google Drive 失敗: {str(e)}"

def load_data_from_drive(credentials, filename):
    """自使用者的 Google Drive 下載並解析 JSON 檔案"""
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        # 1. 搜尋檔案
        results = service.files().list(
            q=f"name = '{filename}' and trashed = false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        
        if not files:
            return None, "雲端硬碟中找不到備份檔案。"
            
        # 2. 下載並讀取內容 (使用 get_media().execute() 直接獲取 bytes)
        file_id = files[0]['id']
        content_bytes = service.files().get_media(fileId=file_id).execute()
        json_data = json.loads(content_bytes.decode('utf-8'))
        return json_data, None
        
    except Exception as e:
        return None, f"自 Google Drive 下載失敗: {str(e)}"
