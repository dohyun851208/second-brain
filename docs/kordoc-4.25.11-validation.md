# Kordoc 4.25.11 호환성 검증

2026-11-24 · Second Brain 시스템 3.13 · 이전 검증판 4.24.47

공식 GitHub 릴리스, npm `latest`, `npx -y kordoc@^4 --version`, 고정판 `npx -y kordoc@4.25.11 --version`이 모두 4.25.11이었다. 공식 태그의 커밋 `0a1f36aab53de137ef04b0738ffb2f36dccf78cd`를 기준으로 변경 기록과 CLI 구현을 비교했다. 실행 범위는 `@^4`다. [공식 릴리스](https://github.com/chrisryugj/kordoc/releases/tag/v4.25.11) · [4.24.47 이후 변경](https://github.com/chrisryugj/kordoc/compare/v4.24.47...v4.25.11)

## CLI 스모크 테스트

Windows, Node.js 24.13.0에서 고정판 CLI를 스모크 테스트로 43회 실행했다. 아래 표에는 별도로 실행한 XLS·lint·그림 링크 이동 검사도 포함한다. 임시 폴더에 만든 합성 자료와 공식 Kordoc 테스트 파일을 사용했다. 각 CLI 호출은 `KORDOC_OFFLINE=1`, `KORDOC_NO_HANCOM=1`을 설정한 상태에서 실행했다.

| 항목 | 결과 |
|---|---|
| Markdown → HWPX → Markdown | 한글 이름 PNG 1장 임베드, 구조 검증 통과. 공백·괄호·한글을 포함한 두 출력명에서 문서별 그림 폴더와 manifest를 확인했다. 한 폴더를 볼트 규약에 맞춰 옮긴 뒤 링크와 manifest의 파일이 일치했다. JSON의 `pages[]`와 `metadata.pageMode: section`도 확인했다. |
| HWPX 표 수정 | UTF-8·LF 원고는 exit 0, 구조 검증과 재파싱 일치. 같은 CRLF 원고도 수정값과 구조 검증을 통과했지만 검증 잔차 경고가 났다. 그림이 있는 `-o` 추출본을 편집 원고로 사용하면 exit 2·이미지 변경 `SKIP`·`.rewrite.hwpx` 생성이 재현됐다. 작업 전후 원본의 SHA-256이 일치했다. |
| 양식 채우기·비교·렌더 | `fill --dry-run -j`에서 목표 좌표를 확인한 뒤 `--require-unique`로 채웠고, 구조 검증과 재파싱으로 입력값을 확인했다. `compare --json`은 동일 문서에서 exit 0, 변경 문서에서 exit 1을 반환했다. 페이지 PNG 렌더도 확인했다. |
| 실패 JSON·암호·한컴 차단 | 없는 입력 또는 출력 폴더에서 exit 1·`FILE_NOT_FOUND`. 암호 HWPX는 `ENCRYPTED`를 반환한 뒤 `KORDOC_PASSWORD`를 받은 호출에서 파싱 성공. 한컴 차단을 켜면 명시적인 `to-hwpx --engine hancom`도 exit 2로 중단됐다. |
| HWP·DOCX·XLS·PDF 파싱 | HWP5 파싱과 `to-hwpx --engine kordoc` 결과의 구조 검증 통과. DOCX는 JSON의 파일 유형과 본문을, XLS는 Markdown 출력을 확인했다. 텍스트 PDF는 한글 본문·표 값·셀 좌표를 확인했고 `-o 결과.hwpx`의 출력은 구조 검증을 통과했다. |
| 한글 OCR | 캐시된 모델로 합성 PNG를 읽고 숫자 값, 줄별 인식 후보, OCR 래스터 크기를 확인했다. |
| 보고서 생성 | `measure --json`에서 PDF 글꼴·여백 측정값을 확인하고 `--layout`·`--toc`를 사용해 목차가 있는 보고서를 생성했다. 구조 검증을 통과했고 `--plain --layout` 조합은 exit 1로 거부됐다. |
| 원고 검수·마스킹 | `lint --json --munche`에서 `DA_ENDING`과 exit 1을 확인했다. `redact` 기본 전화번호 규칙은 dry run에서 본문·미리보기를 탐지했고, 처리 결과를 재파싱해 가려진 값을 확인했다. |

## 저장소 검사와 범위

`SECOND_BRAIN_HANCOM_INTEGRATION=1`을 설정한 `python -X utf8 -m unittest discover -s tests` 49개 통과. 실제 한컴 COM으로 테스트 HWP를 HWPX로 변환하는 기존 통합 테스트를 포함했다. 스킬 메타데이터 검증과 `git diff --check`도 통과했다.

양식의 기본 입출력은 HWPX로 유지했다. 선택적인 HWP 바이너리 내보내기·인명 및 주소 탐지 모델과 `seal`의 자산별 한컴 배치는 이번 실측 범위 밖이다. 기존 문서의 지정 위치에 이미지를 넣을 때는 `place_image.py`를 사용한다.
