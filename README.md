# 📞 AI 배달 주문 에이전트 "단비" (Core Engine)

이 프로젝트는 배달 주문을 대행하는 **AI 대화 에이전트의 핵심 백엔드**입니다. 
WebSocket을 통해 원격지의 오디오 장치와 연결되어 실시간 음성 인식(STT) 및 합성(TTS)을 수행합니다.

## ✨ Key Features
- **Adaptive Dialogue**: 사장님의 응답(주문 수락, 거절, 계좌 안내 등)을 Vosk STT로 인식하여 유기적으로 대응.
- **Entity Extraction**: 통화 중 언급되는 계좌번호(숫자)를 정규표현식과 매핑 로직을 통해 실시간 추출.
- **State Machine**: 인사 → 주문 → 계좌 요청 → 확인으로 이어지는 대화 상태 관리.

## ⚙️ Tech Stack
- **Framework**: FastAPI (Asynchronous Server)
- **STT**: Vosk (Offline Korean Model)
- **TTS**: gTTS (Google Text-to-Speech)
- **Audio Processing**: Pydub

## ⚠️ Note
본 리포지토리는 **AI 백엔드 로직**만을 포함하고 있습니다. 실제 전화 발신 및 오디오 입출력을 위해서는 별도의 리플레이(Relay) 클라이언트가 필요합니다.
