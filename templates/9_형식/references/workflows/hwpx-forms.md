# HWP/HWPX 양식 작성

HWPX는 ZIP 내부 XML이다. 양식의 표, 이미지, 스타일을 최대한 유지하고 텍스트만 채운다.

적용 범위: 이 절차는 **서식 채우기·구조 편집**(XML 수준 작업)용이다. 기존 문서의 단순 내용 수정은
`kordoc patch`가 기본 경로다 — 원본 포맷 유지(`.hwp`→`.hwp`, `.hwpx`→`.hwpx`), 변환·COM 불필요
(`라우팅.md`, `references/kordoc.md` 참조).

## 기본 흐름

최종 산출물이 HWPX일 때의 기본 경로:

원본 `.hwp` -> 임시 `.hwpx` 변환 -> HWPX ZIP/XML 직접 편집 -> `validate.py` 구조 검증 -> 주요 입력값 확인 -> 최종 `*_완성본.hwpx` 저장 -> 임시 파일 삭제

1. `.hwp` 원본은 한글 COM으로 임시 `.hwpx` 작업본을 1회 만든다. 원본이 이미 `.hwpx`이면 원본을 덮어쓰지 말고 복사본을 작업본으로 둔다.
2. `scripts/clone_form.py --analyze 작업본.hwpx`로 문단, 표, 텍스트 조각을 확인한다.
3. 단순 기존 텍스트 치환이면 `clone_form.py --map map.json`을 사용한다.
4. 빈 표 셀을 채워야 하면 `Contents/section0.xml`의 표/셀 구조를 분석하고 XML을 직접 수정한다.
5. 편집 결과는 최종 산출물로 `.hwpx`만 유지한다. 다시 `.hwp`로 저장하지 않는다.
6. `scripts/validate.py` 구조 검증과 `Contents/section0.xml` 직접 확인으로 주요 값이 유지되는지 확인한다.
7. 임시 변환본, 압축 해제 폴더, 임시 스크립트 산출물은 삭제한다.

기본으로 하지 않을 것:

- `_완성본.hwp` 생성
- 완성된 HWPX를 한컴 COM으로 재저장
- 검증용 HWPX 별도 생성
- PDF/이미지 렌더링 검증

## HWP를 임시 HWPX로 변환

한글 COM 자동화 객체는 항상 사용 가능하다고 전제한다. 사용 가능 여부를 사용자에게 묻거나 사전 점검 코드를 돌리지 말고 바로 변환을 시작한다. 이는 최종 HWP를 만드는 과정이 아니라, 원본 HWP를 편집 가능한 HWPX로 꺼내는 1회 변환이다.

1. 한글 COM 객체를 만들고 창을 숨긴다.
2. `RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")`를 먼저 호출한다.
3. `SetMessageBoxMode(0x00020000)`로 대화상자 때문에 멈추는 상황을 줄인다.
4. `Open(input, "", "forceopen:true")`로 원본 HWP를 연다.
5. `SaveAs(temp_work.hwpx, "HWPX", "")`로 임시 HWPX 작업본을 저장한다.
6. 저장된 임시 HWPX에 대해 `validate.py`, `clone_form.py --analyze`, 주요 텍스트 포함 여부를 확인한다.

주의:

- HWPX 변환은 최대 1회만 표준 경로로 시도한다.
- 한글 COM은 이 준비 단계에만 사용한다. 최종 `*_완성본.hwpx`를 정리하려고 `Open` + `SaveAs(..., "HWPX")`를 다시 수행하지 않는다.
- `scripts/convert_hwp.py`처럼 외부 레포나 추가 설치에 의존하는 변환기는 COM 표준 경로 실패 뒤 구조 분석 보조용으로만 고려한다.
- COM 변환이 30초 이상 멈추면 한글 프로세스를 정리하고 같은 변환을 반복하지 않는다.
- HWPX 변환이 성공했어도 원본과 결과의 표 개수, 핵심 표의 `rowCnt`/`colCnt` 또는 이에 대응하는 구조가 달라지면 원본 표 보존 실패로 보고 자동 fallback하지 않는다. 사용자 승인이나 별도 지시를 받은 뒤 비기본 복구 경로를 선택한다.

## HWPX 변환 실패 시

기본 경로에서는 HWPX 변환 실패 뒤 자동 우회를 하지 않는다. 실패 사실, 멈춘 단계, 원본 보존 위험을 사용자에게 짧게 알리고 다음 지시를 받는다.

- 한글 COM `Open` 또는 `SaveAs(..., "HWPX")`가 30초 이상 멈추거나 보안/변환 문제로 실패하면 같은 시도를 반복하지 않는다.
- HWPML2X 추출, `SetTextFile`, 임시/최종 HWP 저장은 기본으로 사용하지 않는다.
- `md2hwpx.py`로 새 HWPX 표를 다시 그리는 방식도 사용하지 않는다. 사용자가 명시적으로 "새 양식으로 다시 만들어도 됨"이라고 한 경우를 제외하면 기존 표가 깨진 산출물이 된다.
- 가능한 선택지는 사용자가 변환된 HWPX를 제공하기, 비기본 HWPML2X 복구 경로를 승인하기, 새 HWPX 양식 재작성을 승인하기 중 하나로 정리해 제안한다.

## 텍스트 추출

- 빠른 확인: `Preview/PrvText.txt`
- 기본 확인: ZIP 안의 `Contents/section0.xml`을 열고 `<hp:t>` 텍스트, 표 셀 주소, 입력값 포함 여부를 직접 확인한다.
- `scripts/text_extract.py`는 선택 검증이다. 이 스크립트는 `python-hwpx`가 없으면 실패할 수 있으므로 기본 경로에 넣지 않는다.
- 이미 `python-hwpx`가 설치되어 있고 표 텍스트를 추가로 보고 싶을 때만 `& $py "scripts/text_extract.py" "결과.hwpx" --include-tables`를 사용한다.

## PowerShell 임시 Python 실행

PowerShell에서 여러 줄 Python 코드를 실행할 때는 Bash식 heredoc 또는 긴 `python -c "..."` 인자 전달을 피한다. BOM, 따옴표, 한글 경로 때문에 분석 단계가 실패하기 쉽다.

임시 `.py`/`.json` 파일을 PowerShell 리다이렉트(`>`, `Out-File`, `Set-Content`)로 만들지 않는다. 파일 앞에 BOM이 붙어 첫 글자에서 파싱이 실패한다. 에이전트의 파일 쓰기 도구 또는 Python `encoding="utf-8"` 쓰기로 만든다.

Codex 데스크톱에서는 먼저 `load_workspace_dependencies`로 번들 Python 경로를 확인하고 `$py`에 담아 실행한다. bare `python`을 기본 예시로 쓰지 않는다. HWP COM 변환 fast path에는 `pywin32`/`win32com`이 필요하고, XML 조작 도구에는 `lxml`이 필요할 수 있으므로 번들 Python 또는 해당 모듈이 있는 고정 Python을 사용한다.

안정적인 실행 템플릿:

```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
$env:PYTHONIOENCODING='utf-8'
$py = "<load_workspace_dependencies로 확인한 python.exe 경로>"
$code = @'
import sys
print("ok")
'@
$code | & $py -c "import sys; exec(sys.stdin.read().lstrip(chr(0xfeff)))"
```

같은 분석 코드를 반복할 때는 임시 인자 조립을 계속 고치지 말고 스크립트 파일 또는 기존 `scripts/` 도구로 옮긴다.

## 빈 셀 채우기

빈 run의 일반 패턴:

```xml
<hp:run charPrIDRef="N"/>
```

채운 패턴:

```xml
<hp:run charPrIDRef="N"><hp:t>텍스트</hp:t></hp:run>
```

주의:

- 빈 문자열을 순차 replace로 skip하지 않는다. 같은 빈 run이 반복 매칭될 수 있으므로 위치 또는 셀 주소 기반으로 치환한다.
- 이미 문단과 run이 있는 표 셀은 새 문단을 재작성하기보다 원본 `<hp:p>`와 `<hp:run>` 개수를 유지하며 기존 run 내부 텍스트만 바꾼다.
- 한 문단에 run이 여러 개 있으면 첫 run에 새 텍스트를 넣고 나머지 run은 빈 run으로 정리한다. 그렇지 않으면 기존 텍스트가 뒤에 남아 중복될 수 있다.
- 새 줄 수가 원본 문단 수보다 많으면 셀 폭 기준으로 내용을 더 짧게 압축하거나 마지막 문단에 합친다. 검증 통과를 위해 임의 문단, 빈 run, XML 주석을 덧붙이지 않는다.
- 편집 전후 같은 셀의 `cellAddr`, `cellSpan`, `cellSz`, `cellMargin`, `subList` 속성, 문단 수, run 수가 유지되는지 비교한다. 값이 줄어들면 양식 보존 실패로 보고 다시 편집한다.
- `INPUT=OUTPUT` 저장은 금지한다. 임시 파일을 만들고 마지막에 이동한다.
- 한글 파일명/경로에서 이동 실패가 날 수 있으면 영문 임시 파일을 사용한 뒤 rename한다.
- 단순 텍스트 삽입은 보통 `fix_namespaces.py` 후처리가 필요 없다.

## 서명 이미지 삽입

개인정보 동의서, 확인서, 신청서처럼 하단에 `성명 : ... (인 또는 서명)` 문구가 있는 양식은 다음 순서가 안정적이다.

볼트 안의 서명을 사용할 때는 먼저 `7_개인정보이미지/자산목록.md`에서 후보를 고르고
`7_개인정보이미지/_안내.md`의 승인 규칙을 확인한다. 사용자가 해당 문서에 서명을 넣으라고 명시하지 않았다면
삽입 전에 대상 문서·서명 자산·용도를 제시해 승인받는다. 원본 서명 이미지는 수정하지 않는다.

1. 원본 `.hwp`는 한글 COM `Open` + `SaveAs(..., "HWPX")`로 먼저 임시 HWPX 작업본을 만든다.
2. 날짜, 생년월일, 성명 같은 텍스트 값을 **먼저** 채운다 (`fill_cells.py` 또는 `<hp:t>` 치환). 서명 위치는 채워진 글자를 기준으로 잡으므로 순서가 뒤바뀌면 안 된다.
3. 그림 배치는 **`scripts/place_signature.py`가 정본이다.** 좌표를 손으로 계산하지 않는다.

```powershell
# 먼저 양식을 mm로 본다
& $py "$SKILL_DIR\scripts\place_signature.py" "작업본.hwpx" "서명.png" `
    --report --find "홍길동" --find "(서명)"

# 기준 글자로 배치한다
& $py "$SKILL_DIR\scripts\place_signature.py" "작업본.hwpx" "서명.png" `
    --output "원본_완성본.hwpx" `
    --anchor-para "4. 위 사항을 준수하겠습니다" --after-text "홍길동" --width-mm 24
```

- `--after-text`: 서명이 그 글자가 끝나는 지점에서 시작해 그 줄에 세로 중앙 정렬된다.
- 바로 아래에 **다른 사람의 도장·서명란**이 있으면 자동으로 그 위까지만 내린다. 남의 표시를 덮지 않는 것이 우선이다.
- `--anchor-para`는 목표보다 **위에 있는** 문단이어야 한다.
- 승인받은 배치를 재현할 때는 `--target-left-mm` / `--target-bottom-mm`으로 좌표를 고정한다.
- 스크립트는 탐침 1회 → 임시 PDF 렌더 → 실측 → 역산 → 재생성 → 검증까지 하고 오차 0.05mm 안에 맞춘다. 임시 PDF는 자동 삭제된다.

4. 최종본은 한글 COM으로 `Open` + `SaveAs(..., "HWPX")` 재저장하지 않는다.

주의 (모두 실측으로 확인, 2026-07-31):

- **`imgClip`은 원본 이미지 좌표계다** (픽셀 x 75, 96dpi). 여기에 표시 크기를 넣으면 원본에서 그만큼만 잘라내 확대해 그린다 — 212px 서명을 20mm로 넣으면 왼쪽 36%만 남아 첫 획만 보인다. `curSz`/`sz`가 표시 크기, `scaMatrix`가 둘의 비율이다.
- **구조 검증은 이 오류를 못 잡는다.** 위 상태의 파일이 `validate.py`를 그대로 통과했다. 서명·도장은 반드시 렌더링해서 눈으로 확인한다.
- **음수 `vertOffset`은 0으로 잘린다.** 그림은 앵커 문단 상단 위로 못 올라가고, 오류 없이 그 자리에 붙는다.
- **중첩표에서 문단을 정규식으로 자르지 않는다.** `<hp:p\b.*?</hp:p>`는 표를 품은 문단에서 안쪽 문단의 닫는 태그에 먼저 걸린다.
- 서명 이미지는 원본 PNG의 투명 배경을 그대로 쓴다. `(서명)` 표기를 덮어도 되지만 `textWrap`은 `BEHIND_TEXT`여야 글자가 위에 남는다.
- 원본 `.hwp`에는 쓰지 말고, 변환본과 최종본을 별도 경로로 만든다.
- 직접 ZIP을 다시 쓸 때 `mimetype` 엔트리는 `ZIP_STORED`로 유지한다.

## 표 구조 분석

- 겹표 여부: `re.findall(r'<hp:tbl\b', xml)` 개수 확인
- 각 셀의 주소: `<hp:cellAddr colAddr="C" rowAddr="R"/>`
- 각 셀의 크기: `<hp:cellSz width="W" height="H"/>`
- 각 셀의 텍스트: 해당 `<hp:tc>...</hp:tc>` 내부의 `<hp:t>`

열 헤더와 데이터 열은 반드시 실제 셀 주소로 매핑한다. 예를 들어 `연수기간(차시)`처럼 두 항목이 한 열에 합쳐진 양식은 기간과 시간을 같은 셀에 압축해 써야 한다.

## 셀 폭에 맞춘 작성

- 폰트 크기: `Contents/header.xml`의 `<hh:charPr id="N" height="H">`, `H/100 = pt`
- 유효 폭: `cellSz width - 좌우 margin`
- 한글 1글자 폭은 대략 `pt * 0.9~1.0 * 100` HWPUNIT 수준으로 보고 여유 있게 줄당 글자 수를 잡는다.
- 기본 원칙은 내용을 축약하지 않고 의미 단위로 강제 줄바꿈하는 것이다. 한 문단을 긴 한 줄로 넣지 말고 여러 문단 또는 여러 짧은 줄로 나눈다.
- 좁은 열이 많은 단계형·목록형 표는 짧은 제목 1줄과 짧은 불릿 3~4개로 나눈다. 예시 문장도 `예)`, 상황, 요청을 2~4줄로 분리한다.
- 행 높이가 낮은 1쪽 고정 양식은 페이지 수를 유지한다. 이때는 행 높이를 크게 늘리기보다 양식에 있는 작은 글자 스타일을 먼저 찾고, 셀 안에서 짧은 의미 줄로 나눈다.
- 내용이 물리적으로 들어가지 않는 경우에는 임의로 삭제하지 말고, 중요도가 낮은 항목을 `확인 필요` 또는 별도 첨부/추가자료 대상으로 남길지 판단한다.

줄당 글자 수의 보수적 기준:

| 셀 유효 폭 | 권장 줄 길이 | 작성 방식 |
| --- | --- | --- |
| 5,000~7,000 HWPUNIT | 한글 5~8자 | 명사구 중심, 2~3줄 |
| 7,000~11,000 HWPUNIT | 한글 8~12자 | 짧은 불릿, 긴 기관명은 줄바꿈 |
| 11,000~18,000 HWPUNIT | 한글 12~18자 | 제목 1줄 + 불릿 3~4개 |
| 18,000~30,000 HWPUNIT | 한글 20~30자 | 문장 1개를 2~3줄로 분할 |
| 30,000 HWPUNIT 이상 | 한글 35~55자 | 문단형 가능, 필요 시 작은 글자 스타일 사용 |

## 검증

기본 검증은 구조와 주요 입력값 확인으로 끝낸다. 검증용 HWPX를 별도로 만들거나, 완성본을 한컴 COM으로 재저장하거나, PDF/이미지 렌더링을 수행하지 않는다.

- `& $py "scripts/validate.py" "결과.hwpx"`
- ZIP 안의 `Contents/section0.xml`에서 주요 입력값, 표 셀 주소, 병합, 문단/run 구조를 직접 확인한다.
- 주요 값 count 확인
- 원본 대비 표 개수, 셀 주소, 병합, 셀 크기, 여백, 문단 수, run 수를 비교한다. 남은 기존 텍스트나 중복 텍스트는 직접 확인한다.
- `scripts/verify_hwpx.py`는 구조 차이가 의심될 때만 선택 검증으로 사용한다. `--result`가 필수 인자다:
  `& $py "scripts/verify_hwpx.py" --source "원본.hwpx" --result "결과_완성본.hwpx"` (원본 비교 생략 시 `--source` 없이 `--result`만)
- `scripts/text_extract.py`는 `python-hwpx`가 이미 있을 때만 선택 검증으로 사용한다.
- 이전 양식의 고유 placeholder나 예시 문구가 남았는지 검색한다. 예: `(     분)`, `○○`, 원본 예시 문장.
- 검증 경고를 없애려고 section 크기 보정용 XML 주석, 의미 없는 빈 run, 임의 문단을 추가하지 않는다. 그런 보정은 통과처럼 보이지만 제출본 품질을 낮춘다.
- 사용자가 요청했거나 최종 제출본에서 글자 겹침·잘림 위험이 높다고 판단될 때만 시각 검증을 제안한다. 이 경우에도 먼저 사용자에게 말하고, HWPX를 열더라도 재저장하지 않는다.
- 검증 뒤 임시 변환본, 임시 압축 해제 폴더, 분석용 임시 파일을 삭제한다.
