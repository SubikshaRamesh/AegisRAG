from llama_cpp import Llama
from typing import List, Dict


class OfflineLLM:
    def __init__(self, model_path: str):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=12,
            n_batch=512,
            verbose=False
        )

    def generate_answer(self, question: str, contexts: List[Dict]) -> str:
        """
        Generate a strictly grounded answer from retrieved contexts.
        """

        # --------------------------------------------------
        # If no context, immediately return fallback
        # --------------------------------------------------
        if not contexts:
            return "Not found in the provided documents."

        # --------------------------------------------------
        # Build structured context block
        # --------------------------------------------------
        context_text = ""

        for i, c in enumerate(contexts, 1):
            context_text += (
                f"[Source {i} | File: {c['source_file']} | "
                f"Page: {c['page_number']} | "
                f"Timestamp: {c['timestamp']}]\n"
                f"{c['text']}\n\n"
            )

        # --------------------------------------------------
        # STRICT EXTRACTION PROMPT (reduces hallucination)
        # --------------------------------------------------
        prompt = f"""
        You are a strict information extractor.

        Your task is to extract relevant sentences from the context that directly answer the question.

        Rules:
        - Only copy or lightly compress information from the context.
        - Do NOT add new explanations.
        - Do NOT speculate.
        - Do NOT extend beyond what is written.
        - If the answer is not explicitly stated, respond exactly with:
        Not found in the provided documents.

        Question:
        {question}

        Context:
        {context_text}

        Extracted Answer:
        """


        # --------------------------------------------------
        # Generate
        # --------------------------------------------------
        output = self.llm(
            prompt,
            max_tokens=150,
            temperature=0.1,
            stop=["Question:", "</s>"]
        )

        answer = output["choices"][0]["text"].strip()

        if not answer:
            return "Not found in the provided documents."

        return answer
