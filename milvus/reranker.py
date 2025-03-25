from flashrank import Ranker, RerankRequest
from pymilvus.model.reranker import BGERerankFunction

ranker = Ranker(model_name="rank-T5-flan", cache_dir="/opt")


def stlFlashRerank(query, passages):
    pa = []
    for i in passages:
        pa.append({"text": i.page_content})
    
    rerankrequest = RerankRequest(query=query, passages=pa)
    results = ranker.rerank(rerankrequest)
    return results


def stlBgeRerank(query, passages):
    bge_rf = BGERerankFunction(
        model_name="BAAI/bge-reranker-v2-m3",
        use_fp16=True
    )

    bge_rf(query=query, documents=passages)
