import pymysql
import os
from dotenv import load_dotenv
from logs.logger import getLogger

# 1. .env 파일 로드
# current_dir = os.path.dirname(os.path.abspath(__file__))
# env_path = os.path.normpath(os.path.join(current_dir, "..", ".env"))
# load_dotenv(env_path)
load_dotenv()

logger = getLogger("system")

def getConn():
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

def createTables():
    # 2. DB 연결 설정
    conn = getConn()

    try:
        with conn.cursor() as cursor:
            # 3. 테이블 생성 쿼리 (순서 중요: user가 먼저!)
            queries = [
                """
                CREATE TABLE IF NOT EXISTS user (
                    u_id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    encry_pw VARCHAR(255) NOT NULL,
                    name VARCHAR(50) NOT NULL,
                    phone_num VARCHAR(100) NOT NULL
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS userInterests (
                    u_id INT NOT NULL,
                    inter_id INT,
                    interested VARCHAR(100),
                    CONSTRAINT fk_user_interests FOREIGN KEY (u_id) REFERENCES user(u_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                """
                CREATE TABLE IF NOT EXISTS loginFail (
                    u_id INT NOT NULL,
                    dateFail DATETIME NOT NULL,
                    CONSTRAINT fk_user_login_fail FOREIGN KEY (u_id) REFERENCES user(u_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            ]

            for query in queries:
                cursor.execute(query)

            conn.commit()
            logger.info("DB Table Successfully Created")

    except Exception as e:
        logger.error(f"{e}")
    finally:
        conn.close()


if __name__ == "__main__":
    createTables()


# -- [회원정보 데이터 테이블]
# -- 부모 테이블: u_id가 기준점이 됩니다.
# CREATE TABLE user (
#     u_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '고유 식별자 (PK)',
#     email VARCHAR(100) UNIQUE NOT NULL COMMENT '사용자 email',
#     encry_pw VARCHAR(255) NOT NULL COMMENT '암호화된 PW',
#     name VARCHAR(50) NOT NULL COMMENT '표시될 이름',
#     phone_num VARCHAR(100) NOT NULL COMMENT '전화번호'
# );
#
# -- [사용자 관심 섹터]
# -- 자식 테이블: u_id는 부모를 참조하는 FK가 됩니다.
# CREATE TABLE userInterests (
#     u_id INT NOT NULL COMMENT '어떤 사용자의 관심사인지 (FK)',
#     inter_id INT NULL COMMENT '섹터/기업 분류',
#     interested VARCHAR(100) NULL COMMENT '키워드 명',
#     CONSTRAINT fk_user_to_interests FOREIGN KEY (u_id) REFERENCES user(u_id) ON DELETE CASCADE
# );
#
# -- [로그인 실패]
# -- 자식 테이블: u_id는 부모를 참조하는 FK가 됩니다.
# CREATE TABLE loginFail (
#     u_id INT NOT NULL COMMENT '누가 실패했는지 (FK)',
#     dateFail DATETIME NOT NULL COMMENT '실패 일시',
#     CONSTRAINT fk_user_to_login_fail FOREIGN KEY (u_id) REFERENCES user(u_id) ON DELETE CASCADE
# );