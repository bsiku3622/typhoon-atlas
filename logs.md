## 2026-11-01 — Add interactive simulation viewer

- 변경 파일: `src/Simulation.tsx`, `src/main.tsx`, `src/App.tsx`, `src/Research.tsx`, `src/styles.css`, `public/research/sim/`, `README.md`
- 요약: RE87 실행 5개를 나란히 재생하는 `#simulation` 페이지를 추가했습니다. 위에서 본 모습, 단면, 시계열이 시간에 맞춰 함께 움직입니다.

위에서 본 모습의 입자는 최하층 접선풍과 방사풍의 실제 비율로 움직이지만 재생 속도는 보기 좋게 빠릅니다. 축대칭 모델이라 구름은 동심원이고 나선 띠는 없다는 점을 페이지에 밝혔습니다. 기본 비교는 기준과 바다·대기 +2 K입니다. 대기만 데운 실험은 온난화 시나리오로 오독되기 쉬워 민감도 실험이라고 표시했습니다. 6시간 평균 출력을 위해 `PLTIME=TAVE=0.25`로 다시 실행했고, `time.out`이 원 실험과 바이트 단위로 같아 같은 모의임을 확인했습니다. 자료는 값당 1바이트로 양자화해 실험당 약 0.57 MB이므로 툴팁 값의 정밀도는 약 0.6 m/s입니다.

## 2026-11-01 — Add simulation and potential intensity research

- 변경 파일: `research/README.md`, `research/results_ko.md`, `research/simulation/`, `research/pi/`, `research/case_haiyan/`, `public/research/`, `README.md`
- 요약: RE87 수치실험, 재분석 PI 분석, 하이옌 사례의 코드와 결과 표·그림을 올리고 현황 페이지를 최종 결과로 갱신했습니다.

모델 원본은 재배포하지 않고 Zenodo를 가리킵니다. 재분석 원본과 모델 출력은 용량이 커서 뺐고, 실험 입력 사운딩과 요약 표만 넣었습니다. 동일 입력의 재실행 결과가 바이트 단위로 같으므로 출력은 다시 만들 수 있습니다. 학교 제출용 포스터와 사전 계획 문서는 저장소에 넣지 않았습니다.

## 2026-10-31 — Add research status page

- 변경 파일: `src/Research.tsx`, `src/main.tsx`, `src/App.tsx`, `src/styles.css`, `public/research/`, `README.md`
- 요약: 텀프로젝트의 가설·진행 단계·결과를 `#research`에서 보여주는 현황 페이지를 추가했습니다. 내용은 `public/research/status.json` 하나로 관리합니다.

연구 현황을 자주 갱신해야 하므로 내용을 코드에서 분리했습니다. JSON과 그림만 고쳐 main에 올리면 Vercel이 배포합니다. 현황 페이지가 지도용 대용량 CSV를 받지 않도록 `App` 안의 탭이 아니라 `main.tsx`의 해시 분기로 나눴습니다. 작업본은 `D:\Projects\Side Projects\typhoon-atlas`로 옮겼고, 맥북 작업본과 내용이 같던 미커밋 수정분과 `research/`, 분석 스크립트도 이번에 함께 커밋했습니다.

Paper UI의 `Badge` 색은 `color`가 아니라 `accent`로 지정합니다. `color`도 HTML 속성이라 타입 오류 없이 통과하지만 색이 적용되지 않습니다. `App.tsx`의 기존 `color="warning"` 배지도 같은 상태이나 이번 범위가 아니어서 그대로 두었습니다. `dev`와 `dev/*`는 Git에서 동시에 존재할 수 없어 `dev` 하나만 쓰고 `dev → main`으로 병합합니다.

## 2026-10-31 — Consolidate cyclone research notes

- 변경 파일: [연구 통합 정리](/Users/baeks/Reports/2026-10-31_19-18-wnp-typhoon-research-compendium.md); 다운로드 폴더의 Markdown 사본
- 요약: 확정한 제목·계획형 초록·연구 단계·Rotunno–Emanuel 실험안·물리 개념·선행 연구·자료 출처와 기존 예비 통계 결과를 한 문서로 모았습니다.

이전 논의의 SST 중심·습도 의존성 대안과 현재 선택한 대기 온도 독립변인 실험을 구분하고, 습도 통제는 최신 실험안의 초기 비습 고정으로 정리했습니다. MPI 계산·모델 실행 계획을 이미 완료한 관측 강도 분석과 구분했습니다. 통계 결과는 2026-10-19 원 보고서와 CSV·manifest를 확인해 수록했으며 이번 작업에서 재계산하거나 모델을 실행하지 않았습니다. 다운로드 폴더가 정리돼도 자료가 남도록 그림과 계산표 링크는 프로젝트 보관본을 가리키고 원본 Markdown은 Reports에 두었습니다.

## 2026-10-19 — Analyze WNP temperature and observed intensity

- 변경 파일: `scripts/analyze_wnp_step2.py`, `scripts/requirements-analysis.txt`, `research/step2-wnp-1980-2024/`, `README.md`; [결과 보고서](/Users/baeks/Reports/2026-10-19_16-09-wnp-cyclone-temperature-analysis.md)
- 요약: 1980–2024년 JMA 풍속 기준 열대저기압 1,141개와 HadISDH 원본 격자로 연간 추세·연도 통제 상관·HAC 불확실성 및 민감도를 계산했습니다.

풍속 평균 시간의 기관 간 혼합을 줄이려고 원본 TOKYO_WIND와 열대 단계 분류를 사용하고 spur 경로를 제외했습니다. 기온 원본 60개 영역 격자 중 전 기간 관측이 있는 격자는 14개뿐이고 서쪽에 집중되어, 전체 해역 평균이라는 해석을 피하고 32개 고관측률 격자 결과도 비교했습니다. 지역 기온은 +0.114°C/10년 추세였지만 연도 통제 후 기온–평균 최대 풍속 부분 r은 −0.080, p=0.599였습니다. 64 kt 이상 비율 감소 추세도 온난화의 인과 효과로 해석할 수 없습니다. MPI·SST·연직 환경은 아직 계산에 포함하지 않았습니다. JMA 공식 일부 연도 발생 수와 2024년 태풍급 개수를 대조하고 태풍별/연도별 합계 및 그림을 확인했습니다. 재현에 쓰인 원본은 변경하지 않았고, 패키지는 작업 전용 가상환경에만 추가했습니다.

## 2026-10-19 — Review cyclone term project feasibility

- 변경 파일: [연구 주제 적합성 검토 보고서](/Users/baeks/Reports/2026-10-19_14-50-tropical-cyclone-project-feasibility.md)
- 요약: PI 계산·관측 추세·통제 실험을 연결하는 선행 연구를 조사하고 일반지구과학 텀프로젝트의 범위와 독창성을 평가했습니다.

Done et al. (2022)와 Delfino et al. (2024)에 매우 가까운 설계가 이미 있어 온도 상승 자체를 새로운 발견으로 주장하지 않기로 했습니다. 핵심 질문은 SST만 상승시키는 경우와 대기 열구조·수증기 가정까지 변경하는 경우의 추정 차이로 좁히는 것이 적절합니다. pyPI는 열역학적 잠재강도 계산이며 실제 태풍 발달이나 연직 시어·건조 공기 유입을 직접 모의하지 않는다는 한계가 있습니다. CM1은 기준 실험 재현 후 판단할 확장으로 두고, 실제 자료 취득·성능 측정은 이번 문헌 검토에서 수행하지 않았습니다.

## 2026-09-29 — Publish the atlas

- 변경 파일: GitHub, Vercel, Cloudflare DNS; `README.md`
- 요약: 공개 GitHub 저장소에 소스와 데이터 CSV를 올리고 Vercel production에 배포했으며 `atlas.bsiku.dev`를 Cloudflare DNS로 연결했습니다.

GitHub 저장소는 `bsiku3622/typhoon-atlas`이며 Vercel에서 제공한 도메인 전용 CNAME을 Cloudflare에 DNS 전용으로 등록했습니다. DNS 확인 및 SSL 발급 후 Vercel 도메인 상태가 `Valid Configuration`으로 바뀌었고 앱·주요 CSV의 HTTP 200 응답을 확인했습니다.

## 2026-09-29 — Add temperature–cyclone relationship charts

- 변경 파일: `src/App.tsx`, `src/styles.css`, `README.md`
- 요약: 1980–2024년 기온 편차와 태풍 발생 수, 64 kt 이상 태풍 수, 연평균 최대풍속의 산점도를 추가했습니다.

HadISDH 전 지구 평균 또는 30°S–30°N 열대 평균을 선택하고 현재 해역 필터에 맞춘 IBTrACS 연간 통계를 비교합니다. 시간의 공통 상승 추세가 상관을 부풀릴 수 있어 원 Pearson r과 연도 선형 추세 제거 후 r을 함께 표시합니다. HadISDH 2 m 기온은 SST가 아니므로 이를 태풍의 열역학적 원인 분석으로 해석할 수 없다는 주의도 뷰어와 README에 밝혔습니다.

## 2026-09-29 — Apply current Paper UI typography system

- 변경 파일: `src/styles.css`
- 요약: 원본 Atlas의 글꼴 크기·굵기·행간·자간을 현행 Paper UI 텍스트 토큰에 맞췄습니다.

비교본의 검증된 타입 스케일을 반영하고, 색상 토큰과 컴포넌트 치수는 유지했습니다.

## 2026-09-29 — Keep responsive chart typography at its intended size

- 변경 파일: `src/App.tsx`
- 요약: 경로 중심 이동 그래프의 넓은 SVG에서 눈금 폰트까지 확대되던 문제를 고쳤습니다.

SVG의 viewBox 너비를 실제 컨테이너 너비에 맞춰 글자 크기가 CSS 픽셀 기준으로 유지되게 했습니다. 데이터·색상·차트 크기는 유지합니다.

## 2026-09-28 — Add Asian tropical cyclone viewer

- 변경 파일: `src/`, `public/data/ibtracs_asia_since1980.csv`, `README.md`
- 요약: NOAA IBTrACS v04r01의 1980년 이후 전 세계 CSV에서 WP·NI 행만 추려 Paper UI 기반 지도·연도별 그래프·목록 뷰어를 만들었습니다.

해역별 ID 수(WP 1,531, NI 472)를 더하면 두 해역을 통과한 태풍이 중복되므로, 합산 화면과 프로젝트 설명은 고유 SID 1,958개를 기준으로 했습니다. IBTrACS에는 명명 태풍뿐 아니라 열대저압부 등도 포함되며 2026 시즌은 진행 중이므로, 화면에 그 범위와 풍속 평균 주기의 기관별 차이를 명시했습니다.
## 2026-09-28 — Expand cyclone atlas to global climate context

- 변경 파일: `src/`, `public/data/ibtracs_global_since1980.csv`, `public/data/hadisdh_global_*.csv`, `README.md`, `scripts/`
- 요약: 태풍 뷰어를 전 세계 7개 IBTrACS 해역으로 확장하고, 연도별 발생·풍속·강도 임계치·경로 중심 그래프와 HadISDH 기온·습도 평년/편차 분석을 추가했습니다.

HadISDH는 2024년까지의 완결된 1.5.1.blend 자료를 택했습니다. 2025 자료는 잠정 자료로 공간 coverage 경고가 있어 긴 시계열 비교에 덜 적합합니다. 5° 원자료는 웹 뷰어의 크기를 줄이기 위해 10° 간격으로 표본화했고, 관측 공백은 보간하지 않습니다. 기단 조건은 온도·습도 편차의 부호를 묶은 탐색용 분류이며 기단 발생지/궤적 분석으로 해석하면 안 됩니다. NOAA 상층장은 1991–2020 월평년을 추출했습니다. 원 NCEP 기온 단위가 이미 °C라 변환을 적용하지 않도록 했습니다.
## 2026-09-28 — Align charts with Paper UI colors

- 변경 파일: `src/App.tsx`, `src/styles.css`
- 요약: 사용자 지정 그래프·지도 색을 Paper UI의 기본/정보/성공/경고/오류 토큰으로 교체하고, 배경·선·텍스트에도 Paper UI 표면 및 잉크 토큰을 적용했습니다.

태풍 강도와 기온은 파랑·중립·호박·빨강 단계로, 습도는 정보색의 농담으로 표시합니다. 기단 조건의 네 범주는 범례가 직접 뜻을 설명하므로 성공/경고/정보/기본 색을 재사용했습니다.
## 2026-09-28 — Apply Paper UI typography tokens

- 변경 파일: `src/styles.css`
- 요약: Paper UI의 Pretendard Variable 폰트, 본문·제목 크기, 줄 간격, 굵기 토큰을 화면 전반에 연결했습니다.

축·범례는 좁은 그래프에서도 기존 정보 밀도를 유지하도록 Paper UI label/caption 기준 크기의 비율로 설정하고, 주요 제목은 display/heading/subheading 위계를 따릅니다.
## 2026-09-29 — Thin graph strokes

- 변경 파일: `src/App.tsx`, `src/styles.css`
- 요약: 시계열 그래프 선과 점, 가로 격자선을 얇게 조정했습니다.

화면 축소 시 선이 데이터 점과 겹쳐 뭉쳐 보이지 않도록 선 굵기를 2px에서 1.25px로, 점 반경을 1.8px에서 1.35px로 낮췄습니다.
## 2026-09-29 — Break tracks at the map seam

- 변경 파일: `src/App.tsx`
- 요약: 태풍 경로가 날짜변경선에서 지도의 반대쪽 끝까지 이어져 생기던 가로선을 제거했습니다.

원본 경도가 아니라 지도에 투영하기 전 정규화한 경도를 비교해 날짜변경선 통과를 감지합니다. 원본 좌표의 차이만 검사하면 179°에서 181°로 이동하는 짧은 구간을 정상 선분으로 오인해 지도를 가로질렀습니다.
## 2026-09-29 — Add map zoom and repair table headings

- 변경 파일: `src/App.tsx`, `src/styles.css`
- 요약: 태풍·기후 지도에 버튼 확대/축소, 드래그 이동, 초기화 기능을 추가하고 태풍 표의 헤더 열 정렬을 고쳤습니다.

Paper UI의 `Table.Header`가 내부에서 헤더 행을 만들기 때문에 그 안에 `Table.Row`를 중첩하면 열 폭이 데이터 행과 분리됐습니다. 중첩 행을 제거하고 열 너비를 명시해 헤더와 데이터가 같은 격자를 쓰도록 했습니다. 지도는 기본 배율에서 드래그가 화면을 벗어나지 않도록 막고, 확대 후에는 경계 안에서 이동시킵니다.

## 2026-09-29 — Intercept keyboard zoom shortcuts

- 변경 파일: `src/App.tsx`, `src/styles.css`
- 요약: 지도 휠 확대 없이 포커스 상태에서 `⌘/Ctrl + +`, `⌘/Ctrl + −`로 확대·축소하고 `⌘/Ctrl + 0`으로 초기화하게 했습니다.

브라우저의 기본 확대 단축키와 충돌하지 않도록 지도에 포커스가 있을 때만 해당 키 입력을 가로챕니다. 드래그 및 화면 버튼 조작도 유지하며 키보드 포커스 테두리를 표시합니다.

## 2026-09-29 — Highlight selected storm row

- 변경 파일: `src/styles.css`
- 요약: 선택된 태풍 행을 검은 배경과 흰 글자로 표시합니다.

행 내부의 보조 SID와 풍속 강조색도 흰색으로 덮어 선택 상태에서 대비를 유지합니다.

## 2026-09-29 — Unify summary metric value size

- 변경 파일: `src/styles.css`
- 요약: 해역 범위 지표에만 따로 지정돼 있던 작은 글자 크기를 제거해 네 요약 값의 크기를 통일했습니다.

특정 범주형 값도 다른 지표 값과 같은 공통 제목 토큰을 사용하도록 맞췄습니다.

## 2026-09-29 — Pin and align storm table headings

- 변경 파일: `src/App.tsx`, `src/styles.css`
- 요약: 태풍 목록 헤더의 세로 여백을 늘리고 내부 스크롤 중 상단에 고정했으며, 시즌 헤더를 숫자 데이터의 오른쪽 정렬과 맞췄습니다.

열 너비는 기존 `colgroup` 설정을 그대로 사용해 본문과 헤더의 열 경계를 유지합니다.

## 2026-09-29 — Refine storm table styling

- 변경 파일: `src/App.tsx`, `src/styles.css`
- 요약: 선택 행을 Paper UI 회색으로 되돌리고, 태풍 목록을 넉넉한 기본 밀도와 밝은 고정 헤더, 선명한 행 구분선으로 정돈했습니다.

표의 구획은 여백과 얇은 수평선으로 만들고, 헤더는 Paper UI의 raised 표면에 두어 스크롤 중에도 본문과 구분되게 했습니다. 모바일에서는 셀 좌우 여백을 줄여 가로 공간을 보존합니다.

## 2026-09-29 — Center season and basin columns

- 변경 파일: `src/App.tsx`
- 요약: 시즌과 해역 헤더 및 데이터를 가운데 정렬했습니다.

짧은 숫자·해역 코드 열을 가운데로 맞추고, 풍속·기압 열의 오른쪽 정렬은 유지했습니다.
