# backend/demo_agent.py

class DemoAgent:
    def __init__(self):
        pass

    def call_and_order(self, restaurant_phone: str, menu: str):
        # AI가 읽어줄 대본
        script = f"안녕하세요. AI 배달 비서 단비입니다. {menu} 한 개 배달 주문 하려고 하는데요. 계좌 번호를 문자로 남겨주시면 입금하겠습니다. 감사합니다."
        
        print(f"🎙️ [Demo Agent] 통화 시뮬레이션 응답 생성 완료 (메뉴: {menu})")

        return {
            "status": "simulated",
            "message": "AI가 성공적으로 주문을 전달했습니다.",
            "script": script,  # 👈 프론트엔드로 대본을 쏴줍니다!
            "bank_account": "카카오뱅크 3333-12-3456789 (테스트 계좌)"
        }
