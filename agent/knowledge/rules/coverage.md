# PoE 1 기본 규칙 커버리지

이 문서는 규칙 수집의 누락을 줄이기 위한 체크리스트입니다. 실제 규칙은 검증 후 `poe1-core-rules.json` 또는 분야별 파일로 옮깁니다.

## P0 — PoB 답변에 바로 필요한 영역

### 피해 계산

- [ ] 증가(`increased`)와 배율(`more/less`)
- [ ] 추가 피해(`added`)와 `gain as extra`의 차이
- [ ] 피해 전환(`conversion`) 순서
- [ ] 저항 감소·노출·저주·관통의 차이와 적용 순서
- [ ] Hit와 DoT에 적용되는 modifier 차이
- [ ] 무기·근접·투사체·주문·지역 피해 태그의 적용 범위

출처: [Damage](https://www.poewiki.net/wiki/Damage), [Resistance penetration](https://www.poewiki.net/wiki/Resistance_penetration)

### 스킬과 젬

- [ ] Attack / Spell / Warcry / Aura / Curse 태그
- [ ] Projectile / AoE / Duration / Channelling / Trigger 태그
- [ ] Totem·Trap·Mine·Brand 같은 proxy의 의미
- [ ] Triggered skill은 일반적인 `use a skill` 조건과 다르게 처리되는 규칙
- [ ] Support Gem이 링크된 스킬에만 적용되는 규칙

출처: [Skill](https://www.poewiki.net/wiki/Skill), [Gem tag](https://www.poewiki.net/wiki/Gem_tag)

### 방어와 생존

- [ ] Armour, Evasion, Energy Shield, Ward
- [ ] Block, Spell Suppression, Dodge의 적용 대상
- [ ] Accuracy와 Evasion의 관계
- [ ] 저항 상한과 실제 저항 계산
- [ ] 피해 완화와 피해 회피의 차이

출처: [Defences](https://www.poewiki.net/wiki/Defences), [Evasion](https://www.poewiki.net/wiki/Evasion), [Spell suppression](https://www.poewiki.net/wiki/Spell_suppression)

### 저주·상태이상

- [ ] Hex와 Mark의 차이
- [ ] 저주 제한과 추가 저주 적용 순서
- [ ] Ignite / Bleed / Poison의 발생 조건과 DoT 계산
- [ ] Shock / Chill / Freeze / Scorch / Brittle / Sap의 효과와 상한
- [ ] 상태이상 효과와 상태이상 피해 modifier의 차이

출처: [Ailment](https://www.poewiki.net/wiki/Ailment), [Curse](https://www.poewiki.net/wiki/Curse)

## P1 — 자주 사용되는 확장 영역

- [ ] Critical Strike Chance / Multiplier / Lucky / Unlucky
- [ ] Accuracy, Critical Strike, 공격 재판정
- [ ] Life·Mana·Energy Shield의 회복, 재생, 흡수, Recoup
- [ ] Reservation과 Cost, Reservation Efficiency
- [ ] Power / Frenzy / Endurance Charge
- [ ] Projectile의 추가 발사체, 분열, 관통, Chain, Fork
- [ ] 명중 횟수와 단일 대상 중첩(일명 shotgun) 규칙
- [ ] Buff / Debuff / Aura / Stance / Guard Skill

출처: [Receiving damage](https://www.poewiki.net/wiki/Receiving_Damage), [List of skill gems by gem tag](https://www.poewiki.net/wiki/List_of_active_skill_gems_by_gem_tag)

## P2 — 이후 수집할 영역

- [ ] Attributes와 요구 조건
- [ ] Level·Experience·Ascendancy·Campaign 보상
- [ ] Map modifier와 몬스터 modifier
- [ ] Minion·Totem·Trap·Mine의 세부 소유권 규칙
- [ ] 리그 메커니즘별 전용 규칙

## 수집 원칙

PoE Wiki는 개념 설명과 교차참조에 사용하고, 현재 수치·스킬·아이템 값은 PoB 데이터와 패치 노트로 대조합니다. Wiki 내용을 그대로 복사하지 않고, Agent가 판단에 필요한 규칙만 짧은 구조화 레코드로 저장합니다.

