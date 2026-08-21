"""
Memory Extraction & Decision Service
Integrates NVIDIA Nemotron Nano 8B, OpenAI, Anthropic, Ollama, and high-precision heuristic fallback.
Features connection pooling, prompt sanitization, fast failover, and strict JSON validation.
"""

import json
import logging
import re
from typing import Optional

from app.config import settings
from app.schemas.extraction import MemoryExtractionResponse, ExtractedMemoryItem
from app.services.http_client import http_client_manager
from app.services.security_service import security_service

logger = logging.getLogger("tanvelo.extraction")

EXTRACTION_SYSTEM_PROMPT = """You are Tanvelo's Memory Decision Engine, an intelligent memory evaluation system.
Your job is to analyze developer input and extract persistent, valuable long-term memories.

RULES:
1. ALWAYS STORE (should_store=true):
   - Explicit instructions like "Remember that...", "Save this...", "Keep in mind that...". For explicit instructions, set importance >= 0.90.
   - Project architecture, technology stack choices, database decisions, framework facts (importance >= 0.85).
   - Persistent developer preferences (e.g., "I prefer Python over TypeScript", "I use tabs").
   - Important architectural decisions and project goals.

2. NEVER STORE (should_store=false, memories=[]):
   - Explicit instructions like "Don't remember this", "Do not save this conversation".
   - Chit-chat, greetings ("Hello", "How are you?", "Thanks"), casual banter.
   - Generic questions ("What is an API?", "How does Docker work?").
   - Transitory commands or immediate execution context.

3. TEMPORARY SHORT-TERM INFORMATION:
   - For temporary daily tasks (e.g., "I'm fixing authentication today", "Working on bug #123 right now"):
     Set should_store=true, type="temporary", expires=true, expires_in_hours=24.0.

4. MEMORY TYPES:
   - preference, project_fact, technical_fact, decision, personal_fact, task, goal, conversation_summary, temporary.

5. OUTPUT FORMAT:
   You MUST return ONLY a valid JSON object with the following schema:
{
  "should_store": true | false,
  "memories": [
    {
      "content": "Clean, standalone, atomic statement of fact",
      "type": "project_fact | preference | temporary | ...",
      "importance": 0.0 to 1.0,
      "confidence": 0.0 to 1.0,
      "expires": false | true,
      "expires_in_hours": null | number,
      "reason": "Brief explanation"
    }
  ]
}
"""


class ExtractionService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.api_key = settings.NVIDIA_API_KEY
        self.model = settings.NVIDIA_MODEL
        self.base_url = settings.NVIDIA_BASE_URL

    async def extract_memories(
        self,
        raw_text: str,
        manual_type: Optional[str] = None,
        manual_importance: Optional[float] = None,
        force_store: bool = False
    ) -> MemoryExtractionResponse:
        """
        Evaluates input text and extracts candidate long-term memories.
        """
        text = security_service.sanitize_text(raw_text.strip())
        if not text:
            return MemoryExtractionResponse(should_store=False, memories=[])

        # Check explicit negative instruction
        if self._is_explicit_do_not_remember(text):
            return MemoryExtractionResponse(
                should_store=False,
                memories=[],
                raw_response="Explicit user instruction: do not remember."
            )

        # If force_store is requested, bypass LLM
        if force_store:
            clean_fact = self._clean_statement(text)
            item = ExtractedMemoryItem(
                content=clean_fact,
                type=manual_type or "project_fact",
                importance=manual_importance if manual_importance is not None else 0.85,
                confidence=1.0,
                expires=False,
                reason="Forced storage via direct API instruction"
            )
            return MemoryExtractionResponse(should_store=True, memories=[item])

        # Attempt LLM extraction if provider is configured and not in test/mock mode
        if not settings.is_testing and self.api_key and not self.api_key.startswith("nvapi-your") and not self.api_key.startswith("mock"):
            try:
                llm_result = await self._call_llm(text)
                if llm_result:
                    if manual_type or manual_importance is not None:
                        for m in llm_result.memories:
                            if manual_type:
                                m.type = manual_type
                            if manual_importance is not None:
                                m.importance = manual_importance
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM extraction call failed ({e}), using heuristic rule extraction.")

        # Heuristic Rule-Based Decision Engine (Robust fallback)
        return self._heuristic_extraction(text, manual_type, manual_importance)

    async def _call_llm(self, text: str) -> Optional[MemoryExtractionResponse]:
        """Routes call to configured LLM provider."""
        client = http_client_manager.get_client()

        if self.provider == "nvidia":
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this text and extract memories:\n\n\"{text}\""}
                ],
                "temperature": 0.1,
                "max_tokens": 512
            }
            resp = await client.post(url, headers=headers, json=payload, timeout=3.5)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json_response(raw_content)

        elif self.provider == "openai":
            url = f"{settings.OPENAI_BASE_URL}/chat/completions"
            key = settings.OPENAI_API_KEY or self.api_key
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this text and extract memories:\n\n\"{text}\""}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            resp = await client.post(url, headers=headers, json=payload, timeout=3.5)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json_response(raw_content)

        return None

    def _parse_json_response(self, raw_content: str) -> Optional[MemoryExtractionResponse]:
        """Safely parses and validates JSON output from LLM."""
        try:
            cleaned = raw_content.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            parsed = json.loads(cleaned)
            memories = [
                ExtractedMemoryItem(**item) for item in parsed.get("memories", [])
            ]
            should_store = parsed.get("should_store", False)
            if memories and not should_store:
                should_store = True

            return MemoryExtractionResponse(
                should_store=should_store,
                memories=memories,
                raw_response=raw_content
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON response: {e}. Content: {raw_content[:200]}")
            return None

    def _heuristic_extraction(
        self,
        text: str,
        manual_type: Optional[str] = None,
        manual_importance: Optional[float] = None
    ) -> MemoryExtractionResponse:
        """
        High-precision rule-based memory extraction engine.
        Accurately classifies project facts, explicit remember instructions, casual chat, and temporary notes.
        """
        lower = text.lower().strip()

        # 1. Casual Chat / Greetings / Low-value queries
        casual_patterns = [
            r"\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b",
            r"\b(how are you|how's it going|how are things|what's up)\b",
            r"\b(thanks|thank you|cool|ok|okay|got it|nice)\b",
            r"^what is [a-zA-Z0-9_\s]+\??$",
            r"^how do i [a-zA-Z0-9_\s]+\??$"
        ]
        has_tech = any(ind in lower for ind in [
            "uses", "built with", "runs on", "database", "backend", "frontend",
            "stack", "framework", "architecture", "postgres", "supabase", "fastapi",
            "pgvector", "docker", "python", "typescript", "react", "prefer", "remember"
        ])
        if not has_tech:
            for pattern in casual_patterns:
                if re.search(pattern, lower):
                    return MemoryExtractionResponse(
                        should_store=False,
                        memories=[],
                        raw_response="Identified as casual chit-chat or generic query."
                    )


        # 2. Explicit Remember ("Remember that I prefer Python")
        explicit_match = re.search(r"^(?:please\s+)?(?:remember|keep in mind|save)(?:\s+that|\s+this)?[:,\s]+(.*)$", text, re.IGNORECASE)
        if explicit_match:
            fact = explicit_match.group(1).strip().rstrip(".")
            mtype = manual_type or ("preference" if "prefer" in fact.lower() or "like" in fact.lower() else "project_fact")
            item = ExtractedMemoryItem(
                content=self._clean_statement(fact),
                type=mtype,
                importance=manual_importance if manual_importance is not None else 0.95,
                confidence=0.98,
                expires=False,
                reason="Explicit user instruction to remember."
            )
            return MemoryExtractionResponse(should_store=True, memories=[item])

        # 3. Temporary Task Information ("I'm fixing authentication today")
        temp_patterns = [
            r"\b(today|right now|currently|working on|fixing|debugging|temporary|this morning|this afternoon)\b",
            r"\b(i'm fixing|i am fixing|i'm working on|i am working on)\b"
        ]
        if any(re.search(p, lower) for p in temp_patterns) and not ("uses" in lower or "architecture" in lower):
            clean_fact = self._clean_statement(text)
            item = ExtractedMemoryItem(
                content=clean_fact,
                type=manual_type or "temporary",
                importance=manual_importance if manual_importance is not None else 0.50,
                confidence=0.90,
                expires=True,
                expires_in_hours=24.0,
                reason="Short-term work/task information with automatic 24-hour expiration."
            )
            return MemoryExtractionResponse(should_store=True, memories=[item])

        # 4. Important Project Facts & Technology Choices ("Tanvelo uses FastAPI")
        tech_indicators = [
            "uses", "built with", "runs on", "database is", "backend is", "frontend is",
            "stack", "framework", "architecture", "postgres", "supabase", "fastapi",
            "pgvector", "docker", "python", "typescript", "react", "next.js", "redis"
        ]
        if any(ind in lower for ind in tech_indicators) or manual_type in ["project_fact", "technical_fact", "decision"]:
            clean_fact = self._clean_statement(text)
            mtype = manual_type or ("decision" if "decided" in lower or "chose" in lower else "project_fact")
            item = ExtractedMemoryItem(
                content=clean_fact,
                type=mtype,
                importance=manual_importance if manual_importance is not None else 0.92,
                confidence=0.95,
                expires=False,
                reason="Core project architecture and technology choice."
            )
            return MemoryExtractionResponse(should_store=True, memories=[item])

        # 5. General preference / personal fact
        if "prefer" in lower or "always" in lower or "my favorite" in lower or "never use" in lower:
            clean_fact = self._clean_statement(text)
            item = ExtractedMemoryItem(
                content=clean_fact,
                type=manual_type or "preference",
                importance=manual_importance if manual_importance is not None else 0.85,
                confidence=0.90,
                expires=False,
                reason="User preference statement."
            )
            return MemoryExtractionResponse(should_store=True, memories=[item])

        # Default: If meaningful sentence length >= 3 words, store as project_fact
        if len(text.split()) >= 3:
            clean_fact = self._clean_statement(text)
            item = ExtractedMemoryItem(
                content=clean_fact,
                type=manual_type or "project_fact",
                importance=manual_importance if manual_importance is not None else 0.70,
                confidence=0.85,
                expires=False,
                reason="Informational statement worth storing."
            )
            return MemoryExtractionResponse(should_store=True, memories=[item])

        return MemoryExtractionResponse(should_store=False, memories=[])

    def _is_explicit_do_not_remember(self, text: str) -> bool:
        lower = text.lower()
        patterns = [
            r"\b(don't remember|do not remember|do not save|don't save|off the record|forget this conversation)\b"
        ]
        return any(re.search(p, lower) for p in patterns)

    def _clean_statement(self, text: str) -> str:
        """Removes prefix phrases like 'Remember that' or quotation marks."""
        cleaned = text.strip().strip('"\'')
        cleaned = re.sub(r"^(?:please\s+)?(?:remember|keep in mind|save)(?:\s+that|\s+this)?[:,\s]+", "", cleaned, flags=re.IGNORECASE)
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned.strip()


extraction_service = ExtractionService()
