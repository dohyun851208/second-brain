# kordoc 사용법

한국 문서 파싱·편집 엔진 ([chrisryugj/kordoc](https://github.com/chrisryugj/kordoc), MIT, npm).
HWP 3.x/5.x·HWPX·HWPML·PDF·DOCX·XLS/XLSX·PNG/JPG/WebP → Markdown, 로컬 한글 OCR, 서식 보존 패치·채우기, 문서 비교, 도장 배치, 개인정보 마스킹(redact), 공문 표기법 검수(lint), 표 서식 프로필.
한컴 오피스·COM 불필요, 로컬 실행이라 문서가 외부로 나가지 않는다 (학생 개인정보 안전).

## 실행

```powershell
npx -y kordoc@^4 <명령> ...
```

Node 18+ 필요. 첫 호출만 다운로드로 느리고 이후 캐시. `ECOMPROMISED`·`MODULE_NOT_FOUND` 에러가 나면
`$env:LOCALAPPDATA\npm-cache\_npx\` 아래 해당 캐시 폴더를 지우고 재시도한다.

상시 사용 환경이면 `npx -y kordoc@^4 setup`(대화형 마법사)으로 MCP 서버 등록도 가능 — 콜드스타트가
없어지고 MCP 전용 기능(`compare_documents`, 세분 파싱 `parse_table`·`parse_metadata` 등)을 쓸 수 있다.
**3.x에서 MCP 전용이던 fill 가드(`--require-unique`·`--formats`·`--mask`)와 서식 프로필(`profile`)은 4.x부터 CLI에 편입돼 MCP 없이도 쓴다.**

### 버전 정책

- `@^4`는 실행할 때 최신 4.x를 사용하고 5.x로는 넘어가지 않는다.
- 작업 재현성을 위해 파싱 배치 시작 시 `npx -y kordoc@^4 --version`을 한 번 확인하고 각 파싱본의 `도구-버전`에 기록한다.
- "세컨드브레인 상태/업그레이드" 때만 `npm view kordoc version`으로 전체 최신판을 확인한다. 최신판이 5.x 이상이어도 자동 전환하지 않고 공식 변경 기록과 대표 문서 테스트 후 지침·호환 범위·시스템 버전을 함께 올린다.

## 명령 치트시트

| 작업 | 명령 |
|---|---|
| 문서 → Markdown | `npx -y kordoc@^4 문서.hwp -o 문서.md` (hwpx·pdf·docx·xls·이미지 동일) |
| 페이지 범위 | `-p 1-3` 또는 `-p 1,3,5` |
| 구조화 JSON | `--format json` (blocks+metadata) · `--format chunks` (RAG용 위계 청크) |
| 스캔 PDF 본문 OCR | `--ocr` (필요 페이지만 로컬 PP-OCRv5, 첫 사용 시 모델 ~18MB) · `--ocr-force` (전 페이지 강제) |
| 이미지 OCR | PNG·JPG·WebP 파일을 직접 입력 — OCR 자동 적용 |
| PDF 수식 OCR | `--formula-ocr` (첫 사용 시 모델 ~155MB 자동 다운로드, `check-formula-models`로 상태 확인) |
| 서식 필드 목록 | `npx -y kordoc@^4 fill 서식.hwpx --dry-run` |
| 서식 채우기 | `npx -y kordoc@^4 fill 서식.hwpx -j 값.json -o 결과.hwpx` (가드 `--require-unique`·`--formats`·`--mask`) |
| 표 빈 열 보존 | `--keep-empty-cols` (서식 입력란인 오른쪽 끝 빈 열이 트림되지 않게) |
| 기존 문서 내용 수정 | `npx -y kordoc@^4 patch 원본.hwpx 편집.md -o 결과.hwpx` (`.hwp`도 가능 — 원본 포맷 유지) |
| 문서 비교 | MCP `compare_documents` (CLI엔 없음 — 양쪽을 md로 파싱해 diff해도 됨) |
| 공문서 생성 (폴백) | `npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서` |
| 구조 검증 | `npx -y kordoc@^4 validate 결과.hwpx` |
| 표 서식 프로필 | `npx -y kordoc@^4 profile 참조.hwpx -o 서식.json` → `generate --profile 서식.json` |
| 개인정보 마스킹 | `npx -y kordoc@^4 redact 문서.hwpx -o 결과.hwpx` (`--dry-run`으로 먼저 탐지) |
| 공문 표기법 검수 | `npx -y kordoc@^4 lint 초안.md` (편람 표기법, error면 exit 1) |
| 도장/서명 배치 | `npx -y kordoc@^4 seal 문서.hwpx --image 도장.png --anchor "(인)" -o 결과.hwpx` |
| 조판 미리보기 | `npx -y kordoc@^4 render 문서.hwpx -o 미리보기.svg` (생성/패치본은 `--reflow`, 형광펜 `--highlight 검색어`) |

## 읽기 (파싱)

- 병합·중첩 표는 GFM으로 표현이 안 되므로 HTML `<table>`(colspan/rowspan)로 나온다 — 그대로 다룬다.
- 표 오른쪽 끝의 빈 열(서식 입력란)은 기본으로 트림된다 — 그 칸을 살려야 하면 `--keep-empty-cols` (#47).
- 수식은 `$...$` / `$$...$$` LaTeX.
- PDF는 텍스트층 품질 신호를 계산한다. `needsOcr`이면 `--ocr`로 다시 파싱한다 — 필요한 페이지만 내장 PP-OCRv5로 로컬 인식하고 정상 페이지는 기존 텍스트를 유지한다. 텍스트층이 있지만 내용이 깨져 자동 판정이 놓친 경우에만 `--ocr-force`. 수식은 별도 `--formula-ocr`.
- PNG·JPG·WebP는 파일을 직접 입력하면 OCR이 자동 적용된다. 별도 PDF 변환이나 `--ocr` 플래그가 필요 없다.
- PDF 머리글/바닥글은 자동 제거된다 (`--no-header-footer`로 끔). HWP5 러닝 헤더가 페이지마다 반복되면 `--dedupe-headers` (기본 off — 붙임별 재번호가 오삭제될 수 있어 주의).
- 문서 속 이미지는 출력 폴더의 `images/`에 `image_001.png`식으로 저장된다 (4.x는 추출률이 크게 올라 HWPX/HWP5 100%, PDF 이미지도 PNG로 디코드). **함정 둘**: ① `-o` 단일 출력은 md 링크에 `images/` 접두사가 안 붙어 링크가 깨진다 (`-d` 모드만 붙음) ② 파일명 번호가 문서마다 1부터라 여러 문서를 같은 폴더로 파싱하면 서로 덮어쓴다 → 문서별 이미지 폴더로 분리하고 링크를 보정한다. HWP5는 `--inline-images`로 base64 인라인도 가능 (별도 파일 없음 — 타 포맷은 옵션 무시).
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
3. 같은 라벨이 2곳 이상이면 **모든 칸에 채운다**. 반복 라벨 양식 오염이 걱정되면 CLI `--require-unique`로 스칼라 라벨이 2곳+ 매칭될 때 거부(rejected 보고)시킨다(배열 값은 예외). 아니면 값을 배열로 주거나 어느 칸인지 확인 후 채운다.
4. 날짜·전화·주민등록번호 등 칸 모양 변환은 CLI `--formats '{"날짜":"yy.mm.dd","주민등록번호":"rrn:masked"}'`(라벨→포맷 JSON)로 지정한다. 3.x에선 MCP 전용이었으나 4.x부터 CLI에 있다.
5. 기본 출력은 원본 글꼴·정렬 보존(`--format hwpx-preserve`, 기본값). `-o` 확장자(`.hwpx`/`.md`)로도 출력 포맷이 결정된다.
6. 주민번호·계좌 등 채운 값은 응답에 되풀이하지 않는다. 값 노출 없이 채움만 확인하려면 CLI `--mask`(출력 파일 없이 안내만 stdout).

## seal (도장 배치)

앵커 문구("(인)" 등) 위/옆에 이미지를 글 앞 부유로 얹는다 — 표·페이지가 밀리지 않음.
같은 앵커 여럿이면 `-n <0-based>`, 위치 보정 `--dx`/`--dy`(mm), 크기 `--size-mm`, 배치 방식 `--mode overlap|right|auto`(기본 auto). 투명 PNG 권장. HWPX 전용.
중첩표·글상자·복잡 rowSpan은 근사 배치(warnings 고지) — 배치 후 `render --reflow`로 확인.

## generate (볼트 템플릿이 없을 때만)

- 프리셋(기본 `기안문`): `기안문`·`보고서`·`계획서`·`통지`·`회의록`·`개조식`(표지·목차·장헤더 자동)·`보도자료`. 영문 별칭도 됨(official/report/plan/notice/minutes/gaejosik/press). 번호 목록이 공문서 항목부호 8단계로 자동 변환, 함초롬바탕 표준 서식.
- 표는 GFM 파이프표, display 수식 `$$...$$`은 네이티브 `<hp:equation>`.
- ` ```chart ` 펜스 → 한컴 네이티브 차트 (type/cat/계열 라인, 펜스 안 주석 금지 — 값으로 오인됨).
- 표 서식은 `--profile 양식.json`으로 기관 양식 재현(아래 "서식 프로필" 절).
- 공문 세부 옵션이 풍부하다: 결재란 `--approval 담당,팀장,과장`, 기안문 두문·결문 `--doc-head`·`--doc-foot`, 공고 `--notice-head`, 보도자료 `--press-head`, 표지 `--org`·`--date`, 쪽번호·끝표시 `--page-numbers`·`--end-mark`. 전체는 `generate --help`.
- 생성 시 공문 표기법 검수(lint)가 자동으로 돌아 경고를 표시한다 (실측 2026-07: `[TIME_24H]` 등) — 산출은 막지 않으니 경고를 읽고 필요하면 md를 고쳐 재생성.
- 생성 후 반드시 `validate` 통과 확인.

## 서식 프로필 (기관 양식의 표 서식 재현)

레퍼런스 hwpx에서 표의 시각 서식(괘선·음영·열 너비·셀 글꼴)만 JSON으로 추출해 generate 때 재현한다.
내용·개인정보 없이 서식만 담기므로, 학교 양식을 프로필 JSON으로 `9_형식/templates/`에 보관·재사용할 수 있다.
4.x부터 CLI 명령으로 승격됐다 (3.x의 `.mjs` 스크립트는 더 필요 없다). 프리셋과 병용 가능(문단 서식은 프리셋, 표 서식은 프로필):

```powershell
# ① 추출 (양식당 1회): 학교 양식 hwpx → 프로필 JSON
npx -y kordoc@^4 profile 학교양식.hwpx -o 양식.profile.json
# ② 적용: md의 N번째 표에 프로필의 N번째 표 서식이 입혀진다 (행·열 수가 일치할 때만 — 불일치 시 무시+경고)
npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서 --profile 양식.profile.json
```

## redact (개인정보 서식 보존 마스킹)

주민번호·전화·이메일·카드·계좌를 탐지해 마스킹한다. HWPX/HWP는 **원본 서식 그대로 patch**, 그 외 포맷은 마스킹된 md 출력.

- 기본 룰 `rrn,phone,email,card,account` (여권·운전면허는 `--rules`로 opt-in), 마스크 문자 `--mask-char ●`.
- **먼저 `--dry-run`으로 탐지 리포트만** 보고 오탐·누락을 확인한다. 자동 검출 보조 도구이므로 결과는 사람이 최종 확인 — 이미지 속 텍스트는 못 잡는다.
- 용도: `0_원본/`에 넣기 전, 학생 개인정보가 섞인 문서를 서식 유지한 채 익명화. (수집은 여전히 수동 — 마스킹만 돕고 자동 투입하지 않는다.)

## lint (공문 표기법 검수)

`npx -y kordoc@^4 lint 초안.md` — 날짜·시간·금액·붙임 등 행정업무운영 편람 표기법을 검사한다(md/txt, `-`=stdin). error가 있으면 exit 1, `--json`으로 기계 판독. 공문·보고서 산출 전 표기 점검용.

## 함정

- 암호 보호·DRM 배포본은 파싱 불가 → 이때만 한컴 COM 폴백 (`scripts/convert_hwp.py`).
- `.hwp`(바이너리)와 `.hwpx`(ZIP/XML)는 다른 포맷. fill/generate 산출물은 항상 HWPX지만 **patch만은 원본 포맷을 유지**한다 (`.hwp`→`.hwp`).
- 표가 깨져 보이는 PDF는 대부분 스캔본/텍스트층 손상 — 품질 신호를 확인하고 `--ocr`로 재파싱한다. 이미지 서식은 직접 입력해 OCR한다.
