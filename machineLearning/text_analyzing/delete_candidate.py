import json
import os
import shutil
from sort_json import sort_json
from logs.logger import getLogger
logger = getLogger("ml")

def clean_candidates(filename):
    dict_path = os.path.join(os.path.dirname(__file__), 'dictionary')
    file_path = os.path.join(dict_path, filename)
    backup_path = os.path.join(dict_path, f"{filename.replace('.json', '')}_backup.json")

    if not os.path.exists(file_path):
        logger.warning(f"파일을 찾을 수 없습니다: {file_path}", extra={"action": "clean_candidate"})
        return

    # 1. 파일 읽기
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"{filename} 파일의 JSON 형식이 깨져 있습니다. 빈 파일인지 확인하세요.", extra={"action": "clean_candidate"})
        return

    # 2. 정식 데이터만 필터링 (안전함!)
    original_count = len(data)
    cleaned_data = {k: v for k, v in data.items() if not k.startswith("candidate_")}
    removed_count = original_count - len(cleaned_data)

    if removed_count == 0:
        logger.info(f"[{filename}] 지울 candidate 없다.", extra={"action": "clean_candidate"})
        return

    # 3. 안전을 위한 자동 백업
    shutil.copy2(file_path, backup_path)
    logger.info(f"원본 데이터 백업 완료: {os.path.basename(backup_path)}", extra={"action": "clean_candidate"})

    # 4. 임시 저장 (파이썬 기본 포맷으로 우선 저장)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

    # 💡 5. [핵심] 기존 포맷(배열 한 줄 표시)으로 예쁘게 덮어쓰기 정렬
    sort_json(file_path)

    logger.info(f"[{filename}] 정리 및 포맷팅 완료 ({removed_count}개 candidate 삭제)", extra={"action": "clean_candidate"})

if __name__ == "__main__":
    target_files = ['company.json', 'person.json']