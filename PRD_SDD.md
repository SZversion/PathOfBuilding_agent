# PoB Agent PRD / SDD

## Part I — PRD

### 1. 제품 정의

PoB Agent는 Path of Building Community를 발전시킨 확장 서비스다. 기존 PoB의 UI와 계산 기능을 유지하고, 작은 AI 버튼으로 여는 별도 Agent 창에서 자연어 질문·메커니즘 설명·빌드 변경 비교를 제공한다.

### 2. 문제

PoB는 캐릭터의 세부 수치와 계산 결과를 제공하지만, 사용자가 그 수치가 어떤 아이템·젬·패시브·버프·조건의 상호작용으로 만들어졌는지 이해하려면 내부 구조와 게임 규칙을 직접 분석해야 한다. 특히 변형 젬, 아이템 제공 스킬, 소켓 순서, 스킬 군 주얼, Config와 활성 상태가 결합된 빌드는 단순한 숫자 조회만으로 설명하기 어렵다.

### 3. 목표

사용자가 PoB를 직접 분석하거나 복잡하게 조작하지 않아도, 현재 빌드의 수치와 메커니즘을 PoB와 동일한 값으로 확인하고 변경 전후 결과와 모든 근거를 Evidence Graph로 이해할 수 있게 한다.

### 4. MVP 기능

#### Core MVP — 7개 사용자 기능

- 수치 조회·근거 추적
- 아이템 교체·비교
- 젬 교체·비교
- 패시브·스킬 군 주얼 변경·비교
- 변경 전후 DPS와 메커니즘 설명
- 빌드 메커니즘 설명
- PoB 코드로 가져온 다른 빌드와 비교·차이 설명

#### 공통 플랫폼 기능

- LLM 기반 자연어 Tool 계획·실행
- 로컬 RAG 기반 게임 지식 검색
- 허용된 외부 출처 검색
- 계산 근거 Evidence Graph 표시

### 5. 비목표

- AI 자동 아이템·젬·패시브 추천
- PoB 계산기의 대체 또는 독자적인 수치 재계산 엔진
- 기존 PoB UI와 저장 흐름의 재설계
- 사용자 API 키 입력과 로컬 모델 설치
- 외부 검색 결과의 자동 지식베이스 저장
- PoE2 지원
- 메이저 버전이 다른 빌드의 계산·비교

### 6. 기본 정책

게임과 PoB는 최신 안정 버전을 기준으로 한다. 세부 버전 차이는 업데이트를 시도하고, 실패해도 메이저 버전이 같으면 경고와 함께 답변할 수 있다. 메이저 버전이 다르면 답변을 거부한다.

사용자는 API 키나 로컬 모델을 제공하지 않는다. 외부 AI 서버는 무상태로 요청을 처리하고, PoB의 계산·상태·변경은 로컬 PoB Bridge에서 수행한다. 첫 요청에는 정규화된 전체 snapshot을 보내고, 이후에는 변경분만 보낸다. 변경분이 불확실하면 전체 snapshot으로 재동기화한다.

### 7. MVP Acceptance Criteria

#### 핵심 기능

Core MVP 7개 기능 각각에 자동화 테스트와 실제 빌드 시나리오가 하나 이상 있어야 한다. 각 기능은 필요한 Tool 호출, PoB 결과, 변경 상태, 사용자에게 표시할 근거를 추적할 수 있어야 한다.

#### 계산 정확성

- Agent가 표시하는 수치는 PoB의 authoritative output과 일치해야 한다.
- Agent는 수치를 임의로 재계산해 PoB 결과를 덮어쓰지 않는다.
- 원본 정밀도를 유지하고, 차이가 있으면 성공으로 판정하지 않고 불일치를 표시한다.
- 버전 정책을 위반한 결과를 확정값으로 출력하지 않는다.

#### 근거 완전성

각 확정 숫자는 최종값, 중간값, 영향을 준 아이템·젬·패시브·버프·조건, 내부 출처, 버전, 확실성, Evidence Graph 경로를 제공해야 한다. 근거가 없으면 답변을 거부한다.

#### 변경·비교

- 아이템·젬·패시브·스킬 군 주얼 변경이 현재 PoB 메모리 상태에 즉시 반영된다.
- 사용자 UI 변경이 Agent 변경보다 우선한다.
- 기존 `Save`·`Save As` 동작이 유지되고 자동 저장은 없다.
- 변경 전후 DPS와 메커니즘 차이를 설명한다.

#### 대표 시나리오

- Impending Doom + Vixen’s Entrapment 저주 적용 순서
- 변형 젬과 일반 젬 구분
- 아이템 제공 스킬에 소켓 보조 젬 적용
- Static Strike 지속시간
- Arc of Oscillating 연쇄와 시전 속도
- 스킬 군 주얼에 따른 패시브 변화
- 경매장 아이템 텍스트 교체
- PoB 코드 기반 다른 빌드 비교

#### Agent·검색

- 공통 플랫폼 기능으로서 외부 AI가 자연어에서 필요한 Tool·검색 실행 계획을 구조화 JSON으로 반환하고, 로컬 Bridge가 이를 검증·실행한다.
- 한 요청에 최대 8회까지 연속 호출한다.
- 로컬 RAG를 먼저 사용하고, 허용된 외부 검색으로 보완한다. 두 검색 모두 Bridge가 실행한다.
- 외부 출처는 PoE Wiki, PoEDB, 공식 Path of Exile 사이트, PoB Community GitHub, Craft of Exile로 제한한다.
- 외부 결과는 세션 임시 근거로 표시하고 자동 저장하지 않는다.
- 확정값·외부 참고값·추론값을 명확히 구분한다.

#### Evidence Graph 플랫폼

- 각 Tool/응답 envelope는 `status`, `facts`, `trace`, `sources`, `version`, `evidenceGraph`, `uncertainty`를 의무적으로 제공하거나, 제공할 수 없는 경우 해당 필드에 누락 사유를 기록한다.
- `uncertainty`는 데이터 부족, 버전 경고, 외부 참고, 추론, 부분 결과를 구분한다.
- 최종 답변은 Core 기능과 플랫폼 근거를 함께 추적할 수 있어야 한다.

#### UX

PoE는 알지만 PoB가 익숙하지 않은 사용자가 XML 편집 없이 자연어 질문과 변경을 완료하고, 기본 응답에서 계산 과정과 Evidence Graph를 이해할 수 있어야 한다.

## Part II — SDD

### 8. 3계층 아키텍처

```text
PoB 본체
  ↕ 현재 메모리 상태·계산 결과·변경
로컬 PoB Bridge
  ↕ 정규화 snapshot/diff·구조화 Tool 호출
외부 AI 서버
  ├─ 자연어 의도·Tool 계획
  ├─ Tool·검색 실행 계획 반환
  └─ 최종 한국어 답변
```

PoB 본체는 기존 계산과 편집을 계속 수행한다. Bridge는 외부 경계와 상태 일관성을 관리한다. 외부 AI는 PoB 메모리나 파일에 직접 접근하지 않는다.

### 9. 처리 흐름

1. AI 버튼이 Agent 창을 연다.
2. Bridge가 현재 authoritative state와 revision을 캡처한다.
3. 빌드별 로컬 캐시를 로드하고 버전 확인·재계산을 시도한다.
4. 첫 요청이면 전체 normalized snapshot, 후속 요청이면 검증된 diff를 외부 AI에 보낸다.
5. 외부 AI가 Tool·검색 실행을 위한 구조화 JSON plan을 반환한다. 외부 AI는 로컬 파일, 로컬 RAG, 외부 웹 검색, PoB Tool을 직접 실행하지 않는다.
6. Bridge가 Tool 이름·인자·revision·호출 횟수를 검증한다.
7. 로컬 PoB에서 Tool을 실행하고 필요한 경우 여러 Tool을 순차 실행한다.
8. 변경 Tool은 현재 화면에 반영하고 PoB 재계산 결과를 생성한다.
9. Bridge가 Tool·로컬 RAG·허용 외부 검색을 실행하고, 결과·RAG 조각·외부 출처를 Evidence Graph로 결합해 AI에 전달한다.
10. AI가 계산값·효과·근거·불확실성을 구분한 한국어 답변을 생성한다.

### 10. Normalized snapshot / diff 개요

```json
{
  "schemaVersion": 1,
  "canonicalBuildId": "local-build-id",
  "snapshotId": "snapshot-id",
  "revision": 42,
  "gameVersion": "3.29",
  "pobVersion": "pob-version",
  "knowledgeVersion": "latest",
  "skillSet": "Endgame",
  "mainSkill": {"group": 6, "name": "Arc of Oscillating"},
  "config": {},
  "enabledState": {},
  "items": [],
  "skills": [],
  "passives": [],
  "calculatedOutputs": {},
  "evidenceGraphRefs": []
}
```

후속 요청의 diff는 `baseRevision`, `revision`, `changes[]`를 포함하며 변경된 item/skill/passive/config/enabledState만 담는다. diff 생성에 실패하거나 revision이 불일치하면 전체 snapshot을 재전송한다.

### 11. Evidence Graph

Evidence Graph는 계산 노드와 근거 노드를 분리하고, 영향 관계를 edge로 표현한다.

```text
[PoB base output: 4.0s]
          ↓
[Passive +40%] ─┐
[Item +25%]  ───┴→ [Increased multiplier 1.65]
                         ↓
                  [Intermediate 6.6s]
                         ↓
                 [Support more ×1.56]
                         ↓
                  [Final 10.296s]
```

노드는 값·단위·계산 버전·출처·조건·확실성을 갖고, edge는 `contributes_to`, `derived_from`, `gated_by`, `replaced_by` 같은 관계를 갖는다. PoB output과 modifier trace는 확정 계산 근거, 로컬 규칙은 지식 근거, 외부 문서는 세션 임시 근거로 표시한다.

### 12. Tool 계약

현재 Tool 계층은 수치·breakdown·상호작용·비교·변경을 모두 동일한 원칙으로 노출한다. 대표 Tool은 `get_skill_dps`, `get_skill_breakdown`, `explain_stat`, `get_projectile_count`, `get_curse_limit`, `get_socket_order`, `get_skill_chain`, `get_duration`, `get_item_modifiers`, `compare_support_effect`, `explain_damage_change`, `compare_build_states` 등이다.

각 Tool/응답 envelope는 `status`, `facts`, `trace`, `sources`, `version`, `evidenceGraph`, `uncertainty`를 의무 필드로 갖는다. `uncertainty`는 값의 불확실성뿐 아니라 버전 차이, 외부 참고, 추론, 부분 결과, 근거 누락을 표현한다. Tool은 직접 계산 컨텍스트를 재현해 임의 수치를 만드는 대신 PoB의 계산 output·breakdown·modifier source를 읽는다.

### 13. RAG와 외부 검색

로컬 RAG는 `agent/knowledge`의 버전별 영어 규칙 문서, 구조화 JSON, 한국어·영어 alias, 검색 인덱스를 사용한다. RAG 실행은 외부 AI가 아니라 Bridge가 담당한다. 현재 빌드의 숫자는 RAG가 아니라 PoB Tool을 우선한다. RAG는 규칙의 의미·상호작용 설명을 보완한다.

로컬 근거가 부족하면 Bridge가 허용 목록에서 외부 검색을 수행한다. 외부 AI는 검색 계획만 반환한다. 외부 결과는 URL, 제목, 확인 시점, 버전, 발췌·요약, 확실성을 포함한 세션 근거로만 유지한다. 자동으로 로컬 KB에 저장하지 않는다.

### 14. 캐시 lifecycle

빌드별 캐시는 사용자 PC에 저장하며 대화 기록, 현재 snapshot, 변경 이력, Evidence Graph 참조, 버전 메타데이터를 포함한다. 서버는 이를 영구 보관하지 않는다.

- 대화 시작: canonical build ID로 캐시 로드
- 캐시 로드: 최신 버전 재계산 시도
- 성공: 최신 결과로 원자적 갱신
- 실패 + 메이저 동일: 기존 캐시 재사용 및 경고
- 실패 + 메이저 불일치: 답변 거부
- Save As 성공: 새 canonical ID 생성 후 당시 캐시를 원자적으로 복제

### 15. 버전·revision·동시성

Tool 실행 직전 Bridge는 revision을 확인한다. 기대 revision과 현재 revision이 다르면 Agent 변경을 실행하지 않고 최신 상태를 재캡처한다. 사용자가 UI에서 직접 변경한 상태가 항상 우선한다. 메이저 버전이 다른 snapshot·캐시는 계산에 사용하지 않는다.

### 16. 보안과 데이터 경계

- 외부 서버 통신은 TLS를 사용한다.
- 원본 XML 대신 정규화 snapshot/diff만 전송한다.
- 사용자 API 키는 MVP에 없으며 모델 입력, snapshot, 로그, 로컬 캐시에 포함하지 않는다.
- Bridge는 Tool allowlist와 인자·revision 검사를 수행한다.
- 일반 텍스트 명령, 임의 파일 경로, OS 명령은 실행하지 않는다.
- 서버는 무상태이며 빌드·대화·캐시를 영구 저장하지 않는다.
- 로그는 최소한의 비민감 운영 정보만 남긴다.

### 17. 테스트 전략

- 기존 PoB 회귀 테스트: UI, 계산, 저장, 불러오기
- Bridge 계약 테스트: snapshot, diff, revision 충돌, Tool allowlist, 8회 제한
- 계산 일치 테스트: PoB output과 Agent facts 비교
- Evidence Graph 테스트: 중간값·출처·관계·누락 근거 검증
- RAG/검색 테스트: 우선순위, 출처 allowlist, 세션 임시성
- 대표 빌드 통합 테스트: PRD의 8개 시나리오
- UX 테스트: PoE 일반 사용자가 질문·변경·Save/Save As를 완료하는지 확인

### 18. 구현 상태와 확장 원칙

현재 저장소에는 PoB 내부 snapshot/trace, Bridge, Agent orchestration, 지식 검색의 기반이 있다. 문서에 정의된 전체 MVP 기능은 각 단계에서 실제 PoB 상태와 연결해 검증해야 한다. 새 기능을 추가할 때도 PoB 계산을 복제하기보다 기존 계산 결과와 출처를 노출하는 최소 계층을 우선한다.

개발 추적은 AgentLoop에 기본 wiring하고 sampling 기본값은 1로 한다. Langfuse
endpoint는 로컬 주소만 허용하고 전송 실패 시 요청을 실패시키지 않는다. 키·SDK·서비스가
없어도 local queue를 사용한다. 실패한
redacted trace는 `data/traces/langfuse-queue.ndjson`에 제한된 크기로 임시 보관하며
동일 run은 중복 저장하지 않는다.
