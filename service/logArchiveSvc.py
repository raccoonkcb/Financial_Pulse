import asyncio
import json
from datetime import datetime, timezone
from elasticsearch.helpers import scan
from dataStorage.elasticSearch.es import getEs, ALL_LOG_IDX
from logs.logModel import LogSearchRequest
from service.logSvc import search_log
from logs.logger import get_logger

logger = get_logger("system")

async def stream_logs(subject: str = None):
    """
    SSE - 실시간 로그 스트리밍
    - 2초마다 새 로그 조회하여 클라이언트에 전송
    - subject 필터로 특정 주제 로그만 스트리밍 가능
    """
    logger.info("실시간 로그 스트리밍 시작", extra={"subject": subject})
    last_timestamp = datetime.now(timezone.utc).isoformat()

    while True:
        req    = LogSearchRequest(subject=subject, start_time=last_timestamp, size=100)
        result = search_log(req)

        for log in result["logs"]:
            last_timestamp = log["timestamp"]
            yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"

        await asyncio.sleep(2)


def archive_logs(index: str, before_date: str) -> dict:
    """
    오래된 로그 아카이빙
    1. before_date 이전 로그 전체 추출
    2. JSONL 파일로 저장
    3. ES 인덱스에서 삭제
    """
    logger.info("로그 아카이빙 시작", extra={
        "index": index, "before_date": before_date
    })

    es   = getEs()
    docs = scan(
        es, index=index,
        query={"query": {"range": {"timestamp": {"lte": before_date}}}},
        size=10000
    )

    archive = []
    for doc in docs:
        archive.append(doc["_source"])

    # JSONL 파일로 저장
    file_name = f"archive_{index}_{before_date}.jsonl"
    with open(f"archives/{file_name}", "w", encoding="utf-8") as f:
        for row in archive:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ES에서 삭제
    es.delete_by_query(
        index=index,
        body={"query": {"range": {"timestamp": {"lte": before_date}}}}
    )
    es.close()

    logger.info("로그 아카이빙 완료", extra={
        "index": index, "archived_cnt": len(archive), "file": file_name
    })
    return {"archived": len(archive), "file": file_name}