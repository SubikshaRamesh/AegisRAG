from llama_cpp import Llama
from typing import List, Dict, Generator
import os
import time

from core.logger import get_logger

logger = get_logger(__name__)


class OfflineLLM:
    """TinyLlama-optimized LLM for fast CPU inference."""

    def __init__(self, model_path: str):
        logger.info(f"[LLM] ⚡ Loading TinyLlama model from {model_path}...")
        load_start = time.time()

        # 🔥 TinyLlama optimized for CPU
        cpu_threads = os.cpu_count() or 4
        cpu_count_display = cpu_threads

        self.llm = Llama(
            model_path=model_path,
            n_ctx=1024,                # Keep context window
            n_threads=cpu_threads,     # 🔥 Use ALL CPU cores
            n_batch=512,               # 🔥 Large batch for throughput
            verbose=False,
            n_gpu_layers=0,            # CPU-only (no GPU)
        )

        load_time = time.time() - load_start
        logger.info(f"[LLM] ✓ Model loaded in {load_time:.3f}s")
        logger.info(f"[LLM] 🔧 Configuration:")
        logger.info(f"     - Model: TinyLlama-1.1B-Chat")
        logger.info(f"     - CPU Threads: {cpu_count_display}")
        logger.info(f"     - Batch Size: 512")
        logger.info(f"     - Context Window: 1024")
        logger.info(f"     - Mode: CPU-only (no GPU)")
        logger.info(f"[LLM] Expected inference time: 2-6 seconds per query")


    def generate_answer(
        self,
        question: str,
        contexts: List[Dict],
        history: List[Dict] = None,
    ) -> str:

        gen_start = time.time()

        if not contexts:
            logger.debug("[LLM] No contexts provided, returning fallback")
            return "Information not found in knowledge base."

        # 🔥 Build context (limit size for speed)
        context_build_start = time.time()

        context_text = ""
        for c in contexts:
            context_text += c["text"].strip() + "\n\n"

        # Limit context to prevent slowdown
        context_text = context_text[:1500]

        context_build_time = time.time() - context_build_start
        logger.debug(f"[LLM] Context build: {context_build_time:.3f}s ({len(context_text)} chars)")

        # 🔥 Multilingual WITHOUT language detection
        prompt_start = time.time()

        prompt = f"""You are a helpful AI assistant.

Answer in the SAME language as the question.
Use ONLY the provided context.
Do NOT invent information.
If the answer is not found, reply exactly:
Information not found in knowledge base.

Question:
{question}

Context:
{context_text}

Answer:
"""

        prompt_time = time.time() - prompt_start
        logger.debug(f"[LLM] Prompt build: {prompt_time:.3f}s ({len(prompt)} chars)")

        # 🔥 LLM Inference with TinyLlama optimized parameters
        llm_call_start = time.time()

        output = self.llm(
            prompt,
            max_tokens=100,          # 🔥 Reduced to 100 tokens for speed (< 6s total)
            temperature=0.1,         # Deterministic decoding (reproducible answers)
            top_p=0.9,               # Nucleus sampling for quality
            repeat_penalty=1.1,      # Avoid word repetition
            stop=["Question:", "</s>"]
        )

        llm_call_time = time.time() - llm_call_start
        tokens_per_second = 100 / llm_call_time if llm_call_time > 0 else 0
        logger.info(
            f"[LLM] 🚀 Inference complete: {llm_call_time:.3f}s "
            f"({tokens_per_second:.1f} tokens/sec)"
        )
        logger.debug(f"[LLM] Model inference: {llm_call_time:.3f}s")

        answer = output["choices"][0]["text"].strip()

        if not answer:
            logger.debug("[LLM] Empty answer, returning fallback")
            answer = "Information not found in knowledge base."

        total_time = time.time() - gen_start

        logger.info(
            f"[LLM] generate_answer complete: {total_time:.3f}s "
            f"(context: {context_build_time:.3f}s, "
            f"prompt: {prompt_time:.3f}s, "
            f"inference: {llm_call_time:.3f}s)"
        )

        return answer

    def stream_answer(
        self,
        question: str,
        contexts: List[Dict],
        history: List[Dict] = None,
    ) -> Generator[str, None, None]:
        """Stream answer tokens as they are generated.
        
        Yields:
            str: Individual tokens from the LLM
        """
        gen_start = time.time()

        if not contexts:
            logger.debug("[LLM] No contexts provided, returning fallback")
            yield "Information not found in knowledge base."
            return

        # 🔥 Build context (limit size for speed)
        context_build_start = time.time()

        context_text = ""
        for c in contexts:
            context_text += c["text"].strip() + "\n\n"

        # Limit context to prevent slowdown
        context_text = context_text[:1500]

        context_build_time = time.time() - context_build_start
        logger.debug(f"[LLM] Context build: {context_build_time:.3f}s ({len(context_text)} chars)")

        # 🔥 Multilingual WITHOUT language detection
        prompt_start = time.time()

        prompt = f"""You are a helpful AI assistant.

Answer in the SAME language as the question.
Use ONLY the provided context.
Do NOT invent information.
If the answer is not found, reply exactly:
Information not found in knowledge base.

Question:
{question}

Context:
{context_text}

Answer:
"""

        prompt_time = time.time() - prompt_start
        logger.debug(f"[LLM] Prompt build: {prompt_time:.3f}s ({len(prompt)} chars)")

        # 🔥 LLM Streaming with TinyLlama optimized parameters
        llm_call_start = time.time()
        token_count = 0

        try:
            for chunk in self.llm(
                prompt,
                max_tokens=100,
                temperature=0.1,
                top_p=0.9,
                repeat_penalty=1.1,
                stop=["Question:", "</s>"],
                stream=True,  # 🔥 Enable streaming
            ):
                token = chunk["choices"][0]["text"]
                if token:
                    token_count += 1
                    yield token
        except Exception as e:
            logger.error(f"[LLM] Streaming error: {e}")
            yield "Error generating response. Please try again."
            return

        llm_call_time = time.time() - llm_call_start
        tokens_per_second = token_count / llm_call_time if llm_call_time > 0 else 0
        total_time = time.time() - gen_start

        logger.info(
            f"[LLM] 🚀 Stream complete: {llm_call_time:.3f}s "
            f"({token_count} tokens, {tokens_per_second:.1f} tokens/sec)"
        )
        logger.debug(
            f"[LLM] Stream breakdown: "
            f"context: {context_build_time:.3f}s, "
            f"streaming: {llm_call_time:.3f}s, "
            f"total: {total_time:.3f}s"
        )

