from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import os
from router.dashboardRouter import router as dashboardRouter
from router.keywordRouter import router as keywordRouter
from router.spikeRouter import router as spikeRouter
from router.searchRouter import router as searchRouter
from router.adminRouter import router as adminRouter
from router.logRouter import router as logRouter
from router.crawlRouter import router as crawlRouter
from router.esRouter import router as esRouter
from router.correctionRouter import router as correctionRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from contextlib import asynccontextmanager
from crawling.crawlSchedular import scheduler, addJobs
from dataStorage.elasticSearch.esIndex import createAllIndices
from dataStorage.mariaDb.db import createTables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ================================================================
    # 서버 시작 시 실행
    # ================================================================
    print("[STARTUP] 인덱스 확인 중...")
    createAllIndices()
    createTables()

    # 스케줄러 시작
    # test_mode=False → 정기 스케줄만 등록
    # test_mode=True  → 즉시 테스트 실행
    addJobs(test_mode=False)
    scheduler.start()
    print("[STARTUP] 스케줄러 시작 완료")

    yield  # 서버 실행 중

    # ================================================================
    # 서버 종료 시 실행
    # ================================================================
    scheduler.shutdown()
    print("[SHUTDOWN] 스케줄러 종료 완료")

app = FastAPI(lifespan=lifespan)

# ── HTML 라우트 (마운트보다 먼저 등록) ──
@app.get("/")
def root():
    return FileResponse("view/index.html")

@app.get("/{filename}.html")
def serve_html(filename: str):
    import os
    path = f"view/{filename}.html"
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"success": False, "message": "페이지를 찾을 수 없습니다.", "data": None})
    return FileResponse(path)

# ================================================================
# 세션 미들웨어 등록
# secret_key : 세션 쿠키 서명에 사용 — 반드시 .env에서 관리
# max_age    : 세션 유지 시간 (초 단위, 3600 = 1시간)
# https_only : 운영 환경에서는 반드시 True (HTTPS 전용)
# ================================================================
app.add_middleware(
    SessionMiddleware,
    secret_key = os.getenv("SESSION_SECRET_KEY"),
    max_age    = 3600,
    https_only = False,     # TODO: 운영 배포 시 True 로 변경
)


# ================================================================
# 공통 에러 핸들러
# ================================================================
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data"   : None
        }
    )


# ================================================================
# 라우터 등록
# ================================================================
from router.memberRouter import router as memberRouter

app.include_router(memberRouter)
app.include_router(dashboardRouter)
app.include_router(keywordRouter)
app.include_router(spikeRouter)
app.include_router(searchRouter)
app.include_router(adminRouter)
app.include_router(logRouter)
app.include_router(crawlRouter)
app.include_router(esRouter)
app.include_router(correctionRouter)

app.mount("/", StaticFiles(directory="view"), name="static")