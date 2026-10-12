# Model providers

MVP는 외부 AI 서버 하나를 기본 Provider로 사용합니다. 사용자가 별도의 API 키를
입력하거나 모델을 다운로드하지 않아도, 앱이 관리하는 서버 연결을 통해 요청합니다.

- `remote`: 질문, 최신 빌드 변경분, Tool 결과를 외부 AI 서버와 주고받음
- Tool 실행: 외부 서버가 아니라 로컬 PoB Bridge에서만 수행
- `local`: 명시적인 development 설정에서만 사용하는 Ollama 개발 provider

`defaultMode`는 항상 `remote`로 유지합니다. `local.enabled=true`만으로는
활성화되지 않으며, `defaultMode=local`과 development 실행 환경이 모두
필요합니다. Ollama는 `http://127.0.0.1:11434/v1`의 OpenAI-compatible
계약과 `qwen3:8b`를 기본값으로 사용하며, 서비스가 없을 때 remote로
자동 전환하지 않습니다.

외부 서버와의 요청·응답은 구조화된 JSON 계약을 사용해야 합니다. 일반 텍스트에
포함된 Tool 지시를 실행하지 않습니다.

## 선택적 Langfuse 개발 추적

Langfuse exporter는 AgentLoop에 기본 연결되어 있으며 sample rate 기본값은 1입니다.
process environment가 우선되고 저장소 root `.env`의 설정이 보완적으로 읽힙니다.
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` 또는 SDK/서비스가
없으면 Langfuse 전송 대신 local queue 모드로 동작합니다.

전송되는 값은 이미 redacted된 Trace event와 stable reference뿐이며 API key, 원문 prompt,
XML, snapshot, notes, free-form 인자, 전체 Tool 결과는 전송하지 않습니다. 로컬 개발
Langfuse의 retention/deletion은 Langfuse 서버 설정과 UI/API에서 관리하며, Agent는
보존 정책을 변경하지 않습니다. exporter가 없거나 설정이 불완전하거나 flush/close가
실패해도 Agent 답변과 PoB 실행은 중단되지 않습니다.

Langfuse 기본 wiring은 AgentLoop에 연결되어 있으며 `LANGFUSE_BASE_URL`은 `localhost`,
`127.0.0.1`, `::1`만 허용됩니다. 전송 실패 시 redacted event만
`data/traces/langfuse-queue.ndjson`에 임시 보관하며 기본 디스크 상한은 10 MiB입니다.
동일 `run_id`는 한 번만 보관하고 상한 초과 시에는 경고 후 쓰지 않습니다.
