from groq import Groq
import os
from typing import List, Dict, Generator


class GroqLLM:

    def __init__(self):

        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    def _build_prompt(self, question: str, context_text: str) -> str:

        return f"""
You are a precise AI assistant.

Use ONLY the provided context to answer.

Context:
{context_text}

Question:
{question}

Answer:
"""

    def generate_answer(
        self,
        question: str,
        contexts: List[Dict],
        history: List[Dict] = None,
    ) -> str:

        if not contexts:
            return "Insufficient evidence in knowledge base."

        context_text = "\n\n".join(
            [c["text"].strip() for c in contexts]
        )[:2500]

        prompt = self._build_prompt(question, context_text)

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )

        return response.choices[0].message.content

    def stream_answer(
        self,
        question: str,
        contexts: List[Dict],
        history: List[Dict] = None,
    ) -> Generator[str, None, None]:

        if not contexts:
            yield "Insufficient evidence in knowledge base."
            return

        context_text = "\n\n".join(
            [c["text"].strip() for c in contexts]
        )[:2500]

        prompt = self._build_prompt(question, context_text)

        stream = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            stream=True,
        )

        for chunk in stream:

            token = chunk.choices[0].delta.content

            if token:
                yield token