# kordoc 사용법

한국 문서 파싱·편집 엔진 ([chrisryugj/kordoc](https://github.com/chrisryugj/kordoc), MIT, npm).
HWP 3.x/5.x·HWPX·HWPML·PDF·DOCX·XLS/XLSX → Markdown, 서식 보존 패치, 문서 비교, 도장 배치.
한컴 오피스·COM 불필요, 로컬 실행이라 문서가 외부로 나가지 않는다 (학생 개인정보 안전).

## 실행

```powershell
npx -y kordoc@^3 <명령> ...
```

Node 18+ 필요. 첫 호출만 다운로드로 느리고 이후 캐시. `ECOMPROMISED`·`MODULE_NOT_FOUND` 에러가 나면
`$env:LOCALAPPDATA\npm-cache\_npx\` 아래 해당 캐시 폴더를 지우고 재시도한다.

상시 사용 환경이면 `npx -y kordoc@^3 setup`(대화형 마법사)으로 MCP 서버 등록도 가능 — 콜드스타트가
없어지고 MCP 전용 기능(`compare_documents`, fill의 `require_unique`·`formats`·`mask_values`)을 쓸 수 있다.

## 명령 치트시트

| 작업 | 명령 |
|---|---|
| 문서 → Markdown | `npx -y kordoc@^3 문서.hwp -o 문서.md` (hwpx·pdf·docx·xls 동일) |
| 페이지 범위 | `-p 1-3` 또는 `-p 1,3,5` |
| 구조화 JSON | `--format json` (blocks+metadata) |
| PDF 수식 OCR | `--formula-ocr` (첫 사용 시 모델 ~155MB 자동 다운로드, `check-formula-models`로 상태 확인) |
| 서식 필드 목록 | `npx -y kordoc@^3 fill 서식.hwpx --dry-run` |
| 서식 채우기 | `npx -y kordoc@^3 fill 서식.hwpx -j 값.json -o 결과.hwpx` |
| 기존 문서 내용 수정 | `npx -y kordoc@^3 patch 원본.hwpx 편집.md -o 결과.hwpx` (`.hwp`도 가능 — 원본 포맷 유지) |
| 문서 비교 | MCP `compare_documents` (CLI엔 없음 — 양쪽을 md로 파싱해 diff해도 됨) |
| 공문서 생성 (폴백) | `npx -y kordoc@^3 generate 초안.md -o 결과.hwpx --preset 보고서` |
| 구조 검증 | `npx -y kordoc@^3 validate 결과.hwpx` |
| 도장/서명 배치 | `npx -y kordoc@^3 seal 문서.hwpx --image 도장.png --anchor "(인)" -o 결과.hwpx` |
| 조판 미리보기 | `npx -y kordoc@^3 render 문서.hwpx -o 미리보기.svg` (생성/패치본은 `--reflow`, 형광펜 `--highlight 검색어`) |

## 읽기 (파싱)

- 병합·중첩 표는 GFM으로 표현이 안 되므로 HTML `<table>`(colspan/rowspan)로 나온다 — 그대로 다룬다.
- 수식은 `$...$` / `$$...$$` LaTeX.
- PDF는 텍스트층 품질 신호를 계산한다 — `needsOcr`이면 스캔/손상 PDF라는 뜻 (본문 텍스트 OCR은 미내장, 사용자에게 알린다). 단 **수식만은** `--formula-ocr`로 OCR 가능.
- PDF 머리글/바닥글은 자동 제거된다 (`--no-header-footer`로 끔). HWP5 러닝 헤더가 페이지마다 반복되면 `--dedupe-headers` (기본 off — 붙임별 재번호가 오삭제될 수 있어 주의).
- 문서 속 이미지는 출력 폴더의 `images/`에 `image_001.png`식으로 저장된다. **함정 둘**: ① `-o` 단일 출력은 md 링크에 `images/` 접두사가 안 붙어 링크가 깨진다 (`-d` 모드만 붙음) ② 파일명 번호가 문서마다 1부터라 여러 문서를 같은 폴더로 파싱하면 서로 덮어쓴다 → 문서별 이미지 폴더로 분리하고 링크를 보정한다. HWP5는 `--inline-images`로 base64 인라인도 가능 (별도 파일 없음 — 타 포맷은 옵션 무시).
- 여러 파일은 `-d 디렉토리/` 일괄 모드 — 단 출력명이 확장자를 뗀 `수업안.md`식이라 `수업안.hwp`·`수업안.pdf`가 공존하면 충돌한다. 출력명을 통제하려면 파일별 `-o`.

## patch (서식 보존 편집)

① 원본을 md로 파싱 → ② md에서 내용만 수정 (구조 이동·삭제 최소화) → ③ `patch 원본 편집.md -o 수정본`.
원본의 글꼴·표·개체·조판을 보존한 채 텍스트 변경만 반영한다.

- **원본 포맷 유지**: 포맷을 감지해 `.hwp`는 바이너리 in-place 패치(`patchHwp`) → `.hwp` 출력, `.hwpx`는 ZIP 패치 → `.hwpx` 출력. `.hwp` 내용 수정에 변환이 필요 없다.
- 패치 후 재파싱 자동 검증이 내장돼 있다 (`--no-verify`로 생략 가능 — 생략하지 않는다).
- 문단 안 강제 줄바꿈은 편집 md에 명시적 `<br>` (에디터 soft-wrap은 수정으로 안 침).
- 원본은 절대 덮어쓰지 않는다 — `-o` 필수.

## fill (서식 채우기)

0. **HWPX 전용으로 쓴다.** 스타일 보존(`hwpx-preserve`)은 원본 ZIP 직접 수정이라 HWPX에만 작동한다.
   `.hwp`를 넣으면 CLI는 조용히 `hwpx` 모드로 전환("HWPX가 아니므로 hwpx 모드로 전환합니다") —
   파싱한 내용을 새 HWPX 표로 **재구성**하므로 병합·열너비가 깨진다 (실측 확인). MCP `fill_form`도
   `output_format: hwpx`면 동일한 재구성 경로다. `.hwp` 채우기는 한컴 COM으로 `.hwpx` 1회 변환 후 fill.
1. `--dry-run`으로 라벨 목록 먼저 파악.
2. 값은 `-j 값.json` 권장 (`-f 'k=v'`는 셸 히스토리에 값 노출). 다중줄은 JSON 문자열 안 `\n`.
3. 같은 라벨이 2곳 이상이면 **모든 칸에 채운다** — MCP `fill_form`은 `require_unique: true`로 2곳+ 매칭되는 스칼라 라벨을 거부(rejected 보고)시킬 수 있다(배열 값은 예외). CLI엔 이 가드가 없으니 값을 배열로 주거나 어느 칸인지 확인 후 채운다.
4. 날짜·전화·주민등록번호 등 칸 모양 변환(`yyyy.mm.dd`, `###-####-####` 숫자 마스크)은 MCP `fill_form`의 `formats` 파라미터가 지원한다.
5. 기본 출력은 원본 글꼴·정렬 보존(`hwpx-preserve`).
6. 주민번호·계좌 등 채운 값은 응답에 되풀이하지 않는다. 채움 결과 확인이 필요하면 MCP `fill_form`의 `mask_values` 마스킹 verify를 쓴다.

## seal (도장 배치)

앵커 문구("(인)" 등) 위/옆에 이미지를 글 앞 부유로 얹는다 — 표·페이지가 밀리지 않음.
같은 앵커 여럿이면 `-n <0-based>`, 위치 보정 `--dx`/`--dy`(mm), 크기 `--size-mm`. 투명 PNG 권장. HWPX 전용.
중첩표·글상자·복잡 rowSpan은 근사 배치(warnings 고지) — 배치 후 `render --reflow`로 확인.

## generate (볼트 템플릿이 없을 때만)

- 프리셋: `기안문`·`보고서`·`계획서`·`통지`·`회의록`. 번호 목록이 공문서 항목부호 8단계로 자동 변환, 함초롬바탕 표준 서식.
- 표는 GFM 파이프표, display 수식 `$$...$$`은 네이티브 `<hp:equation>`.
- ` ```chart ` 펜스 → 한컴 네이티브 차트 (type/cat/계열 라인, 펜스 안 주석 금지 — 값으로 오인됨).
- 생성 후 반드시 `validate` 통과 확인.

## 서식 프로필 (기관 양식의 표 서식 재현)

레퍼런스 hwpx에서 표의 시각 서식(괘선·음영·열 너비·셀 글꼴)만 JSON으로 추출해 generate 때 재현한다.
내용·개인정보 없이 서식만 담기므로, 학교 양식을 프로필 JSON으로 `9_형식/templates/`에 보관·재사용할 수 있다.
CLI 옵션은 아직 없고 라이브러리 API만 있다 — `.mjs` 스크립트로 실행 (프리셋과 병용 가능: 문단 서식은 프리셋, 표 서식은 프로필):

```js
import { hwpxToProfile, markdownToHwpx } from "kordoc"
import { readFileSync, writeFileSync } from "node:fs"
// ① 추출 (양식당 1회): 학교 양식 hwpx → 프로필 JSON
writeFileSync("양식.profile.json", JSON.stringify(await hwpxToProfile(readFileSync("학교양식.hwpx"))))
// ② 적용: md의 N번째 표에 프로필의 N번째 표 서식이 입혀진다 (행·열 수가 일치할 때만 — 불일치 시 무시+경고)
const profile = JSON.parse(readFileSync("양식.profile.json", "utf8"))
writeFileSync("결과.hwpx", await markdownToHwpx(readFileSync("초안.md", "utf8"), { profile }))
```

## 함정

- 암호 보호·DRM 배포본은 파싱 불가 → 이때만 한컴 COM 폴백 (`scripts/convert_hwp.py`).
- `.hwp`(바이너리)와 `.hwpx`(ZIP/XML)는 다른 포맷. fill/generate 산출물은 항상 HWPX지만 **patch만은 원본 포맷을 유지**한다 (`.hwp`→`.hwp`).
- 표가 깨져 보이는 PDF는 대부분 스캔본/텍스트층 손상 — 품질 신호를 근거로 설명한다.
