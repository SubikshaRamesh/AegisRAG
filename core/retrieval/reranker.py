from typing import List, Dict
from sentence_transformers import CrossEncoder
from core.logger import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """
    Cross-encoder reranker for improving retrieval accuracy.
    Adds explainable scoring (retrieval + rerank).
    Fully offline compatible.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):

        logger.info("[RERANKER] Loading cross-encoder model...")

        # Load model only from local cache (offline safe)
        self.model = CrossEncoder(
            model_name,
            local_files_only=True
        )

        logger.info("[RERANKER] Model loaded")

    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:

        if not results:
            return results

        # Prepare query-document pairs
        pairs = [(query, r.get("text", "")) for r in results]

        scores = self.model.predict(pairs)

        for r, s in zip(results, scores):

            rerank_score = float(s)

            # Convert FAISS distance to similarity
            distance = r.get("distance", 1.0)
            retrieval_score = 1 / (1 + distance)

            r["rerank_score"] = rerank_score
            r["retrieval_score"] = retrieval_score

            # Combined score for ranking
            r["final_score"] = (
                retrieval_score * 0.4 +
                rerank_score * 0.6
            )

        ranked = sorted(
            results,
            key=lambda x: x["final_score"],
            reverse=True
        )

        return ranked[:top_k]