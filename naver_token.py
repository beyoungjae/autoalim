import os
import time
import bcrypt
import pybase64
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = ".naver_access_token"

def generate_signature(client_id, client_secret, timestamp):
    password = f"{client_id}_{timestamp}".encode("utf-8")
    salt = client_secret.encode("utf-8")
    hashed = bcrypt.hashpw(password, salt)
    return pybase64.standard_b64encode(hashed).decode("utf-8")

def fetch_naver_access_token():
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"

    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    account_id = os.getenv("NAVER_ACCOUNT_ID")
    token_type = os.getenv("NAVER_TYPE", "SELLER").upper()
    timestamp = str(int(time.time() * 1000))

    if not all([client_id, client_secret, account_id]):
        print("❌ NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 또는 NAVER_ACCOUNT_ID가 설정되지 않았습니다.")
        return None

    signature = generate_signature(client_id, client_secret, timestamp)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    data = {
        "client_id": client_id,
        "grant_type": "client_credentials",
        "timestamp": timestamp,
        "client_secret_sign": signature,
        "type": token_type,
        "account_id": account_id
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        if access_token:
            with open(TOKEN_FILE, "w") as f:
                f.write(access_token)
            print("✅ NAVER ACCESS TOKEN 발급 및 저장 완료")
            return access_token
        else:
            print("❌ 발급된 access_token이 없습니다.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ NAVER ACCESS TOKEN 발급 실패: {e}")
        if e.response is not None:
            print("📦 응답 본문:", e.response.text)
        return None

def get_naver_access_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    else:
        return fetch_naver_access_token()