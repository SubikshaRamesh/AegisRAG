from llama_cpp import Llama
from typing import List, Dict
from langdetect import detect


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
        Fully offline multilingual-safe grounded generation.
        """

        # -----------------------------------------
        # 1️⃣ If no context → fallback
        # -----------------------------------------
        if not contexts:
            return "Information not found in knowledge base."

        # -----------------------------------------
        # 2️⃣ Detect language of question
        # -----------------------------------------
        try:
            detected_lang = detect(question)
        except:
            detected_lang = "en"

        lang_map = {
            "en": "English",
            "ta": "Tamil",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
        }

        language_name = lang_map.get(detected_lang, "English")

        # -----------------------------------------
        # 3️⃣ Build context block
        # -----------------------------------------
        context_text = ""

        for i, c in enumerate(contexts, 1):
            context_text += (
                f"[Source {i} | File: {c['source_file']} | "
                f"Page: {c['page_number']} | "
                f"Timestamp: {c['timestamp']}]\n"
                f"{c['text']}\n\n"
            )

        # -----------------------------------------
        # 4️⃣ Conversation history (last 3)
        # -----------------------------------------
        history_block = ""
        if history:
            formatted_lines = []
            for msg in history[-3:]:
                role = msg.get("role", "user")
                content = msg.get("content", "").strip()
                if not content:
                    continue
                formatted_lines.append(f"{role.title()}: {content}")

            if formatted_lines:
                history_block = (
                    "\nConversation History:\n"
                    + "\n".join(formatted_lines)
                    + "\n"
                )

        # -----------------------------------------
        # 5️⃣ Strict Prompt
        # -----------------------------------------
        prompt = f"""
You are a strict extraction assistant.

You MUST answer ONLY in {language_name}.
Do NOT switch languages.
Do NOT translate unless explicitly asked.
Use ONLY the provided context.
Do NOT repeat the question.
Do NOT mention the context.

If answer is not found in context, respond EXACTLY:
Information not found in knowledge base.

{history_block}

Question:
{question}

Context:
{context_text}

Answer:
"""

        # -----------------------------------------
        # 6️⃣ Generate (deterministic)
        # -----------------------------------------
        output = self.llm(
            prompt,
            max_tokens=150,
            temperature=0.0,
            stop=["Question:", "</s>", "Context:"]
        )

        answer = output["choices"][0]["text"].strip()

        if not answer:
            return "Information not found in knowledge base."

        # -----------------------------------------
        # 7️⃣ HARD LANGUAGE ENFORCEMENT
        # -----------------------------------------
        try:
            answer_lang = detect(answer)
        except:
            answer_lang = detected_lang

        # If language mismatch → regenerate once
        if answer_lang != detected_lang:
            correction_prompt = f"""
The previous answer was not in {language_name}.

Rewrite the following answer STRICTLY in {language_name}.
Do NOT add anything.

Answer:
{answer}
"""

            retry = self.llm(
                correction_prompt,
                max_tokens=150,
                temperature=0.0
            )

            corrected = retry["choices"][0]["text"].strip()

            if corrected:
                return corrected

        return answer
