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
