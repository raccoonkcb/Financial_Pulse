import smtplib, os
import secrets, string
from dotenv import load_dotenv
from fastapi import HTTPException, status
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from logs.logger import getLogger
from dataStorage.mariaDb.db import getConn
from encryption.argonPepper import hashPassword, comparePassword

load_dotenv()

MAIL_HOST     = os.getenv("MAIL_HOST",     "smtp.gmail.com")
MAIL_PORT     = int(os.getenv("MAIL_PORT", 587))
MAIL_USER     = os.getenv("MAIL_USER",     "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM     = os.getenv("MAIL_FROM",     "")

u_logger= getLogger("user")
s_logger = getLogger("system")

def generateTempPassword(length: int = 10) -> str:
    """
    임시 비밀번호 생성
    """
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def findPassword(email: str, name: str, phone_num: str) -> dict:
    """
    임시 비밀번호 발급
    """
    u_logger.info("임시 비밀번호 발급 요청", extra={"action": "findPassword"})

    conn = getConn()
    try:
        with conn.cursor() as cursor:

            # [1] email + name + phone_num 세 가지 모두 일치 여부 확인
            # 이메일만으로 찾으면 이메일 주소를 아는 사람이 악용 가능
            # 세 가지 정보가 모두 일치해야 본인으로 간주
            cursor.execute(
                """
                SELECT u_id, email
                FROM user
                WHERE email     = %s
                  AND name      = %s
                  AND phone_num = %s
                """,
                (email, name, phone_num)
            )
            user = cursor.fetchone()

            # [2] 일치하는 회원 없으면 404
            if not user:
                u_logger.warning("일치하는 회원 없음", extra={"action": "findPassword"})
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="일치하는 회원 정보가 없습니다."
                )

            # [3] 임시 비밀번호 생성 (평문)
            temp_password = generateTempPassword()

            # [4] Argon2 + Pepper 해싱 후 DB 업데이트
            hashed_pw = hashPassword(temp_password)
            cursor.execute(
                """
                UPDATE user
                SET encry_pw = %s
                WHERE u_id = %s
                """,
                (hashed_pw, user["u_id"])
            )

            # [5] 이메일 발송 (평문 임시 비밀번호 발송)
            mail_sent = sendTempPassword(
                to_email=email,
                temp_password=temp_password
            )

            # [6] 이메일 발송 실패 → DB 롤백
            if not mail_sent:
                conn.rollback()
                u_logger.error("이메일 발송 실패로 DB 롤백", extra={"action": "findPassword"})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
                )

            # 이메일 발송 성공 → DB 커밋
            conn.commit()
            u_logger.info("임시 비밀번호 발급 완료", extra={"action": "findPassword"})

            return {
                "message": "가입한 이메일을 확인해 주세요. (임시 비밀번호가 발송되었습니다)"
            }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        u_logger.error("임시 비밀번호 발급 중 서버 오류", extra={"action": "findPassword", "err_msg": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 오류가 발생했습니다."
        )
    finally:
        conn.close()

#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
#----------------------------------------------------------------------------

def sendTempPassword(to_email: str, temp_password: str) -> bool:
    """
    임시 비밀번호 이메일 발송
    [MIMEMultipart("alternative")]
    - Subject : 이메일 제목 (수신함에서 보이는 제목)
    - From    : 발신자 표시 (.env의 MAIL_FROM)
    - To      : 수신자 이메일 주소

    [smtp.sendmail(from, to, message)]
    - from   : 발신자 이메일 (MAIL_USER)
    - to     : 수신자 이메일 (to_email)
    - message: msg.as_string()으로 변환된 이메일 내용
    ================================================================
    """
    try:
        # [1] 이메일 메시지 구성
        msg= MIMEMultipart("alternative")
        msg["Subject"]= "[Financial Pulse] 임시 비밀번호 안내"
        msg["From"]= MAIL_FROM
        msg["To"]= to_email

        # HTML 본문 구성
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1a1a2e; padding: 30px; border-radius: 10px;">
                <h2 style="color: #00d4aa; text-align: center;">
                    🦖금융🦕박동🦖
                </h2>
                <div style="background-color: #ffffff; padding: 20px; border-radius: 8px;">
                    <h3 style="color: #333;">임시 비밀번호 안내</h3>
                    <p style="color: #666;">
                        요청하신 임시 비밀번호를 안내해 드립니다.
                    </p>
                    <div style="background-color: #f5f5f5; padding: 15px;
                                border-radius: 5px; text-align: center; margin: 20px 0;">
                        <p style="color: #333; margin: 0; font-size: 12px;">임시 비밀번호</p>
                        <p style="color: #00d4aa; font-size: 24px;
                                  font-weight: bold; margin: 10px 0; letter-spacing: 3px;">
                            {temp_password}
                        </p>
                    </div>
                    <p style="color: #e74c3c; font-size: 12px;">
                        로그인 후 반드시 비밀번호를 변경해 주세요.
                    </p>
                </div>
                <p style="color: #888; font-size: 11px; text-align: center; margin-top: 20px;">
                    본 메일은 발신 전용입니다.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # [2] SMTP 서버 연결 및 발송
        # with 구문 사용으로 발송 완료 후 자동으로 연결 종료
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as smtp:
            smtp.ehlo()       # 서버에 클라이언트 소개
            smtp.starttls()   # TLS 암호화 연결 업그레이드
            smtp.login(MAIL_USER, MAIL_PASSWORD)
            smtp.sendmail(MAIL_USER, to_email, msg.as_string())

        s_logger.info("임시 비밀번호 이메일 발송 성공", extra={"action": "sendTempPassword"})
        return True

    except smtplib.SMTPAuthenticationError:
        # Gmail 앱 비밀번호가 잘못된 경우
        s_logger.error("이메일 인증 실패 - 앱 비밀번호 확인 필요", extra={"action": "sendTempPassword"})
        return False

    except smtplib.SMTPRecipientsRefused:
        # 수신자 이메일 주소가 잘못된 경우
        s_logger.error("수신자 이메일 주소 오류", extra={"action": "sendTempPassword"})
        return False

    except Exception as e:
        s_logger.error("이메일 발송 실패", extra={"action": "sendTempPassword", "err_msg": str(e)})
        return False