# PoB Agent

PoB의 계산 결과를 근거로 답변하는 별도 Agent 런타임입니다.

## 실행 모드

- `online`: 사용자가 입력한 Provider API 키로 모델 호출
- `local`: 사용자가 다운로드한 Qwen3-8B 4-bit 모델 호출

두 모드는 동일한 `ModelRequest` 계약을 사용합니다. 숫자와 빌드 상태는 항상 PoB Tool 결과를 권위 있는 근거로 사용합니다.

## 하위 디렉터리

- `app/`: 질문 라우팅과 Agent 실행 흐름
- `config/`: Provider 설정 예시
- `knowledge/`: RAG 원문과 검색 인덱스
- `models/`: 모델 매니페스트와 다운로드 관리자
- `providers/`: 온라인·로컬 모델 어댑터
- `prompts/`: 시스템 프롬프트와 답변 형식
- `protocol/`: PoB-Agent JSON 계약
- `security/`: Windows Credential Manager 연동
- `tools/`: PoB 계산 Tool 계약과 구현

