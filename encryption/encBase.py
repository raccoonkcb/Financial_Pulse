import os
from dotenv import load_dotenv

# 상대 경로 지정
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.normpath(os.path.join(current_dir, "..", ".env"))
load_dotenv(env_path)

# 후추
pepper= os.getenv("SECRET_PEPPER")
if not pepper:
    raise RuntimeError("pepper not set")

# 관리자
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
ADMIN_PASSWORD= os.getenv("ADMIN_PASSWORD")
ADMIN_EMAIL= os.getenv("ADMIN_EMAIL")
if not ADMIN_API_KEY:
    raise RuntimeError("api-key not set")
