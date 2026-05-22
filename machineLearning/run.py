from datetime import datetime
from text_analyzing.TextAnalyzer import TextAnalyzer
from sentiment_analyzing.main_senti import run_sentiment_pipeline
from labeling.main_labeling import run_sector_sync
from logs.logger import getLogger
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logger = getLogger("ml")

# =====================================================================
# [ML 파이프라인 제어 설정 구역]
# 팀장님이 원하시는 대로 여기 값만 마우스로 클릭해서 수정하시면 됩니다!
# =====================================================================

# 1. 날짜 설정
# - 특정 날짜 지정 예시: "2026-05-20"
# - 당일(오늘) 날짜 기사만 자동으로 분석하고 싶다면: datetime.now().strftime("%Y-%m-%d")

# 2. 언어 설정 (원하는 언어만 리스트에 남겨두면 됩니다)
TARGET_LANGS = ["ko", "en"]


# =====================================================================


def run(lang: str):
    td = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"[ML 파이프라인 시작] 대상 날짜: {td} | 대상 언어: {lang}")

    # 1. 섹터 라벨링 실행 (설정한 날짜 반영)
    logger.info("[1/3] 섹터 라벨링(Sector Sync) 시작...")
    run_sector_sync(lang, td, td)

    # 2. 감성 분석 실행 (설정한 날짜 반영)
    logger.info("[2/3] 감성 분석 파이프라인 시작...")
    run_sentiment_pipeline(lang, td, td)

    # 3. NER 및 키워드 분석 실행 (설정한 언어와 날짜 반영)
    logger.info("[3/3] Text Analyzer 시작...")
    TextAnalyzer().run_analysis(lang, td, td)

    logger.info(f"[{td}] 모든 ML 분석 작업 완료 및 종료.")


if __name__ == "__main__":
    run()