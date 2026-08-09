# Model providers

온라인 Provider와 로컬 llama.cpp Provider는 같은 요청·응답 형식을 구현해야 합니다.

- `online`: Windows Credential Manager에서 사용자 키를 읽어 API 호출
- `local`: `local-models/`의 검증된 Qwen3-8B GGUF를 로컬 런타임으로 호출

