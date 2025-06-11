import os
import requests
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from naver_token import fetch_naver_access_token

load_dotenv()

def test_naver_with_bearer():
    print("\\n--- 🧪 [네이버 커머스 API 테스트 - Bearer 인증 방식] ---")

    access_token = fetch_naver_access_token()
    if not access_token:
        print("❌ 토큰 발급 실패로 인해 테스트 중단")
        return

    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders"

    now_kst = datetime.now(timezone(timedelta(hours=9)))
    from_time = (now_kst - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+09:00"
    to_time = now_kst.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+09:00"

    params = {
        "from": from_time,
        "to": to_time,
        "rangeType": "PAYED_DATETIME",
        "productOrderStatuses": "PAYED",
        "page": 1,
        "pageSize": 5
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"  ▶️ 요청 URL: {url}")
        print(f"  ▶️ 요청 Params: {json.dumps(params, indent=2, ensure_ascii=False)}")
        print(f"  ▶️ 요청 헤더: {json.dumps(headers, indent=2)}")
        print(f"  ✅ 응답 코드: {response.status_code}")
        print(f"  ▶️ 응답 본문: {response.text[:500]}")
    except Exception as e:
        print(f"❌ 요청 실패: {e}")

if __name__ == "__main__":
    test_naver_with_bearer()