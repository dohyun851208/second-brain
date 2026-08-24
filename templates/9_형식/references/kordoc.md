# kordoc 사용법

한국 문서 파싱·편집 엔진 ([chrisryugj/kordoc](https://github.com/chrisryugj/kordoc), MIT, npm).
HWP 3.x/5.x·HWPX·HWPML·PDF·DOCX·XLS/XLSX·PNG/JPG/WebP → Markdown, 로컬 한글 OCR, 실제 페이지 복원·페이지별 JSON, 서식 보존 패치·채우기, 문서 비교, 개인정보 마스킹(redact), 공문 표기법·개조식 문체 검수(lint), 표 서식 프로필.
일반 작업에는 한컴 오피스·COM이 불필요하고, 로컬 실행이라 문서가 외부로 나가지 않는다 (학생 개인정보 안전). 승인된 이미지 배치 작업에 `.hwp`가 입력된 경우만 `place_image.py`가 한컴 COM으로 임시 HWPX를 만든다.

> 호환 범위: `@^4` · 마지막 공식 소스/CLI 검증판: **4.9.2 (2026-08-24)**. Kordoc 엔진 소스는 이 스킬에 복제하지 않고 npm의 호환 범위로 실행한다.

## 실행

```powershell
npx -y kordoc@^4 <명령> ...
```

Node 18+ 필요. 첫 호출만 다운로드로 느리고 이후 캐시. `ECOMPROMISED`·`MODULE_NOT_FOUND` 에러가 나면
`$env:LOCALAPPDATA\npm-cache\_npx\` 아래 해당 캐시 폴더를 지우고 재시도한다.

상시 사용 환경이면 `npx -y kordoc@^4 setup`(대화형 마법사)으로 MCP 서버 등록도 가능 — 콜드스타트가
없어지고 MCP 전용 기능(`compare_documents`, 세분 파싱 `parse_table`·`parse_metadata` 등)을 쓸 수 있다.
**3.x에서 MCP 전용이던 fill 가드(`--require-unique`·`--formats`·`--mask`)와 서식 프로필(`profile`)은 4.x부터 CLI에 편입돼 MCP 없이도 쓴다.**

폐쇄망에서는 미리 모델을 `models --export/--import`로 반입하고 `KORDOC_OFFLINE=1`을 사용한다. MCP가 읽고 쓸 수 있는 범위를 볼트로 제한하려면 `KORDOC_ROOT=<볼트 경로>`를 설정한다. 두 환경변수는 opt-in이며, OCR 모델이 없는 상태에서 offline을 켜면 다운로드 대신 실패한다.

### 버전 정책

- `@^4`는 실행할 때 최신 4.x를 사용하고 5.x로는 넘어가지 않는다.
- 작업 재현성을 위해 파싱 배치 시작 시 `npx -y kordoc@^4 --version`을 한 번 확인하고 각 파싱본의 `도구-버전`에 기록한다.
- "세컨드브레인 상태/업그레이드" 때만 `npm view kordoc version`으로 전체 최신판을 확인한다. 최신판이 5.x 이상이어도 자동 전환하지 않고 공식 변경 기록과 대표 문서 테스트 후 지침·호환 범위·시스템 버전을 함께 올린다.
- 같은 메이저의 새 기능을 지침에 반영할 때도 공식 저장소의 마지막 검증 태그 이후 변경을 임시 clone에서 비교하고, 이 문서의 마지막 검증판과 시스템 버전을 함께 올린다. upstream 소스 자체를 `templates/`에 복사하지 않는다.

### 4.9.2까지 반영한 변경점

- 4.5: `generate --image-dir`, 용지·방향·다단·머리말·꼬리말.
- 4.6: PDF `--no-tables`, 이미지 많은 JSON의 `--image-refs`.
- 4.7~4.8: HWP/HWPX 실제 페이지 경계, `metadata.pageMode`, JSON `pages[]`, 폐쇄망 모델 반입.
- 4.9: AI 흔적 lint와 `lint --munche`; 4.9.2의 여러 줄 `<right>` 출처행·캡션 조판 수정은 엔진이 자동 적용한다.

## 명령 치트시트

| 작업 | 명령 |
|---|---|
| 문서 → Markdown | `npx -y kordoc@^4 문서.hwp -o 문서.md` (hwpx·pdf·docx·xls·이미지 동일) |
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
| 기존 문서 내용 수정 | `npx -y kordoc@^4 patch 원본.hwpx 편집.md -o 결과.hwpx` (`.hwp`도 가능 — 원본 포맷 유지) |
| 문서 비교 | MCP `compare_documents` (CLI엔 없음 — 양쪽을 md로 파싱해 diff해도 됨) |
| 새 공문서 생성 | `npx -y kordoc@^4 generate 초안.md -o 결과.hwpx --preset 보고서` |
| 새 HWPX에 이미지 임베드 | 마크다운 `![](사진.png)` + `generate ... --image-dir <이미지 폴더>` |
| 구조 검증 | `npx -y kordoc@^4 validate 결과.hwpx` |
| 표 서식 프로필 | `npx -y kordoc@^4 profile 참조.hwpx -o 서식.json` → `generate --profile 서식.json` |
| 개인정보 마스킹 | `npx -y kordoc@^4 redact 문서.hwpx -o 결과.hwpx` (`--dry-run`으로 먼저 탐지) |
| 공문 표기법·문체 검수 | `npx -y kordoc@^4 lint 초안.md` · 보고서/계획서 원고는 `--munche` 추가 |
| 기존 문서 지정 위치 이미지 배치 | Kordoc 밖의 승인 이미지 예외인 `scripts/place_image.py` 사용 (`seal` 미사용) |
| 조판 미리보기 | `npx -y kordoc@^4 render 문서.hwpx -o 미리보기.svg` (reflow는 기본 활성화, 형광펜 `--highlight 검색어`) |

## 읽기 (파싱)

- 병합·중첩 표는 GFM으로 표현이 안 되므로 HTML `<table>`(colspan/rowspan)로 나온다 — 그대로 다룬다.
- 표 오른쪽 끝의 빈 열(서식 입력란)은 기본으로 트림된다 — 그 칸을 살려야 하면 `--keep-empty-cols` (#47).
- 수식은 `$...$` / `$$...$$` LaTeX.
- HWP/HWPX의 조판 캐시가 있으면 실제 페이지 경계를 복원하고 `metadata.pageMode`가 `layout`이다. 캐시가 없는 생성·편집본은 섹션 근사(`section`)이며 `-p` 사용 시 `PAGE_BOUNDARY_APPROXIMATE` 경고를 확인한다. `--format json`의 `pages[]`는 쪽별 Markdown을 제공하지만, 여러 쪽에 걸친 표는 시작 쪽 블록으로 남을 수 있다.
- PDF는 텍스트층 품질 신호를 계산한다. `needsOcr`이면 `--ocr`로 다시 파싱한다 — 필요한 페이지만 내장 PP-OCRv5로 로컬 인식하고 정상 페이지는 기존 텍스트를 유지한다. 텍스트층이 있지만 내용이 깨져 자동 판정이 놓친 경우에만 `--ocr-force`. 수식은 별도 `--formula-ocr`.
- 2단 시험지처럼 장식 테두리가 표로 오인되어 읽기 순서가 뒤집힐 때만 `--no-tables`로 다시 파싱한다. 기본 표 감지는 먼저 유지한다.
- PNG·JPG·WebP는 파일을 직접 입력하면 OCR이 자동 적용된다. 별도 PDF 변환이나 `--ocr` 플래그가 필요 없다.
- PDF 머리글/바닥글은 자동 제거된다 (`--no-header-footer`로 끔). HWP5 러닝 헤더가 페이지마다 반복되면 `--dedupe-headers` (기본 off — 붙임별 재번호가 오삭제될 수 있어 주의).
- 문서 속 이미지는 출력 폴더의 `images/`에 `image_001.png`식으로 저장된다 (4.x는 추출률이 크게 올라 HWPX/HWP5 100%, PDF 이미지도 PNG로 디코드). **함정 둘**: ① `-o` 단일 출력은 md 링크에 `images/` 접두사가 안 붙어 링크가 깨진다 (`-d` 모드만 붙음) ② 파일명 번호가 문서마다 1부터라 여러 문서를 같은 폴더로 파싱하면 서로 덮어쓴다 → 문서별 이미지 폴더로 분리하고 링크를 보정한다. HWP5는 `--inline-images`로 base64 인라인도 가능 (별도 파일 없음 — 타 포맷은 옵션 무시).
- 이미지가 수백 장인 문서의 JSON은 `--image-refs`를 `-o` 또는 `-d`와 함께 써 직렬화 한계를 피한다. 이미지 바이트 대신 `images/<파일명>` 참조가 남는다.
- 여러 파일은 `-d 디렉토리/` 일괄 모드 — 단 출력명이 확장자를 뗀 `수업안.md`식이라 `수업안.hwp`·`수업안.pdf`가 공존하면 충돌한다. 출력명을 통제하려면 파일별 `-o`.

### 암호·DRM

- 암호가 제공된 HWPX·HWP3·HWP5는 `--password`로 Kordoc 경로 안에서 연다. 암호를 명령 예시, 응답, 로그, 파싱본 frontmatter에 재기록하지 않는다.
- `--password`는 한컴 DRM 해제 옵션이 아니다. Kordoc이 처리하지 못하는 DRM·손상·미지원 구조는 원본을 보존하고 실패 이유만 보고한다.

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
   `output_format: hwpx`면 동일한 재구성 경로다. Kordoc 단일 경로에서는 `.hwp` 양식에 `fill`을 쓰거나 변환하지 않는다.
   단순한 기존 텍스트 교체라면 `patch`를 사용하고, 양식 필드 채우기가 필요하면 HWPX 원본 제공을 요청한다.
1. `--dry-run`으로 라벨 목록 먼저 파악.
2. 값은 `-j 값.json` 권장 (`-f 'k=v'`는 셸 히스토리에 값 노출). 다중줄은 JSON 문자열 안 `\n`.
3. 같은 라벨이 2곳 이상이면 **모든 칸에 채운다**. 반복 라벨 양식 오염이 걱정되면 CLI `--require-unique`로 스칼라 라벨이 2곳+ 매칭될 때 거부(rejected 보고)시킨다(배열 값은 예외). 아니면 값을 배열로 주거나 어느 칸인지 확인 후 채운다.
4. 날짜·전화·주민등록번호 등 칸 모양 변환은 CLI `--formats '{"날짜":"yy.mm.dd","주민등록번호":"rrn:masked"}'`(라벨→포맷 JSON)로 지정한다. 3.x에선 MCP 전용이었으나 4.x부터 CLI에 있다.
5. 기본 출력은 원본 글꼴·정렬 보존(`--format hwpx-preserve`, 기본값). `-o` 확장자(`.hwpx`/`.md`)로도 출력 포맷이 결정된다.
6. 주민번호·계좌 등 채운 값은 응답에 되풀이하지 않는다. 값 노출 없이 채움만 확인하려면 CLI `--mask`(출력 파일 없이 안내만 stdout).

## 기존 문서의 지정 위치 이미지 쓰기 예외 (`seal` 미사용)

Kordoc 자체에는 `seal` 기능이 있지만, Second Brain의 승인된 서명·도장 배치에는 사용하지 않는다.
Kordoc `generate --image-dir`는 **새 HWPX 생성 중** 마크다운 이미지를 임베드한다. 반면 일반 래스터 이미지를 **기존 문서의 지정 위치**에 실측 배치하는 경로는 없으므로, 이 경우만 서명·도장·신분증·통장사본·증명사진·일반 사진을 `scripts/place_image.py`로 넣는다. 기존 `place_signature.py` 이름은 호환용이다.
이 경로는 `.hwpx`를 바로 처리하고, `.hwp`만 내부 `hwp_to_hwpx.py`로 임시 HWPX를 정확히 한 번 만든 뒤 같은 삽입·검증을 수행한다. 변환은 승인된 이미지 배치 요청 안에서만 허용하며 최종본은 HWPX로만 낸다.
실측 경로를 실행할 수 없으면 서명은 `seal`로, 일반 이미지는 임의 도구로 자동 우회하지 않고 원본을 그대로 둔 채 필요한 조건을 알린다.

## generate (볼트 템플릿이 없을 때만)

- 프리셋(기본 `기안문`): `기안문`·`보고서`·`계획서`·`통지`·`회의록`·`개조식`(표지·목차·장헤더 자동)·`보도자료`. 영문 별칭도 됨(official/report/plan/notice/minutes/gaejosik/press). 번호 목록이 공문서 항목부호 8단계로 자동 변환, 함초롬바탕 표준 서식.
- 표는 GFM 파이프표, display 수식 `$$...$$`은 네이티브 `<hp:equation>`.
- ` ```chart ` 펜스 → 한컴 네이티브 차트 (type/cat/계열 라인, 펜스 안 주석 금지 — 값으로 오인됨).
- 마크다운 `![](사진.png)`의 실제 PNG/JPEG/GIF/BMP를 넣으려면 `--image-dir <폴더>`를 지정한다. 새 문서 이미지에는 `place_image.py`를 쓰지 않는다.
- 표 서식은 `--profile 양식.json`으로 기관 양식 재현(아래 "서식 프로필" 절).
- 용지·조판은 `--paper`·`--landscape`·`--columns`·`--header`·`--footer`로 지정할 수 있다.
- 공문 세부 옵션이 풍부하다: 결재란 `--approval 담당,팀장,과장`, 기안문 두문·결문 `--doc-head`·`--doc-foot`, 공고 `--notice-head`, 보도자료 `--press-head`, 표지 `--org`·`--date`, 쪽번호·끝표시 `--page-numbers`·`--end-mark`. 전체는 `generate --help`.
- 생성 시 공문 표기법과 AI 흔적(`AI_*`) 검수가 자동으로 돌아 경고를 표시한다. 보고서·계획서·개조식 프리셋은 개조식 문체 경고도 자동으로 붙는다. 산출은 막지 않으니 경고를 읽고 md를 고쳐 재생성한다.
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

- 기본 룰 `rrn,phone,email,card,account` (여권·운전면허는 `--rules`로 opt-in), 마스크 문자 `--mask-char ●`.
- **먼저 `--dry-run`으로 탐지 리포트만** 보고 오탐·누락을 확인한다. 자동 검출 보조 도구이므로 결과는 사람이 최종 확인 — 이미지 속 텍스트는 못 잡는다.
- 용도: `0_원본/`에 넣기 전, 학생 개인정보가 섞인 문서를 서식 유지한 채 익명화. (수집은 여전히 수동 — 마스킹만 돕고 자동 투입하지 않는다.)

## lint (공문 표기법 검수)

`npx -y kordoc@^4 lint 초안.md` — 날짜·시간·금액·붙임 등 행정업무운영 편람 표기법과 AI 줄표·강조 남용 경고를 검사한다. 보고서·계획서 원고는 `--munche`를 붙여 서술형 종결·당위·수사·항목 길이 등 개조식 문체도 검사한다.

- 입력은 UTF-8 `md`/`txt` 또는 stdin(`-`)뿐이다. HWP/HWPX/PDF를 직접 넘기지 말고 먼저 Markdown으로 파싱한다.
- `error`가 있으면 exit 1, `--json`으로 기계 판독한다. AI·문체 warning도 검토하되 사실·규범을 훼손하면서 기계적으로 고치지 않는다.
- `generate`는 관련 lint를 자동 실행하지만 생성을 막지 않는다. 경고를 확인하고 필요한 수정을 한 뒤 재생성한다.

## 함정

- 암호가 제공된 지원 문서는 `--password`로 읽는다. 한컴 DRM·손상·미지원 구조처럼 Kordoc이 처리하지 못하는 파일은 원본을 그대로 두고 실패 이유를 보고한다. 승인된 `.hwp` 이미지 배치 작업 외에는 COM 변환이나 다른 도구로 자동 우회하지 않는다.
- `.hwp`(바이너리)와 `.hwpx`(ZIP/XML)는 다른 포맷. fill/generate 산출물은 항상 HWPX지만 **patch만은 원본 포맷을 유지**한다 (`.hwp`→`.hwp`).
- 표가 깨져 보이는 PDF는 대부분 스캔본/텍스트층 손상 — 품질 신호를 확인하고 `--ocr`로 재파싱한다. 이미지 서식은 직접 입력해 OCR한다.
