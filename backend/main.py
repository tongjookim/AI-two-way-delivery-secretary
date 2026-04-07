# backend/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
from map_service import MapService
from ai_agent import ai_agent
#from demo_agent import DemoAgent
from fastapi.middleware.cors import CORSMiddleware
import random
import uvicorn
import asyncio

app = FastAPI()

# 주문진 릴레이와 연결된 소켓을 저장 (나중에 명령을 내리기 위함)
connected_relay = None

# CORS 설정 유지
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_queue = asyncio.Queue()

map_svc = MapService()

# --- 데이터 모델 정의 ---
class RestaurantInfo(BaseModel):
    id: str
    name: str
    phone: str
    address: str
    rating: float
    distance: Optional[str] = None

class SearchResponse(BaseModel):
    menu: str
    recommendations: List[RestaurantInfo]

class OrderFinalizeRequest(BaseModel):
    restaurant_id: str
    menu: str

def extract_menu_from_text(text: str) -> str:
    """
    사용자의 애매한 질문을 구체적인 메뉴 키워드로 변환하는 '눈치 탑재' 함수
    """
    # 1. 거슬리는 이모지를 먼저 싹 지워줍니다.
    clean_text = text.replace("😋", "").replace("🍖", "").replace("🆓", "").replace("🔥", "").strip()
    
    # 2. 칩(Quick Reply) 의도 매칭: 추상적인 질문을 카카오맵이 아는 메뉴로 변환!
    if "오늘 뭐 먹지" in clean_text:
        # 결정장애를 위해 여러 메뉴 중 하나를 랜덤으로 골라줍니다.
        return random.choice(["치킨", "피자", "짜장면", "돈까스", "초밥"])
        
    elif "배달비 무료" in clean_text:
        # 카카오맵 자체에는 배달비 필터가 없으므로, 배달이 활발한 인기 카테고리로 우회합니다.
        return random.choice(["국밥", "분식", "패스트푸드", "카페"]) 
        
    elif "매운" in clean_text:
        # 매운 음식 리스트 중 하나를 랜덤으로 고릅니다.
        return random.choice(["마라탕", "떡볶이", "짬뽕", "낙지볶음"])
        
    # 3. 일반 검색어 정제 (위의 조건에 안 맞으면 원래대로 불필요한 단어 제거)
    words_to_remove = ["맛집", "추천해줘", "근처", "있는", "곳", "어디", "?", "먹고싶어", "땡겨", "인"]
    result = clean_text
    for word in words_to_remove:
        result = result.replace(word, "")
        
    result = result.strip()
    
    # 만약 키워드가 다 지워져서 비어버렸다면 에러 방지용으로 "맛집" 검색
    return result if result else "맛집"

class ChatRequest(BaseModel):
    user_input: str
    lat: Optional[float] = None
    lng: Optional[float] = None

# --- 엔드포인트 ---

# 1. 사용자가 메뉴를 말했을 때 맛집 추천 (무엇을 -> 어디서 단계)
@app.post("/search-restaurants", response_model=SearchResponse)
async def search_and_recommend(request: ChatRequest):
    
    # [수정 1] 기존의 단순 replace 로직은 지우고, 새로 만든 함수를 사용합니다.
    # 괄호 안의 이름도 'req'가 아니라 'request'로 맞춰줍니다!
    keyword = extract_menu_from_text(request.user_input)
    
    # [수정 2] 여기서도 req.lat이 아니라 request.lat으로 맞춰줍니다.
    # 지도 API에서 추천 맛집 가져오기
    recommendations = map_svc.search_top_restaurants(keyword, request.lat, request.lng)
    
    return {
        "menu": keyword,
        "recommendations": recommendations
    }

# ======================================================
# [신규 추가] 전화 서버 연동
# ======================================================
@app.websocket("/ws/audio/")
async def websocket_endpoint(websocket: WebSocket):
    global connected_relay
    await websocket.accept()
    
    connected_relay = websocket  # 노트북 세션 저장
    print("📡 [서울] 주문진 전초기지 연결 성공!")

    try:
        while True:
            # 노트북으로부터 데이터 수신 대기
            data = await websocket.receive()
            
            # 1. 마이크 소리(Binary) 데이터 처리
            if "bytes" in data:
                # 노트북에서 보낸 음성 조각을 큐에 차곡차곡 쌓습니다.
                # ai_agent.py의 listen_and_transcribe 함수가 여기서 꺼내갑니다.
                await audio_queue.put(data["bytes"])
                
                # [디버그] 데이터가 너무 많이 쌓이는 것을 방지하기 위해 
                # 큐 크기가 너무 커지면 오래된 데이터는 버리는 로직을 넣을 수도 있습니다.
                if audio_queue.qsize() > 100: 
                    try:
                        audio_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass

            # 2. 제어 메시지(Text) 데이터 처리
            elif "text" in data:
                print(f"💬 주문진 메시지: {data['text']}")

    except WebSocketDisconnect:
        print("❌ [서울] 주문진 전초기지가 연결을 종료했습니다.")
        
    except Exception as e:
        print(f"⚠️ 웹소켓 예외 발생: {e}")

    finally:
        # 3. 자원 정리
        connected_relay = None
        
        # 연결 종료 시 큐에 남은 쓸모없는 오디오 데이터 비우기
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
        print("🧹 연결 자원 정리 및 오디오 큐 초기화 완료.")

        
# =============================================================
# 2. [실제 서비스용] 사용자가 식당을 선택했을 때 최종 주문 (어디서 -> AI 전화 단계)
# =============================================================
@app.post("/place-order")
async def finalize_order(request: OrderFinalizeRequest):
    # 1. 전역 변수(노트북 연결 세션)를 가져옵니다.
    global connected_relay
    
    # 2. 선택된 식당 상세 정보 가져오기
    restaurant = map_svc.get_restaurant_by_id(request.restaurant_id)
    
    # 3. AI가 전초기지(노트북)를 통해 전화 걸기
    # [수정 사항] 
    # - await 추가 (비동기 처리)
    # - restaurant['phone']은 현재 테스트용 하드코딩 중이라 무시되지만, 
    #   AIAgent의 새 구조에 맞춰 request.menu와 connected_relay를 전달합니다.
    try:
        payment_info = await ai_agent.call_and_order(
            menu=request.menu, 
            connected_relay=connected_relay
        )
        
        # 만약 노트북 연결이 안 되어 있다면 에러 응답
        if payment_info.get("status") == "error":
            return {
                "status": "failed",
                "message": "주문진 전초기지(노트북)와 연결되어 있지 않습니다. 서버를 확인해 주세요."
            }

    except Exception as e:
        print(f"❌ 주문 중 치명적 에러: {e}")
        return {"status": "error", "message": str(e)}
    
    return {
        "status": "success",
        "restaurant_name": restaurant['name'],
        "payment_info": payment_info
    }

# ========================================================================
# 2. [시연용] 사용자가 식당을 선택했을 때 사장님과 통화
# =======================================================================
#@app.post("/place-order")
#async def finalize_order(request: OrderFinalizeRequest):
#    # 선택된 식당 상세 정보 가져오기
#    restaurant = map_svc.get_restaurant_by_id(request.restaurant_id)
#    
#    # 위에서 선언한 시연용 agent(= DemoAgent())를 호출하여 대본 확보
#    # (주의: 만약 객체 이름을 ai_agent로 선언하셨다면 ai_agent.call_and_order 로 맞춰주세요!)
#    payment_info = agent.call_and_order(restaurant['phone'], request.menu)
#    
#    return {
#        "status": "success",
#        "restaurant_name": restaurant['name'],
#        "payment_info": payment_info
#    }

# 서버 상태 확인용 루트 경로
@app.get("/")
async def root():
    return {"status": "AI Chatbot Backend is running!"}