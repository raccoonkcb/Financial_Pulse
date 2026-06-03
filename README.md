# 📊 Finance Pulse (금융박동) - 금융 뉴스 기반 거시적 시장 심리 대시보드

> **"금융 뉴스로 시장의 맥박을 읽다."**
> 
> 본 프로젝트는 한국 및 해외의 방대한 경제 뉴스 데이터를 실시간 배치로 수집하고, 금융 도메인 특화 AI 모델(FinBERT)을 통해 시장의 거시적 투자 심리 추세와 섹터별 긍·부정 흐름을 직관적으로 시각화하는 **AI 기반 금융 데이터 엔지니어링 프로젝트**입니다.

---

## 1. 프로젝트 요약 (Overview)
* **팀명:** 금융박동
* **개발 기간:** 2026년 5월 ~ 
* **핵심 타겟:** 정보의 비대칭성 및 파편화된 뉴스 속에서 거시적인 투자 심리 흐름을 직관적으로 파악하고자 하는 스마트 개인 투자자 및 자산 관리자.
* **주요 기능:** * 한국(네이버 금융, 한국경제)/해외 경제 뉴스 대량 실시간 배치 크롤링
  * FinBERT / KR-FinBERT 기반 금융 감성 분석 (Sentiment Analysis)
  * Zero-shot Classification 기반 뉴스 7대 섹터 자동 분류
  * Elasticsearch 역색인을 활용한 형태소 전문 검색 및 대시보드 실시간 집계(Aggregation)
  * 독자적인 가드레일 기반 미수집 로그 추적 및 어드민 수동 복구 제어 기능

---

## 2. 기술 스택 (Technical Stacks)

### Data Engineering & Infrastructure
* **Storage & Search Engine:** Elasticsearch (주 저장소, 전문 검색 및 실시간 집계 특화), MariaDB (메타데이터 및 사용자 정보 관리)
* **Backend Framework:** FastAPI (Python 기반 고성능 비동기 API 서버)
* **Automation & DevOps:** Linux (Ubuntu), Crontab (수집 스케줄링 제어), Cloudflare Tunnel

### Web Scraping Pipeline
* **Libraries:** Selenium WebDriver (Dynamic Web Scraping), BeautifulSoup4, Requests
* **Concurrency:** Python `queue.Queue` & `threading` 기반 멀티스레드 분산 수집 아키텍처

### AI & Natural Language Processing
* **Hugging Face Transformers:** * `ProsusAI/finbert` (영어 뉴스 감성 분석 담당)
  * `snunlp/KR-FinBERT-SC` (한국어 금융 도메인 특화 감성 분석 담당)
  * `BART-large-MNLI` / `mBART-large-50` (Zero-shot 섹터 분류 파이프라인)

---

## 3. 핵심 아키텍처: 감성 점수 (Sentiment Score) 계산 로직

Finance Pulse의 가장 핵심적인 정량 지표인 **감성 점수**는 개별 뉴스의 미시적 평가에서 시작하여 거시적 섹터 지표로 융합되는 **2단계 데이터 파이프라인**을 가집니다.

### 3.1. 1단계: 개별 기사의 정량 점수화 (Article Scoring)
수집된 뉴스 본문 텍스트는 분리된 언어별 파이프라인(영어: FinBERT / 한국어: KR-FinBERT)을 거쳐 최종 Softmax 레이어를 통과합니다. Softmax의 결과물로 `[Positive(긍정), Neutral(중립), Negative(부정)]` 확률값(합산 1.0)이 출력됩니다. 

시장의 낙관론과 비관론 척도를 선형 왜곡 없이 직관적으로 매핑하기 위해 **'긍정(Positive) 확률값'**을 대표 지표로 채택하여 100을 곱하는 표준화 연산을 수행합니다.

$$\text{Article Sentiment Score} = \text{Softmax}(\text{Positive Probability}) \times 100$$
*(단, 점수의 범위는 $0 \le \text{Score} \le 100$)*

> **💡 수식 채택 사유 (꼬리 질문 방어):** > Softmax 특성상 세 클래스의 합은 항상 1입니다. 즉, 긍정 확률이 높아지면 부정과 중립의 파이는 반비례하여 줄어듭니다. 굳이 부정 확률을 빼는 복잡한 수식을 쓰면 대역이 마이너스로 내려가 직관성을 해치므로, 시스템 아키텍처를 슬림하게 유지하면서 왜곡 없이 감성을 반영할 수 있는 긍정 확률 스케일링을 채택했습니다.

### 3.2. 2단계: 섹터별/기간별 종합 성향 점수 산출 (Composite Index)
산출된 기사별 점수들은 데이터 저장 단계에서 지정된 **7대 섹터** 및 **크롤링 배치 타임라인**별로 묶여 Elasticsearch 인덱스 내에서 **산술 평균(Mean)**으로 실시간 집계(Aggregation)됩니다.

$$\text{Composite Sentiment Score} = \frac{\sum_{i=1}^{N} \text{Article Sentiment Score}_i}{N}$$
*($N = \text{선택한 섹터 및 타임라인 내 전체 분석 대상 기사 수}$)*

### 3.3. 구체적 연산 시뮬레이션 예시
오전 11:30 배치 타임라인에 'IT/기술' 섹터 뉴스가 총 3건 수집되었을 때의 실제 내부 스코어링 변화:

1. **기사 A (강한 호재):** FinBERT 예측 `[Positive: 0.92, Neutral: 0.06, Negative: 0.02]` $\rightarrow$ **`92점`**
2. **기사 B (중립 관망):** FinBERT 예측 `[Positive: 0.50, Neutral: 0.45, Negative: 0.05]` $\rightarrow$ **`50점`**
3. **기사 C (강한 악재):** FinBERT 예측 `[Positive: 0.08, Neutral: 0.12, Negative: 0.80]` $\rightarrow$ **`8점`**

* **대시보드 최종 반영:** $$\text{종합 성향 점수} = \frac{92 + 50 + 8}{3} = \mathbf{50.0 \text{점}}$$
  개별 찌라시나 자극적인 단발성 뉴스(92점, 8점)가 유입되더라도, 전체 집계 연산을 통해 시장 전체가 현재 균형 있는 관망세(50점)를 유지하고 있음을 사용자에게 직관적으로 제시합니다.

---

## 4. 데이터 수집 가드레일 및 어드민 복구 전략

Finance Pulse는 무차별적인 크롤링으로 인한 IP 차단 리스크를 최소화하고 데이터 신뢰성을 보장하기 위해 고도화된 수집 가드레일을 운영합니다.

### 4.1. 수집 필터 가드레일 (Data Guardrails)
* **중복 원천 차단:** 기사의 정제된 `URL + Title` 조합 문자열을 기반으로 **MD5/SHA 고유 해시 ID(`doc_id`)**를 생성합니다. 데이터 수집 직전, Elasticsearch 내 존재 여부(`es.exists()`)를 체크하여 중복 뉴스는 네트워크 요청 전에 완전히 스킵(Skip)합니다.
* **품질 필터링:** 본문 길이가 150자 미만이거나 정제 패턴 유효성(KoNewsCleaner)을 충족하지 못하는 기사(페이월, 깨진 페이지 등)는 적재에서 탈락시킵니다.
* **날짜 표준화:** 수집 대상 날짜 정보 파싱 실패 시 예외 처리로 유실을 방지합니다.

### 4.2. 어드민 로그 기반 수동 복구 (Human-in-the-loop 리트라이)
자동화된 봇의 기계적 리트라이는 대상 언론사 서버의 영구 차단(Block)을 유발할 수 있습니다. 이를 방지하기 위해 Finance Pulse는 독자적인 수동 복구 시스템을 제공합니다.

1. 수집 파이프라인 가드레일에서 탈락된 기사는 원시 로그 형태로 유실 사유와 함께 백엔드 시스템에 꽂힙니다.
2. 관리자는 대시보드 어드민 화면에서 에러 로그 목록(`[미수집 기사] 사유: 본문 미달 | URL: ...`)을 직관적으로 확인합니다.
3. 운영자가 판단하여 중요 기사라고 판단 시 **[재크롤링 버튼]**을 클릭하면, 단발성 원포인트 수집 함수인 `crawlSingleArticleByAdmin(url, title, source)`가 가동됩니다.
4. 이 수동 긴급 수집 루틴은 엄격한 길이 가드레일 제한을 일시적으로 바이패스하여 본문을 강제 정제한 후 Elasticsearch에 안전하게 적재합니다.

---

## 5. 시스템 설정 및 핵심 유틸리티 로직 (`getTodayRange`)

대시보드 모니터링 주기와 정기 크롤링 배치 타임라인을 일치시키기 위해 크롤링 스케줄 기반의 **동적 시간 범위 계산(Time-Windowing)** 로직이 포함되어 있습니다.

* **한국어 크롤링 스케줄 (KST):** `["07:30", "11:30", "18:30", "23:59"]`
* **영어 크롤링 스케줄 (KST):** `["06:10", "21:00"]`

현재 조회 시간 기준 가장 최근에 완료된 수집 배치 스케줄 시점을 역산하여 정확히 **과거 24시간 동안의 데이터 범위**를 리턴함으로써, 자정이나 새벽 시간대 날짜가 바뀌는 시점에도 공백 없이 안정적인 대시보드 지표 렌더링을 보장합니다.

---

## 6. 기대 효과 및 비즈니스 로직
* **거시적 인사이트 제공:** 분 단위 단타 매매 툴이 아닌, 하루 4~6회 시장 속의 '소음(Noise)'을 정제하여 거시적 심리 추세(Macro Sentiment)를 읽는 금융 나침반 역할을 수행합니다.
* **수익화 로드맵:** * **STEP 1:** 금융 상품 타겟팅 및 유저 트래픽 기반 플랫폼 배너 광고 수익 창출
  * **STEP 2:** 고액 자산가 및 맞춤형 알림 서비스용 프리미엄 구독제(SaaS) 멤버십 도입
  * **STEP 3:** 정제 가공된 섹터별 일일 감성 지수 API 데이터를 퀀트 투자사 및 자산운용사에 판매하는 B2B 대체 데이터(Alternative Data) 비즈니스 확장
