# Kordoc 4.24.47 호환성 검증

2026-11-06 · Second Brain 시스템 3.12 · 이전 검증판 4.15.7.

## 대상과 반영 범위

- npm `latest`, `npx -y kordoc@^4 --version`, 고정판 `kordoc@4.24.47`이 모두 4.24.47임을 확인했다. 실행 범위는 기존 `@^4`를 유지한다.
- 공식 [v4.24.47](https://github.com/chrisryugj/kordoc/tree/v4.24.47), 커밋 `69f3dfa4fef50bb2536619a35f54f703376bc090`과 [변경 기록](https://github.com/chrisryugj/kordoc/blob/v4.24.47/CHANGELOG.md), CLI 도움말·관련 구현을 검토했다. main의 Unreleased 변경은 검증판에 포함하지 않았다.
- 엔진은 npm에서 실행하며 소스를 Second Brain에 복제하지 않는다. 환경은 Windows, Node.js 24.13.0, Python 3.14.3, 설치된 한컴이었다. 엔진 최소 요구사항은 Node.js 20이다.
- 문서별 그림 폴더, patch용 구조 보존 파싱, fill 사전 좌표 계획, 부분 patch 대체본, OCR 옵션·DOCX 쪽 경계 조건을 지침에 반영했다. 기존 승인 이미지 배치 스크립트는 변경하지 않았다.

## 실제 실행 검증

볼트 밖 임시 폴더에서 고정판 CLI로 30회 실행했고, 각 종료 코드와 아래 결과를 확인했다. 종료 코드 1·2를 의도한 제한·실패 사례도 포함한다. 테스트 산출물은 임시 폴더 종료 시 삭제했다.

| 항목 | 결과 |
|---|---|
| 합성 Markdown → HWPX, 한글 파일명 PNG 임베드 | exit 0, 이미지 1개, 구조 검증 통과 |
| 공백·괄호·한글을 포함한 출력명으로 그림 추출 | `images/<출력 stem>/`의 이미지·manifest 생성, 각 링크가 실제 파일을 가리킴 |
| 같은 폴더에 두 번째 문서 추출 | 두 문서의 이미지 폴더·manifest가 각각 유지됨 |
| `--format json --image-refs` | success, `pages[]`, 생성본 `metadata.pageMode: section` 확인 |
| 구조 보존 stdout 원고의 LF·CRLF 표 수정 | 둘 다 exit 0, validate 통과, 재파싱에서 수정값 확인 |
| `-o`로 그림을 추출한 원고의 patch | 예상대로 exit 2, 이미지 변경 SKIP과 `.rewrite.hwpx` 생성 확인 |
| `fill --dry-run -j` → `fill --require-unique` | 계획 출력, 채움 exit 0, validate·재파싱 값 대조 통과 |
| `render --format png` | exit 0, 페이지 PNG 생성 확인(픽셀 단위 시각 검증은 아님) |
| `lint --json --munche` | 서술형 테스트 문장에 `DA_ENDING`, 예상 exit 1, JSON 파싱 성공 |
| 없는 입력 / 없는 출력 폴더 | 예상 exit 1과 `FILE_NOT_FOUND`; 없는 입력의 출력물 미생성 확인 |
| 저장소의 1차시·8차시 음악 수업 지도안 HWPX 2건 | 구조 보존 Markdown 파싱·validate 통과, 원본 SHA-256 불변 |
| 합성 문서를 한컴으로 저장한 HWP5 | 파싱·본문 patch·재파싱 수정값 확인 |
| 같은 HWP5의 `to-hwpx --engine kordoc` | exit 0, 변환 HWPX validate 통과 |

핵심 명령(재현할 때 `@4.24.47`로 고정):

```powershell
npx -y kordoc@4.24.47 generate source.md --plain --image-dir images -o source.hwpx
npx -y kordoc@4.24.47 source.hwpx --keep-layout-tables --keep-empty-cols
npx -y kordoc@4.24.47 patch source.hwpx edit.md -o patched.hwpx
npx -y kordoc@4.24.47 fill source.hwpx --dry-run -j fields.json
npx -y kordoc@4.24.47 fill source.hwpx -j fields.json --require-unique -o filled.hwpx
npx -y kordoc@4.24.47 validate filled.hwpx
npx -y kordoc@4.24.47 render source.hwpx --format png -d pages
```

그림 포함 patch의 편집 원고는 두 번째 명령의 stdout을 UTF-8·LF로 저장해 만든다. `-o`로 생성된 공유용 Markdown의 그림 경로를 그대로 patch에 넣지 않는다. 자세한 절차는 `templates/9_형식/references/workflows/hwpx-forms.md`에 있다.

## 저장소 검사와 제한

`py -3 -X utf8 -m unittest discover -s tests -v`: 49개 중 48개 통과, 선택 한컴 COM 통합 테스트 1개 건너뜀. 위 별도 스모크에서는 실제 한컴으로 테스트 HWP를 저장한 뒤 최신 Kordoc의 파싱·patch·변환을 실행했다. `git diff --check` 통과.

- 그림 링크가 포함된 추출본의 patch 제한을 재현했으므로 stdout 기반 편집 원고를 안내한다. exit 2나 대체본 생성을 서식 보존 성공으로 취급하지 않는다.
- 최신 HWP5 fill 지원에도 변환 불가 입력의 CLI 재구성 폴백이 남아 있다. 볼트의 기본 fill은 HWPX에 한정하고, 자동 COM 우회는 기존 승인 이미지 예외 안에서만 허용한다.
- `seal`의 서명·신분증·통장사본 등 자산별 한컴 좌표·비율 실측은 이번에 재검증하지 않았다. 기존 `place_image.py` 경로를 유지한다.
- PDF/OCR·DOCX·XLS의 대규모 정확도 검증, 암호·DRM·손상 문서, 견본/기관팩 생성은 이번 스모크 범위 밖이다. 해당 기능 안내는 공식 소스·CLI 계약 확인에 근거하며 모든 문서에서의 품질을 보증하지 않는다.
