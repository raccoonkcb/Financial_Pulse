from pydantic import BaseModel

class ArchiveRequest(BaseModel):
    """
    아카이빙 요청 모델
    - index       : 아카이빙할 인덱스명
    - before_date : 해당 날짜 이전 데이터를 아카이빙
                    예) "2024-01-01" → 2024-01-01 이전 로그를 파일로 저장 후 ES에서 삭제
    """
    index:       str
    before_date: str