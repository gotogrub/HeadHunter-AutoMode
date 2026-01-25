"""
HeadHunter Destroyer - AI Assistant
Optional AI-powered cover letter generation using OpenAI or Ollama.
"""

import os
import json
import hashlib
from typing import Dict, Optional
from database import Database


class AIAssistant:
    """
    AI-powered assistant for generating personalized cover letters.
    Supports OpenAI API and local Ollama models.
    """

    def __init__(self, db: Database = None, provider: str = "auto"):
        """
        Initialize AI Assistant.

        Args:
            db: Database instance for caching
            provider: "openai", "ollama", "auto", or "disabled"
        """
        self.db = db
        self.provider = provider.lower()
        self.enabled = False
        self.client = None
        self.model = None

        self._ensure_cache_table()
        self._init_provider()

    def _ensure_cache_table(self):
        """Create cache table for generated letters."""
        if not self.db:
            return

        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,
                prompt TEXT,
                response TEXT,
                provider TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.conn.commit()

    def _init_provider(self):
        """Initialize AI provider based on configuration."""
        if self.provider == "disabled":
            self.enabled = False
            return

        # Try OpenAI first
        if self.provider in ("openai", "auto"):
            if self._init_openai():
                return

        # Try Ollama
        if self.provider in ("ollama", "auto"):
            if self._init_ollama():
                return

        self.enabled = False

    def _init_openai(self) -> bool:
        """Initialize OpenAI client."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return False

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
            self.provider = "openai"
            self.enabled = True
            print(f"[*] AI Assistant: OpenAI ({self.model})")
            return True
        except ImportError:
            print("[!] OpenAI library not installed. Run: pip install openai")
            return False
        except Exception as e:
            print(f"[!] OpenAI init failed: {e}")
            return False

    def _init_ollama(self) -> bool:
        """Initialize Ollama client."""
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama2")

        try:
            import requests
            # Check if Ollama is running
            response = requests.get(f"{ollama_host}/api/tags", timeout=2)
            if response.status_code == 200:
                self.client = {"host": ollama_host}
                self.model = ollama_model
                self.provider = "ollama"
                self.enabled = True
                print(f"[*] AI Assistant: Ollama ({self.model})")
                return True
        except Exception:
            pass

        return False

    def is_enabled(self) -> bool:
        """Check if AI assistant is enabled and working."""
        return self.enabled

    def generate_cover_letter(
        self,
        vacancy: Dict,
        resume_summary: str = None,
        style: str = "professional",
        max_sentences: int = 3
    ) -> Optional[str]:
        """
        Generate personalized cover letter using AI.

        Args:
            vacancy: Vacancy data (title, employer, description, requirements)
            resume_summary: Optional summary of user's resume
            style: Writing style (professional, casual, enthusiastic)
            max_sentences: Maximum sentences in the letter

        Returns:
            Generated cover letter or None if failed
        """
        if not self.enabled:
            return None

        # Build prompt
        prompt = self._build_prompt(vacancy, resume_summary, style, max_sentences)

        # Check cache first
        cache_key = self._get_cache_key(prompt)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Generate new response
        try:
            if self.provider == "openai":
                response = self._generate_openai(prompt)
            elif self.provider == "ollama":
                response = self._generate_ollama(prompt)
            else:
                return None

            if response:
                self._cache_response(cache_key, prompt, response)
                return response

        except Exception as e:
            print(f"[!] AI generation failed: {e}")

        return None

    def _build_prompt(
        self,
        vacancy: Dict,
        resume_summary: str,
        style: str,
        max_sentences: int
    ) -> str:
        """Build prompt for AI model."""
        style_instructions = {
            "professional": "Используй профессиональный деловой тон.",
            "casual": "Используй дружелюбный, но профессиональный тон.",
            "enthusiastic": "Покажи энтузиазм и заинтересованность в позиции.",
        }

        prompt = f"""Напиши короткое сопроводительное письмо для отклика на вакансию.

Вакансия: {vacancy.get('title', 'Не указано')}
Компания: {vacancy.get('employer', 'Не указано')}
"""

        if vacancy.get('description'):
            # Truncate long descriptions
            desc = vacancy['description'][:500]
            prompt += f"Описание: {desc}\n"

        if vacancy.get('requirements'):
            prompt += f"Требования: {vacancy['requirements'][:300]}\n"

        if resume_summary:
            prompt += f"\nМоё резюме (кратко): {resume_summary}\n"

        prompt += f"""
Требования к письму:
- Максимум {max_sentences} предложения
- {style_instructions.get(style, style_instructions['professional'])}
- На русском языке
- Без приветствия "Здравствуйте" в начале (оно добавится автоматически)
- Только текст письма, без подписи

Письмо:"""

        return prompt

    def _generate_openai(self, prompt: str) -> Optional[str]:
        """Generate using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник для написания сопроводительных писем при поиске работы. Пиши кратко и по делу."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    def _generate_ollama(self, prompt: str) -> Optional[str]:
        """Generate using Ollama API."""
        import requests

        response = requests.post(
            f"{self.client['host']}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 200
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()
        return None

    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[str]:
        """Get cached response."""
        if not self.db:
            return None

        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT response FROM ai_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _cache_response(self, cache_key: str, prompt: str, response: str):
        """Cache AI response."""
        if not self.db:
            return

        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO ai_cache (cache_key, prompt, response, provider, model)
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, prompt, response, self.provider, self.model))
        self.db.conn.commit()

    def analyze_vacancy_relevance(self, vacancy: Dict, skills: list) -> Optional[int]:
        """
        Analyze vacancy relevance to user's skills (0-100).

        Args:
            vacancy: Vacancy data
            skills: List of user's skills

        Returns:
            Relevance score 0-100 or None if AI unavailable
        """
        if not self.enabled:
            return None

        prompt = f"""Оцени релевантность вакансии для кандидата от 0 до 100.

Вакансия: {vacancy.get('title', '')}
Описание: {vacancy.get('description', '')[:300]}

Навыки кандидата: {', '.join(skills)}

Ответь только числом от 0 до 100:"""

        try:
            if self.provider == "openai":
                response = self._generate_openai(prompt)
            elif self.provider == "ollama":
                response = self._generate_ollama(prompt)
            else:
                return None

            # Extract number from response
            import re
            match = re.search(r'\d+', response or "")
            if match:
                score = int(match.group())
                return min(100, max(0, score))

        except Exception:
            pass

        return None

    def get_status(self) -> Dict:
        """Get AI assistant status."""
        return {
            "enabled": self.enabled,
            "provider": self.provider if self.enabled else None,
            "model": self.model if self.enabled else None,
        }


# Configuration from environment
AI_PROVIDER = os.environ.get("HH_AI_PROVIDER", "auto")  # openai, ollama, auto, disabled

# Global instance
_ai_assistant = None


def get_ai_assistant(db: Database = None) -> AIAssistant:
    """Get or create AI assistant instance."""
    global _ai_assistant
    if _ai_assistant is None:
        _ai_assistant = AIAssistant(db, provider=AI_PROVIDER)
    return _ai_assistant
