#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import time
import bcrypt
import pybase64
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import sys
import io

# .env 파일 및 출력 설정
load_dotenv()
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# --- 환경변수 ---
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_ACCOUNT_ID = os.getenv("NAVER_ACCOUNT_ID")
NAVER_TYPE = os.getenv("NAVER_TYPE", "SELLER").upper()

# --- 네이버 API 인증 함수 (수정 없음) ---
def generate_naver_signature(client_id, client_secret, timestamp):
    pw = f"{client_id}_{timestamp}".encode("utf-8")
    salt = client_secret.encode("utf-8")
    hashed = bcrypt.hashpw(pw, salt)
    return pybase64.standard_b64encode(hashed).decode("utf-8")

def fetch_naver_access_token():
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    timestamp = str(int(time.time() * 1000))
    signature = generate_naver_signature(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, timestamp)
    data = {"client_id": NAVER_CLIENT_ID, "grant_type": "client_credentials", "timestamp": timestamp, "client_secret_sign": signature, "type": NAVER_TYPE, "account_id": NAVER_ACCOUNT_ID}
    try:
        r = requests.post(url, data=data, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ 네이버 토큰 발급 실패: {e.response.text if e.response else e}")
        return None

# --- 네이버 '발주확인' 주문 목록 조회 (최종) ---
def fetch_naver_confirmed_orders():
    """지난 24시간 내의 '발주확인' 주문 전체 정보를 가져옵니다."""
    token = fetch_naver_access_token()
    if not token:
        return []

    # ❗️❗️❗️ 최종 수정: API의 '최대 24시간 조회' 규칙을 준수 ❗️❗️❗️
    now = datetime.now(timezone(timedelta(hours=9)))
    # 조회 기간을 24시간(1일)으로 설정
    frm = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+09:00"
    to  = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+09:00"

    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders"
    
    # 동작이 확인된 구형(legacy) 파라미터 조합을 사용
    params = {
        "from": frm, 
        "to": to,
        "rangeType": "PAYED_DATETIME",
        "productOrderStatuses": "PAYED", # 단순 문자열
        "placeOrderStatusType": "OK",
        "page": 1, 
        "pageSize": 100
    }
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        # 구형 응답 구조에 맞춰 'contents' 키에서 데이터를 추출
        return response.json().get("data", {}).get("contents", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ 네이버 주문 조회 실패: {e}")
        if e.response:
            print(f"    - 응답 내용: {e.response.text}")
        return []

# --- 메인 실행 함수 ---
def main():
    print("🚀 네이버 '발주확인' 주문 목록 조회를 시작합니다...")
    
    if not all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_ACCOUNT_ID]):
        print("❌ .env 파일에 네이버 관련 정보를 설정해주세요.")
        return

    order_items = fetch_naver_confirmed_orders()

    if not order_items:
        print("✅ 지난 24시간 내 '발주확인' 상태인 주문이 없습니다.")
        return
        
    print(f"\n✨ 총 {len(order_items)}건의 '발주확인' 주문을 찾았습니다.\n")
    
    for i, item in enumerate(order_items, 1):
        # 응답 구조에 따라 'content' 안에 실제 정보가 들어있습니다.
        order_content = item.get('content', {})
        product_order_id = order_content.get('productOrder', {}).get('productOrderId', 'N/A')

        print(f"--- {i}번째 주문 (상품주문번호: {product_order_id}) ---")
        print(json.dumps(order_content, indent=2, ensure_ascii=False))
        print("-" * 50 + "\n")

if __name__ == "__main__":
    main()