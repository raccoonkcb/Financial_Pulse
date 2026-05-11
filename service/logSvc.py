from dataStorage.elasticSearch.es import getEs, ALL_LOG_IDX
from model.logModel import LogSearchRequest
from logs.logger import get_logger

logger = get_logger("system")

def search_log(req: LogSearchRequest) -> dict:
    """
    필터 조건으로 fp-logs-all 에서 로그 조회
    - level, subject, 시간 범위 필터
    - 최신순 정렬
    """
    logger.info("로그 조회 시작", extra={
        "level": req.level, "subject": req.subject,
        "start_time": req.start_time, "end_time": req.end_time
    })

    es   = getEs()
    must = []

    if req.level:
        must.append({"term": {"level": req.level}})
    if req.subject:
        must.append({"term": {"subject": req.subject}})
    if req.start_time or req.end_time:
        time_range = {}
        if req.start_time: time_range["gte"] = req.start_time
        if req.end_time:   time_range["lte"] = req.end_time
        must.append({"range": {"timestamp": time_range}})

    query  = {"bool": {"must": must}} if must else {"match_all": {}}
    result = es.search(
        index=ALL_LOG_IDX,
        body={
            "query": query,
            "sort":  [{"timestamp": {"order": "desc"}}],
            "size":  req.size
        }
    )

    logs = [hit["_source"] for hit in result["hits"]["hits"]]
    es.close()

    logger.info("로그 조회 완료", extra={"result_cnt": len(logs)})
    return {"total": len(logs), "logs": logs}


def export_log_csv(req: LogSearchRequest) -> str:
    """
    로그 조회 결과를 CSV 형식으로 변환
    - logViewer의 CSV 내보내기 버튼 처리
    - BOM(utf-8-sig) 추가로 한글 깨짐 방지
    """
    import csv
    import io

    logger.info("CSV 내보내기 시작")

    result = search_log(req)
    logs   = result["logs"]

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["log_id", "timestamp", "subject", "level", "message", "extra"]
    )
    writer.writeheader()

    for log in logs:
        writer.writerow({
            "log_id":    log.get("log_id", ""),
            "timestamp": log.get("timestamp", ""),
            "subject":   log.get("subject", ""),
            "level":     log.get("level", ""),
            "message":   log.get("message", ""),
            "extra":     str(log.get("extra", {}))
        })

    logger.info("CSV 내보내기 완료", extra={"export_cnt": len(logs)})

    # BOM 추가 (한글 깨짐 방지)
    return "\ufeff" + output.getvalue()


def get_log_summary(subject: str = None) -> dict:
    """
    로그 집계 조회
    - logViewer 상단 집계 카드 (총로그/ERROR/WARN/SUCCESS) 처리
    - crawCon 상단 집계 카드 처리
    """
    es   = getEs()
    index = f"fp-logs-{subject}" if subject else ALL_LOG_IDX

    result = es.search(
        index=index,
        body={
            "query": {"match_all": {}},
            "aggs": {
                # 레벨별 집계
                "by_level": {
                    "terms": {"field": "level", "size": 10}
                },
                # 가장 최근 로그 시각
                "latest": {
                    "max": {"field": "timestamp"}
                }
            },
            "size": 0  # 집계만 필요하므로 도큐먼트는 가져오지 않음
        }
    )

    # 레벨별 집계 결과 파싱
    buckets   = result["aggregations"]["by_level"]["buckets"]
    level_map = {b["key"]: b["doc_count"] for b in buckets}

    summary = {
        "total":   result["hits"]["total"]["value"],
        "error":   level_map.get("ERROR",   0),
        "warning": level_map.get("WARNING", 0),
        "info":    level_map.get("INFO",    0),
        "latest":  result["aggregations"]["latest"]["value_as_string"]
                   if result["aggregations"]["latest"]["value"] else None
    }

    es.close()
    return summary