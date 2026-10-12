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

- All 32 implemented tool contracts are exposed by a separate Streamable HTTP MCP container. The backend container connects to it over the private Compose network. Names, schemas, purpose/usage descriptions, side effects, timeouts, retries, and error codes are declared in `agent/tool_catalog.py`; regenerate the catalog section with `python tools/render_mcp_tool_catalog.py`.
- A read-only in-process Dispatcher can capture the current PoB context, including active Spec, Skill Set, Item Set, Config, gems, links, conditions, and a `snapshotRevision`.
- PoB tool calls use the authenticated live Lua endpoint on the Windows host; the MCP container reaches it through `host.docker.internal`. Knowledge, alias, external search, and snapshot comparison tools run in the MCP container.
- Mutation Tools remain discoverable but return `MUTATION_NOT_PERSISTENT`; the production MCP path never falls back to the headless XML adapter.
- Evidence-bearing results use PoB paths, trace data, version metadata, uncertainty, and an Evidence Graph where available.

Copy `.env.docker.example` to `.env.docker`, replace its `CHANGE_ME` values, put PoB build XML files in the configured build folder, and set `POB_ENDPOINT_HOST_PATH` to PoB's endpoint folder. Install/update the Lua modules with `powershell -ExecutionPolicy Bypass -File tools/install_live_control.ps1`. Launch PoB from a PowerShell session where `$env:POB_AGENT_BIND_HOST = '0.0.0.0'` is set; keep the Windows firewall restricted to Docker traffic because the authenticated endpoint then listens beyond loopback. Start the stack with `docker compose --env-file .env.docker up -d --build`. The backend API is at `http://localhost:8080`; Langfuse is currently at `http://localhost:13000` (`LANGFUSE_PORT=13000` in `.env.docker`; the example defaults to `3000`). The backend connects over the private Compose network using `LANGFUSE_BASE_URL=http://langfuse-web:3000` and `POB_AGENT_LANGFUSE_ALLOWED_HOSTS=langfuse-web`; the host port does not change the container port. See the Korean request example below. The catalog and Lua handler extension points are documented in [Tool Catalog](docs/tools/catalog.md).

The project does not claim complete support for every game mechanism. When PoB does not expose a value or source, the extension must report that limitation instead of guessing.

Planned next capabilities:

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

- 구현된 32개 도구 계약은 별도 Streamable HTTP MCP 컨테이너가 제공합니다. 백엔드 컨테이너는 Compose 내부 네트워크로 MCP 서버에 연결합니다. 이름, 스키마, 목적/사용 조건, 부작용, 타임아웃, 재시도, 오류 코드는 `agent/tool_catalog.py`에서 관리하며 `python tools/render_mcp_tool_catalog.py`로 카탈로그 계약 섹션을 갱신합니다.
- 현재 PoB 컨텍스트의 활성 Spec, Skill Set, Item Set, Config, 젬, 링크, 조건과 `snapshotRevision`을 캡처할 수 있는 읽기 전용 in-process Dispatcher가 있습니다.
- PoB 도구 호출은 Windows 호스트의 인증된 Lua endpoint를 사용하며 MCP 컨테이너는 `host.docker.internal`을 통해 접근합니다. 지식·별칭·외부검색·스냅샷 비교는 MCP 컨테이너에서 실행됩니다.
- mutation Tool은 목록에는 표시되지만 `MUTATION_NOT_PERSISTENT`를 반환하고, 프로덕션 MCP 경로는 headless XML adapter로 대체 실행하지 않습니다.
- 근거를 포함하는 결과는 가능한 경우 PoB 경로, trace 데이터, 버전 메타데이터, 불확실성, Evidence Graph를 포함합니다.

`.env.docker.example`을 `.env.docker`로 복사해 `CHANGE_ME` 값을 교체하고, 설정된 빌드 폴더에 PoB XML을 둔 뒤 `POB_ENDPOINT_HOST_PATH`를 PoB endpoint 폴더로 설정하세요. `powershell -ExecutionPolicy Bypass -File tools/install_live_control.ps1`로 Lua 모듈을 설치/갱신합니다. PowerShell에서 `$env:POB_AGENT_BIND_HOST = '0.0.0.0'`을 설정한 세션에서 PoB를 실행해야 Docker가 endpoint에 접근할 수 있습니다. 인증 endpoint가 loopback 밖에서 대기하므로 Windows 방화벽은 Docker 트래픽만 허용하도록 제한하세요. `docker compose --env-file .env.docker up -d --build`로 전체 스택을 시작합니다. backend API는 `http://localhost:8080`, 현재 Langfuse는 `http://localhost:13000`입니다(`.env.docker`의 `LANGFUSE_PORT=13000`; 예제 기본값은 `3000`). 백엔드는 Compose 내부 네트워크에서 `LANGFUSE_BASE_URL=http://langfuse-web:3000`, `POB_AGENT_LANGFUSE_ALLOWED_HOSTS=langfuse-web`을 사용합니다. 호스트 공개 포트를 바꿔도 컨테이너 내부 포트는 `3000`입니다. 요청 예시는 아래와 같습니다. 도구 추가 방법은 [도구 카탈로그](docs/tools/catalog.md)를 참고하세요.

```powershell
$token = (Select-String -Path .env.docker -Pattern '^POB_AGENT_API_TOKEN=').Line.Split('=', 2)[1]
$headers = @{ Authorization = "Bearer $token" }
$body = @{ build_file = "my-build.xml"; question = "현재 가장 높은 DPS 스킬은 뭐야?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/run -Headers $headers -ContentType "application/json" -Body $body
```

이 프로젝트는 모든 게임 메커니즘을 완전히 지원한다고 주장하지 않습니다. PoB가 값이나 출처를 노출하지 않으면 추측하지 않고 해당 제한을 보고해야 합니다.

다음 목표:

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
