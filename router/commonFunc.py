# ok 함수 여기에 정의
from fastapi.responses import JSONResponse
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
# ================================================================
# 공통 성공 응답
def ok(message: str, data: dict | None = None):
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": message,
            "data"   : data
        }
    )

SECTOR_KO = {
    "Tech"             : "IT/기술",
    "Finance"          : "금융",
    "Industry"         : "중공업/인프라",
    "Consumer"         : "소비재/서비스",
    "Healthcare"       : "바이오/헬스",
    "Mobility"         : "모빌리티",
    "Macro & Policy"   : "매크로/정책",
}

SECTOR_EN = {v: k for k, v in SECTOR_KO.items()}
# 결과: { "IT/기술": "Tech", "금융": "Finance", ... }

def translateSectorToEn(name: str) -> str:
    return SECTOR_EN.get(name, name)

def translateSector(name: str) -> str:
    return SECTOR_KO.get(name, name)

def getDocIds(es, index: str, date_from: str, date_to: str, size: int = 10000) -> list:
    res = es.search(
        index = index,
        body  = {
            "query"  : {"range": {"published_at": {"gte": date_from, "lte": date_to}}},
            "_source": ["doc_id"],
            "size"   : size
        }
    )
    return [hit["_source"]["doc_id"] for hit in res["hits"]["hits"]]

KST = ZoneInfo("Asia/Seoul")

KO_SCHEDULES = ["07:30", "11:30", "18:30", "00:00"]
EN_SCHEDULES = ["06:10", "21:00", "00:00"]

def getTodayRange(lang: str) -> tuple[str, str]:
    now = datetime.now(KST)
    today = now.date()

    schedules = KO_SCHEDULES if lang == "ko" else EN_SCHEDULES

    # 현재 시간 기준으로 직전/현재 크롤링 구간 찾기
    current_time = now.strftime("%H:%M")

    # 현재 시간이 속하는 구간 찾기
    prev_schedule = None
    curr_schedule = None

    for sched in schedules:
        if current_time >= sched:
            prev_schedule = curr_schedule
            curr_schedule = sched
        else:
            break

    if curr_schedule is None:
        # 오늘 첫 스케줄 이전 → 전날 마지막 구간
        prev_sched = schedules[-2] if len(schedules) > 1 else schedules[-1]
        last_sched = schedules[-1]
        start_dt = datetime.strptime(f"{today - timedelta(days=1)} {prev_sched}", "%Y-%m-%d %H:%M") + timedelta(minutes=1)
        end_dt   = datetime.strptime(f"{today - timedelta(days=1)} {last_sched}", "%Y-%m-%d %H:%M")
    elif prev_schedule is None:
        # 첫 번째 스케줄 직후 → 전날 마지막 ~ 오늘 첫 스케줄
        last_sched = schedules[-1]
        start_dt = datetime.strptime(f"{today - timedelta(days=1)} {last_sched}", "%Y-%m-%d %H:%M") + timedelta(minutes=1)
        end_dt   = datetime.strptime(f"{today} {curr_schedule}", "%Y-%m-%d %H:%M")
    else:
        # 일반 구간
        start_dt = datetime.strptime(f"{today} {prev_schedule}", "%Y-%m-%d %H:%M") + timedelta(minutes=1)
        end_dt   = datetime.strptime(f"{today} {curr_schedule}", "%Y-%m-%d %H:%M")

    return start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")