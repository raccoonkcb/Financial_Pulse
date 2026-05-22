import torch
import time
import math
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm
from logs.logger import getLogger
logger = getLogger("ml")


# === [ 설정 영역 ] ===
ES_URL = "http://100.88.143.23:9200/"
TARGET_INDEX = 'analyze'
BATCH_SIZE = 8
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

es = Elasticsearch(ES_URL, request_timeout=60)

MODELS = {
    "en": "ProsusAI/finbert",
    "ko": "snunlp/KR-FinBert-SC"
}
# 0~100점 스케일 버전을 명시합니다.
SENTIMENT_VERSION = "sentiment_v1.0"

def run_sentiment_pipeline(lang: str, start_date: str, end_date: str):
    start_time = time.time()

    model_name= MODELS.get(lang)
    if not model_name:
        logger.warning("모델 없음")
        return
    logger.info(f"[{lang.upper()}] 모델 로딩: {model_name} ({DEVICE})", extra={"action": "run_sentiment_pipeline"})
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name).to(DEVICE)
    model.eval()

    origin_index = f"news_{lang}"
    if start_date and end_date:
        query = {
            "query": {
                "range": {
                    "published_at": {"gte": start_date, "lte": end_date}
                }
            }
        }
    else:
        query = {"query": {"match_all": {}}}
    docs = list(helpers.scan(es, index=origin_index, query=query, _source=["content", "title"]))

    if not docs: return

    actions = []
    for i in tqdm(range(0, len(docs), BATCH_SIZE), desc=f"Sentiment ({lang})"):
        batch_docs = docs[i : i + BATCH_SIZE]
        batch_texts = []
        valid_batch_docs = []

        for d in batch_docs:
            source = d['_source']
            title = source.get('title', '')
            content = source.get('content', '')

            # 제목 가중치를 위해 3회 반복
            weighted_text = f"{title}. {title}. {title}. {content}"

            if weighted_text and len(str(weighted_text).strip()) > 10:
                batch_texts.append(weighted_text)
                valid_batch_docs.append(d)

        if not batch_texts: continue

        inputs = tokenizer(batch_texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(DEVICE)

        with torch.no_grad():
            outputs = model(**inputs)
            # Softmax 없이 모델의 raw 가중치 점수(Logits)를 그대로 확보
            raw_logits = outputs.logits.cpu()

        for j, doc in enumerate(valid_batch_docs):
            source = doc['_source']
            pk_id = source.get('doc_id')

            if not pk_id:
                pk_id = doc['_id']

            # --- [언어별 인덱스 매핑 규칙] ---
            if lang == "en":
                # {0: 'positive', 1: 'negative', 2: 'neutral'}
                p_logit = raw_logits[j][0].item()
                n_logit = raw_logits[j][1].item()
            else:  # "ko" 인 경우
                # {0: 'negative', 1: 'neutral', 2: 'positive'}
                n_logit = raw_logits[j][0].item()
                p_logit = raw_logits[j][2].item()
            # ---------------------------------------------------

            # --- [Raw Logit 기반 0~100점 변환 로직] ---
            # 긍정과 부정한 어감의 순수 차이량(Margin) 계산
            logit_margin = p_logit - n_logit

            # 시그모이드로 극단적 변동을 제어하고 0.0 ~ 1.0 범위로 중화
            prob_base = 1 / (1 + math.exp(-logit_margin))

            # 최종 0~100점 정수형 스케일로 변환
            final_score_100 = round(prob_base * 100)

            # 요청하신 조건 반영: 50점 이상은 긍정(positive), 50점 미만은 부정(negative)
            if final_score_100 >= 50:
                sentiment_label = "positive"
            else:
                sentiment_label = "negative"
            # ---------------------------------------------------

            actions.append({
                "_op_type": "update",
                "_index": TARGET_INDEX,
                "_id": pk_id,
                "doc": {
                    "doc_id": pk_id,
                    "tendency": sentiment_label,
                    "tend_score": final_score_100,  # 깔끔한 0 ~ 100점 데이터 저장
                    "model_ver": {
                        "sentiment": SENTIMENT_VERSION
                    }
                },
                "doc_as_upsert": True
            })

        if len(actions) >= 100:
            helpers.bulk(es, actions)
            actions = []

    if actions:
        helpers.bulk(es, actions)

    # 메모리 정리
    del model
    del tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info(f"전체 감성 분석 완료: {round(time.time() - start_time, 2)}초", extra={"action": "run_sentiment_pipeline"})

if __name__ == "__main__":
    run_sentiment_pipeline()