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
        context_text = "\n\n".join(
            f"[Source: {c['source_file']}, Page: {c['page_number']}]\n{c['text']}"
            for c in contexts
        )

        prompt = f"""
You are a factual assistant.
Answer ONLY using the information provided below.
If the answer is not contained in the context, say "Not found in the provided documents".

Context:
{context_text}

Question:
{question}

Answer (include citations):
"""

        output = self.llm(
            prompt,
            max_tokens=512,
            temperature=0.1,
            stop=["</s>"]
        )

        return output["choices"][0]["text"].strip()
