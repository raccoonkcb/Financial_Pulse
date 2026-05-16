from pydantic import BaseModel, EmailStr

class AdminLoginRequest(BaseModel):
    """
    관리자 로그인 요청 모델
    - logViewer 로그인 화면 처리
    """
    email:    EmailStr
    password: str

class AdminLoginResponse(BaseModel):
    """관리자 로그인 응답 모델"""
    message: str
    email:   str

class FindPasswordRequest(BaseModel):
    """임시 비밀번호 발급 요청 모델"""
    email:     EmailStr
    name:      str
    phone_num: str

class FindPasswordResponse(BaseModel):
    """임시 비밀번호 발급 응답 모델"""
    message: str