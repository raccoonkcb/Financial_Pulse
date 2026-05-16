from fastapi import Header, Cookie, HTTPException, status, Request
from encryption.encBase import ADMIN_API_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
from encryption.argonPepper import hashPassword, comparePassword
from logs.logger import getLogger

logger = getLogger("user")
# ================================================================
# 세션 저장소 (메모리 기반)
#
# [역할]
# 로그인 성공 시 세션 토큰을 메모리에 저장
# 이후 요청에서 쿠키의 세션 토큰과 비교하여 인증
#
# [한계]
# 서버 재시작 시 세션 초기화 → 재로그인 필요
# 포트폴리오 규모에서는 충분
# 실제 운영 시 Redis로 대체 권장
# ================================================================
_sessions: dict = {}

def create_session(email: str) -> str:
    """
    세션 토큰 생성 및 저장

    [secrets 모듈 사용 이유]
    - 예측 불가능한 토큰 생성
    - 세션 하이재킹 방지
    """
    import secrets
    token = secrets.token_hex(32)   # 64자리 16진수 토큰
    _sessions[token] = email        # 메모리에 저장
    logger.info("세션 생성", extra={"email": email})
    return token


def delete_session(token: str):
    """세션 삭제 (로그아웃)"""
    if token in _sessions:
        email = _sessions.pop(token)
        logger.info("세션 삭제", extra={"email": email})


def verify_admin(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key")
) -> str:
    """
    관리자 인증 통합 의존성 함수

    [인증 우선순위]
    1. X-API-Key 헤더 → Postman/curl/서버간 통신용
    2. 세션 쿠키      → logViewer 브라우저용

    [이유]
    logViewer는 브라우저 UI이므로 헤더를 직접 다루기 어려움
    로그인 후 쿠키로 인증하는 방식이 자연스러움
    외부 도구(Postman 등)는 API Key로 바로 접근 가능
    """
    # [1] API Key 인증 시도
    if x_api_key:
        if x_api_key == ADMIN_API_KEY:
            logger.info("API Key 인증 성공")
            return "admin"
        else:
            logger.warning("API Key 인증 실패")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="유효하지 않은 API Key입니다."
            )

    # [2] 세션 쿠키 인증 시도
    session_token = request.cookies.get("admin_session")
    if session_token and session_token in _sessions:
        logger.info("세션 인증 성공", extra={
            "email": _sessions[session_token]
        })
        return _sessions[session_token]

    # [3] 둘 다 없으면 401
    logger.warning("인증 실패 - API Key 또는 세션 없음")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다."
    )