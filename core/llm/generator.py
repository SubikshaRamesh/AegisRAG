from llama_cpp import Llama
from typing import List, Dict, Generator
import os
import time
import re

from core.logger import get_logger

logger = get_logger(__name__)


class OfflineLLM:
    """
    Production-ready Offline LLM optimized for Phi-3 GGUF.
    Deterministic, context-grounded, and clean output generation.
    """

    def __init__(self, model_path: str):

        logger.info(f"[LLM] ⚡ Loading model from {model_path}...")
        load_start = time.time()

        cpu_threads = os.cpu_count() or 4

        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=cpu_threads,
            n_batch=1024,
            n_gpu_layers=0,
            use_mlock=True,
            use_mmap=True,
            verbose=False
        )

        load_time = time.time() - load_start

        logger.info(f"[LLM] ✓ Model loaded in {load_time:.3f}s")
        logger.info(f"[LLM] Threads: {cpu_threads}")
        logger.info("[LLM] Deterministic RAG mode enabled")

    # ==========================================================
    # PROMPT BUILDER
    # ==========================================================

    def _build_prompt(self, question: str, context_text: str) -> str:

        system_prompt = (
            "You are a precise AI assistant.\n"
            "Use ONLY the provided context to answer.\n"
            "Combine information from all sources if needed.\n"
            "Do NOT use external knowledge.\n"
            "Do NOT repeat the question.\n"
            "Return only the final answer.\n"
            "If the context does not contain enough information respond with:\n"
            "'Insufficient evidence in knowledge base.'"
        )

        user_prompt = (
            f"Context:\n{context_text}\n\n"
            f"Question:\n{question}\n\n"
            "Provide only the answer."
        )

        prompt = (
            "<|system|>\n"
            f"{system_prompt}\n"
            "<|user|>\n"
            f"{user_prompt}\n"
            "<|assistant|>\n"
        )

        return prompt

    # ==========================================================
    # OUTPUT CLEANING
    # ==========================================================

    def _clean_output(self, answer: str) -> str:

        if not answer:
            return ""

        # Remove Phi tokens
        answer = answer.replace("<|assistant|>", "")
        answer = answer.replace("===<|assistant|>", "")

        # Remove unwanted labels
        answer = answer.replace("Answer:", "")
        answer = answer.replace("Context:", "")

        # Remove Phi artifacts
        answer = answer.replace("[Response]:", "")
        answer = answer.replace("- [Response]:", "")

        # Remove fallback duplicates
        answer = answer.replace(
            "Insufficient evidence in knowledge base.",
            ""
        )

        # Fix common model typo/token artifacts
        answer = answer.replace("celestinas", "celestial")

        # Remove role/control tokens if they leak into output
        answer = re.sub(r"<\|[^|]+\|>", "", answer)

        # Remove leading labels repeatedly (Answer:, Context:, Response:)
        answer = re.sub(
            r"(?im)^\s*(answer|context|response)\s*:\s*",
            "",
            answer,
        )

        answer = answer.strip()

        # Remove duplicated consecutive phrases within a line.
        # Example: "It launched successfully. It launched successfully."
        phrase_pattern = re.compile(
            r"\b(?P<phrase>[A-Za-z0-9][A-Za-z0-9 ,;:'\-]{3,}?[\.!?])\s+(?P=phrase)",
            flags=re.IGNORECASE,
        )
        while True:
            deduped = phrase_pattern.sub(r"\g<phrase>", answer)
            if deduped == answer:
                break
            answer = deduped

        # Collapse obvious repeated words: "the the" -> "the"
        answer = re.sub(r"\b(\w+)\s+\1\b", r"\1", answer, flags=re.IGNORECASE)

        # Remove duplicate lines
        lines = answer.split("\n")

        unique_lines = []

        for line in lines:

            line = line.strip()

            if not line:
                continue

            if line not in unique_lines:
                unique_lines.append(line)

        cleaned = "\n".join(unique_lines).strip()

        return cleaned

    # ==========================================================
    # NON STREAMING GENERATION
    # ==========================================================

    def generate_answer(
        self,
        question: str,
        contexts: List[Dict],
        history: List[Dict] = None,
    ) -> str:

        gen_start = time.time()

        if not contexts:

            logger.debug("[LLM] No contexts provided")

            return "Insufficient evidence in knowledge base."

        context_text = "\n\n".join(
            [c["text"].strip() for c in contexts]
        )[:2500]

        prompt = self._build_prompt(question, context_text)

        output = self.llm(
            prompt,
            max_tokens=120,
            temperature=0.0,
            top_p=1.0,
            repeat_penalty=1.15,
            stop=["<|user|>", "</s>"]
        )

        raw_answer = output["choices"][0]["text"].strip()

        answer = self._clean_output(raw_answer)

        total_time = time.time() - gen_start

        logger.info(f"[LLM] generate_answer complete in {total_time:.3f}s")

        return answer

    # ==========================================================
    # STREAMING GENERATION
    # ==========================================================

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

        collected = ""

        try:

            for chunk in self.llm(
                prompt,
                max_tokens=120,
                temperature=0.0,
                top_p=1.0,
                repeat_penalty=1.15,
                stop=["<|user|>", "</s>"],
                stream=True
            ):

                token = chunk["choices"][0]["text"]

                if token:

                    collected += token

                    yield token

        except Exception as e:

            logger.error(f"[LLM] Streaming error: {e}")

            yield "Error generating response."

        cleaned = self._clean_output(collected)

        logger.debug(f"[LLM] Final cleaned answer: {cleaned}")