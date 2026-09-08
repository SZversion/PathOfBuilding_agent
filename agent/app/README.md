# Agent application layer

질문 분류, 로컬 PoB Bridge와의 상태 동기화, PoB Tool 호출 순서, 로컬 RAG 검색,
외부 AI 서버와의 대화 흐름을 담당합니다.

외부 AI 서버는 자연어 해석과 Tool 호출 계획·최종 답변을 담당하고, 실제 PoB 상태
접근·계산·변경은 로컬 Bridge에서만 수행합니다. 한 요청의 Tool 호출은 최대 8회이며,
현재 상태와 이전 상태의 차이만 우선 전달하고 diff가 불확실하면 전체 최신 상태로
재동기화합니다.
