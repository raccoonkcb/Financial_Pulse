import uuid
from datetime import datetime, timezone
from elasticsearch.helpers import bulk
from dataStorage.elasticSearch.es import getEs, NEWS_KO_IDX, NEWS_EN_IDX
from logs.logger import getLogger

logger = getLogger("crawl")

def runCrawlBatch(urls: list, lang: str = "ko", batch_id: str = None) -> dict:
    """
    배치 크롤링 실행
    1. 시작 로그 기록
    2. URL 목록 순회하며 크롤링
       - 성공 → actions 리스트에 추가
       - 실패 → ERROR 로그 기록
    3. bulk로 뉴스 인덱스에 저장
    4. 종료 로그 기록 (crawl_cnt 포함)
    """
    es           = getEs()
    batch_id     = batch_id or str(uuid.uuid4())
    collected_at = datetime.now(timezone.utc).isoformat()
    target_index = NEWS_KO_IDX if lang == "ko" else NEWS_EN_IDX

    logger.info("크롤링 배치 시작", extra={
        "batch_id": batch_id, "lang": lang, "total_urls": len(urls)
    })

    actions   = []
    fail_urls = []

    for url in urls:
        try:
            # 실제 크롤링 로직으로 대체 필요
            doc_id       = str(uuid.uuid4())
            title        = f"제목 - {url}"
            content      = f"본문 - {url}"
            published_at = collected_at

            actions.append({
                "_op_type": "index",
                "_index":   target_index,
                "_id":      doc_id,
                "_source": {
                    "doc_id":       doc_id,
                    "lang":         lang,
                    "url":          url,
                    "title":        title,
                    "content":      content,
                    "published_at": published_at,
                    "collected_at": collected_at
                }
            })

        except Exception as e:
            logger.error("크롤링 실패", extra={
                "batch_id": batch_id, "url": url, "reason": str(e)
            })
            fail_urls.append(url)

    # bulk 저장
    crawl_cnt = 0
    if actions:
        result    = bulk(es, actions)
        crawl_cnt = result[0]

    logger.info("크롤링 배치 종료", extra={
        "batch_id":  batch_id,
        "lang":      lang,
        "crawl_cnt": crawl_cnt,
        "fail_cnt":  len(fail_urls)
    })

    es.close()
    return {
        "batch_id":  batch_id,
        "lang":      lang,
        "crawl_cnt": crawl_cnt,
        "fail_cnt":  len(fail_urls)
    }


def extractErrorUrls(batch_id: str) -> list:
    """
    fp-logs-crawl 에서 특정 배치의 ERROR 로그를 조회하여
    extra.url 필드에서 실패 URL 목록 추출
    """
    logger.info("실패 URL 추출 시작", extra={"batch_id": batch_id})

    es     = getEs()
    result = es.search(
        index="fp-logs-crawl",
        body={
            "query": {"bool": {"must": [
                {"term": {"level":          "ERROR"}},
                {"term": {"extra.batch_id": batch_id}}
            ]}},
            "size": 10000
        }
    )

    error_urls = [
        hit["_source"]["extra"]["url"]
        for hit in result["hits"]["hits"]
        if "url" in hit["_source"]["extra"]
    ]
    es.close()

    logger.info("실패 URL 추출 완료", extra={
        "batch_id": batch_id, "error_cnt": len(error_urls)
    })
    return error_urls


def retryErrorUrls(batch_id: str, lang: str = "ko") -> dict:
    """
    실패한 URL 추출 후 재크롤링
    - 새로운 batch_id 부여하여 원본 배치와 구분
    """
    error_urls = extractErrorUrls(batch_id)

    if not error_urls:
        logger.info("재시도할 URL 없음", extra={"batch_id": batch_id})
        return {"message": "재시도할 URL 없음", "retry_cnt": 0}

    retry_batch_id = str(uuid.uuid4())
    logger.info("재크롤링 시작", extra={
        "origin_batch_id": batch_id,
        "retry_batch_id":  retry_batch_id,
        "retry_cnt":       len(error_urls)
    })
    return runCrawlBatch(urls=error_urls, lang=lang, batch_id=retry_batch_id)


def getCrawlSummary() -> dict:
    """
    크롤링 현황 집계
    - crawCon 상단 카드 (총로그/ERROR/WARN/마지막실행) 처리
    """
    from service.logSvc import getLogSummary
    return getLogSummary(subject="crawl")


def retrySelectedUrls(urls: list, batch_id: str, lang: str = "ko") -> dict:
    """
    선택적 재시도 - crawCon UI에서 체크박스로 선택한 URL만 재시도
    """
    if not urls:
        logger.info("선택된 URL 없음")
        return {"message": "선택된 URL 없음"}

    retry_batch_id = str(uuid.uuid4())
    logger.info("선택적 재크롤링 시작", extra={
        "origin_batch_id": batch_id,
        "retry_batch_id":  retry_batch_id,
        "selected_cnt":    len(urls)
    })
    return runCrawlBatch(urls=urls, lang=lang, batch_id=retry_batch_id)