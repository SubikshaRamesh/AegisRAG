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

    def generate_answer(
        self,
        question: str,
        contexts: List[Dict],
        history: List[Dict] = None,
    ) -> str:
        """
        Generate a strictly grounded answer from retrieved contexts.
        
        Multilingual support:
        - Question may be in any language
        - Always responds in English for stability
        - Uses only provided context (no speculation)
        """

        # --------------------------------------------------
        # If no context, immediately return fallback
        # --------------------------------------------------
        if not contexts:
            return "Information not found in knowledge base."

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
        # MULTILINGUAL-SAFE EXTRACTION PROMPT
        # --------------------------------------------------
        history_block = ""
        if history:
            formatted_lines = []
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "").strip()
                if not content:
                    continue
                formatted_lines.append(f"{role.title()}: {content}")
            if formatted_lines:
                history_block = "\nConversation History (last 3 messages):\n" + "\n".join(formatted_lines) + "\n"

        prompt = f"""You are a helpful AI assistant.

The user may ask questions in any language.
You MUST always respond in English.
Use only the provided context to answer.

Rules:
- Extract relevant information directly from the context
- Do NOT add new explanations or interpretations
- Do NOT speculate or make assumptions
- Do NOT extend beyond what is in the context
- If the answer is not found in the context, respond exactly with:
"Information not found in knowledge base."
- Always respond in English, regardless of the question language
{history_block}
Question:
{question}

Context:
{context_text}

Answer (in English):
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
            return "Information not found in knowledge base."

        return answer
