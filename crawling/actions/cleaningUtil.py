# 주석만 수정. (05.12)
import re

class NewsCleaner:
    """
    미국 뉴스(영어) 전용 클리너

    [개선 사항]
    - 정규식 패턴 플래그 통일 (IGNORECASE | MULTILINE)
    - isValid() 검증 로직 강화

    [목적]
    - 크롤링된 원문에서 광고, 기자 정보, 저작권 문구 등 노이즈 제거
    - ML 모델 학습/분석에 사용할 고품질 텍스트 생성

    [효과]
    - 노이즈가 제거된 텍스트로 ML 분석 정확도 향상
    - 불필요한 데이터가 ES에 적재되는 것을 사전 차단
    """

    @staticmethod
    def clean(text):
        """
        영어 뉴스 텍스트 정제
        - HTML 태그, URL, 광고, 기자 정보 등 노이즈 제거
        - 특수문자 정리 및 공백 정규화
        """
        if not text: return ""

        # 1. HTML 태그 및 URL 제거 (기존 유지)
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)

        # 2. [필살] 한글 광고 제거 (기존 유지)
        text = re.sub(r'[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]+', '', text)

        # 3. 영문 뉴스 하단/중간 정크 패턴 (추가 및 보강)
        en_junk_patterns = [
            # --- [추가] 기자 정보 및 날짜 바이라인 ---
            r'By\s+[a-zA-Z\s]+\s+[A-Z][a-z]+\s+\d+,\s+\d{4}.*',  # By Name May 8, 2026...
            r'\d+\s+min\s+read',  # 2 min read
            r'(AhmadArdity|Pixabay|Unsplash|Getty|Pexels)',  # 이미지 출처 파편
            r'What to know',  # UI 문구
            r'Make preferred on.*',  # UI 문구

            # --- [기존 패턴 유지] ---
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'(Reporting|Writing|Editing|Additional reporting) by [^.\n]*',
            r'Sign up for (our|the) .*? newsletter.*',
            r'Subscribe to .*? for (more|daily) updates.*',
            r'Follow us on (Twitter|Facebook|LinkedIn|Instagram).*',
            r'©\s?\d{4}.*?All rights reserved\.?',
            r'Copyright\s?\d{4}.*?',
            r'Photo (by|credit):? [^.\n]*',
            r'Image (by|credit):? [^.\n]*',
            r'ADVERTISEMENT',
            r'Check out our latest.*?videos.*',
            r'Read (more|also):.*'
        ]

        for pattern in en_junk_patterns:
            # re.IGNORECASE를 추가하여 대소문자 관계없이 매칭
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 4. 특수문자 정리 (기존 유지)
        text = re.sub(r'[^a-zA-Z0-9\s.?!,\'\"-]', ' ', text)

        # 5. 공백 및 가독성 정리 (기존 유지)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'([.?!])\s+', r'\1\n\n', text)

        return text

    @staticmethod
    def isValid(text, title=""):
        """
        영어 뉴스 품질 검증

        [검증 기준]
        1. 불필요한 콘텐츠 유형 필터링 (transcript, earnings call 등)
        2. 본문 길이 250자 이상
        3. 영문 알파벳 비중 70% 이상

        [목적]
        - ML 분석에 부적합한 저품질 텍스트 사전 차단
        - ES에 불필요한 데이터가 적재되는 것을 방지
        """
        # 불필요한 콘텐츠 유형 필터링
        stop_words = ["transcript", "earnings call", "live blog", "full text"]
        combined = (title + " " + (text if text else "")).lower()
        if any(word in combined for word in stop_words): return False

        if text:
            # 본문 길이 250자 미만은 제외 (기존 유지)
            if len(text.strip()) < 250: return False

            # [검증] 영어 알파벳 비중 검사 (기존 유지)
            alpha_count = len(re.findall(r'[a-zA-Z]', text))
            if alpha_count / len(text) < 0.7: return False
        return True


class KoNewsCleaner:
    """
    한국 뉴스 전용 클리너

    [개선 사항]
    - 정규식 오류 수정 (잘못된 따옴표 패턴 수정)
    - 기존: r'유튜브 채널\s?'.*?'' → 개선: r"유튜브 채널\s?'.*?'"

    [개선 이유]
    - 기존 코드의 따옴표 혼용으로 정규식이 의도대로 동작하지 않음
    - 유튜브 채널 유도 문구가 제거되지 않아 노이즈로 남을 수 있음

    [목적]
    - 한국 뉴스 특유의 광고, 기자 정보, 저작권 문구 제거
    - ML 분석용 고품질 텍스트 생성

    [효과]
    - 정규식 오류 수정으로 클리닝 정확도 향상
    - 유튜브 채널 유도 문구가 올바르게 제거됨
    """

    @staticmethod
    def clean(text):
        """
        한국 뉴스 텍스트 정제
        - HTML 태그, URL, 광고, 기자 정보 등 노이즈 제거
        - 특수문자 정리 및 공백 정규화
        """
        if not text: return ""

        # 1. HTML 태그 및 URL 제거
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)

        # 2. 한국 뉴스 특유의 정크 패턴 (광고, 저작권, 기자 메일 등)
        ko_junk_patterns = [
            # 유튜브 및 외부 채널 유도 (안경찬 CP 등 직함 포함 패턴)
            r'.*자세한 내용과 영상은 유튜브 채널.*확인할 수 있습니다\.?',
            r'최신 영상에서 확인할 수 있습니다\.?',
            r'유튜브 채널\s?‘.*?’',

            # 자극적 홍보 문구
            r'주식 초고수는 지금.*',
            r'실시간 인기 주식.*',

            # 사진 및 이미지 출처 (괄호 포함)
            r'\(사진\s?=\s?.*?\)',
            r'\[사진\s?=\s?.*?\]',
            r'/사진\s?=\s?.*?\n',

            # 이메일 및 기자 정보
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'\[.*?=.*?기자\]', r'\(.*?=.*?기자\)', r'기자\s?=\s?.*?\n',

            # 저작권 및 무단 전재
            r'저작권자\s?ⓒ.*', r'무단\s?전재\s?및\s?재배포\s?금지',
            r'Copyrights.*All rights reserved.*',
            r'재배포\s?금지.*',

            # 기타 파편
            r'▲.*?\n', r'▼.*?\n', r'▶.*?\n'
        ]

        for pattern in ko_junk_patterns:
            # MULTILINE 플래그를 써서 줄바꿈 뒤에 오는 문구도 잘 잡히게 함
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 3. 특수문자 정제
        text = re.sub(r'[^a-zA-Z0-9ㄱ-ㅣ가-힣\s.?!,\'\"-]', ' ', text)

        # 4. 공백 및 줄바꿈 정리
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'([.?!])\s+', r'\1\n\n', text)

        return text

    @staticmethod
    def isValid(text, title=""):
        """
        한국 뉴스 품질 검증

        [검증 기준]
        1. 불필요한 콘텐츠 유형 필터링 (생중계, 포토뉴스 등)
        2. 본문 길이 150자 이상 (한국어는 압축도가 높아 250자보다 낮게 설정)
        3. 본문 길이 15000자 이하 (너무 긴 기사 제외)

        [목적]
        - ML 분석에 부적합한 저품질 텍스트 사전 차단
        """
        stop_words = ["생중계", "포토", "영상", "부고", "인사", "오늘의 운세", "녹취록"]
        combined = (title + " " + (text if text else "")).lower()
        if any(word in combined for word in stop_words): return False

        if text:
            # 한글 기사는 내용 압축도가 높으므로 150자 이상이면 통과
            if len(text.strip()) < 150: return False
            if len(text) > 15000: return False
        return True