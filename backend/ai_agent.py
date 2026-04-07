import asyncio
import io
import json
import re
import os
from gtts import gTTS
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer

class AIAgent:
    def __init__(self):
        self.test_target_number = "01026678073"
        # 📂 모델 경로 설정
        model_path = "/home/web-project/delivery_ai_proto/backend/lib/model"
        
        if not os.path.exists(model_path):
            print(f"❌ [Vosk] 모델 폴더를 찾을 수 없습니다: {model_path}")
            self.stt_model = None
        else:
            self.stt_model = Model(model_path)
            print(f"✅ [Vosk] 모델 로드 완료")

        # 한국어 숫자 변환용 딕셔너리
        self.num_map = {
            "영": "0", "공": "0", "일": "1", "하나": "1", "이": "2", "둘": "2",
            "삼": "3", "셋": "3", "사": "4", "넷": "4", "오": "5", "육": "6",
            "칠": "7", "팔": "8", "구": "9"
        }

    def extract_account(self, text):
        """텍스트에서 숫자만 추출 (계좌번호 후보 찾기)"""
        for kor, num in self.num_map.items():
            text = text.replace(kor, num)
        # 숫자 외 문자 제거
        numbers = re.sub(r'[^0-9]', '', text)
        return numbers if len(numbers) >= 8 else None # 8자리 이상일 때만 계좌로 간주

    async def call_and_order(self, menu: str, connected_relay):
        if connected_relay is None: return {"status": "error", "message": "연결 없음"}

        # 대화 상태 관리 변수
        detected_account = None
        step = "GREETING" # GREETING -> ASK_ACCOUNT -> CONFIRM_ACCOUNT -> END
        
        try:
            # 1. 전화 발신
            await connected_relay.send_text(f"CALL:{self.test_target_number}")
            await asyncio.sleep(6) # 통화 연결 대기

            # 2. 유기적 대화 루프 (최대 6회 티키타카)
            for turn in range(6):
                # --- [Step A] AI가 상황에 맞는 대사 결정 ---
                if step == "GREETING":
                    script = f"안녕하세요. AI 배달 비서 단비입니다. {menu} 하나 주문 가능한가요?"
                elif step == "ASK_ACCOUNT":
                    script = "네 감사합니다. 주소는 문자로 보내드릴게요. 입금해드릴 계좌번호 하나 불러주시겠어요?"
                elif step == "CONFIRM_ACCOUNT":
                    script = f"말씀하신 계좌번호가 {detected_account} 맞으실까요?"
                elif step == "WRONG_ACCOUNT":
                    script = "아, 죄송합니다. 계좌번호를 다시 한 번만 천천히 말씀해 주시겠어요?"
                    step = "ASK_ACCOUNT"
                else:
                    break # 대화 종료

                # --- [Step B] AI가 말하기 ---
                await self.speak(script, connected_relay)

                # --- [Step C] 사장님 대답 듣기 (STT) ---
                boss_text = await self.listen_and_transcribe(timeout=7)
                print(f"👤 사장님 응답: {boss_text}")

                if not boss_text:
                    if turn > 4: break # 너무 대답이 없으면 종료
                    await self.speak("여보세요? 잘 안 들리는데 다시 말씀해 주시겠어요?", connected_relay)
                    continue

                # --- [Step D] 사장님 응답 분석 및 상태 전환 ---
                
                # 1. 거절 상황
                if any(word in boss_text for word in ["안돼", "마감", "안됩니다", "없어요"]):
                    await self.speak("아, 오늘 마감이군요. 알겠습니다. 다음에 주문할게요.", connected_relay)
                    return {"status": "failed", "reason": "식당 거절"}

                # 2. 계좌번호가 들리는 상황
                account_candidate = self.extract_account(boss_text)
                if account_candidate:
                    detected_account = account_candidate
                    step = "CONFIRM_ACCOUNT"
                    continue

                # 3. 긍정 상황 (주문 수락)
                if step == "GREETING" and any(word in boss_text for word in ["돼", "가능", "네", "어디"]):
                    step = "ASK_ACCOUNT"
                    continue

                # 4. 계좌번호 확인 완료
                if step == "CONFIRM_ACCOUNT":
                    if any(word in boss_text for word in ["맞아", "네", "그래", "응"]):
                        await self.speak(f"네 확인했습니다. {detected_account}로 바로 입금해 드릴게요. 감사합니다!", connected_relay)
                        step = "END"
                        break
                    elif any(word in boss_text for word in ["아니", "틀려", "다시"]):
                        step = "WRONG_ACCOUNT"
                        continue

                # 5. 문자로 보낸다고 할 때
                if any(word in boss_text for word in ["문자", "톡", "번호"]):
                    await self.speak("네, 알겠습니다. 이 번호로 문자 남겨주시면 바로 입금할게요. 감사합니다!", connected_relay)
                    detected_account = "문자 수신 예정"
                    break

            return {
                "status": "success",
                "bank_account": detected_account if detected_account else "미수신"
            }

        except Exception as e:
            print(f"❌ 에러: {e}")
            return {"status": "error", "message": str(e)}

    async def speak(self, text, connected_relay):
        print(f"🤖 AI: {text}")
        def generate_pcm():
            tts = gTTS(text=text, lang='ko')
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            audio = AudioSegment.from_file(mp3_fp, format="mp3")
            return audio.set_frame_rate(16000).set_channels(1).set_sample_width(2).raw_data

        pcm_data = await asyncio.to_thread(generate_pcm)
        await connected_relay.send_bytes(pcm_data)
        await asyncio.sleep(len(text) * 0.3 + 1.2)

    async def listen_and_transcribe(self, timeout=7):
        if not self.stt_model: return ""
        
        # main.py에서 정의한 audio_queue를 가져옵니다.
        from main import audio_queue 
        recognizer = KaldiRecognizer(self.stt_model, 16000)
        
        # 큐 비우기 (이전 잡음 제거)
        while not audio_queue.empty(): audio_queue.get_nowait()

        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # 큐에서 데이터 조각 가져오기
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                if recognizer.AcceptWaveform(chunk):
                    result = json.loads(recognizer.Result())
                    return result.get("text", "").replace(" ", "")
            except:
                continue
        
        final = json.loads(recognizer.FinalResult())
        return final.get("text", "").replace(" ", "")

ai_agent = AIAgent()