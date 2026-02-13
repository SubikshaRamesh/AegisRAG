from llama_cpp import Llama
from typing import List, Dict


class OfflineLLM:
    def __init__(self, model_path: str):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=8,
            verbose=False
        )

    def generate_answer(self, question: str, contexts: List[Dict]) -> str:
        """
        Generate an answer strictly from retrieved contexts.
        """

        # Build clean context block
        context_text = ""

        for i, c in enumerate(contexts, 1):
            context_text += (
                f"[Source {i} | File: {c['source_file']} | "
                f"Page: {c['page_number']} | "
                f"Timestamp: {c['timestamp']}]\n"
                f"{c['text']}\n\n"
            )

        prompt = f"""
You are a precise factual assistant.

Answer ONLY the given question using the provided context.
Do NOT generate additional questions.
Do NOT invent information.
If the answer is not found in the context, say exactly:
Not found in the provided documents.

Question:
{question}

Context:
{context_text}

Answer:
"""

        output = self.llm(
            prompt,
            max_tokens=400,
            temperature=0.05,
            stop=["Question:", "</s>"]
        )

        return output["choices"][0]["text"].strip()
