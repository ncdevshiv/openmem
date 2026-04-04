"""
OpenMem — Agent-Agnostic LLM Interface.

Works with ANY LLM provider via litellm (OpenAI, Anthropic, Ollama, Gemini, etc.)
Falls back to heuristic keyword mode when no LLM is configured.

Usage:
    from core.llm import OpenMemLLM

    llm = OpenMemLLM()  # Auto-detects provider
    result = llm.summarize("daily memories text...")
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

OPENMEM_ROOT = Path(__file__).parent.parent
CONFIG_FILE = OPENMEM_ROOT / "config.json"


class OpenMemLLM:
    """
    Agent-agnostic LLM wrapper.

    Supports any provider via litellm:
    - OpenAI: gpt-4, gpt-3.5-turbo
    - Anthropic: claude-sonnet, claude-opus
    - Ollama: llama3, mistral, qwen
    - Gemini: gemini-pro
    - Any OpenAI-compatible endpoint

    Falls back to heuristic mode when no LLM is configured.
    """

    def __init__(self, config: Dict = None):
        self.config = config or self._load_config()
        self._client = None
        self._available = False
        self._init_client()

    def _load_config(self) -> Dict:
        """Load configuration."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"llm": {"provider": "auto", "model": "auto"}}

    def _init_client(self):
        """Initialize LLM client."""
        llm_config = self.config.get("llm", {})
        provider = llm_config.get("provider", "auto").lower()
        model = llm_config.get("model", "auto")

        # Check for litellm
        try:
            import litellm
            self._litellm = litellm

            # Set API key from env if not configured
            api_key_env = llm_config.get("api_key_env", "AUTO")
            if api_key_env == "AUTO":
                # Try common env vars
                for env_var in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
                    if os.environ.get(env_var):
                        api_key_env = env_var
                        break

            if api_key_env != "AUTO" and os.environ.get(api_key_env):
                # Set provider-specific key
                if "OPENAI" in api_key_env:
                    litellm.openai_key = os.environ[api_key_env]
                elif "ANTHROPIC" in api_key_env:
                    litellm.anthropic_key = os.environ[api_key_env]
                elif "GEMINI" in api_key_env:
                    litellm.google_ai_studio_key = os.environ[api_key_env]

            # Auto-detect provider if not set
            if provider == "auto":
                if os.environ.get("OPENAI_API_KEY"):
                    provider = "openai"
                    if model == "auto":
                        model = "gpt-4o-mini"
                elif os.environ.get("ANTHROPIC_API_KEY"):
                    provider = "anthropic"
                    if model == "auto":
                        model = "claude-sonnet-4-20250514"
                elif os.environ.get("OLLAMA_BASE_URL"):
                    provider = "ollama"
                    if model == "auto":
                        model = "llama3"
                else:
                    # No provider configured — use heuristic fallback
                    self._available = False
                    return

            # Test the connection
            try:
                model_name = f"{provider}/{model}" if provider != "ollama" else f"ollama/{model}"
                response = litellm.completion(
                    model=model_name,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=5,
                    timeout=10,
                )
                self._available = True
                self._provider = provider
                self._model = model
                self._model_name = model_name
            except Exception:
                self._available = False

        except ImportError:
            # litellm not installed — use heuristic mode
            self._available = False
            self._litellm = None

    @property
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self._available

    @property
    def provider(self) -> str:
        """Get current provider."""
        return getattr(self, "_provider", "heuristic")

    @property
    def model(self) -> str:
        """Get current model."""
        return getattr(self, "_model", "heuristic")

    def chat(self, messages: List[Dict], max_tokens: int = 2000,
             temperature: float = 0.7) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            max_tokens: Max response tokens
            temperature: Response temperature

        Returns:
            Response text
        """
        if self._available and self._litellm:
            try:
                response = self._litellm.completion(
                    model=self._model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"[LLM Error: {e}]"

        # Heuristic fallback
        return self._heuristic_response(messages)

    def summarize(self, text: str, max_length: int = 200) -> str:
        """
        Summarize text content.

        Args:
            text: Text to summarize
            max_length: Max summary length

        Returns:
            Summary string
        """
        if self._available:
            return self.chat([
                {"role": "system", "content": "Summarize the following text concisely."},
                {"role": "user", "content": text[:4000]},
            ], max_tokens=max_length, temperature=0.3)

        # Heuristic: extract important sentences
        return self._heuristic_summarize(text, max_length)

    def generate_skill(self, pattern: Dict, existing_skills: List[Dict] = None) -> str:
        """
        Generate a skill definition from a pattern.

        Args:
            pattern: Pattern dict from pattern recognizer
            existing_skills: List of existing skill definitions

        Returns:
            Skill code as string
        """
        if self._available:
            existing_text = ""
            if existing_skills:
                existing_text = "\n\nExisting skills (avoid duplicating):\n"
                for s in existing_skills[:3]:
                    existing_text += f"- {s.get('name', 'unknown')}: triggers: {s.get('triggers', [])}\n"

            return self.chat([
                {"role": "system", "content": (
                    "You are an expert Python developer. Generate a complete skill module "
                    "for an AI agent memory system. The skill should detect trigger keywords "
                    "in user messages and provide helpful responses based on past interactions."
                )},
                {"role": "user", "content": (
                    f"Generate a Python skill module for this pattern:\n"
                    f"Pattern: {json.dumps(pattern, indent=2)[:1000]}\n"
                    f"{existing_text}"
                    f"\nReturn only the Python code for a learner module with:\n"
                    f"- should_activate(context) -> bool\n"
                    f"- execute(context) -> dict\n"
                    f"- get_metadata() -> dict"
                )},
            ], max_tokens=3000, temperature=0.5)

        # Heuristic: generate template-based skill
        return self._heuristic_skill(pattern)

    def reflect(self, session_messages: List[Dict]) -> Dict:
        """
        Perform self-reflection on a conversation session.

        Args:
            session_messages: List of {"role": ..., "content": ...}

        Returns:
            Reflection dict with analysis, improvements, memories
        """
        if self._available:
            conversation = "\n".join(
                f"{m['role']}: {m['content'][:300]}"
                for m in session_messages[:20]
            )

            response = self.chat([
                {"role": "system", "content": (
                    "You are a self-reflection engine for an AI assistant. "
                    "Analyze the conversation and return JSON with:\n"
                    "- outcome: 'success', 'failure', or 'neutral'\n"
                    "- what_went_well: list of things that worked\n"
                    "- what_to_improve: list of improvements\n"
                    "- facts_to_remember: list of important facts from the user\n"
                    "- knowledge_gaps: topics the assistant didn't know about"
                )},
                {"role": "user", "content": f"Reflect on this conversation:\n{conversation}"},
            ], max_tokens=1000, temperature=0.3)

            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"raw_reflection": response}

        # Heuristic fallback
        return self._heuristic_reflection(session_messages)

    def extract_facts(self, text: str) -> Dict[str, str]:
        """
        Extract important facts from text.

        Args:
            text: Text to analyze

        Returns:
            Dict of {fact_key: fact_value}
        """
        if self._available:
            response = self.chat([
                {"role": "system", "content": (
                    "Extract important facts about the user from this text. "
                    "Return JSON: {\"fact_key\": \"fact_value\"}. "
                    "Keys like: user_name, current_project, company, location, preferences."
                )},
                {"role": "user", "content": text[:2000]},
            ], max_tokens=500, temperature=0.2)

            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {}

        # Heuristic
        return self._heuristic_facts(text)

    def profile_user(self, messages: List[Dict]) -> Dict:
        """
        Analyze user communication style from messages.

        Args:
            messages: User messages

        Returns:
            Profile dict with formality, verbosity, topics, etc.
        """
        if self._available:
            user_texts = "\n".join(
                m.get("content", "")[:200]
                for m in messages
                if m.get("role") == "user"
            )[:3000]

            response = self.chat([
                {"role": "system", "content": (
                    "Analyze this user's communication style. Return JSON:\n"
                    "{\n"
                    '  "formality": 0.0-1.0,\n'
                    '  "verbosity": 0.0-1.0,\n'
                    '  "emoji_usage": 0.0-1.0,\n'
                    '  "preferred_response": "concise"|"detailed"|"structured",\n'
                    '  "topics_of_interest": ["topic1", "topic2"],\n'
                    '  "communication_tips": ["tip1", "tip2"]\n'
                    "}"
                )},
                {"role": "user", "content": f"Analyze this user's communication style:\n{user_texts}"},
            ], max_tokens=500, temperature=0.3)

            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {}

        return {}

    # ------------------------------------------------------------------
    # Heuristic Fallbacks (when no LLM is configured)
    # ------------------------------------------------------------------

    def _heuristic_response(self, messages: List[Dict]) -> str:
        """Generate response without LLM."""
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break

        if not last_user:
            return ""

        # Simple keyword matching
        lower = last_user.lower()
        if any(kw in lower for kw in ["hello", "hi ", "hey"]):
            return "Hello! How can I help you today?"
        if any(kw in lower for kw in ["thanks", "thank", "great", "perfect"]):
            return "You're welcome! Let me know if you need anything else."
        if any(kw in lower for kw in ["who are you", "what are you"]):
            return "I'm an AI assistant with persistent memory via OpenMem."

        return ""

    def _heuristic_summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize without LLM."""
        sentences = text.replace(". ", ".\n").split("\n")
        # Take first N sentences that fit max_length
        summary = []
        total = 0
        for s in sentences:
            s = s.strip()
            if len(s) > 10:
                summary.append(s)
                total += len(s)
                if total >= max_length:
                    break
        return ". ".join(summary)

    def _heuristic_skill(self, pattern: Dict) -> str:
        """Generate skill template without LLM."""
        keywords = pattern.get("high_freq_keywords", [])[:5]
        return f"""# Auto-generated skill (heuristic mode — configure LLM for full generation)

Triggers: {', '.join(keywords)}

def should_activate(context):
    msg = context.get("message", "").lower()
    return any(kw in msg for kw in {keywords})

def execute(context):
    return {{"response": f"Skill activated for: {{context.get('message', '')[:100]}}"}}
"""

    def _heuristic_reflection(self, messages: List[Dict]) -> Dict:
        """Reflect without LLM."""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if not user_msgs:
            return {"outcome": "neutral", "what_went_well": [], "what_to_improve": []}

        last = user_msgs[-1].get("content", "").lower()
        if any(kw in last for kw in ["thanks", "perfect", "great"]):
            outcome = "success"
        elif any(kw in last for kw in ["doesn't work", "wrong", "still"]):
            outcome = "failure"
        else:
            outcome = "neutral"

        return {
            "outcome": outcome,
            "what_went_well": ["Completed the interaction"],
            "what_to_improve": [],
            "facts_to_remember": [],
        }

    def _heuristic_facts(self, text: str) -> Dict[str, str]:
        """Extract facts without LLM."""
        import re
        facts = {}
        lower = text.lower()

        for pattern, key in [
            (r"my name is (\w+)", "user_name"),
            (r"i'm (\w+)", "user_name"),
            (r"i am (\w+)", "user_name"),
            (r"call me (\w+)", "user_name"),
            (r"working on (\w+)", "current_project"),
            (r"project (\w+)", "current_project"),
        ]:
            match = re.search(pattern, lower)
            if match:
                facts[key] = match.group(1)

        return facts

    def get_status(self) -> Dict:
        """Get LLM status."""
        return {
            "available": self._available,
            "provider": getattr(self, "_provider", "none"),
            "model": getattr(self, "_model", "none"),
            "fallback": "heuristic" if not self._available else "none",
        }


# Singleton
_llm_instance = None


def get_llm(config: Dict = None) -> OpenMemLLM:
    """Get or create LLM singleton."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = OpenMemLLM(config)
    return _llm_instance
