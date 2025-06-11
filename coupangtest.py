import os
import time
import hmac
import hashlib
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
VENDOR_ID = os.getenv("COUPANG_VENDOR_ID")

def generate_signature(method, path, query=''):
    timestamp = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
    message = timestamp + method + path + query
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    authorization = f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={timestamp}, signature={signature}"
    return authorization, timestamp, message

def test_coupang_ordersheets_api():
    if not all([ACCESS_KEY, SECRET_KEY, VENDOR_ID]):
        print("❌ 환경변수 누락. .env 파일을 확인하세요.")
        return

    base_url = "https://api-gateway.coupang.com"
    path = f"/v2/providers/openapi/apis/api/v4/vendors/{VENDOR_ID}/ordersheets"
    method = "GET"
    query_params = {
        "createdAtFrom": (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d'),
        "createdAtTo": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        "status": "ACCEPT",
        "maxPerPage": "1"
    }
    query = urllib.parse.urlencode(query_params)
    authorization, timestamp, signature_message = generate_signature(method, path, query)

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8"
    }
    url = f"{base_url}{path}?{query}"

    print(f"\n--- 🧪 [쿠팡 API 테스트] ---")
    print(f"▶️ 요청 URL: {url}")
    print(f"▶️ 요청 Method: {method}")
    print(f"▶️ 요청 Timestamp: {timestamp}")
    print(f"▶️ 서명 원본: {signature_message}")
    print(f"▶️ 요청 Headers:\n{headers}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✅ 응답 코드: {response.status_code}")
        try:
            print("📦 응답 본문(JSON):")
            print(response.json())
        except:
            print("📦 응답 본문(Text):")
            print(response.text[:300])
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")

# 실행
if __name__ == "__main__":
    test_coupang_ordersheets_api()
