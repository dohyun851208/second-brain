# kordoc 사용법

한국 문서 파싱·편집 엔진 ([chrisryugj/kordoc](https://github.com/chrisryugj/kordoc), MIT, npm).
HWP 3.x/5.x·HWPX·HWPML·PDF·DOCX·XLS/XLSX·PNG/JPG/WebP → Markdown, 로컬 한글 OCR, 실제 페이지 복원·페이지별 JSON, 서식 보존 패치·채우기, 문서 비교, 개인정보 마스킹(redact), 공문 표기법·개조식 문체 검수(lint), 표 서식 프로필.
일반 작업에는 한컴 오피스·COM이 불필요하고, 로컬 실행이라 문서가 외부로 나가지 않는다 (학생 개인정보 안전). 승인된 이미지 배치 작업에 `.hwp`가 입력된 경우만 `9_형식/scripts/place_image.py`가 한컴 COM으로 임시 HWPX를 만든다.

> 호환 범위: `@^4` · 마지막 공식 소스/CLI 검증판: **4.24.47 (2026-11-06)**. Kordoc 엔진 소스는 이 스킬에 복제하지 않고 npm의 호환 범위로 실행한다.

## 실행

```powershell
npx -y kordoc@^4 <명령> ...
```

Node.js 20 이상 필요. 첫 호출만 다운로드로 느리고 이후 캐시. `ECOMPROMISED`·`MODULE_NOT_FOUND` 에러가 나면
`$env:LOCALAPPDATA\npm-cache\_npx\` 아래 해당 캐시 폴더를 지우고 재시도한다.

상시 사용 환경이면 `npx -y kordoc@^4 setup`(대화형 마법사)으로 MCP 서버 등록도 가능 — 콜드스타트가
없어지고 문서 비교·세분 파싱·표 분류 등 MCP 도구 22종을 쓸 수 있다(CLI와 겹치는 기능 포함).
마법사는 Claude Code/Desktop·Cursor·Codex 등 설치된 클라이언트를 감지한다. Codex에서는
`codex mcp add kordoc -- npx -y kordoc@^4 mcp`로 수동 등록하면 CLI와 같은 호환 범위를 유지한다. 자동 setup의 등록 명령은 범위가 고정되지 않을 수 있으므로 등록 결과를 확인한다. Second Brain의 정본 경로는 여전히 CLI이며 MCP는 선택이다.
**3.x에서 MCP 전용이던 fill 가드(`--require-unique`·`--formats`·`--mask`)와 서식 프로필(`profile`)은 4.x부터 CLI에 편입돼 MCP 없이도 쓴다.**

폐쇄망에서는 미리 모델을 `models --export/--import`로 반입하고 `KORDOC_OFFLINE=1`을 사용한다. MCP가 읽고 쓸 수 있는 범위를 볼트로 제한하려면 `KORDOC_ROOT=<볼트 경로>`를 설정한다. 두 환경변수는 opt-in이며, OCR 모델이 없는 상태에서 offline을 켜면 다운로드 대신 실패한다.

### 버전 정책

- `@^4`는 실행할 때 최신 4.x를 사용하고 5.x로는 넘어가지 않는다.
- 작업 재현성을 위해 파싱 배치 시작 시 `npx -y kordoc@^4 --version`을 한 번 확인하고 각 파싱본의 `도구-버전`에 기록한다.
- "세컨드브레인 상태/업그레이드" 때만 `npm view kordoc version`으로 전체 최신판을 확인한다. 최신판이 5.x 이상이어도 자동 전환하지 않고 공식 변경 기록과 대표 문서 테스트 후 지침·호환 범위·시스템 버전을 함께 올린다.
- 같은 메이저의 새 기능을 지침에 반영할 때도 공식 저장소의 마지막 검증 태그 이후 변경을 임시 clone에서 비교하고, 이 문서의 마지막 검증판과 시스템 버전을 함께 올린다. upstream 소스 자체를 스킬 `templates/`(볼트 밖)에 복사하지 않는다.

### 4.24.47까지 반영한 변경점

- 4.5: `generate --image-dir`, 용지·방향·다단·머리말·꼬리말.
- 4.6: PDF `--no-tables`, 이미지 많은 JSON의 `--image-refs`.
- 4.7~4.8: HWP/HWPX 실제 페이지 경계, `metadata.pageMode`, JSON `pages[]`, 폐쇄망 모델 반입.
- 4.9: AI 흔적 lint와 `lint --munche`; 4.9.2의 여러 줄 `<right>` 출처행·캡션 조판 수정은 엔진이 자동 적용한다.
- 4.10: 파싱 실패 JSON 계약(`success:false`+`code`)이 전 포맷 stdout으로 확장, `images/manifest.json`, `.hwp` patch의 soft-wrap 손상 수정.
- 4.11~4.12: HWP3 기호·한자·글상자 텍스트 유실 수정, 굵게·밑줄 문단의 한컴 PUA 잔존 수정(전 포맷), 법제처 별지서식 PDF 표 복원, 결재란 "(인)" 복원, 기입 빈칸 "년 월 일" 보존.
- 4.12.1~4.13: `lint` 19룰(금액 한글 병기·물결표·두음법칙·외래어·차별 표현·"끝." 누락·하이픈 날짜), 공문 생성 v5 엔진(서울 실결재 실측 위계·두문표·결문표·요약박스), `render`의 HTML/PNG/JPEG/PDF·쪽 지정·`.hwp` 지원, `tables`·`crop`, 여러 쪽 표의 쪽 경계 분할.
- 4.14: 프리셋 `업무보고`(ministry), 표지 취급 표시 `--cover-label`, 표 셀 테두리 색 지정. Codex MCP 등록은 4.1대(2026-07)부터 있었고 이 판에서 확인했다.
- 4.14.2~4.15.6: 생성 조판 정리(항목 둘째 줄 정렬·어절 줄바꿈·날짜 묶음 빈칸)와 PDF 표·글·OCR 정확도 개선은 엔진이 자동 적용한다. 절차에 닿는 것은 실패 코드 `FILE_NOT_FOUND`(4.15.5, 아래 "실패 계약")와 redact 기본 룰 확대(4.14.3, 아래 "redact")뿐이다.
- 4.15.7: `-o` 출력의 그림 링크에 `images/`가 붙는다(#94 — 링크를 고치는 쪽은 옛 모양과 함께 처리), `generate --image-dir`가 한글 파일명 그림도 넣는다(#95), 암호 HWPX가 Windows에서 멈추던 문제 수정(#93), HWP5 표·중첩 표 보존 향상, 양식 선택 상자·라디오 단추를 ☐·☑로 읽는다. 빈 서식의 누름틀 안내문은 `--include-field-placeholders`를 켤 때만 나온다(#92 — 칸 용도가 안내문뿐인 양식을 분석할 때). HWP5 칸 속 중첩 표의 `patch`는 여전히 미지원이다(아래 "함정").
- 4.16: 추출 그림·manifest가 `images/<출력 stem>/`으로 분리된다. 기존 파서의 `images/` 전체 개명은 금지하고 아래 문서별 폴더 규칙을 따른다.
- 4.17: 기본 파싱은 보이지 않는 틀 표를 글로 푼다. 편집용은 반드시 `--keep-layout-tables`, 빈 입력 열은 `--keep-empty-cols`로 보존한다.
- 4.18~4.22: 표·셀 줄바꿈과 빈칸 patch 개선, `fill --dry-run -j`의 좌표 계획·`overwrittenBy`, HWPX 문단 추가·삭제 patch, 문서 직접 lint·`--gate`, 선택 OCR 모델·줄 신뢰도 지원.
- 4.23~4.24: `generate --template` 견본 생성·`--pack` 기관팩, HWP→HWPX 변환, HWP5 fill/seal 입력, 부분 patch의 `.rewrite.hwpx` 대체본. 새 기능 지원과 볼트의 기본 작업 경로는 구별한다(아래 제한 참조).
- 4.24.47: DOCX 저장 쪽 나눔 수가 문서 속성 Pages와 일치할 때만 `metadata.pageMode: "layout"`·쪽별 결과·`-p`를 적용한다. 쪽 번호 없는 DOCX에 임의 쪽 번호를 붙이지 않는다. OCR 표 머리·숫자·두 행 표 인식 개선도 포함한다.

## 명령 치트시트

| 작업 | 명령 |
|---|---|
| 문서 → Markdown | `npx -y kordoc@^4 문서.hwp -o 문서.md` (hwpx·pdf·docx·xls·이미지 동일) |
| 파싱 실패 | stdout에 `{"success":false,"code":"…"}` JSON + exit 1, 출력 파일 미생성 — `code`로 분기 (아래 "실패 계약") |
| 페이지 범위 | `-p 1-3` 또는 `-p 1,3,5` |
| 구조화 JSON | `--format json` (blocks+metadata+쪽별 `pages[]`, `metadata.pageMode`) · `--format chunks` (RAG용 위계 청크) |
| 스캔 PDF 본문 OCR | `--ocr` (필요 페이지만 로컬 PP-OCRv5, 첫 사용 시 모델 ~18MB) · `--ocr-force` (전 페이지 강제) |
| PDF 표 오탐 회피 | `--no-tables` (2단 시험지 등에서 테두리 박스가 표로 오인돼 읽기 순서가 뒤집힐 때) |
| 이미지 OCR | PNG·JPG·WebP 파일을 직접 입력 — OCR 자동 적용 |
| 이미지 많은 JSON | `--image-refs` (`--format json`의 이미지 바이트 대신 저장 경로만 기록, `-o`/`-d` 필요) |
| PDF 수식 OCR | `--formula-ocr` (첫 사용 시 모델 ~155MB 자동 다운로드, `check-formula-models`로 상태 확인) |
| 암호 문서 열기 | `--password <암호>` (HWPX·HWP3·HWP5, 한컴 DRM은 해당 없음; 암호를 응답·로그에 남기지 않음) |
| 서식 필드 목록 | `npx -y kordoc@^4 fill 서식.hwpx --dry-run` |
| 서식 채우기 | `npx -y kordoc@^4 fill 서식.hwpx -j 값.json -o 결과.hwpx` (가드 `--require-unique`·`--formats`·`--mask`) |
| 표 빈 열 보존 | `--keep-empty-cols` (서식 입력란인 오른쪽 끝 빈 열이 트림되지 않게) |
| 기존 문서 내용 수정 | `npx -y kordoc@^4 patch 원본.hwpx 편집.md -o 결과.hwpx` (`.hwp`도 가능 — 원본 포맷 유지; 편집 md는 LF 유지, 미적용 편집이 있으면 exit 2) |
| 문서 비교 | MCP `compare_documents` (CLI엔 없음 — 양쪽을 md로 파싱해 diff해도 됨) |
| 새 공문서 생성 | `npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서` |
| 새 HWPX에 이미지 임베드 | 마크다운 `![](사진.png)` + `generate ... --image-dir <이미지 폴더>` |
| 구조 검증 | `npx -y kordoc@^4 validate 결과.hwpx` |
| 표 서식 프로필 | `npx -y kordoc@^4 profile 참조.hwpx -o 서식.json` → `generate --profile 서식.json` |
| 개인정보 마스킹 | `npx -y kordoc@^4 redact 문서.hwpx -o 결과.hwpx` (`--dry-run`으로 먼저 탐지) |
| 공문 표기법·문체 검수 | `npx -y kordoc@^4 lint 초안.md` · 보고서/계획서 원고는 `--munche` 추가 |
| 기존 문서 지정 위치 이미지 배치 | Kordoc 밖의 승인 이미지 예외인 `9_형식/scripts/place_image.py` 사용 (`seal` 미사용) |
| 조판 미리보기 | `npx -y kordoc@^4 render 문서.hwpx -o 미리보기.svg` · 쪽별 PNG는 `render 문서.hwpx --format png --pages 1-2 -d 쪽/` (`.hwp`도 가능, svg·html·png·jpeg·pdf — pdf는 Chromium 필요; reflow는 기본 활성화, 형광펜 `--highlight 검색어`) |
| 표 분류 | `npx -y kordoc@^4 tables 문서.hwpx -o 표.json` (데이터표/조직도류/불확실 분류, `--visual non-tabular-and-uncertain -d 폴더/`로 조직도만 crop) |

## 읽기 (파싱)

- 기본 파싱은 보이는 표만 표로 남기고 보이지 않는 틀 표는 글로 푼다(`layoutTables: "visual"`). 구조 편집·양식 분석은 `--keep-layout-tables --keep-empty-cols`로 별도 추출한다. 일반 증류용 파싱본을 그대로 patch에 쓰지 않는다.
- 병합·중첩 표는 GFM으로 표현이 안 되므로 HTML `<table>`(colspan/rowspan)로 나온다 — 그대로 다룬다.
- 표 오른쪽 끝의 빈 열(서식 입력란)은 기본으로 트림된다 — 그 칸을 살려야 하면 `--keep-empty-cols` (#47).
- 수식은 `$...$` / `$$...$$` LaTeX.
- HWP/HWPX의 조판 캐시가 있으면 실제 페이지 경계를 복원하고 `metadata.pageMode`가 `layout`이다. 캐시가 없는 생성·편집본은 섹션 근사(`section`)이며 `-p` 사용 시 `PAGE_BOUNDARY_APPROXIMATE` 경고를 확인한다. `--format json`의 `pages[]`는 쪽별 Markdown을 제공한다. PDF는 4.19.1부터 이어 붙인 표도 쪽별 결과에서 다시 나누지만, 문서 전체 Markdown과 쪽별 결과의 구조는 다를 수 있다. DOCX의 쪽 경계는 위 4.24.47 조건을 따른다.
- PDF는 OCR 모델이 캐시에 있으면 스캔 쪽과 큰 그림 속 글을 자동으로 읽을 수 있다. 명시 `--ocr`는 필요한 모델을 처음 받을 수 있고, 폐쇄망에서는 미리 반입한다.
- PDF는 텍스트층 품질 신호를 계산한다. `needsOcr`이면 `--ocr`로 다시 파싱한다 — 필요한 페이지만 내장 PP-OCRv5로 로컬 인식하고 정상 페이지는 기존 텍스트를 유지한다. 텍스트층이 있지만 내용이 깨져 자동 판정이 놓친 경우에만 `--ocr-force`. 수식은 별도 `--formula-ocr`.
- 2단 시험지처럼 장식 테두리가 표로 오인되어 읽기 순서가 뒤집힐 때만 `--no-tables`로 다시 파싱한다. 기본 표 감지는 먼저 유지한다.
- OCR 기본값도 뚜렷한 손글씨 쪽을 선택 모델로 재인식할 수 있다. 인쇄 전용은 `--ocr-rec printed`, 혼합 자료는 `--ocr-rec auto`, 수기 서류는 `--ocr-rec handwriting`; 기울거나 흐린 스캔은 `--ocr-det medium`을 선택적으로 비교한다. JSON `--ocr-lines`·`--ocr-lines-all`은 줄 좌표·신뢰도·버린 줄 점검용이다. 개인정보 자산의 OCR 금지 규칙은 그대로다.
- PNG·JPG·WebP는 파일을 직접 입력하면 OCR이 자동 적용된다. 별도 PDF 변환이나 `--ocr` 플래그가 필요 없다.
- PDF 머리글/바닥글은 자동 제거된다 (`--no-header-footer`로 끔). HWP5 러닝 헤더가 페이지마다 반복되면 `--dedupe-headers` (기본 off — 붙임별 재번호가 오삭제될 수 있어 주의).
- 문서 속 이미지는 4.16부터 `images/<출력 stem>/image_001.png`식으로 저장되고 같은 문서 폴더의 `manifest.json`이 이름·mimeType·bytes를 담는다. stem은 `-o` 출력 파일에서 마지막 확장자를 뺀 이름이다. 형식은 manifest로 확인하고, 폴더 이동·링크 보정은 `8_시스템/파서-프롬프트.md`를 따른다. HWP5 `--inline-images`는 base64 인라인이며 증류 입력에는 사용하지 않는다.
- 이미지가 수백 장인 문서의 JSON은 `--image-refs`를 `-o` 또는 `-d`와 함께 써 직렬화 한계를 피한다. 이미지 바이트 대신 `images/<출력 stem>/<파일명>` 참조가 남는다.
- 여러 파일은 `-d 디렉토리/` 일괄 모드 — 단 출력명이 확장자를 뗀 `수업안.md`식이라 `수업안.hwp`·`수업안.pdf`가 공존하면 충돌한다. 출력명을 통제하려면 파일별 `-o`.

### 암호·DRM

- 암호가 제공된 HWPX·HWP3·HWP5는 `--password`로 Kordoc 경로 안에서 연다. 암호를 명령 예시, 응답, 로그, 파싱본 frontmatter에 재기록하지 않는다.
- `--password`는 한컴 DRM 해제 옵션이 아니다. Kordoc이 처리하지 못하는 DRM·손상·미지원 구조는 원본을 보존하고 실패 이유만 보고한다.

### 실패 계약 (4.10)

변환 실패는 `--format`과 무관하게 stdout에 실패 JSON 한 개를 내고 exit 1로 끝난다. `-o`/`-d`를 줘도 실패한 파일의 출력물은 만들지 않는다.
사람용 `error` 문구가 아니라 `code`로 분기한다 (`code` 집합은 추가만 되고 기존 값은 바뀌지 않는다):

| `code` | 뜻 | 파서 대응 |
|---|---|---|
| `ENCRYPTED` | 열기 암호 필요·불일치 | 암호를 요청해 `--password`로 재시도 |
| `DRM_PROTECTED` | 한컴 문서보안 | 원본 그대로 두고 보고 |
| `IMAGE_BASED_PDF` | 텍스트층 없는 스캔 PDF | `--ocr`로 재파싱 |
| `OUTPUT_TOO_LARGE` | 직렬화 한계 | `--format json`이면 `--image-refs`, 아니면 `-p`로 나눠 파싱 |
| `FILE_NOT_FOUND` | 입력 파일이 없음 — **또는 `-o`의 출력 폴더가 없음** (4.15.6 실측: 파싱은 성공하고 저장만 실패해도 이 코드. 이때 `fileType`이 `unknown`이 아니다) | 출력 폴더를 만든 뒤 재시도. 그래도 나면 원본 경로를 확인 |
| `CORRUPTED` · `UNSUPPORTED_FORMAT` · `NO_SECTIONS` · `EMPTY_INPUT` | 손상·미지원·빈 문서 | 원본 그대로 두고 보고 |
| `ZIP_BOMB` · `DECOMPRESSION_BOMB` · `MISSING_DEPENDENCY` · `PARSE_ERROR` | 방어 발동·의존성·기타 | 원본 그대로 두고 보고 |

## patch (서식 보존 편집)

① 원본을 `--keep-layout-tables --keep-empty-cols`로 편집용 md에 파싱 → ② md에서 내용만 수정 (구조 이동·삭제 최소화) → ③ `patch 원본 편집.md -o 수정본`.
원본의 서식을 보존해 수정한다. HWPX는 문단 추가·삭제와 표 행 편집도 지원하며, 문단 구조 변경을 막으려면 `--no-structure`를 쓴다. HWP5의 문단 추가·삭제·셀 안 중첩표 편집은 여전히 제한된다.

- **원본 포맷 유지**: 포맷을 감지해 `.hwp`는 바이너리 in-place 패치(`patchHwp`) → `.hwp` 출력, `.hwpx`는 ZIP 패치 → `.hwpx` 출력. `.hwp` 내용 수정에 변환이 필요 없다.
- 패치 후 재파싱 자동 검증이 내장돼 있다 (`--no-verify`로 생략 가능 — 생략하지 않는다).
- 문단 안 강제 줄바꿈은 편집 md에 명시적 `<br>` (에디터 soft-wrap은 수정으로 안 침).
- 원본은 절대 덮어쓰지 않는다 — `-o` 필수.
- 종료 코드: 0 = 전부 적용, 2 = 일부 편집 미적용(stderr의 `SKIP` 목록에 이유 — 표 구조 변경 같은 미지원 편집). exit 2인 산출물은 완성본으로 보고하지 않고, skip된 편집을 지원되는 형태로 다시 반영하거나 사용자에게 알린다.
- **편집 md는 UTF-8·LF로 저장한다.** 4.24.47 스모크에서 LF·CRLF 표 수정 모두 exit 0으로 재파싱까지 통과했다. 옛 판의 CRLF 전면 실패 설명은 현재 제한으로 적용하지 않는다.
- 그림 포함 문서는 `-o`로 추출된 `images/<출력 stem>/...` 링크를 그대로 patch에 넣으면 그림 변경으로 오인해 exit 2가 날 수 있다(4.24.47 실측). 편집 전용 원고는 stdout을 UTF-8·LF로 저장해 원래 그림 파일명 참조를 유지한다. 공유용 파싱본의 링크를 고쳐 patch용으로 재사용하지 않는다.
- exit 2에서는 `<출력 stem>.rewrite.hwpx` 대체본도 생길 수 있다. 원본 서식 보존 성공을 뜻하지 않으므로 자동 제출·완성본 승격하지 말고 미적용 내용·서식·페이지를 별도로 검수한다.
- `.hwp` in-place 패치는 4.10부터 자동 줄바꿈 문단을 더 짧게 고쳐도 한컴이 "손상/변조"로 거부하지 않는다. 그 이전 판으로 만든 `.hwp` 산출물이 열리지 않았다면 다시 패치한다.

## fill (서식 채우기)

0. **볼트의 기본 fill 경로는 HWPX 전용으로 유지한다.** 4.24.27부터 HWP5를 내부 변환해 서식 보존 채우기도 지원하지만, CLI는 변환 불가 입력에서 `hwpx` 재구성 모드로 폴백할 수 있다. 그래서 `.hwp`에 직접 `fill`하지 않는다. 단순 텍스트 수정은 `patch`, 양식 필드 채우기는 HWPX 원본을 요청한다. 새 `to-hwpx --engine kordoc`은 별도 변환 기능이며 이 업데이트만으로 일반 양식의 자동 우회 경로로 채택하지 않는다. `--engine hancom|auto`는 COM을 쓸 수 있어 기존 승인 이미지 예외 밖에서 자동 선택하지 않는다.
1. `--dry-run`으로 라벨 목록을 파악한 뒤 `--dry-run -j 값.json`으로 값별 목표 좌표(`target.table/row/col`)를 확인한다. `overwrittenBy`·`unmatched`·`rejected`가 있으면 입력 충돌·누락을 해결하고 실행한다. 계획 JSON에는 값이 포함될 수 있으므로 응답·공유 로그에 그대로 싣지 않는다.
2. 값은 `-j 값.json` 권장 (`-f 'k=v'`는 셸 히스토리에 값 노출). 다중줄은 JSON 문자열 안 `\n`.
3. 같은 라벨이 2곳 이상이면 **모든 칸에 채운다**. 반복 라벨 양식 오염이 걱정되면 CLI `--require-unique`로 스칼라 라벨이 2곳+ 매칭될 때 거부(rejected 보고)시킨다(배열 값은 예외). 아니면 값을 배열로 주거나 어느 칸인지 확인 후 채운다.
4. 날짜·전화·주민등록번호 등 칸 모양 변환은 CLI `--formats '{"날짜":"yy.mm.dd","주민등록번호":"rrn:masked"}'`(라벨→포맷 JSON)로 지정한다. 3.x에선 MCP 전용이었으나 4.x부터 CLI에 있다.
5. 기본 출력은 원본 글꼴·정렬 보존(`--format hwpx-preserve`, 기본값). `-o` 확장자(`.hwpx`/`.md`)로도 출력 포맷이 결정된다.
6. 주민번호·계좌 등 채운 값은 응답에 되풀이하지 않는다. 값 노출 없이 채움만 확인하려면 CLI `--mask`(출력 파일 없이 안내만 stdout).

## 기존 문서의 지정 위치 이미지 쓰기 예외 (`seal` 미사용)

Kordoc `generate --image-dir`는 **새 HWPX 생성 중** 마크다운 이미지를 임베드한다. **기존 문서의 지정 위치**에 서명·도장·신분증·통장사본·증명사진·일반 사진을 넣는 일은 Kordoc 밖의 `9_형식/scripts/place_image.py`가 맡는다(절차: `9_형식/references/workflows/hwpx-forms.md` 3절). `.hwp`는 이 작업 안에서만 임시 HWPX로 한 번 변환하고 최종본은 HWPX로만 낸다.

Kordoc `seal`(앵커 글자 위에 도장·서명을 띄워 놓는 명령)은 쓰지 않는다. 4.15.6 실측(2026-09-28, 같은 양식·같은 이미지, 한글 렌더 기준):

- 기본값: 7mm 크기로 "(인)"·"(서명)" 오른쪽에 넣었다고 보고하지만 한글에서 그림이 보이지 않았다(`validate`는 통과).
- `--size-mm`·`--mode overlap` 지정: 도장이 한 칸 위 다른 행에 찍혔고, 서명은 한 줄 아래로 내려가며 가로세로 비율이 정사각형으로 늘어났다. Kordoc이 만든 양식에서도 같았다.
- 당시 `.hwp`는 받지 않았다. 4.24.27부터 HWP5 입력은 지원하지만, 이것만으로 이미지 비율·위치의 한컴 실측 문제가 해소됐다고 판단하지 않는다.

4.24.47에서는 서명·신분증 등 자산별 한컴 실측을 재검증하지 않았으므로 기존 예외를 유지한다. 이 세 가지를 다시 재 보고, 모두 풀렸을 때만 `place_image.py` 예외를 줄이는 것을 검토한다. 실측 경로를 실행할 수 없으면 `seal`이나 다른 도구로 대신하지 않고 원본을 그대로 둔 채 필요한 조건을 알린다.

## generate (볼트 템플릿이 없을 때만)

- 승인된 견본으로 구조가 다른 새 문서를 만들 때는 `generate --template 견본.hwpx`를 검토한다. 같은 골격의 내용 수정은 patch다. 기관팩 `--pack`과 견본 생성은 일부 요소에 경고·재조판이 생길 수 있으므로 기존 양식 채우기의 대체 경로로 자동 선택하지 않는다.
- 프리셋(기본 `기안문`): `기안문`·`보고서`·`계획서`·`통지`·`회의록`·`개조식`(표지·목차·장헤더 자동)·`업무보고`(중앙부처 국회 서면보고형)·`보도자료`·`서울방침`. 영문 별칭도 됨(official/report/plan/notice/minutes/gaejosik/ministry/press). 번호 목록이 공문서 항목부호 8단계로 자동 변환된다.
- 4.13부터 기안문·보고서·계획서·통지·회의록은 서울 실결재 629건 실측 위계로 고정된 v5 엔진이다. `#`=제목, `##`=장(보고서·계획서는 Ⅰ. Ⅱ. 띠 표, 기안문·통지는 법정 `1.`), `###`=□(또는 `가.`), 그 아래 리스트는 ㅇ → - → ㆍ. 본문에 □/ㅇ/-/1./가.를 직접 써도 같은 단계로 정규화된다. 기본 글꼴은 기안문 굴림체 12pt 160%(함초롬바탕은 `--font myeongjo`), 보고서·계획서 줄간격 180%. 장 제목을 띠 표 대신 텍스트로 내려면 `--h2-marker roman`. 한 쪽을 넘는 표는 쪽 경계에서 나뉘고 머리 행이 반복된다 (4.13.2).
- □·제목이 한 줄을 넘으면 장평·자간을 줄여 맞추고 그래도 넘치면 경고한다 — 글자 크기를 줄이지 말고 문장을 줄인다.
- **보고서·계획서는 제목 직후 인용문(`>`)에 보고 목적을 한 문장으로 쓴다** (부호 없이, 3줄 이내, "…하고자 함" 꼴). 그 문장이 요약박스가 되며 없거나 넘치면 경고한다. `출처:`·`자료:`·`근거:`로 시작하는 줄은 ※ 참고(작은 글씨)로 가고, 법령 코드·KOSIS 표 ID·"MCP 조회" 같은 도구 언급은 자동 제거된다 — 출처는 기관·자료명만 쓴다.
- 표는 GFM 파이프표, display 수식 `$$...$$`은 네이티브 `<hp:equation>`.
- ` ```chart ` 펜스 → 한컴 네이티브 차트 (type/cat/계열 라인, 펜스 안 주석 금지 — 값으로 오인됨).
- 마크다운 `![](photo.png)`의 실제 PNG/JPEG/GIF/BMP를 넣으려면 `--image-dir <폴더>`를 지정한다. 새 문서 이미지에는 `9_형식/scripts/place_image.py`를 쓰지 않는다. 4.15.6까지는 한글 파일명(`사진.png`)을 오류 없이 건너뛰었다 (4.15.7에서 수정, #95 — 4.15.7 실측 "이미지 임베드: 1개"). 생성 뒤 stderr의 "이미지 임베드: N개"가 md의 이미지 참조 수와 같은지는 계속 확인한다.
- 표 서식은 `--profile 양식.json`으로 기관 양식 재현(아래 "서식 프로필" 절).
- 용지·조판은 `--paper`·`--landscape`·`--columns`·`--header`·`--footer`로 지정할 수 있다.
- 공문 세부 옵션이 풍부하다: 결재란 `--approval 담당,팀장,과장`, 기안문 두문표·결문표 `--doc-head "org=기관명,slogan=원훈,to=수신,title=제목"`·`--doc-foot "sender=발신명의,drafter=주무관 홍길동,reviewer=과장 김철수,approver=국장 박영희,docNum=과-번호 (날짜),zip=…,address=…,phone=…,email=…,disclosure=공개"`(수신이 `내부결재`면 발신명의 자동 생략), 보고서 담당자 행 `--report-info`·요약박스 `--summary`·표지 `--cover --dept 부서 --doc-info "docNum=…"`·취급 표시 `--cover-label 대외주의`, 장 띠 색 `--band-color #DFE6F7 --band-text-color #000000`(교육청형 밝은 띠), 단계별 글꼴 `--levels "0=HY견고딕/17/bold,1=한컴돋움/15/bold,2=휴먼명조/14"`, 공고 `--notice-head`, 보도자료 `--press-head`, 표지 `--org`·`--date`, 쪽번호·끝표시 `--page-numbers`·`--end-mark`. 전체는 `generate --help`.
- 생성 시 공문 표기법과 AI 흔적(`AI_*`) 검수가 자동으로 돌아 경고를 표시한다. 보고서·계획서·개조식 프리셋은 개조식 문체 경고도 자동으로 붙는다. 산출은 막지 않으니 경고를 읽고 md를 고쳐 재생성한다.
- 엄격한 원고 검수가 필요하면 `lint --gate --preset 보고서` 또는 `generate --gate`를 쓴다. gate 미통과는 exit 1이며 generate는 출력하지 않는다. 기본 generate의 경고와 구분한다.
- 생성 후 반드시 `validate` 통과 확인.

## 서식 프로필 (기관 양식의 표 서식 재현)

레퍼런스 hwpx에서 표의 시각 서식(괘선·음영·열 너비·셀 글꼴)만 JSON으로 추출해 generate 때 재현한다.
내용·개인정보 없이 서식만 담기므로, 필요할 때 볼트의 `9_형식/서식프로필/`을 만들어 프로필 JSON을 보관·재사용할 수 있다.
4.x부터 CLI 명령으로 승격됐다 (3.x의 `.mjs` 스크립트는 더 필요 없다). 프리셋과 병용 가능(문단 서식은 프리셋, 표 서식은 프로필):

```powershell
# ① 추출 (양식당 1회): 학교 양식 hwpx → 프로필 JSON
npx -y kordoc@^4 profile 학교양식.hwpx -o 양식.profile.json
# ② 적용: md의 N번째 표에 프로필의 N번째 표 서식이 입혀진다 (행·열 수가 일치할 때만 — 불일치 시 무시+경고)
npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서 --profile 양식.profile.json
```

## redact (개인정보 서식 보존 마스킹)

주민번호·전화·이메일·카드·계좌를 탐지해 마스킹한다. HWPX/HWP는 **원본 서식 그대로 patch**, 그 외 포맷은 마스킹된 md 출력.

- 기본 룰 `rrn,phone,email,card,account,brn,passport,driver` (4.14.3부터 사업자번호·여권·운전면허도 기본), 마스크 문자 `--mask-char ●`. `--rules`는 기본값에 더하지 않고 **대체**한다. exit 2는 가린 뒤에도 개인정보가 남았다는 뜻이므로 그 결과를 쓰지 않는다.
- **먼저 `--dry-run`으로 탐지 리포트만** 보고 오탐·누락을 확인한다. 자동 검출 보조 도구이므로 결과는 사람이 최종 확인 — 이미지 속 텍스트는 못 잡는다.
- 용도: `0_원본/`에 넣기 전, 학생 개인정보가 섞인 문서를 서식 유지한 채 익명화. (수집은 여전히 수동 — 마스킹만 돕고 자동 투입하지 않는다.)

## lint (공문 표기법 검수)

`npx -y kordoc@^4 lint 초안.md` — 날짜·시간·금액·붙임 등 행정업무운영 편람 표기법 19룰과 AI 줄표·강조 남용 2룰을 검사한다. 4.12~4.13에서 늘어난 룰: 금액 한글 병기 `MONEY_NO_HANGUL`(실제 병기값을 제안), 하이픈 날짜 `DATE_HYPHEN`(`2026-07-18` → `2026. 7. 18.`), 물결표 붙여쓰기 `TILDE_SPACE`, 두음법칙 `DUEUM_ERROR`, 외래어 오기 `LOANWORD_ERROR`, 차별·비하 표현 `DISCRIMINATORY_TERM`, 붙임 있는데 "끝." 없음 `END_MARK_MISSING`(완성 원고를 보는 `lint`에서만 켜지고 `generate` 경고에는 없다 — 기안문 프리셋이 "끝."을 자동으로 넣기 때문). 표 셀 안의 "성 명 :" 같은 서식 라벨은 쌍점 규칙에서 제외된다. 보고서·계획서 원고는 `--munche`를 붙여 서술형 종결·당위·수사·항목 길이 등 개조식 문체도 검사한다(부호로 시작하는 인용문은 요약박스로 보아 리드문 규칙에서 뺀다).

- 엔진은 현재 HWP/HWPX/PDF 직접 lint도 지원한다. 다만 볼트의 생성 전 검수는 UTF-8 `md`/`txt` 또는 stdin(`-`)로 통일하고 HWP/HWPX/PDF를 직접 넘기지 않는다. 파싱 문서에서는 연속 공백·강조 규칙이 생략돼 원고 검수와 같지 않다.
- `error`가 있으면 exit 1, `--json`으로 기계 판독한다. AI·문체 warning도 검토하되 사실·규범을 훼손하면서 기계적으로 고치지 않는다.
- `generate`는 관련 lint를 자동 실행하지만 생성을 막지 않는다. 경고를 확인하고 필요한 수정을 한 뒤 재생성한다.

## 함정

- 암호가 제공된 지원 문서는 `--password`로 읽는다. 한컴 DRM·손상·미지원 구조처럼 Kordoc이 처리하지 못하는 파일은 원본을 그대로 두고 실패 이유를 보고한다. 승인된 `.hwp` 이미지 배치 작업 외에는 COM 변환이나 다른 도구로 자동 우회하지 않는다.
- `.hwp`(바이너리)와 `.hwpx`(ZIP/XML)는 다른 포맷. fill/generate 산출물은 항상 HWPX지만 **patch만은 원본 포맷을 유지**한다 (`.hwp`→`.hwp`).
- 표가 깨져 보이는 PDF는 대부분 스캔본/텍스트층 손상 — 품질 신호를 확인하고 `--ocr`로 재파싱한다. 이미지 서식은 직접 입력해 OCR한다.
- 편집 원고는 `--keep-layout-tables --keep-empty-cols`로 별도 추출하고 UTF-8·LF를 유지한다. 그림이 있으면 위 patch 절의 stdout 추출 규칙을 따른다.
- 기본 파싱에서 풀린 1×1·1열 틀 표 때문에 표 대응이 어긋날 수 있다. 옛 판의 무조건 미지원 설명 대신 `--keep-layout-tables --keep-empty-cols`로 다시 추출하고, 그래도 skip이면 완성본으로 보고하지 않는다.
- HWP5 `.hwp`에서 칸 안에 든 중첩 표는 `patch`로 고칠 수 없다 — `SKIP: 셀 내 중첩표 수정은 HWP5 미지원 (v1)`, exit 2 (4.15.7 실측). HWPX에서는 같은 편집이 된다. 볼트마다의 우회 사례는 `9_형식/현장메모.md`.
