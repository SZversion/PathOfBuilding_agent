# Path of Building Community — PoB Agent Extension

<details open>
<summary>English</summary>

## About Path of Building Community

Path of Building Community is an offline build planner for Path of Exile.

It provides:

- Offence and defence calculations, including skill DPS, damage over time, life, mana, energy shield, auras, buffs, charges, curses, resistances, and reservations.
- A passive skill tree planner with jewel support, alternate path tracing, and integrated calculations.
- Import of passive-tree links from PathOfExile.com and PoEPlanner.com.
- A skill planner for active skills, support gems, auras, curses, buffs, socketed-gem modifiers, and item-granted support gems.
- An item planner with in-game item copy/paste, unique and rare item data, trade search, crafting tools, modifier rolls, league-specific items, and legacy variants.
- Character/build import, share codes, and automatic updates.

<p float="middle">
  <img alt="Tree tab" src="https://github.com/user-attachments/assets/0826b7ab-84ba-440f-be52-2f216f13e75c" width="48%" />
  <img alt="Items tab" src="https://github.com/user-attachments/assets/e5af1326-7e22-43d8-ab12-aa5500da611a" width="48%" />
</p>

## Download the upstream application

Download the install wizard or portable ZIP from the [Path of Building Community Releases](https://github.com/PathOfBuildingCommunity/PathOfBuilding/releases) page.

## PoB Agent Extension

The PoB Agent Extension is a separate extension layer designed to use PoB's authoritative in-memory calculations and explain their evidence to an external agent.

```text
User question → external LLM → structured Tool/RAG plan → PoB Bridge → PoB output and trace → Evidence Graph → LLM answer
```

Current status:

- 28 Tool contracts are registered in the catalog. Registration does not mean every Tool is live-ready or that every PoE mechanism is supported.
- A read-only in-process Dispatcher can capture the current PoB context, including active Spec, Skill Set, Item Set, Config, gems, links, conditions, and a `snapshotRevision`.
- A headless XML/fixture adapter remains available for read-only development and verification.
- Mutation Tools are currently disabled for the live PoB screen. The one-shot headless adapter must not be interpreted as persistent mutation of the user's open PoB window.
- Evidence-bearing results use PoB paths, trace data, version metadata, uncertainty, and an Evidence Graph where available.

The project does not claim complete support for every game mechanism. When PoB does not expose a value or source, the extension must report that limitation instead of guessing.

Planned next capabilities:

- A persistent in-process live session that keeps the current PoB state authoritative across requests.
- Validated live mutation with transaction, rollback, idempotency, stale-revision protection, and PoB recalculation.
- Applying approved changes to the current PoB screen while leaving Save and Save As under the user's control.

Project contracts and boundaries are documented in [AGENT.md](AGENT.md), [CUSTOMER.md](CUSTOMER.md), [PRD_SDD.md](PRD_SDD.md), [AgentBridge.md](agent/AgentBridge.md), [Tool Authoring](agent/TOOL_AUTHORING.md), [Exception Handling](agent/EXCEPTION_HANDLING.md), [Tool Testing](agent/TOOL_TESTING.md), the [Tool Catalog](docs/tools/catalog.md), the [Response Envelope](docs/tools/response-envelope.md), the [Knowledge Base README](agent/knowledge/README.md), [Rule Schema](agent/knowledge/RULE_SCHEMA.md), and the [Validation Workflow](agent/knowledge/VALIDATION_WORKFLOW.md).

## Verification status

The development checks include Lua tool fixtures, Dispatcher checks, catalog linting, and Python regression tests. These checks do not claim full PoE-mechanism or live-window coverage.

## Changelog

The full upstream version history is available in [CHANGELOG.md](CHANGELOG.md).

## Contribute

Instructions for contributing code and reporting bugs are available in [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

The upstream project is licensed under the [MIT License](https://opensource.org/licenses/MIT). Third-party licensing information is available in [LICENSE.md](LICENSE.md).

</details>

<details>
<summary>한국어</summary>

## Path of Building Community 소개

Path of Building Community는 Path of Exile을 위한 오프라인 빌드 플래너입니다.

주요 기능은 다음과 같습니다.

- 스킬 DPS, 지속 피해, 생명력, 마나, 에너지 보호막, 오라, 버프, 충전, 저주, 저항, 점유를 포함한 공격·방어 계산.
- 주얼 지원, 경로 추적, 계산 연동을 제공하는 패시브 스킬 트리 플래너.
- PathOfExile.com과 PoEPlanner.com의 패시브 트리 링크 가져오기.
- 액티브 스킬, 보조 젬, 오라, 저주, 버프, 장착 젬 옵션, 아이템 제공 보조 젬을 지원하는 스킬 플래너.
- 게임 내 아이템 복사·붙여넣기, 고유·희귀 아이템 데이터, 거래 검색, 제작 도구, 옵션 수치, 리그 전용 아이템, 레거시 변형을 제공하는 아이템 플래너.
- 캐릭터·빌드 가져오기, 공유 코드, 자동 업데이트.

<p float="middle">
  <img alt="Tree tab" src="https://github.com/user-attachments/assets/0826b7ab-84ba-440f-be52-2f216f13e75c" width="48%" />
  <img alt="Items tab" src="https://github.com/user-attachments/assets/e5af1326-7e22-43d8-ab12-aa5500da611a" width="48%" />
</p>

## 업스트림 프로그램 다운로드

[Path of Building Community Releases](https://github.com/PathOfBuildingCommunity/PathOfBuilding/releases) 페이지에서 설치 마법사 또는 포터블 ZIP을 다운로드할 수 있습니다.

## PoB Agent Extension

PoB Agent Extension은 실행 중인 PoB 메모리의 기준 계산값을 사용하고 그 근거를 외부 에이전트가 설명하도록 설계된 별도 확장 계층입니다.

```text
사용자 질문 → 외부 LLM → 구조화된 Tool/RAG 계획 → PoB Bridge → PoB 출력·trace → Evidence Graph → LLM 답변
```

현재 상태:

- 카탈로그에 Tool 계약이 등록되어 있습니다. 등록은 모든 Tool이 실사용 가능하거나 모든 PoE 메커니즘을 지원한다는 뜻이 아닙니다.
- 현재 PoB 컨텍스트의 활성 Spec, Skill Set, Item Set, Config, 젬, 링크, 조건과 `snapshotRevision`을 캡처할 수 있는 읽기 전용 in-process Dispatcher가 있습니다.
- 읽기 전용 개발·검증을 위해 headless XML/fixture adapter도 유지됩니다.
- mutation Tool은 현재 실행 중인 PoB 화면에 대해 비활성화되어 있습니다. 일회성 headless adapter를 사용자의 PoB 창에 지속적으로 mutation이 적용되는 것으로 해석해서는 안 됩니다.
- 근거를 포함하는 결과는 가능한 경우 PoB 경로, trace 데이터, 버전 메타데이터, 불확실성, Evidence Graph를 포함합니다.

이 프로젝트는 모든 게임 메커니즘을 완전히 지원한다고 주장하지 않습니다. PoB가 값이나 출처를 노출하지 않으면 추측하지 않고 해당 제한을 보고해야 합니다.

다음 목표:

- 요청 사이에 현재 PoB 상태를 기준 상태로 유지하는 지속형 in-process live session.
- transaction, rollback, idempotency, stale revision 보호, PoB 재계산을 포함한 검증된 live mutation.
- 사용자의 Save와 Save As 제어는 유지하면서 현재 PoB 화면에 승인된 변경을 반영.

프로젝트 계약과 경계는 [AGENT.md](AGENT.md), [CUSTOMER.md](CUSTOMER.md), [PRD_SDD.md](PRD_SDD.md), [AgentBridge.md](agent/AgentBridge.md), [Tool Authoring](agent/TOOL_AUTHORING.md), [Exception Handling](agent/EXCEPTION_HANDLING.md), [Tool Testing](agent/TOOL_TESTING.md), [Tool Catalog](docs/tools/catalog.md), [Response Envelope](docs/tools/response-envelope.md), [Knowledge Base README](agent/knowledge/README.md), [Rule Schema](agent/knowledge/RULE_SCHEMA.md), [Validation Workflow](agent/knowledge/VALIDATION_WORKFLOW.md)에 정리되어 있습니다.

## 검증 상태

현재 개발 검사는 Lua Tool fixture, Dispatcher 검사, 카탈로그 lint, Python 회귀 테스트로 구성됩니다. 이는 개발 검사이며 모든 PoE 메커니즘이나 실제 실행 중 창 제어를 완전히 검증했다는 뜻은 아닙니다.

## 변경 이력

업스트림 전체 버전 이력은 [CHANGELOG.md](CHANGELOG.md)에서 확인할 수 있습니다.

## 기여

코드 기여와 버그 제보 방법은 [CONTRIBUTING.md](CONTRIBUTING.md)에서 확인할 수 있습니다.

## 라이선스

업스트림 프로젝트는 [MIT License](https://opensource.org/licenses/MIT)를 따릅니다. 서드파티 라이선스 정보는 [LICENSE.md](LICENSE.md)에서 확인할 수 있습니다.

</details>
