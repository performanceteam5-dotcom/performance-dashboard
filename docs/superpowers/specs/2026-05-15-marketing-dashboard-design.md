# 마케팅 성과 대시보드 설계

**날짜**: 2026-05-15  
**스택**: Python + Streamlit + Pandas + Plotly  
**데이터 위치**: `C:\Users\MADUP\Desktop\clade_0514\` (로컬 폴더)

---

## 1. 목표

- 채널 데이터(`*_channel.csv`)와 AppsFlyer 데이터(`*_appsflyer.csv`)를 자동 조인
- 매일 새 파일이 추가되면 새로고침만으로 반영
- 탭 구조의 인터랙티브 대시보드로 성과 분석

---

## 2. 데이터 구조

### 채널 데이터 (`YYYY-MM-DD_channel.csv`)
| 컬럼 | 설명 |
|------|------|
| 일, 채널, 채널분류, 캠페인, 캠페인목적, 그룹, 소재 | 차원 |
| 노출, 클릭, 비용 | 채널 고유 지표 |
| 회원가입, 구매, 구매매출 | 채널 보고 전환 |

### AppsFlyer 데이터 (`YYYY-MM-DD_appsflyer.csv`)
| 컬럼 | 설명 |
|------|------|
| 일, 미디어소스, 캠페인, 그룹, 소재 | 차원 |
| 클릭, 회원가입, 구매, 구매매출 | MMP 어트리뷰션 전환 |

### 채널명 매핑
| 채널 데이터 | AppsFlyer |
|------------|-----------|
| 구글 | googleadwords_int |
| 메타 | Facebook Ads |
| 네이버 | naver_search |

---

## 3. 데이터 파이프라인

```
폴더 스캔
  → *_channel.csv 전체 읽기 → 세로로 concat
  → *_appsflyer.csv 전체 읽기 → 세로로 concat
  → 채널명 정규화 (구글 → googleadwords_int 등)
  → LEFT JOIN on [일, 캠페인, 그룹, 소재]
  → 파생 지표 계산
```

### 파생 지표
- `ROAS` = 구매매출(채널) / 비용
- `CTR` = 클릭 / 노출
- `CVR` = 구매 / 클릭
- `CPA` = 비용 / 구매
- `CPM` = 비용 / 노출 * 1000
- `AF_ROAS` = AF 구매매출 / 비용 (AF 어트리뷰션 기준)

---

## 4. 대시보드 구조 (탭 4개)

### 탭 1 — 채널 개요
- KPI 카드 4개: 총비용, 총매출, ROAS, CPA
- 채널별 비용·매출 막대 차트 (Plotly)
- 캠페인 목적별 성과 테이블
- 필터: 날짜 범위, 채널

### 탭 2 — 소재 분석
- 소재 유형별(VID/IMG/CRS) 성과 비교 차트
- 소재별 CTR · CVR · ROAS 테이블 (컬럼 정렬 가능)
- ROAS 기준 Top 10 소재 바 차트
- 필터: 채널, 캠페인, 소재 유형

### 탭 3 — 트렌드
- 날짜별 비용·매출·ROAS 라인 차트
- 채널별 일별 트렌드 멀티라인
- 필터: 채널, 지표 선택

### 탭 4 — 채널 vs AppsFlyer
- 채널 보고 클릭 vs AF 클릭 비교 (차이율)
- 채널 보고 전환 vs AF 어트리뷰션 전환 비교
- 채널별 데이터 갭 요약 테이블
- 필터: 날짜, 채널

---

## 5. 파일 구조

```
clade_0514/
├── dashboard.py          # Streamlit 앱 진입점
├── data_loader.py        # CSV 스캔·조인·파생지표 계산
├── 2025-01-01_channel.csv
├── 2025-01-01_appsflyer.csv
└── (날짜별 파일 추가됨)
```

---

## 6. 실행 방법

```bash
pip install streamlit pandas plotly
streamlit run dashboard.py
```

새 날짜 파일 추가 시 → 브라우저에서 새로고침(R키)만 하면 자동 반영.

---

## 7. 미결 사항

- 없음. 구현 준비 완료.
