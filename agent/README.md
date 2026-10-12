# PoB Agent

PoB에 추가되는 Agent 기능입니다. MVP에서는 모델을 사용자 컴퓨터에 설치하지 않고,
외부 AI 서버에 질문을 전달합니다. PoB의 현재 상태를 읽고 계산·변경하는 작업은
항상 로컬 PoB Bridge가 담당합니다.

## MVP 실행 흐름

1. 사용자가 PoB의 AI 창에 질문을 입력합니다.
2. 로컬 Bridge가 현재 Skill Set, Main Skill, Config와 빌드 변경분을 수집합니다.
3. 질문과 필요한 상태 요약을 외부 AI 서버에 전달합니다.
4. AI 서버가 구조화된 Tool 호출 계획을 반환합니다.
5. 로컬 Bridge가 호출을 검증하고 PoB에서 실행합니다.
6. 계산 결과와 Evidence Graph를 AI 서버에 전달합니다.
7. AI 서버가 한국어 최종 답변을 반환합니다.

사용자 API 키와 로컬 모델 다운로드는 MVP에 포함하지 않습니다. 로컬 모델 Provider는
향후 선택 기능으로만 남겨 둡니다. 현재 빌드의 수치와 변경 결과는 항상 PoB Tool 결과를
권위 있는 근거로 사용합니다.

## 하위 디렉터리

- `app/`: 질문 라우팅과 Agent 실행 흐름
- `config/`: 외부 AI 서버 연결 설정 예시
- `knowledge/`: RAG 원문과 검색 인덱스
- `models/`: 향후 로컬 모델 확장을 위한 매니페스트
- `providers/`: 외부 AI 서버 프로토콜과 향후 로컬 Provider 어댑터
- `prompts/`: 시스템 프롬프트와 답변 형식
- `protocol/`: PoB-Agent JSON 계약
- `security/`: 외부 전송 범위와 Bridge 호출 보안 규칙
- `tools/`: PoB 계산 Tool 계약과 구현

## MCP tool runtime

The production backend runs as an HTTP container and connects to the separate MCP container over authenticated Streamable HTTP. Local development can continue to use stdio. `agent/tool_catalog.py` is the single executable contract for tool names, semantic categories, input schemas, model-facing descriptions, provider groups, side effects, idempotency, deadlines, retry policy, and registered failure codes. AgentLoop's allowlist and MCP definitions derive from it. Regenerate its documentation with `python tools/render_mcp_tool_catalog.py`; `python tools/lint_agent_catalog.py` checks generated docs and Lua capability parity. Add a handler to the record's provider group; Lua-backed tools also require a PoB Lua capability/handler entry.

The MCP server exposes all 32 registered tool contracts. The three mutation calls return `MUTATION_NOT_PERSISTENT`; production execution never falls back to the headless XML adapter.
