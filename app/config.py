"""
Configuration settings for LLM Council application.
"""

import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    app_name: str = "Vision : The LLM Council"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # OpenRouter API settings (default key, can be overridden per role)
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Per-role API keys (optional - falls back to openrouter_api_key if not set)
    # Set these in .env as: RESEARCHER_API_KEY=sk-xxx, CRITIC_API_KEY=sk-yyy, etc.
    researcher_api_key: str = Field(default="", env="RESEARCHER_API_KEY")
    critic_api_key: str = Field(default="", env="CRITIC_API_KEY")
    creative_thinker_api_key: str = Field(default="", env="CREATIVE_THINKER_API_KEY")
    practical_advisor_api_key: str = Field(default="", env="PRACTICAL_ADVISOR_API_KEY")
    verifier_api_key: str = Field(default="", env="VERIFIER_API_KEY")
    chairman_api_key: str = Field(default="", env="CHAIRMAN_API_KEY")
    
    # Default models for different roles
    # Using user-selected models with better observed availability.
    default_models: Dict[str, str] = {
        "researcher": "liquid/lfm-2.5-1.2b-instruct:free",
        "critic": "arcee-ai/trinity-mini:free",
        "creative_thinker": "arcee-ai/trinity-large-preview:free",
        "practical_advisor": "nvidia/nemotron-3-nano-30b-a3b:free",
        "verifier": "stepfun/step-3.5-flash:free",
        "chairman": "nvidia/nemotron-nano-9b-v2:free"
    }
    
    # Scoring weights
    scoring_weights: Dict[str, float] = {
        "accuracy": 0.30,
        "clarity": 0.20,
        "completeness": 0.25,
        "reasoning": 0.25
    }
    
    # Deliberation settings (balanced for free tier)
    max_deliberation_rounds: int = 1  # One improvement round
    enable_peer_review: bool = True  # Core feature - peer review
    enable_verification: bool = True  # Verifier validation
    
    # API settings (conservative for free tier)
    request_timeout: int = 45
    max_concurrent_requests: int = 1
    request_delay_seconds: float = 12.0  # Slightly higher delay to reduce 429s on free endpoints
    
    class Config:
        env_file = ".env"
        extra = "allow"


# Global settings instance
settings = Settings()


# Role definitions with descriptions
ROLE_DEFINITIONS = {
    "researcher": {
        "name": "Researcher",
        "description": "Provides factual explanations and background knowledge. Focuses on accuracy and depth of information.",
        "system_prompt": """You are the Researcher in an expert council. Your role is to:
- Provide detailed factual explanations and background knowledge
- Cite relevant concepts, theories, and established facts
- Offer comprehensive coverage of the topic
- Focus on accuracy and educational value
- Structure your response clearly with relevant context

Respond thoughtfully and thoroughly, ensuring your answer is well-researched and informative."""
    },
    "critic": {
        "name": "Critic",
        "description": "Identifies weaknesses, incorrect assumptions, or logical errors. Challenges assumptions constructively.",
        "system_prompt": """You are the Critic in an expert council. Your role is to:
- Identify weaknesses, gaps, or incorrect assumptions
- Point out logical errors or inconsistencies
- Challenge claims that lack evidence
- Suggest areas that need more consideration
- Provide constructive criticism that improves the discussion

Be thorough but fair in your analysis. Focus on improving the quality of the answer."""
    },
    "creative_thinker": {
        "name": "Creative Thinker",
        "description": "Suggests innovative ideas or alternative viewpoints. Thinks outside the box.",
        "system_prompt": """You are the Creative Thinker in an expert council. Your role is to:
- Suggest innovative ideas and alternative viewpoints
- Think outside conventional boundaries
- Propose creative solutions or approaches
- Make unexpected connections between concepts
- Challenge traditional thinking with fresh perspectives

Be imaginative and bold in your suggestions while keeping them relevant to the query."""
    },
    "practical_advisor": {
        "name": "Practical Advisor",
        "description": "Focuses on real-world implementation and actionable solutions. Provides concrete steps.",
        "system_prompt": """You are the Practical Advisor in an expert council. Your role is to:
- Focus on real-world implementation
- Provide actionable, concrete solutions
- Consider practical constraints and resources
- Suggest step-by-step approaches
- Address feasibility and practicality concerns

Keep your advice grounded and implementable in real-world scenarios."""
    },
    "verifier": {
        "name": "Verifier",
        "description": "Checks for hallucinations, logical inconsistencies, and factual errors. Ensures reliability.",
        "system_prompt": """You are the Verifier in an expert council. Your role is to:
- Check responses for hallucinations and fabricated information
- Identify logical inconsistencies and contradictions
- Verify factual accuracy of claims
- Flag uncertain or unverified statements
- Assess the reliability of the overall response

Produce a detailed validation report highlighting any issues found."""
    },
    "chairman": {
        "name": "Chairman",
        "description": "Synthesizes all responses into the final answer. Creates consensus and comprehensive summary.",
        "system_prompt": """You are the Chairman of an expert council. Your role is to:
- Synthesize all perspectives into a comprehensive final answer
- Weigh different viewpoints based on their merit and scores
- Create a balanced, well-structured response
- Highlight areas of consensus and note significant disagreements
- Produce a clear, actionable conclusion

Your synthesis should be authoritative while acknowledging the contributions of all council members."""
    }
}


# Available models on OpenRouter
AVAILABLE_MODELS = [
    # FREE MODELS (user-selected)
    {"id": "liquid/lfm-2.5-1.2b-instruct:free", "name": "Liquid LFM 2.5 1.2B (FREE)", "provider": "Liquid"},
    {"id": "arcee-ai/trinity-mini:free", "name": "Arcee Trinity Mini (FREE)", "provider": "Arcee"},
    {"id": "arcee-ai/trinity-large-preview:free", "name": "Arcee Trinity Large (FREE)", "provider": "Arcee"},
    {"id": "nvidia/nemotron-3-nano-30b-a3b:free", "name": "Nvidia Nemotron 3 Nano (FREE)", "provider": "Nvidia"},
    {"id": "stepfun/step-3.5-flash:free", "name": "StepFun Step 3.5 Flash (FREE)", "provider": "StepFun"},
    {"id": "nvidia/nemotron-nano-9b-v2:free", "name": "Nvidia Nemotron Nano 9B (FREE)", "provider": "Nvidia"},
]
