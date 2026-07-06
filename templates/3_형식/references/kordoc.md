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

## 명령 치트시트

| 작업 | 명령 |
|---|---|
| 문서 → Markdown | `npx -y kordoc@^3 문서.hwp -o 문서.md` (hwpx·pdf·docx·xls 동일) |
| 페이지 범위 | `-p 1-3` 또는 `-p 1,3,5` |
| 구조화 JSON | `--format json` (blocks+metadata) |
| 서식 필드 목록 | `npx -y kordoc@^3 fill 서식.hwpx --dry-run` |
| 서식 채우기 | `npx -y kordoc@^3 fill 서식.hwpx -j 값.json -o 결과.hwpx` |
| 기존 문서 내용 수정 | `npx -y kordoc@^3 patch 원본.hwpx 편집.md -o 결과.hwpx` (`.hwp`도 가능 — 원본 포맷 유지) |
| 문서 비교 | MCP `compare_documents` (CLI엔 없음 — 양쪽을 md로 파싱해 diff해도 됨) |
| 공문서 생성 (폴백) | `npx -y kordoc@^3 generate 초안.md -o 결과.hwpx --preset 보고서` |
| 구조 검증 | `npx -y kordoc@^3 validate 결과.hwpx` |
| 도장/서명 배치 | `npx -y kordoc@^3 seal 문서.hwpx --image 도장.png --anchor "(인)" -o 결과.hwpx` |
| 조판 미리보기 | `npx -y kordoc@^3 render 문서.hwpx -o 미리보기.svg` (생성/패치본은 `--reflow`) |

## 읽기 (파싱)

- 병합·중첩 표는 GFM으로 표현이 안 되므로 HTML `<table>`(colspan/rowspan)로 나온다 — 그대로 다룬다.
- 수식은 `$...$` / `$$...$$` LaTeX.
- PDF는 텍스트층 품질 신호를 계산한다 — `needsOcr`이면 스캔/손상 PDF라는 뜻 (kordoc은 OCR 미내장, 사용자에게 알린다).
- 여러 파일은 `-d 디렉토리/` 일괄 모드.

## patch (서식 보존 편집)

① 원본을 md로 파싱 → ② md에서 내용만 수정 (구조 이동·삭제 최소화) → ③ `patch 원본 편집.md -o 수정본`.
원본의 글꼴·표·개체·조판을 보존한 채 텍스트 변경만 반영한다.

- **원본 포맷 유지**: 포맷을 감지해 `.hwp`는 바이너리 in-place 패치(`patchHwp`) → `.hwp` 출력, `.hwpx`는 ZIP 패치 → `.hwpx` 출력. `.hwp` 내용 수정에 변환이 필요 없다.
- 문단 안 강제 줄바꿈은 편집 md에 명시적 `<br>` (에디터 soft-wrap은 수정으로 안 침).
- 원본은 절대 덮어쓰지 않는다 — `-o` 필수.

## fill (서식 채우기)

0. **HWPX 전용으로 쓴다.** 스타일 보존(`hwpx-preserve`)은 원본 ZIP 직접 수정이라 HWPX에만 작동한다.
   `.hwp`를 넣으면 CLI는 조용히 `hwpx` 모드로 전환("HWPX가 아니므로 hwpx 모드로 전환합니다") —
   파싱한 내용을 새 HWPX 표로 **재구성**하므로 병합·열너비가 깨진다 (도현 실측). MCP `fill_form`도
   `output_format: hwpx`면 동일한 재구성 경로다. `.hwp` 채우기는 한컴 COM으로 `.hwpx` 1회 변환 후 fill.
1. `--dry-run`으로 라벨 목록 먼저 파악.
2. 값은 `-j 값.json` 권장 (`-f 'k=v'`는 셸 히스토리에 값 노출). 다중줄은 JSON 문자열 안 `\n`.
3. 같은 라벨이 2곳 이상이면 **모든 칸에 채운다** — 반복 라벨 서식은 값을 배열로 주거나 어느 칸인지 확인 후 채운다.
4. 기본 출력은 원본 글꼴·정렬 보존(`hwpx-preserve`).
5. 주민번호·계좌 등 채운 값은 응답에 되풀이하지 않는다.

## seal (도장 배치)

앵커 문구("(인)" 등) 위/옆에 이미지를 글 앞 부유로 얹는다 — 표·페이지가 밀리지 않음.
같은 앵커 여럿이면 `-n <0-based>`, 위치 보정 `--dx`/`--dy`(mm), 크기 `--size-mm`. 투명 PNG 권장. HWPX 전용.
중첩표·글상자·복잡 rowSpan은 근사 배치(warnings 고지) — 배치 후 `render --reflow`로 확인.

## generate (볼트 템플릿이 없을 때만)

- 프리셋: `기안문`·`보고서`·`계획서`·`통지`·`회의록`. 번호 목록이 공문서 항목부호 8단계로 자동 변환, 함초롬바탕 표준 서식.
- 표는 GFM 파이프표, display 수식 `$$...$$`은 네이티브 `<hp:equation>`.
- ` ```chart ` 펜스 → 한컴 네이티브 차트 (type/cat/계열 라인, 펜스 안 주석 금지 — 값으로 오인됨).
- 생성 후 반드시 `validate` 통과 확인.

## 함정

- 암호 보호·DRM 배포본은 파싱 불가 → 이때만 한컴 COM 폴백 (`scripts/convert_hwp.py`).
- `.hwp`(바이너리)와 `.hwpx`(ZIP/XML)는 다른 포맷. fill/generate 산출물은 항상 HWPX지만 **patch만은 원본 포맷을 유지**한다 (`.hwp`→`.hwp`).
- 표가 깨져 보이는 PDF는 대부분 스캔본/텍스트층 손상 — 품질 신호를 근거로 설명한다.
