# PoB Agent MVP 프로젝트 기획서

> 문서 상태: 팀 내부 개발 기준  
> 대상 범위: Path of Exile 1 및 최신 안정 Path of Building Community 기반 MVP  
> 제품명: PoB Agent Extension

## 1. 문서 목적

이 문서는 PoB Agent MVP의 제품 범위, 기술 책임 경계, 개발 우선순위, 검증 기준을 하나의 팀 공통 기준으로 정의한다. 개발 중 세부 구현 판단이 갈릴 때 이 문서를 우선 참조하며, 상세 API·Tool 규격과 예외 코드는 연결된 참조 문서에서 관리한다.

PoB Agent는 Path of Building Community(이하 PoB)를 대체하는 계산기가 아니다. 기존 PoB가 가진 빌드 편집과 계산을 그대로 권위값으로 사용하고, 사용자가 자연어로 이를 이해하거나 제한된 변경을 요청할 수 있게 하는 확장 계층이다.

## 2. 제품 비전과 성공 정의

### 2.1 해결하려는 문제

PoB는 높은 정확도의 빌드 계산 결과를 제공하지만, 일반 사용자가 결과의 원인과 상호작용을 파악하려면 아이템·젬·패시브·버프·Config·조건의 관계와 PoB 내부 구조를 직접 분석해야 한다. 그 결과 사용자는 다음과 같은 어려움을 겪는다.

- 특정 DPS·지속시간·방어 수치가 왜 나왔는지 설명하기 어렵다.
- 아이템·젬·패시브 변경의 효과를 안전하게 비교하기 어렵다.
- 현재 선택된 Skill Set, Main Skill, Config에 따라 결과가 달라지는 점을 놓치기 쉽다.
- 복잡한 빌드를 수정하기 위해 XML 편집이나 다수의 PoB 화면 조작을 해야 한다.

### 2.2 제품 비전

사용자는 기존 PoB 화면에서 작은 AI 진입점을 통해 별도 Agent 창을 열고, 자연어로 현재 빌드의 수치·메커니즘·변경 전후 차이를 이해한다. 모든 확정 수치는 PoB의 현재 계산 결과를 근거로 하며, 변경은 사용자의 현재 PoB 메모리 상태에만 적용된다. 저장 여부는 항상 사용자가 기존 PoB의 `Save` 또는 `Save As`로 결정한다.

### 2.3 MVP 성공 기준

MVP는 아래 조건을 모두 충족할 때 완료로 본다.

- 핵심 사용자 기능 7종이 정의된 Tool 계약과 자동화 테스트를 갖는다.
- Agent가 표시하는 확정 수치는 PoB의 authoritative output과 일치한다.
- 수치·변경·메커니즘 설명에 출처, 조건, 버전, 확실성, Evidence Graph를 제공한다.
- 사용자 UI 변경은 진행 중인 Agent 변경보다 항상 우선한다.
- 자동 저장, 자동 백업, 자동 Save As 없이 기존 PoB 저장 흐름을 보존한다.
- 메이저 버전 불일치, 근거 부족, 모호한 대상, 검증 실패를 안전하게 질문·거부·복구한다.

## 3. 대상 사용자와 사용 경험

### 3.1 대상 사용자

주요 대상은 Path of Exile의 기본 개념은 이해하지만, PoB의 상세 UI와 계산 구조에는 익숙하지 않은 플레이어다. PoE·PoB 숙련 사용자는 상세 trace와 Evidence Graph를 검증용으로 사용할 수 있다.

### 3.2 대표 사용 흐름

1. 사용자가 PoB에서 빌드를 열거나 PoB 코드를 불러온다.
2. 사용자가 AI 버튼을 눌러 별도 Agent 창을 연다.
3. Bridge가 현재 Skill Set, Main Skill, Config, 활성 상태 및 계산 결과를 캡처한다.
4. 사용자가 자연어로 질문하거나 구체적인 변경을 요청한다.
5. Agent가 필요한 Tool·검색 실행 계획을 만들고, Bridge가 이를 검증·실행한다.
6. Agent가 결론, PoB 계산값, 적용 효과, 근거, 불확실성을 한국어 기본 응답으로 제시한다.
7. 변경 요청이면 검증된 결과만 현재 PoB 화면의 메모리 상태에 적용한다.
8. 사용자가 기존 PoB의 `Save` 또는 `Save As`로 저장 여부를 결정한다.

### 3.3 기본 응답 원칙

기본 응답은 한국어로 제공하며, 다음 순서를 따른다.

1. 결론과 최종 수치
2. 적용 효과와 핵심 상호작용
3. 계산 과정과 중간값
4. Evidence Graph
5. PoB 내부·로컬 지식·외부 출처
6. 확실성 및 버전 정보

PoB 계산값, 외부 문서 참고값, 모델 추론값은 서로 다른 표식으로 구분한다. 수치는 내부적으로 PoB 원본 정밀도를 보존하고 표시 단계에서만 반올림한다.

## 4. MVP 범위

### 4.1 핵심 사용자 기능

| 번호 | 기능 | 사용자 가치 | 완료 기준 |
| --- | --- | --- | --- |
| 1 | 수치 조회·근거 추적 | 현재 수치와 원인을 이해한다. | PoB output·trace·출처·Evidence Graph를 함께 반환한다. |
| 2 | 아이템 교체·비교 | 장비 변경의 결과를 안전하게 확인한다. | 대상 검증, 전후 비교, 현재 화면 반영, 재계산을 수행한다. |
| 3 | 젬 교체·비교 | 스킬·보조 젬의 영향을 확인한다. | 레벨·퀄리티·변형·링크 조건을 보존하고 비교한다. |
| 4 | 패시브·스킬 군 주얼 변경·비교 | 트리 및 주얼 변경의 영향을 확인한다. | 선택 대상·연결 상태·재계산 결과를 검증한다. |
| 5 | 변경 전후 DPS·메커니즘 설명 | 숫자 변화의 이유를 이해한다. | 최종값뿐 아니라 중간값·영향 요인을 설명한다. |
| 6 | 현재 빌드 메커니즘 설명 | 빌드의 작동 방식을 빠르게 파악한다. | PoB·로컬 지식 근거를 우선해 설명한다. |
| 7 | 다른 PoB 빌드 비교 | 두 빌드의 차이와 트레이드오프를 이해한다. | 가져온 빌드의 버전·상태를 검증하고 차이를 비교한다. |

### 4.2 공통 플랫폼 기능

- 자연어를 구조화된 Tool·검색 실행 계획으로 변환하는 LLM orchestration
- 버전별 규칙·아이템·스킬·패시브·별칭을 제공하는 로컬 RAG
- 허용 목록 기반 외부 검색
- 수치와 근거의 관계를 표현하는 Evidence Graph
- snapshot, diff, revision 기반 상태 동기화
- 빌드별 캐시 및 Save As 이후 캐시 분리
- 관측 가능성 및 안전한 오류·복구 체계

### 4.3 비목표

- AI의 자동 아이템·젬·패시브 추천
- PoB 계산기를 대체하거나 독자 계산 엔진을 만드는 일
- 기존 PoB UI, 탭, 저장 흐름의 재설계
- 사용자 API 키 입력 또는 로컬 모델 설치 요구
- 외부 검색 결과의 자동 지식베이스 편입
- Path of Exile 2 지원
- 메이저 버전이 다른 빌드의 계산·비교

## 5. 제품 및 기술 원칙

### 5.1 권위와 책임

- **PoB 본체**는 빌드 상태, 계산, 편집, 저장을 소유한다.
- **로컬 PoB Bridge**는 PoB와 외부 AI의 유일한 로컬 경계이며 snapshot·revision·Tool 검증·실행·재계산을 담당한다.
- **외부 AI 서버**는 자연어 해석, 구조화 계획 작성, 결과 해석, 최종 답변을 담당한다.
- **로컬 RAG 및 외부 검색**은 외부 AI가 직접 실행하지 않고 Bridge가 실행한다.

### 5.2 불변조건

- 기존 PoB UI, 계산, 저장, 불러오기, 공유, 업데이트 기능을 제거하거나 회귀시키지 않는다.
- 현재 선택된 Skill Set, Main Skill, Config, 활성 젬·보조 젬·버프·조건이 authoritative state다.
- 최신 PoB UI 상태가 Bridge의 이전 snapshot보다 항상 우선한다.
- Agent는 PoB 계산값을 다시 계산해 권위값으로 만들지 않는다.
- 변경은 사용자가 요청한 경우에만 현재 메모리 상태에 적용한다.
- 원본 XML은 외부 서버로 전송하지 않는다.
- 근거가 없으면 추측하지 않고 질문하거나 거부한다.

## 6. 시스템 아키텍처

```text
사용자
  ↕ 자연어 질문·변경 요청 / 근거 포함 답변
PoB Agent 창
  ↕ 구조화된 요청·응답
외부 AI 서버
  ├─ 의도 해석
  ├─ Tool·검색 실행 계획 생성
  └─ 한국어 답변 생성
  ↕ 정규화 snapshot/diff·Tool 결과·근거
로컬 PoB Bridge
  ├─ 상태 캡처 및 revision 관리
  ├─ Tool allowlist·인자·호출 수 검증
  ├─ 로컬 RAG·허용 외부 검색 실행
  ├─ 변경 적용·재계산·rollback
  └─ Evidence Graph 구성
  ↕
Path of Building Community
  ├─ 현재 빌드 메모리 상태
  ├─ 계산 output·breakdown·trace
  ├─ 아이템·젬·패시브 편집
  └─ Save / Save As
```

### 6.1 PoB 본체

PoB는 유일한 계산 권위자다. Bridge는 현재 메모리 상태와 계산 output·breakdown·trace를 읽고, 검증된 변경만 PoB의 편집 경로를 통해 적용한다. 기존 저장 동작은 그대로 유지한다.

### 6.2 로컬 PoB Bridge

Bridge는 신뢰 경계와 상태 일관성의 중심이다.

- 정규화된 전체 snapshot과 diff를 생성한다.
- 기대 revision과 현재 revision을 비교한다.
- Tool 이름·스키마·타입·대상·revision을 검증한다.
- 한 요청에서 연속 Tool 호출을 최대 8회로 제한한다.
- 로컬 RAG와 허용 외부 검색을 실행한다.
- 변경 전후 결과와 trace를 Evidence Graph로 결합한다.
- 실패 시 transaction·rollback·복구 가능한 오류 envelope를 반환한다.

### 6.3 외부 AI 서버

외부 AI 서버는 로컬 파일, PoB 메모리, 운영체제 명령, Tool 구현에 직접 접근하지 않는다. 입력 snapshot과 Tool 결과를 바탕으로 구조화된 JSON 계획을 반환하며, Bridge가 실행한 사실과 근거만으로 최종 답변을 작성한다. 서버는 빌드 상태와 대화 내용을 영구 저장하지 않는다.

### 6.4 지식 및 외부 검색

로컬 RAG는 게임 규칙과 메커니즘 설명을 보완한다. 현재 빌드의 숫자는 반드시 PoB Tool 결과를 우선한다. 로컬 근거가 부족할 때만 Bridge가 아래 출처를 대상으로 외부 검색을 수행한다.

- PoE Wiki
- PoEDB
- 공식 Path of Exile 사이트
- Path of Building Community GitHub
- Craft of Exile

외부 검색 결과는 URL, 문서명, 확인 시점, PoB 계산값이 아님을 포함한 세션 임시 근거로만 사용하며 자동 저장하지 않는다.

## 7. 핵심 데이터 및 실행 흐름

### 7.1 정규화 snapshot과 diff

Bridge는 원본 XML 대신 다음 정보를 포함한 정규화 snapshot을 관리한다.

- canonical build ID, snapshot ID, revision
- 게임·PoB·지식베이스 버전
- Skill Set, Main Skill, Config, 활성 상태
- 아이템, 소켓, 젬(레벨·퀄리티·변형 포함)
- 패시브, 주얼, 스킬 군 주얼 상태
- 질문에 필요한 계산 output 및 Evidence Graph 참조

첫 요청에는 전체 snapshot을 보낸다. 이후에는 마지막으로 동기화된 revision을 기준으로 변경된 item, skill, passive, config, enabledState만 diff에 담는다. diff를 신뢰할 수 없거나 revision이 불일치하면 전체 최신 snapshot으로 재동기화한다.

### 7.2 Tool 실행 흐름

1. Bridge가 요청 직전 PoB의 최신 상태와 version을 캡처한다.
2. 외부 AI가 구조화된 Tool·검색 계획을 반환한다.
3. Bridge가 allowlist, 인자, 대상, revision, 호출 횟수를 검증한다.
4. Bridge가 Tool을 순차 실행하고 필요한 로컬 RAG·외부 검색을 수행한다.
5. 변경 요청이면 실행 직전 revision을 다시 비교한다.
6. revision이 일치할 때만 변경을 적용하고 PoB 재계산 결과를 수집한다.
7. Bridge가 결과·trace·출처·버전·불확실성을 Evidence Graph에 연결한다.
8. 외부 AI가 근거와 해석을 구분한 최종 답변을 생성한다.

### 7.3 Evidence Graph

Evidence Graph는 최종 계산값과 그 값에 영향을 준 근거를 연결한다. 노드는 값·단위·계산 버전·출처·조건·확실성을 가지며, edge는 `contributes_to`, `derived_from`, `gated_by`, `replaced_by` 같은 관계를 표현한다.

```text
[PoB 기본 출력]
      ↓ derived_from
[아이템·패시브·젬 효과] ──→ [중간 계산값]
                                  ↓
                          [최종 PoB 출력]
                                  ↓
                            [사용자 답변]
```

모든 Tool·응답 envelope는 원칙적으로 다음 필드를 제공한다.

`status`, `facts`, `trace`, `sources`, `version`, `evidenceGraph`, `uncertainty`

값이나 출처를 제공할 수 없는 경우에는 해당 필드에 누락 사유를 기록한다.

### 7.4 캐시와 Save As

대화, snapshot, 변경 이력, Evidence Graph 참조, 버전 메타데이터는 사용자 PC의 빌드별 캐시에 보관한다.

- 대화 시작 시 canonical build ID로 캐시를 불러온다.
- 최신 버전 재계산이 성공하면 캐시를 갱신한다.
- 메이저 버전이 같고 재계산에 실패하면 경고와 함께 기존 캐시를 재사용할 수 있다.
- 메이저 버전이 다르면 캐시를 사용하지 않고 계산·비교를 거부한다.
- `Save As`가 실제로 성공한 뒤에만 새 canonical build ID를 만들고 해당 시점의 캐시를 원자적으로 복사한다.
- 복사 실패 시 새 캐시를 만들지 않으며, 이후 원본과 새 캐시는 독립적으로 갱신한다.

## 8. 안전성, 오류 처리 및 보안

### 8.1 버전 정책

게임과 PoB는 최신 안정 버전을 기준으로 한다. 요청 시작 시 게임, PoB, 지식베이스 버전을 확인한다.

- 세부 버전 차이: 업데이트를 시도하고, 실패했더라도 메이저 버전이 같으면 경고 및 낮은 신뢰도와 함께 처리할 수 있다.
- 메이저 버전 차이: 계산과 비교를 실행하지 않고 명확한 이유와 함께 거부한다.
- snapshot, Tool 결과, Evidence Graph, 캐시에는 관련 버전을 기록한다.

### 8.2 사용자 상태와 변경 안전성

변경 Tool 실행 직전에 Bridge는 기대 revision과 현재 revision을 비교한다. 다르면 오래된 Agent 변경을 폐기하고 최신 사용자 상태를 재캡처한다. 사용자가 PoB UI에서 직접 바꾼 내용은 어떤 경우에도 Agent 변경보다 우선한다.

변경은 transaction으로 다루며, 적용·재계산·결과 수집 중 실패하면 가능한 범위에서 이전 상태로 rollback한다. 성공한 변경도 자동으로 저장하지 않는다.

### 8.3 오류·거부 원칙

- 필수 정보가 없으면 필요한 정보만 짧게 질문한다.
- 여러 대상으로 해석되면 임의 선택하지 않고 대상을 확인한다.
- 근거 부족, 지원하지 않는 요청, 버전 불일치, revision 충돌은 추측으로 보완하지 않는다.
- 동일 Tool과 동일 인자의 반복 호출을 차단한다.
- 호출 한도를 초과하면 중단 이유와 확보된 부분 결과를 알린다.
- 오류 envelope는 상위 분류(`error_ref`), 등록된 세부 코드(`error_code`), 복구 방식(`recovery_class`), 사용자 안전 메시지를 일관되게 포함한다.

### 8.4 보안 및 데이터 경계

- 외부 서버 통신은 TLS를 사용한다.
- 원본 XML, 임의 파일 경로, OS 명령은 외부 AI에 노출하거나 실행하지 않는다.
- Tool은 allowlist와 인자 검증을 통과한 구조화된 호출만 실행한다.
- MVP는 사용자 API 키를 요구하지 않으며, API 키가 모델 입력·snapshot·로그·캐시에 들어가서는 안 된다.
- 서버는 빌드·대화·캐시를 영구 보관하지 않는다.
- 운영 로그는 최소한의 비민감 정보만 redaction 후 기록한다.

## 9. 개발 로드맵

### 단계 0 — 기반 계약 고정

- Tool catalog, response envelope, error registry, snapshot schema, version 정책을 정비한다.
- PoB 계산 권위와 저장·상태 불변조건을 회귀 테스트로 고정한다.

### 단계 1 — 읽기 전용 MVP 기반

- in-process Dispatcher로 현재 PoB 컨텍스트, snapshot revision, output·trace를 캡처한다.
- 수치 조회·근거 추적·메커니즘 설명 Tool을 우선 제공한다.
- headless XML/fixture adapter를 개발·검증 전용으로 유지한다.

### 단계 2 — 비교와 근거 플랫폼

- 아이템·젬·패시브·다른 빌드의 비교 흐름을 구현한다.
- Evidence Graph, 로컬 RAG, 허용 외부 검색, 불확실성 표시를 통합한다.

### 단계 3 — 안전한 실시간 변경

- 지속형 in-process session을 구축한다.
- revision 검증, transaction, rollback, idempotency, 재계산을 포함한 live mutation을 구현한다.
- 아이템·젬·패시브·스킬 군 주얼 변경을 현재 화면에 적용한다.

### 단계 4 — 통합 검증과 출시 준비

- 대표 빌드 시나리오, PoB 회귀, 사용자 흐름, 장애 복구, 관측 가능성 검증을 완료한다.
- 지원 범위·제한 사항·사용자 데이터 안내를 제품 화면과 문서에 명확히 반영한다.

## 10. 테스트 및 품질 전략

### 10.1 필수 테스트 계층

| 계층 | 검증 대상 |
| --- | --- |
| 기존 PoB 회귀 | UI, 계산, 저장, 불러오기, 공유, 업데이트 동작의 유지 |
| Bridge 계약 | snapshot, diff, revision 충돌, Tool allowlist, 호출 한도 |
| Tool 단위 테스트 | 인자 검증, PoB output 추출, 오류 envelope, 예외 처리 |
| 계산 일치 테스트 | Agent facts와 PoB authoritative output의 일치 |
| Evidence Graph 테스트 | 중간값, 출처, 관계, 조건, 누락 사유의 완전성 |
| RAG·검색 테스트 | 로컬 우선순위, 외부 출처 allowlist, 세션 임시성 |
| 통합 테스트 | 실제·fixture 빌드에 대한 질문, 비교, 변경, rollback |
| UX 테스트 | 일반 사용자가 질문·변경·Save/Save As를 완료하는지 확인 |

### 10.2 대표 검증 시나리오

- Impending Doom과 Vixen’s Entrapment의 저주 적용 순서
- 변형 젬과 일반 젬의 구분
- 아이템 제공 스킬에 대한 소켓 보조 젬 적용
- Static Strike 지속시간
- Arc of Oscillating의 연쇄와 시전 속도
- 스킬 군 주얼에 따른 패시브 변화
- 경매장 아이템 텍스트 교체
- PoB 코드로 불러온 다른 빌드 비교

### 10.3 출시 차단 기준

아래 문제는 해결 전 출시를 차단한다.

- PoB output과 확정 수치가 일치하지 않음
- 사용자의 UI 변경이 Agent 변경으로 덮어써짐
- 자동 저장 또는 Save As 흐름 회귀
- 원본 XML 또는 민감 정보의 외부 전송 가능성
- allowlist 밖 Tool 실행 또는 검증되지 않은 인자 실행
- 근거 없는 수치가 확정값으로 표시됨
- 메이저 버전 불일치 계산·비교가 허용됨

## 11. 운영 및 의사결정 기준

### 11.1 관측 가능성

AgentLoop는 Langfuse 추적과 연결하며 기본 sampling은 1로 둔다. endpoint는 localhost, 127.0.0.1, ::1만 허용한다. 전송 실패는 사용자 요청을 실패시키지 않으며, redacted event를 크기 제한된 로컬 NDJSON queue에 남긴다. 동일 run의 중복 저장은 방지한다.

### 11.2 주요 리스크와 대응

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| PoB 내부 구조·버전 변경 | Tool과 snapshot 추출의 회귀 | 버전 메타데이터, 계약 테스트, 호환성 검사 |
| 실시간 변경 실패 | 빌드 상태 손상 가능성 | transaction, revision 검사, rollback, 자동 저장 금지 |
| LLM의 환각·과도한 호출 | 잘못된 설명 또는 비안전 실행 | 구조화 계획, allowlist, 근거 기반 응답, 호출 상한 |
| 외부 검색 품질·변경 | 오래되거나 부정확한 설명 | 허용 출처, 확인 시점, PoB 값과 분리 표시 |
| 복잡한 게임 메커니즘 | 설명·근거 누락 | 지원 범위 명시, 근거 부족 시 거부, 대표 시나리오 확대 |

### 11.3 팀 의사결정 규칙

- 계산값의 진실성은 PoB output이 최우선이다.
- 안전성과 사용자 상태 보존은 기능 편의성보다 우선한다.
- 새 Tool은 catalog, 입력 스키마, 출력 envelope, 오류 코드, 테스트를 함께 추가해야 한다.
- 외부 AI가 수행할 수 있는 일은 계획과 설명까지이며, 로컬 실행 권한은 Bridge에만 둔다.
- 지원하지 않는 메커니즘은 추정 구현보다 제한 사항을 명시하는 방식을 택한다.
- 기존 PoB 기능에 영향을 주는 변경은 해당 PoB 회귀 검증을 통과해야 한다.

## 12. 참조 문서

- [개발·운영 계약](../AGENT.md)
- [고객 및 사용자 경험 정의](../CUSTOMER.md)
- [PRD / SDD](../PRD_SDD.md)
- [Bridge 계약](../agent/AgentBridge.md)
- [Tool 작성 기준](../agent/TOOL_AUTHORING.md)
- [예외 처리 기준](../agent/EXCEPTION_HANDLING.md)
- [Tool 테스트 기준](../agent/TOOL_TESTING.md)
- [Tool Catalog](tools/catalog.md)
- [Response Envelope](tools/response-envelope.md)

## 13. 문서 유지 관리

이 문서는 MVP의 팀 공통 기준이다. 구현 상태, 지원 Tool, 대표 시나리오, 출시 기준이 변경되면 관련 기능 변경과 같은 검토 단위에서 갱신한다. 단, 세부 구현 API와 개별 테스트 절차는 각 계약 문서에서 관리하며 이 문서에는 제품·시스템 수준의 결정만 반영한다.
