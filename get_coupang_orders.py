#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import hmac
import hashlib
import requests
import urllib.parse
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# .env 파일에서 환경변수 로드
load_dotenv()

# --- 환경변수 ---
COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
COUPANG_VENDOR_ID = os.getenv("COUPANG_VENDOR_ID")

# --- 쿠팡 API 인증 서명 생성 함수 ---
def generate_coupang_auth(method, path, query=""):
    """쿠팡 API 요청을 위한 인증 서명을 생성합니다."""
    timestamp = datetime.utcnow().strftime('%y%m%d') + 'T' + datetime.utcnow().strftime('%H%M%S') + 'Z'
    message = timestamp + method + path + query
    signature = hmac.new(
        COUPANG_SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    authorization = (
        f"CEA algorithm=HmacSHA256, access-key={COUPANG_ACCESS_KEY}, "
        f"signed-date={timestamp}, signature={signature}"
    )
    return authorization

# --- 상품준비중(배송준비중) 주문 목록 조회 함수 ---
def fetch_preparing_shipment_orders():
    """쿠팡 윙에서 '상품준비중' 상태인 주문 목록을 가져옵니다."""
    
    method = "GET"
    domain = "https://api-gateway.coupang.com"
    path = f"/v2/providers/openapi/apis/api/v4/vendors/{COUPANG_VENDOR_ID}/ordersheets"
    
    search_to = datetime.utcnow()
    search_from = search_to - timedelta(days=30)
    
    params = {
        "createdAtFrom": search_from.strftime('%Y-%m-%d'),
        "createdAtTo": search_to.strftime('%Y-%m-%d'),
        "status": "INSTRUCT",
        "maxPerPage": "50"
    }
    query = urllib.parse.urlencode(params)
    
    authorization = generate_coupang_auth(method, path, query)
    
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-By": COUPANG_VENDOR_ID
    }
    
    url = f"{domain}{path}?{query}"

    try:
        response = requests.request(method=method, url=url, headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        # ❗️❗️❗️ 여기가 결정적인 수정 부분입니다! "SUCCESS"가 아닌 숫자 200을 확인합니다. ❗️❗️❗️
        if response_data.get("code") != 200:
            print(f"❌ API에서 오류 응답을 받았습니다: {response_data.get('message')}")
            # 상세 디버깅을 위해 전체 응답 내용도 출력
            print(f"📄 전체 응답 내용: {response_data}")
            return []
            
        return response_data.get("data", [])

    except requests.exceptions.RequestException as e:
        print(f"❌ API 요청 중 오류가 발생했습니다: {e}")
        if e.response:
            print(f"    - 상태 코드: {e.response.status_code}")
            print(f"    - 응답 내용: {e.response.text}")
        return []

# --- 메인 실행 함수 ---
def main():
    print("🚀 쿠팡 '상품준비중' 주문 목록 조회를 시작합니다...")
    
    # 필수 환경변수 확인
    if not all([COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY, COUPANG_VENDOR_ID]):
        print("❌ .env 파일에 COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY, COUPANG_VENDOR_ID를 설정해주세요.")
        return
        
    orders = fetch_preparing_shipment_orders()
    
    if not orders:
        print("✅ 조회된 '상품준비중' 상태의 주문이 없습니다.")
        return
        
    print(f"\n✨ 총 {len(orders)}건의 '상품준비중' 주문을 찾았습니다.\n")
    
    # 각 주문의 상세 정보 출력
    for i, order in enumerate(orders, 1):
        print(f"--- {i}번째 주문 (주문번호: {order.get('orderId')}) ---")
        print(json.dumps(order, indent=2, ensure_ascii=False)) # 이 부분만 남김
        print("-" * 20 + "\n")

if __name__ == "__main__":
    main()