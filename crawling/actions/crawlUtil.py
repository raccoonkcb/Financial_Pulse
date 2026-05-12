import hashlib
import atexit
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 클리닝 유틸 임포트
from crawling.actions.cleaningUtil import NewsCleaner
# ================================================================
# [개선] 로거 적용
#
# [개선 이유]
# 기존 코드는 print()만 사용하여 콘솔 출력만 가능했습니다.
# 드라이버 생성/종료 이력이 기록되지 않아 문제 발생 시 추적 불가능합니다.
#
# [목적]
# 드라이버 생성/종료, 본문 추출 성공/실패를 ES에 기록합니다.
# logViewer에서 크롤링 드라이버 동작 이력을 실시간으로 확인 가능합니다.
#
# [효과]
# - 드라이버 누수 발생 시 로그로 추적 가능
# - 본문 추출 실패 원인을 로그에서 확인 가능
# ================================================================
from logs.logger import getLogger
logger = getLogger("crawl")

# [성능 최적화] 서비스 객체 전역 선언
CHROME_SERVICE = Service(ChromeDriverManager().install())

# 생성된 드라이버들을 추적하기 위한 리스트 (비상용)
_active_drivers = []


def cleanUpAllDrivers():
    """
    스크립트 종료 시 남아있는 모든 드라이버 강제 종료

    [목적]
    - 정상 종료 시에도 드라이버가 남아있을 수 있어 메모리 누수 방지
    - atexit으로 등록하여 프로세스 종료 시 자동 실행
    """

    logger.info("Web-Driver: 종료 시작", extra={"action": "cleanUpAllDrivers"})
    while _active_drivers:
        driver = _active_drivers.pop()
        try:
            driver.quit()
        except:
            pass
    logger.info("Web-Driver: 종료 완료", extra={"action": "cleanUpAllDrivers"})


# 파이썬 프로세스 종료 시 자동 실행 등록 (비정상 종료 대비)
atexit.register(cleanUpAllDrivers)


def getDriver(timeout=10):
    """
    Chrome 드라이버 생성 및 추적 리스트 등록

    [옵션 설명]
    - headless       : 브라우저 UI 없이 백그라운드 실행 (서버 환경 필수)
    - no-sandbox     : 리눅스 서버 환경에서 필수 옵션
    - disable-gpu    : headless 모드에서 GPU 비활성화
    - images/fonts 2 : 이미지/폰트 로딩 차단 → 속도 향상
    - eager          : DOM 로딩 완료 시 바로 진행 (모든 리소스 대기 X)
    """
    options = ChromiumOptions()
    options.page_load_strategy = 'eager'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2
    })
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(service=CHROME_SERVICE, options=options)

    # 봇 감지 우회
    # navigator.webdriver 속성을 undefined로 덮어써 자동화 감지 차단
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })

    driver.set_page_load_timeout(timeout)

    # 추적 리스트에 추가
    _active_drivers.append(driver)
    return driver


@contextmanager
def managedDriver():
    """
    Context Manager 기반 드라이버 관리

    [목적]
    - with 블록 종료 시 정상/예외 상황 모두 driver.quit() 자동 호출 보장
    - try/finally 구조로 드라이버 누수 완전 차단

    [사용법]
        with managedDriver() as driver:
            driver.get(url)
            # 작업 수행
        # with 블록 종료 시 자동 quit()
    """
    driver = getDriver()
    try:
        yield driver
    finally:
        if driver in _active_drivers:
            _active_drivers.remove(driver)
        try:
            driver.quit()
            logger.info("Driver: 종료 성공", extra={"action": "managedDriver"})
        except Exception as e:
            logger.error("Driver: 종료 실패", extra={"action": "managedDriver", "err_msg": str(e)})


def extractContentWithJS(driver, title=""):
    """
    본문 영역 우선 탐색 + JS 범용 추출

    [처리 순서]
    1. 제목 기반 사전 필터링 (isValid로 불필요한 페이지 차단)
    2. p 태그 로딩 대기 (최대 3초)
    3. JS로 본문 컨테이너 탐색 및 텍스트 추출
    4. 클리닝 적용
    5. 최종 품질 검증

    [목적]
    - 다양한 뉴스 사이트 구조에 대응하는 범용 본문 추출
    - 컨테이너 기반 탐색으로 광고/메뉴 텍스트 제외
    """
    # [1] 제목 기반 사전 필터링
    # 본문을 가져오기 전에 제목만으로 불필요한 페이지 차단
    # → 불필요한 페이지 로딩 시간 절약
    if not NewsCleaner.isValid("", title):
        return ""

    try:
        # 대기 시간을 3초로 단축 (eager 모드 효율 극대화)
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.TAG_NAME, "p")))
    except:
        pass

    # [2단계] 본문 컨테이너 기반 JS 추출
    # 뉴스 사이트별 주요 본문 컨테이너를 우선 탐색하여
    # 광고/네비게이션 등 불필요한 요소 제외
    js_script = """
    var res = [];
    var seen = new Set();

    // 뉴스 사이트별 주요 본문 컨테이너 후보
    var selectors = [
        'article', 'main', '.article-body', '.story-content', 
        '.entry-content', '[itemprop="articleBody"]', '#main-content', '.content'
    ];

    let bestContainer = null;
    let maxLen = 0;

    document.querySelectorAll(selectors.join(',')).forEach(el => {
        let length = el.innerText.length;
        if(length > maxLen) {
            maxLen = length;
            bestContainer = el;
        }
    });

    // 컨테이너를 찾으면 그 안에서만, 못 찾으면 전체에서 추출
    let target = (bestContainer && maxLen > 200) ? bestContainer : document.body;

    // p태그 및 본문 블록 요소들 수집
    let elements = target.querySelectorAll('p, div[class*="article-text"], div[class*="story-block"], section');

    elements.forEach(el => {
        var txt = el.innerText.replace(/\\s+/g, ' ').trim();
        // 중복 및 너무 짧은 텍스트(광고/버튼 등) 필터링
        if(txt.length > 55 && !seen.has(txt)) {
            res.push(txt);
            seen.add(txt);
        }
    });

    return res.join('\\n\\n');
    """

    try:
        raw_content = driver.execute_script(js_script)
    except Exception as e:
        logger.error("JS 본문 추출 실패", extra={"action": "managedDriver", "err_msg": str(e)})
        return ""

    # [3단계] 정밀 클리닝
    cleaned_content = NewsCleaner.clean(raw_content)

    # [4단계] 최종 품질 검수 (본문 미달 시 실패 처리)
    if not NewsCleaner.isValid(cleaned_content, title):
        return ""

    return cleaned_content


def generateHashId(url, title):
    """
    중복 방지용 고유 ID 생성

    [목적]
    - URL + 제목 기반 MD5 해시로 동일 기사 중복 적재 방지
    - URL 쿼리스트링/앵커 제거 후 해시 생성으로 동일 기사 변형 URL 처리

    [효과]
    - ES에 동일 기사가 중복 적재되는 것을 완전 차단
    - doc_id를 ES _id로 사용하여 upsert 방식으로 중복 관리
    """
    clean_url = url.split('?')[0].split('#')[0].strip()
    raw_str = f"{clean_url}{title.strip()}"
    return hashlib.md5(raw_str.encode()).hexdigest()