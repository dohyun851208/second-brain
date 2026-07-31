# HWP/HWPX 양식 작성

일반 HWP/HWPX 작업의 정본은 Kordoc이다. 직접 XML 편집, 한컴 COM 변환, pack/unpack, 다른 HWPX 생성기로 자동 우회하지 않는다.
Kordoc이 안전하게 처리하지 못하면 원본을 그대로 두고 실패 이유와 필요한 다음 입력만 알린다.

## 1. 먼저 분석

- 읽기·텍스트 구조 확인: `npx -y kordoc@^4 원본.hwp -o 원본.md`
- HWPX 필드 확인: `npx -y kordoc@^4 fill 양식.hwpx --dry-run`
- 원본은 항상 보존하고 출력 경로를 별도로 지정한다.

## 2. 텍스트 수정·양식 채우기

### 기존 내용 수정

```powershell
npx -y kordoc@^4 patch 원본.hwp 편집.md -o 원본_완성본.hwp
npx -y kordoc@^4 patch 원본.hwpx 편집.md -o 원본_완성본.hwpx
```

`patch`는 원본 포맷을 유지한다. 내장 재검증을 끄는 `--no-verify`는 사용하지 않는다.

### HWPX 양식 채우기

```powershell
npx -y kordoc@^4 fill 양식.hwpx --dry-run
npx -y kordoc@^4 fill 양식.hwpx -j 값.json -o 양식_완성본.hwpx --require-unique
```

- `fill`의 서식 보존 경로는 HWPX용이다. `.hwp` 양식에 직행시키지 않는다.
- 같은 라벨이 여러 곳이면 `--require-unique` 또는 배열 값을 사용해 오입력을 막는다.
- 주민번호·계좌 등 민감 값은 응답이나 로그에 다시 쓰지 않는다.
- Kordoc으로 안전하게 채울 수 없는 `.hwp` 양식은 변환하지 말고 HWPX 제공이 필요하다고 알린다.

### 새 문서

볼트에 승인된 양식이 없고 새 문서 생성이 필요한 경우에만 Kordoc `generate`를 사용한다.

```powershell
npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서
```

## 3. 서명·도장 배치

서명·도장은 텍스트 작업을 끝낸 HWPX에 마지막으로 넣는다. 사용 승인은 `7_개인정보이미지/_안내.md`를 따른다.
특정 문서와 자산을 사용자가 직접 지정했다면 그 범위는 승인된 것으로 본다.

정본은 `scripts/place_signature.py`다. Kordoc `seal`이나 내부 모듈 `insert_signature_hwpx.py`를 직접 호출하지 않는다.

필요 조건:

- 입력: `.hwpx`
- 환경: Windows, 한컴, Python `pywin32`, PyMuPDF
- 출력: 원본과 다른 `.hwpx` 경로

```powershell
# 위치 조사
py -3 scripts/place_signature.py "신청서.hwpx" "서명.png" `
  --report --find "홍길동" --find "(서명)"

# 이름 끝에서 시작하도록 실측 배치
py -3 scripts/place_signature.py "신청서.hwpx" "서명.png" `
  --output "신청서_완성본.hwpx" `
  --anchor-para "신청인은 위 내용에 동의합니다" `
  --after-text "홍길동" --width-mm 24
```

- `--anchor-para`는 목표 줄보다 위에 있는 고유 문단을 사용한다.
- 스크립트는 서명 원본 비율을 유지하고, 탐침 렌더 → 실측 → 역산 → 결과 렌더 검증을 수행한다.
- 기존 출력은 기본적으로 덮어쓰지 않는다. 사용자가 교체를 명시한 경우에만 `--overwrite`를 쓴다.
- 실패하거나 요구 환경이 없으면 원본과 기존 출력을 그대로 두고 알린다. Kordoc `seal`로 우회하지 않는다.
- 성공 뒤 `7_개인정보이미지/사용기록.md`에 날짜·자산 ID·산출물·용도만 기록한다.

## 4. 검증

- 일반 HWP/HWPX: `npx -y kordoc@^4 validate 결과.hwpx`와 핵심 값 확인.
- 서명·도장: `place_signature.py`의 XML 구조 검사와 한컴 렌더 실측 결과를 확인.
- 원본 대비 페이지·표·핵심 문구가 바뀌지 않았는지 확인한다.
- 임시 렌더와 작업 파일은 정리하고 최종 산출물만 남긴다.
