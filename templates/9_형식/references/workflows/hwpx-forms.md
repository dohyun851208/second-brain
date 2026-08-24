# HWP/HWPX 양식 작성

일반 HWP/HWPX 작업의 정본은 Kordoc이다. 직접 XML 편집, 한컴 COM 변환, pack/unpack, 다른 HWPX 생성기로 자동 우회하지 않는다.
Kordoc이 안전하게 처리하지 못하면 원본을 그대로 두고 실패 이유와 필요한 다음 입력만 알린다. 지원되는 암호 문서는 `--password`로 열 수 있지만 암호를 응답·로그에 남기지 않는다.

## 1. 먼저 분석

- 읽기·텍스트 구조 확인: `npx -y kordoc@^4 원본.hwp -o 원본.md`
- HWPX 필드 확인: `npx -y kordoc@^4 fill 양식.hwpx --dry-run`
- 쓰기 전에 양식 전체의 필수·선택 항목과 이미지 칸·별도 첨부·서명·날인란을 확인한다. 작업 중 뒤늦게 발견해도 같은 승인·배치 규칙을 적용한다.
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
- 승인 이미지 삽입이 아닌 **양식 채우기**에서 Kordoc으로 안전하게 처리할 수 없는 `.hwp`는 변환하지 말고 HWPX 제공이 필요하다고 알린다.

### 새 문서

볼트에 승인된 양식이 없고 새 문서 생성이 필요한 경우에만 Kordoc `generate`를 사용한다.

```powershell
npx -y kordoc@^4 lint 초안.md --munche
npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서

# 마크다운의 ![](사진.png)를 실제 이미지로 임베드할 때
npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서 --image-dir ".\images"
```

- `lint`는 md/txt 원고에만 사용한다. 보고서·계획서는 `--munche`를 붙이고, 기안문·통지·회의록은 문체 관행이 달라 기본 lint만 쓴다.
- 새 문서의 마크다운 이미지는 `--image-dir`로 Kordoc이 직접 임베드한다. 이 경우 `place_image.py`를 쓰지 않는다.

## 3. 기존 문서의 승인 이미지 지정 위치 배치

Kordoc `generate --image-dir`로 새 문서를 만드는 경우가 아니라, 서명·도장·신분증·통장사본·증명사진·일반 사진을 **기존 HWP/HWPX의 지정 위치**에 넣어야 할 때만 텍스트 작업을 끝낸 뒤 마지막에 배치한다. 개인정보 자산 사용 승인은 `7_개인정보이미지/_안내.md`를 따른다.
특정 문서와 이미지를 사용자가 직접 지정했다면 그 범위는 승인된 것으로 본다. 실행 여부는 최초 요청 문구가 아니라 최종 제출 요건과 승인 상태로 결정한다. 필수 개인정보 이미지·서명·날인란을 발견했지만 승인이 없으면 사용할 자산과 용도를 한 번 확인하고, 승인 뒤 같은 작업을 계속한다. 선택·모호한 이미지란은 자동 삽입하지 않으며 필수란을 말없이 비운 채 완성본으로 보고하지 않는다. 별도 파일 첨부 요구는 문서 안 삽입으로 대체하지 않는다.

정본은 `scripts/place_image.py`다. 호환용 `place_signature.py`, Kordoc `seal`, 내부 모듈 `hwp_to_hwpx.py`·`insert_signature_hwpx.py`를 새 작업에서 직접 호출하지 않는다.

필요 조건:

- 입력: `.hwp` 또는 `.hwpx`, 이미지 `.png`·`.jpg`·`.jpeg`·`.bmp` (`.hwp`는 이 작업 안에서만 임시 HWPX로 한 번 변환)
- 환경: Windows, 한컴, Python `pywin32`, PyMuPDF
- 출력: 원본과 다른 `.hwpx` 경로. HWP 입력도 최종본은 `*_완성본.hwpx`

```powershell
# 위치 조사
py -3 scripts/place_image.py "신청서.hwpx" "통장사본.jpg" `
  --report --find "통장사본" --find "(서명)"

# 이름 끝에서 시작하도록 실측 배치
py -3 scripts/place_image.py "신청서.hwpx" "서명.png" `
  --output "신청서_완성본.hwpx" `
  --anchor-para "신청인은 위 내용에 동의합니다" `
  --after-text "홍길동" --width-mm 24

# 일반 이미지: 조사한 좌·상단에 비율을 유지해 배치
py -3 scripts/place_image.py "신청서.hwpx" "통장사본.jpg" `
  --output "신청서_완성본.hwpx" `
  --anchor-para "첨부 이미지" `
  --target-left-mm 25 --target-top-mm 120 --width-mm 80

# HWP 입력: 내부에서 임시 HWPX로 한 번 변환한 뒤 같은 실측 배치 실행
py -3 scripts/place_image.py "신청서.hwp" "증명사진.jpg" `
  --output "신청서_완성본.hwpx" `
  --anchor-para "사진" `
  --target-left-mm 150 --target-top-mm 25 --width-mm 30
```

- `--anchor-para`는 목표 줄보다 위에 있는 고유 문단을 사용한다.
- `--after-text`는 글자 옆 서명·도장에 사용한다. 일반 이미지는 `--report`와 렌더를 확인한 뒤 `--target-left-mm` + `--target-top-mm`(또는 `--target-bottom-mm`)으로 명시 배치한다.
- `hwp_to_hwpx.py`와 `insert_signature_hwpx.py`는 내부 모듈이므로 직접 실행하지 않는다.
- 스크립트는 이미지 원본 비율을 유지하고, 탐침 렌더 → 실측 → 역산 → 결과 렌더 검증과 페이지 경계 검사를 수행한다.
- 여러 이미지는 검증된 앞 단계 HWPX를 다음 단계 입력으로 순차 처리하고 최종본을 만든 뒤 중간본을 정리한다.
- 기존 출력은 기본적으로 덮어쓰지 않는다. 사용자가 교체를 명시한 경우에만 `--overwrite`를 쓴다.
- HWP 원본은 절대 다시 저장하지 않고 임시 변환본도 정리한다. 최종 HWPX를 COM으로 다시 저장하지 않는다.
- 변환·배치에 실패하거나 요구 환경이 없으면 원본과 기존 출력을 그대로 두고 알린다. 서명은 Kordoc `seal`로, 일반 이미지는 임의 도구로 우회하지 않는다.
- 성공 뒤 `7_개인정보이미지/사용기록.md`에 날짜·자산 ID·산출물·용도만 기록한다.

## 4. 검증

- 일반 HWP/HWPX: `npx -y kordoc@^4 validate 결과.hwpx`와 핵심 값 확인. 새 공문 원고는 생성 전 lint 경고도 확인.
- 승인 이미지: `place_image.py`의 XML 구조 검사와 한컴 렌더 실측 결과를 확인.
- 원본 대비 페이지·표·핵심 문구가 바뀌지 않았는지 확인한다.
- 임시 렌더와 작업 파일은 정리하고 최종 산출물만 남긴다.
