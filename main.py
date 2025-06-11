#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import time
import bcrypt
import pybase64
import hmac
import hashlib
import requests
import urllib.parse
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path
import sys
import io


load_dotenv()

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# ──────────────────────────────────────────────────────────
# 1) 환경변수
NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_ACCOUNT_ID    = os.getenv("NAVER_ACCOUNT_ID")
NAVER_TYPE          = os.getenv("NAVER_TYPE", "SELLER").upper()

COUPANG_ACCESS_KEY  = os.getenv("COUPANG_ACCESS_KEY")
COUPANG_SECRET_KEY  = os.getenv("COUPANG_SECRET_KEY")
COUPANG_VENDOR_ID   = os.getenv("COUPANG_VENDOR_ID")

ALIGO_API_KEY       = os.getenv("ALIGO_API_KEY")
ALIGO_USER_ID       = os.getenv("ALIGO_USER_ID")
ALIGO_SENDER_KEY    = os.getenv("ALIGO_SENDER_KEY")
ALIGO_TEMPLATE_CODE = os.getenv("ALIGO_TEMPLATE_CODE")
ALIGO_SENDER        = os.getenv("ALIGO_SENDER_PHONE")

SENT_RECORD_FILE    = Path("sent_records.json")

# ──────────────────────────────────────────────────────────
# 2) 제외할 지역 키워드 목록
EXCLUDE_REGIONS = [
    "강원도", "강원특별자치도",
    "전북", "전북특별자치도",
    "충남 보령시", "충청남도 보령시",
    "충남 논산시", "충청남도 논산시",
    "충북 보은군", "충청북도 보은군",
    "충북 음성군", "충청북도 음성군",
    "충북 진천군", "충청북도 진천군",
    "경기도 이천시", "경기 이천시",
    "전남 목포시", "전라남도 목포시",
    "전남 무안군", "전라남도 무안군",
    "제주도", "제주"
]

# ──────────────────────────────────────────────────────────


def load_sent_records():
    if SENT_RECORD_FILE.exists():
        return json.loads(SENT_RECORD_FILE.read_text(encoding="utf-8"))
    return {"naver": [], "coupang": []}


def save_sent_records(records):
    SENT_RECORD_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


# ──────────────────────────────────────────────────────────
# 네이버 토큰 발급/갱신 (OAuth2 Client‐Credentials + bcrypt signature)
def generate_naver_signature(client_id, client_secret, timestamp):
    pw = f"{client_id}_{timestamp}".encode("utf-8")
    salt = client_secret.encode("utf-8")
    hashed = bcrypt.hashpw(pw, salt)
    return pybase64.standard_b64encode(hashed).decode("utf-8")


def fetch_naver_access_token():
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    timestamp = str(int(time.time() * 1000))
    sig = generate_naver_signature(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, timestamp)
    data = {
        "client_id": NAVER_CLIENT_ID,
        "grant_type": "client_credentials",
        "timestamp": timestamp,
        "client_secret_sign": sig,
        "type": NAVER_TYPE,
        "account_id": NAVER_ACCOUNT_ID
    }
    r = requests.post(url, data=data, headers={"Accept":"application/json"})
    r.raise_for_status()
    return r.json()["access_token"]


def get_naver_access_token():
    # 간단히 매번 새로 발급하도록 구현 (3시간 유효, 성능 여유 있을 때)
    return fetch_naver_access_token()


def fetch_naver_orders():
    token = get_naver_access_token()
    now = datetime.now(timezone(timedelta(hours=9)))
    frm = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+09:00"
    to  =  now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+09:00"

    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders"
    params = {
        "from": frm, "to": to,
        "rangeType": "PAYED_DATETIME",
        "productOrderStatuses": "PAYED",
        "placeOrderStatusType": "OK",
        "page": 1, "pageSize": 100
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", {}).get("contents", [])

    results = []
    for item in data:
        order = item["content"]["order"]
        product_order = item["content"]["productOrder"]
        region = product_order.get("shippingAddress", {}).get("baseAddress", "")
        if any(ex in region for ex in EXCLUDE_REGIONS):
            continue
        phone = order.get("ordererTel")
        if phone:
            results.append((order["orderId"], phone))
    return results


# ──────────────────────────────────────────────────────────
# 쿠팡 서명 생성 (CEA HmacSHA256)
def generate_coupang_auth(method, path, query=""):
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
    return authorization, timestamp, message


def fetch_coupang_orders():
    base_url = "https://api-gateway.coupang.com"
    path     = f"/v2/providers/openapi/apis/api/v4/vendors/{COUPANG_VENDOR_ID}/ordersheets"
    method   = "GET"
    frm = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    to  =  datetime.utcnow().strftime('%Y-%m-%d')
    params = {
        "createdAtFrom": frm,
        "createdAtTo":   to,
        "status":        "INSTRUCT",
        "maxPerPage":    "50"
    }

    query      = urllib.parse.urlencode(params)
    auth, ts, _ = generate_coupang_auth(method, path, query)

    headers = {
        "Authorization": auth,
        "Content-Type":  "application/json",
        "X-Requested-By": COUPANG_VENDOR_ID,
    }

    try:
        resp = requests.get(f"{base_url}{path}", headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        arr = resp.json().get("data", [])
    except requests.HTTPError as e:
        print("❌ 쿠팡 주문 조회 오류:", e, resp.text)
        return []

    results = []
    for item in arr:
        receiver = item.get("receiver", {})
        region = receiver.get("addr1", "")
        if any(ex in region for ex in EXCLUDE_REGIONS):
            continue
        phone = receiver.get("safeNumber") or receiver.get("receiverNumber")
        if phone:
            results.append((str(item["orderId"]), phone))
    return results


# ──────────────────────────────────────────────────────────
# 알리고 알림톡 발송
def send_alimtalk(phone, payload_template):
    url = "https://kakaoapi.aligo.in/akv10/alimtalk/send/"
    data = {
        "apikey": ALIGO_API_KEY,
        "userid": ALIGO_USER_ID,
        "senderkey": ALIGO_SENDER_KEY,
        "tpl_code": ALIGO_TEMPLATE_CODE,
        "sender": ALIGO_SENDER,
        "receiver_1": phone,
        "subject_1": "접수완료",
        "templateEmType": "BASIC",
        "failover": "Y",
        "fsubject_1": "접수완료",
        "fmessage_1": "[한경희홈케어] \n접수안내\n\n서비스 신청해 주셔서 감사드립니다.\n접수 완료 되었습니다.\n\n케어 마스터 담당자가 순차적으로 영업일 기준 4일 이내 해피콜하여 방문 일정 안내 예정이니 안심하고 기다려주세요.  \n\n고객 만족을 최우선으로 하는 한경희홈케어는 최고의 서비스 제공을 위해 더욱 노력할 것을 약속드리겠습니다. \n\n감사합니다.\n\n\n■한경희홈케어 문의하기\n▷1:1 채팅상담\nhttp://pf.kakao.com/_JRxoxfxl/chat\n▷한경희홈케어 고객센터:1566-3321\n▷운영시간:평일 09:00~18:00(주말&공휴일제외)\n\n＊서비스 받으실 제품 확인을 위해 주문 상품의 사진을 요청할 수 있습니다.\n＊주차공간 확보는 필수이며 유료 주차장 이용 시 고객님께서 부담해주셔야 합니다.\n＊시즌형 서비스 상품의 경우 주문량이 많아 해피콜 및 일정 지연될 수 있습니다. \n＊장소  협소, 기기 노후, 분해 시 하자 발생 위험이 높은 경우 등으로 서비스가 제한될 수 있습니다."
    }
    data.update(payload_template)
    r = requests.post(url, data=data, timeout=10)
    return r.json() if r.status_code == 200 else {"code":r.status_code, "message":r.text}


# ──────────────────────────────────────────────────────────
def main():
    sent = load_sent_records()

    # 1) 네이버 신규 결제 완료 주문
    try:
        for order_id, phone in fetch_naver_orders():
            if order_id not in sent["naver"]:
                res = send_alimtalk(phone, {
                    "subject_1": "접수 완료 안내",
                    "message_1": os.getenv("ALIGO_MESSAGE"),   # .env로 본문 관리
                    "button_1": os.getenv("ALIGO_BUTTON_JSON"),
                    "testMode": os.getenv("ALIGO_TEST_MODE")
                })
                print("NAVER→", order_id, phone, res)
                if res.get("code") == 0:
                    sent["naver"].append(order_id)
    except Exception as e:
        print("❌ 네이버 처리 실패:", e)

    # 2) 쿠팡 신규 결제 완료 주문
    try:
        for order_id, phone in fetch_coupang_orders():
            if order_id not in sent["coupang"]:
                res = send_alimtalk(phone, {
                    "subject_1": "접수 완료 안내",
                    "message_1": os.getenv("ALIGO_MESSAGE"),
                    "button_1": os.getenv("ALIGO_BUTTON_JSON"),
                    "testMode": os.getenv("ALIGO_TEST_MODE")
                })
                print("COUPANG→", order_id, phone, res)
                if res.get("code") == 0:
                    sent["coupang"].append(order_id)
    except Exception as e:
        print("❌ 쿠팡 처리 실패:", e)

    # 3) 저장된 발송 기록 업데이트
    save_sent_records(sent)


if __name__ == "__main__":
    main()
