import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ALIGO_API_KEY = os.getenv("ALIGO_API_KEY")
ALIGO_USER_ID = os.getenv("ALIGO_USER_ID")
ALIGO_SENDER_KEY = os.getenv("ALIGO_SENDER_KEY")
ALIGO_TEMPLATE_CODE = "TZ_9681"  # 예: "TN_7303"
ALIGO_SENDER = "15663321"  # 예: "01012345678"

receiver = "01093600385"  # 수신자 번호

message = "[한경희홈케어] \n접수안내\n\n서비스 신청해 주셔서 감사드립니다.\n접수 완료 되었습니다.\n\n케어 마스터 담당자가 순차적으로 영업일 기준 4일 이내 해피콜하여 방문 일정 안내 예정이니 안심하고 기다려주세요.  \n\n고객 만족을 최우선으로 하는 한경희홈케어는 최고의 서비스 제공을 위해 더욱 노력할 것을 약속드리겠습니다. \n\n감사합니다.\n\n\n■한경희홈케어 문의하기\n▷1:1 채팅상담\nhttp://pf.kakao.com/_JRxoxfxl/chat\n▷한경희홈케어 고객센터:1566-3321\n▷운영시간:평일 09:00~18:00(주말&공휴일제외)"

# 버튼 구성 (1개 - 봇키워드)
button_info = json.dumps({
    "button": [
        {
            "name": "채널 추가",
            "linkType": "AC",
            "linkTypeName": "채널 추가"
        },
        {
            "name": "1:1 문의하기",
            "linkType": "BK",
            "linkTypeName": "봇키워드"
        }
    ]
}, ensure_ascii=False)

# 요청 데이터 구성
payload = {
    "apikey": ALIGO_API_KEY,
    "userid": ALIGO_USER_ID,
    "senderkey": ALIGO_SENDER_KEY,
    "tpl_code": ALIGO_TEMPLATE_CODE,
    "sender": ALIGO_SENDER,
    "receiver_1": receiver,
    "subject_1": "접수완료",  # 제목은 수신자에겐 보이지 않지만 필수
    "message_1": message,
    "button_1": button_info,
    "failover": "Y",
    "fsubject_1": "접수완료",
    "fmessage_1": "[한경희홈케어] \n접수안내\n\n서비스 신청해 주셔서 감사드립니다.\n접수 완료 되었습니다.\n\n케어 마스터 담당자가 순차적으로 영업일 기준 4일 이내 해피콜하여 방문 일정 안내 예정이니 안심하고 기다려주세요.  \n\n고객 만족을 최우선으로 하는 한경희홈케어는 최고의 서비스 제공을 위해 더욱 노력할 것을 약속드리겠습니다. \n\n감사합니다.\n\n\n■한경희홈케어 문의하기\n▷1:1 채팅상담\nhttp://pf.kakao.com/_JRxoxfxl/chat\n▷한경희홈케어 고객센터:1566-3321\n▷운영시간:평일 09:00~18:00(주말&공휴일제외)\n\n＊서비스 받으실 제품 확인을 위해 주문 상품의 사진을 요청할 수 있습니다.\n＊주차공간 확보는 필수이며 유료 주차장 이용 시 고객님께서 부담해주셔야 합니다.\n＊시즌형 서비스 상품의 경우 주문량이 많아 해피콜 및 일정 지연될 수 있습니다. \n＊장소  협소, 기기 노후, 분해 시 하자 발생 위험이 높은 경우 등으로 서비스가 제한될 수 있습니다."

}

# 요청
url = "https://kakaoapi.aligo.in/akv10/alimtalk/send/"
response = requests.post(url, data=payload)

# 결과 출력
print("✅ 응답 코드:", response.status_code)
try:
    print("📦 응답 내용:", response.json())
except Exception:
    print("📦 응답 본문 (text):", response.text)
