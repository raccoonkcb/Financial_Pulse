from pydantic import BaseModel
from typing import Optional

class IntegrityCheckRequest(BaseModel):
    """
    정합성 검사 요청 모델
    - batch_id : 검사할 배치 ID
                 크롤링 종료 로그의 crawl_cnt vs 실제 저장된 save_cnt 비교
    - lang     : 언어 → 조회할 뉴스 인덱스 결정 (news_ko / news_en)
    """
    batch_id: str
    lang:     str = "ko"

class CompareUrlRequest(BaseModel):
    """
    URL 비교 요청 모델
    - batch_id : 비교할 배치 ID
                 로그의 URL 집합 vs 실제 저장된 URL 집합 → 차집합으로 누락 URL 특정
    - lang     : 언어
    """
    batch_id: str
    lang:     str = "ko"