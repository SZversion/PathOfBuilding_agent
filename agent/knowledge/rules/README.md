# PoE 1 Game Rules

이 디렉터리는 PoB의 현재 빌드 계산값과 구분되는 **게임 시스템 규칙**을 저장합니다.

## 작성 규칙

- 숫자·제한·패널티는 반드시 `patchRange`, `sources`, `verification`을 기록합니다.
- PoB에서 직접 계산되는 현재 캐릭터 값은 이 파일에 복사하지 않고 PoB Tool에서 조회합니다.
- `draft` 규칙은 Agent가 최종 답변의 단독 근거로 사용하지 않습니다.
- 패치 변경이 의심되면 기존 규칙을 덮어쓰지 말고 패치별 항목을 추가합니다.

## 기본 분류

- `damage-type`: 물리, 화염, 냉기, 번개, 카오스
- `delivery`: hit, damage-over-time
- `ailment`: damaging/non-damaging ailment
- `campaign`: 액트 진행에 따른 캐릭터 규칙
- `curse`: 저주 제한과 저주 상호작용

