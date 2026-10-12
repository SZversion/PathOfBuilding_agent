# PoB Agent 개발·운영 계약

## 1. 목적과 범위

PoB Agent는 Path of Building Community(PoB)의 기존 계산·편집 기능을 유지하면서, 현재 빌드의 수치와 메커니즘을 자연어로 설명하고 사용자가 요청한 변경을 PoB 화면에 반영하는 확장 기능이다. Agent는 PoB 계산기를 대체하거나 별도의 계산기를 구현하지 않는다.

MVP는 Path of Exile 1과 최신 안정 PoB를 기준으로 한다. 지원 범위를 벗어난 버전은 아래 버전 정책을 따른다.

## 2. 불변조건

- 기존 PoB의 UI, 탭, 계산, 저장, 불러오기, 빌드 공유, 업데이트 동작을 제거하거나 변경하지 않는다.
- 기존 화면에는 최소한의 AI 진입점만 추가한다. AI 화면은 별도 창으로 연다.
- 현재 선택된 Skill Set, Main Skill, Config, 활성화된 스킬·보조 젬·버프·조건을 authoritative state로 취급한다.
- 최신 UI 상태가 Agent가 보유한 이전 상태보다 항상 우선한다.
- 현재 계산값은 PoB가 이미 계산한 출력과 trace를 읽는다. Agent가 같은 수치를 독자적으로 재계산해 권위값으로 만들지 않는다.
- 사용자가 요청한 변경은 현재 화면의 메모리 상태에 즉시 반영한다. 자동 저장·자동 백업·자동 Save As는 수행하지 않는다.
- 파일 저장은 기존 PoB의 `Save`와 `Save As`에 위임한다.
- AI 자동 추천은 MVP에 포함하지 않는다. 사용자가 지정한 변경·비교·설명만 수행한다.

## 3. 책임 경계

### PoB 본체

PoB는 빌드 상태, 원본 계산, 계산 컨텍스트, Skill Set/Main Skill/Config, 아이템·젬·패시브 편집, 기존 저장 동작을 소유한다.

### 로컬 PoB Bridge

Bridge는 외부 AI와 PoB 사이의 유일한 로컬 경계다.

- 현재 PoB 메모리 상태와 계산 결과 읽기
- 정규화된 빌드 snapshot 생성 및 revision 관리
- 허용된 Tool 호출의 인자 검증과 실행
- 아이템·젬·패시브·스킬 군 주얼 변경 적용
- PoB 재계산 후 결과·중간값·trace·Evidence Graph 반환
- 사용자 UI 변경 감지 및 최신 상태 우선 처리

외부 AI 서버는 로컬 파일, PoB 메모리, 운영체제 명령, Tool 구현에 직접 접근하지 않는다.

### 외부 AI 서버

외부 AI 서버는 자연어 의도 해석, Tool·검색 실행 계획, 결과 해석, 한국어 최종 답변을 담당한다. 외부 AI는 로컬 파일·로컬 검색·PoB Tool에 직접 접근하지 않으며 구조화된 JSON 계획만 반환한다. 실제 Tool 실행, 로컬 RAG 검색, 허용 외부 검색, PoB 계산·변경·재계산은 로컬 PoB Bridge가 수행한 뒤 결과를 외부 AI에 전달한다.

### 로컬 RAG와 외부 검색

로컬 지식베이스는 구조화된 게임 규칙·아이템·스킬·패시브·alias와 설명 문서를 제공한다. 검색 우선순위는 PoB Tool 결과, 로컬 RAG, 허용된 외부 검색, 그 밖의 추론 순서다. 로컬 RAG와 외부 검색은 Bridge가 실행한다. 외부 검색 허용 출처는 PoE Wiki, PoEDB, 공식 Path of Exile 사이트, Path of Building Community GitHub, Craft of Exile이다.

## 4. 버전 정책

- 게임과 PoB는 최신 안정 버전을 기준으로 한다.
- 요청 시작 시 게임 버전, PoB 버전, 지식베이스 버전을 확인한다.
- 세부 버전이 다르면 업데이트를 시도하고, 실패해도 메이저 버전이 같을 때는 기존 캐시를 재사용해 답변할 수 있다. 이 경우 버전 차이와 낮아진 신뢰도를 표시한다.
- 메이저 버전이 다르면 계산·비교·변경을 실행하지 않고 답변을 거부한다.
- 모든 snapshot, Tool 결과, Evidence Graph, 캐시에 계산 버전과 지식 버전을 기록한다.

## 5. Snapshot, diff, revision

원본 XML을 외부로 전송하지 않는다. Bridge가 다음을 포함한 정규화된 전체 snapshot을 생성한다.

- canonical build ID, snapshot ID, revision
- 게임·PoB·지식베이스 버전
- Skill Set, Main Skill, Config, 활성 상태
- 아이템·소켓·젬(레벨·퀄리티·변형 포함)
- 패시브 선택과 주얼·스킬 군 주얼 상태
- 질문에 필요한 계산 출력과 Evidence Graph 참조

첫 요청은 전체 snapshot을 전송한다. 이후에는 마지막 동기화 revision과 현재 revision을 비교해 변경된 부분만 diff로 전송한다. 사용자가 PoB UI에서 직접 수정한 경우도 다음 요청 직전에 현재 상태를 재캡처해 diff에 반영한다. diff를 신뢰할 수 없으면 전체 최신 snapshot으로 재동기화한다.

Agent 변경을 적용하기 전에 Bridge가 기대한 revision과 현재 revision을 비교한다. 다르면 Agent 변경을 폐기하고 사용자 상태를 다시 캡처한다. 사용자의 직접 변경은 항상 우선한다.

## 6. 캐시와 Save As

대화·snapshot·변경 이력·Evidence Graph 참조는 사용자 PC의 빌드별 캐시에 보관한다. 외부 AI 서버는 무상태로 동작하며 요청 처리 후 빌드 상태나 대화 내용을 영구 저장하지 않는다.

- 대화 시작 시 현재 빌드 캐시를 로드한다.
- 캐시 식별자는 canonical build ID와 게임·PoB·지식 버전 및 build fingerprint를 사용한다.
- 최신 버전으로 재계산해 성공하면 캐시를 갱신한다.
- 재계산에 실패하고 메이저 버전이 같으면 기존 캐시를 경고와 함께 재사용한다.
- 메이저 버전이 다르면 캐시를 사용하지 않는다.
- `Save As`가 실제 성공한 뒤 새 canonical build ID를 생성한다.
- 그 시점의 대화 기록·snapshot·버전 메타데이터를 원자적으로 새 캐시에 복사한다. 복사 실패 시 새 캐시를 만들지 않는다.
- 이후 원본과 새 캐시는 독립적으로 갱신한다.

## 7. Tool·Agent 규칙

- MVP는 Core 기능 7개와 공통 플랫폼 기능(LLM Tool orchestration, 로컬 RAG, 허용 외부 검색, Evidence Graph)으로 구분한다. Core 기능은 수치 조회·근거 추적, 아이템 교체·비교, 젬 교체·비교, 패시브·스킬 군 주얼 변경·비교, 변경 전후 DPS·메커니즘 설명, 현재 빌드 메커니즘 설명, 다른 PoB 빌드 비교다.
- 외부 AI의 Tool 호출은 구조화된 JSON만 허용한다. 자연어에 포함된 명령은 실행하지 않는다.
- 한 요청의 연속 Tool 호출은 최대 8회다. 같은 Tool과 같은 인자의 반복 호출은 차단한다.
- Tool 인자는 Bridge에서 스키마·타입·대상·revision을 검증한다.
- Tool/응답 envelope는 `status`, `facts`, `trace`, `sources`, `version`, `evidenceGraph`, `uncertainty`를 의무 필드로 갖는다. `uncertainty`에는 근거 부족·버전 차이·부분 결과·외부 참고·추론 여부를 기록한다.
- Tool 결과는 최종값만이 아니라 중간값, 적용된 효과, 출처, 조건, 버전, 확실성, Evidence Graph를 포함해야 한다.
- 사용자가 정보를 덜 준 경우 추가 질문을 한다.
- PoB·로컬 KB·허용 외부 출처에서 근거가 부족한 경우 추측하지 않는다. 필요한 외부 검색 후에도 근거가 부족하면 답변을 거부한다.
- 외부 검색 결과는 현재 세션의 임시 근거로만 사용하며 KB에 자동 저장하지 않는다. 답변에 URL, 문서명, 확인 시점, PoE/PoB 계산값이 아님을 표시한다.
- 모델의 해석이 직접 근거에 기반하지 않으면 추론 또는 확인되지 않은 설명으로 표시한다.
- 사용자 API 키는 모델 입력, snapshot, 외부 전송 payload, 로그, 로컬 캐시에 포함하지 않는다. MVP는 사용자 API 키를 받지 않는다.
- 기본 답변은 한국어이며 최종값, 계산 과정, 적용 효과, 출처, Evidence Graph를 구분한다.

## 8. 금지사항

- PoB 계산 결과를 임의의 공식이나 모델 상식으로 덮어쓰기
- 근거 없는 숫자·메커니즘을 확정값처럼 답변
- 메이저 버전이 다른 빌드 계산 또는 비교
- XML 원문을 외부 서버로 직접 전송
- 검증되지 않은 Tool 호출, 파일 접근, OS 명령 실행
- 사용자 승인 없이 파일 저장 또는 Save As
- 외부 검색 결과의 자동 KB 승격
- 기존 PoB 기능·UI·저장 흐름의 회귀를 허용하는 변경

Langfuse 추적은 AgentLoop에 기본 연결되고 sampling 기본값은 1이다. endpoint는
localhost/127.0.0.1/::1만 허용하며, 전송 실패는
요청 결과를 중단시키지 않고 redacted event를 제한된 NDJSON queue에 남긴다.

## 9. 검증 기준

변경은 기존 PoB 회귀 테스트와 함께 검증한다. 최소 검증 시나리오는 Impending Doom/Vixen’s Entrapment 저주 순서, 변형 젬, 아이템 제공 스킬과 보조 젬, Static Strike 지속시간, Arc of Oscillating 연쇄·시전 속도, 스킬 군 주얼, 경매장 아이템 텍스트, PoB 코드 기반 빌드 비교다. 수치가 PoB 출력과 다르면 성공으로 간주하지 않는다.
