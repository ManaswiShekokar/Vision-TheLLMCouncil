"""
OpenRouter API integration service.
Handles all LLM API calls through OpenRouter.
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..config import settings, ROLE_DEFINITIONS

logger = logging.getLogger(__name__)


class OpenRouterService:
    """Service for interacting with OpenRouter API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.default_api_key = api_key or settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.timeout = settings.request_timeout
        
        # Per-role API keys mapping
        self.role_api_keys = {
            "researcher": settings.researcher_api_key or self.default_api_key,
            "critic": settings.critic_api_key or self.default_api_key,
            "creative_thinker": settings.creative_thinker_api_key or self.default_api_key,
            "practical_advisor": settings.practical_advisor_api_key or self.default_api_key,
            "verifier": settings.verifier_api_key or self.default_api_key,
            "chairman": settings.chairman_api_key or self.default_api_key,
        }
        
        # Log which keys are configured (showing last 4 chars only)
        logger.info("API Keys configured:")
        for role, key in self.role_api_keys.items():
            key_suffix = key[-4:] if key else "NONE"
            logger.info(f"  {role}: ...{key_suffix}")
        
    def _get_api_key_for_role(self, role: Optional[str] = None) -> str:
        """Get the API key for a specific role."""
        if role and role in self.role_api_keys:
            key = self.role_api_keys[role]
            logger.debug(f"Using key ...{key[-4:]} for role {role}")
            return key
        return self.default_api_key
        
    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests."""
        key = api_key or self.default_api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://llmcouncil.app",
            "X-Title": "LLM Council"
        }

    def _get_fallback_models(self, model: str) -> List[str]:
        """Return fallback candidates from the user-preferred stable free set."""
        candidates = [
            "arcee-ai/trinity-mini:free",
            "arcee-ai/trinity-large-preview:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "stepfun/step-3.5-flash:free",
            "liquid/lfm-2.5-1.2b-instruct:free",
            "nvidia/nemotron-nano-9b-v2:free",
        ]
        return [m for m in candidates if m != model]
    
    async def generate_response(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_retries: int = 1,
        role: Optional[str] = None,
        allow_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a response from a specific model.

        Args:
            prompt: The user prompt
            model: The model identifier
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_retries: Maximum retries for rate limiting
            role: Optional role name to use role-specific API key

        Returns:
            Dict containing the response and metadata
        """
        # Get the appropriate API key for this role
        api_key = self._get_api_key_for_role(role)
        
        messages = []
        if system_prompt:
            # Some Gemma endpoints reject system/developer instructions on OpenRouter.
            if "gemma" in model.lower():
                prompt = f"{system_prompt}\n\n---\n\n{prompt}"
            else:
                messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    # Log which key we're using
                    key_suffix = api_key[-4:] if api_key else "NONE"
                    logger.info(f"API call for role={role}, model={model}, key=...{key_suffix}")
                    
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(api_key),
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Defensive parsing: some provider errors may return 200 without choices.
                    choices = data.get("choices")
                    if not choices or not isinstance(choices, list):
                        err = data.get("error", {}) if isinstance(data, dict) else {}
                        err_code = err.get("code") if isinstance(err, dict) else None
                        # Retry transient upstream/provider failures wrapped in 200 payloads.
                        if err_code in (429, 502, 503, 504) and attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 3
                            logger.warning(
                                f"Transient provider error {err_code} on {model}, waiting {wait_time}s "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                        # One fallback pass for transient provider errors.
                        if err_code in (429, 502, 503, 504) and allow_fallback:
                            for fallback_model in self._get_fallback_models(model):
                                try:
                                    logger.warning(
                                        f"Provider error {err_code} on {model}; trying fallback {fallback_model}"
                                    )
                                    return await self.generate_response(
                                        prompt=prompt,
                                        model=fallback_model,
                                        system_prompt=system_prompt,
                                        temperature=temperature,
                                        max_tokens=max_tokens,
                                        max_retries=1,
                                        role=role,
                                        allow_fallback=False,
                                    )
                                except Exception:
                                    pass

                        logger.error(f"Unexpected response format from {model}: {str(data)[:500]}")
                        return {
                            "success": False,
                            "error": "Invalid response format: missing choices",
                            "model": model,
                            "content": "Error: Provider response missing choices"
                        }

                    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
                    content = message.get("content", "") if isinstance(message, dict) else ""
                    
                    return {
                        "success": True,
                        "content": content or "",
                        "model": model,
                        "usage": data.get("usage", {}),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                except httpx.HTTPStatusError as e:
                    error_body = e.response.text[:500] if e.response else "no body"
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        # Keep retries short to avoid browser/proxy timeout on long requests.
                        wait_time = (attempt + 1) * 3
                        logger.warning(f"Rate limited on {model}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue

                    if e.response.status_code == 429 and allow_fallback:
                        # One quick fallback pass before giving up.
                        for fallback_model in self._get_fallback_models(model):
                            if fallback_model == model:
                                continue
                            try:
                                logger.warning(f"429 on {model}; trying fallback {fallback_model}")
                                return await self.generate_response(
                                    prompt=prompt,
                                    model=fallback_model,
                                    system_prompt=system_prompt,
                                    temperature=temperature,
                                    max_tokens=max_tokens,
                                    max_retries=1,
                                    role=role,
                                    allow_fallback=False,
                                )
                            except Exception:
                                pass

                    logger.error(f"HTTP {e.response.status_code} calling {model}: {error_body}")
                    return {
                        "success": False,
                        "error": str(e),
                        "model": model,
                        "content": f"Error: HTTP {e.response.status_code}"
                    }
                except httpx.TimeoutException as e:
                    logger.warning(f"Timeout calling {model}: {e}")
                    if allow_fallback:
                        for fallback_model in self._get_fallback_models(model):
                            try:
                                logger.warning(f"Timeout on {model}; trying fallback {fallback_model}")
                                return await self.generate_response(
                                    prompt=prompt,
                                    model=fallback_model,
                                    system_prompt=system_prompt,
                                    temperature=temperature,
                                    max_tokens=max_tokens,
                                    max_retries=1,
                                    role=role,
                                    allow_fallback=False,
                                )
                            except Exception:
                                pass
                    return {
                        "success": False,
                        "error": "Timeout",
                        "model": model,
                        "content": "Error: Request timed out"
                    }
                except Exception as e:
                    logger.error(f"Error calling {model}: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "model": model,
                        "content": f"Error: {str(e)}"
                    }
        
        # Max retries exceeded
        return {
            "success": False,
            "error": "Max retries exceeded",
            "model": model,
            "content": "Error: Rate limit exceeded after retries"
        }
    
    async def generate_role_response(
        self,
        query: str,
        role: str,
        model: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from a specific role.
        
        Args:
            query: The user's query
            role: The role identifier
            model: Optional model override
            additional_context: Additional context to include
            
        Returns:
            Dict containing the role response
        """
        role_config = ROLE_DEFINITIONS.get(role)
        if not role_config:
            return {
                "success": False,
                "error": f"Unknown role: {role}",
                "content": ""
            }
        
        model = model or settings.default_models.get(role, "openai/gpt-4o")
        system_prompt = role_config["system_prompt"]
        
        full_prompt = query
        if additional_context:
            full_prompt = f"{additional_context}\n\n---\n\nUser Query: {query}"
        
        response = await self.generate_response(
            prompt=full_prompt,
            model=model,
            system_prompt=system_prompt,
            role=role  # Pass role to use role-specific API key
        )

        response["role"] = role
        response["role_name"] = role_config["name"]
        
        return response
    
    async def generate_parallel_responses(
        self,
        query: str,
        roles: List[str],
        model_config: Optional[Dict[str, str]] = None,
        additional_context: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate responses from multiple roles SEQUENTIALLY with delays.
        
        Args:
            query: The user's query
            roles: List of role identifiers
            model_config: Optional model configuration for roles
            additional_context: Additional context for all roles
            
        Returns:
            Dict mapping role to response
        """
        model_config = model_config or {}
        results = {}
        
        # Run SEQUENTIALLY with delays to avoid rate limits
        for i, role in enumerate(roles):
            if i > 0:
                # Wait between requests
                delay = getattr(settings, 'request_delay_seconds', 5.0)
                logger.info(f"Waiting {delay}s before next request...")
                await asyncio.sleep(delay)
            
            model = model_config.get(role)
            try:
                result = await self.generate_role_response(
                    query=query,
                    role=role,
                    model=model,
                    additional_context=additional_context
                )
                results[role] = result
            except Exception as e:
                results[role] = {
                    "success": False,
                    "error": str(e),
                    "content": f"Error: {str(e)}",
                    "role": role
                }
        
        return results
    
    async def generate_peer_review(
        self,
        reviewer_role: str,
        target_role: str,
        target_response: str,
        original_query: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a peer review from one role reviewing another's response.
        
        Args:
            reviewer_role: The reviewing role
            target_role: The role being reviewed
            target_response: The response being reviewed
            original_query: The original user query
            model: Optional model override
            
        Returns:
            Dict containing review scores and feedback
        """
        model = model or settings.default_models.get(reviewer_role, "openai/gpt-4o")
        
        system_prompt = f"""You are an expert reviewer evaluating a response. 
Your task is to provide a detailed evaluation with numerical scores.

Score each criterion from 0-10:
- Accuracy: How factually correct is the response?
- Clarity: How clear and understandable is the response?
- Completeness: How thoroughly does it address the query?
- Reasoning: How sound is the logical reasoning?

Provide your evaluation in the following exact format:
ACCURACY_SCORE: [0-10]
CLARITY_SCORE: [0-10]
COMPLETENESS_SCORE: [0-10]
REASONING_SCORE: [0-10]
FEEDBACK: [Your detailed feedback]"""

        prompt = f"""Original Query: {original_query}

Response to Review (from an anonymous council member):
{target_response}

Please evaluate this response according to the criteria provided."""

        response = await self.generate_response(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.3,
            role=reviewer_role  # Use reviewer's API key
        )
        
        # Parse the scores from the response
        scores = self._parse_review_scores(response.get("content", ""))
        response["parsed_scores"] = scores
        response["reviewer_role"] = reviewer_role
        response["target_role"] = target_role
        
        return response
    
    def _parse_review_scores(self, content: str) -> Dict[str, Any]:
        """Parse review scores from LLM response."""
        content = content or ""
        scores = {
            "accuracy": 5.0,
            "clarity": 5.0,
            "completeness": 5.0,
            "reasoning": 5.0,
            "feedback": ""
        }
        
        lines = content.split("\n")
        feedback_lines = []
        in_feedback = False
        
        for line in lines:
            line = line.strip()
            
            if "ACCURACY_SCORE:" in line.upper():
                try:
                    scores["accuracy"] = float(line.split(":")[-1].strip().split()[0])
                except:
                    pass
            elif "CLARITY_SCORE:" in line.upper():
                try:
                    scores["clarity"] = float(line.split(":")[-1].strip().split()[0])
                except:
                    pass
            elif "COMPLETENESS_SCORE:" in line.upper():
                try:
                    scores["completeness"] = float(line.split(":")[-1].strip().split()[0])
                except:
                    pass
            elif "REASONING_SCORE:" in line.upper():
                try:
                    scores["reasoning"] = float(line.split(":")[-1].strip().split()[0])
                except:
                    pass
            elif "FEEDBACK:" in line.upper():
                in_feedback = True
                feedback_start = line.split(":", 1)[-1].strip()
                if feedback_start:
                    feedback_lines.append(feedback_start)
            elif in_feedback:
                feedback_lines.append(line)
        
        scores["feedback"] = " ".join(feedback_lines).strip()
        
        return scores
    
    async def generate_improvement(
        self,
        original_response: str,
        role: str,
        peer_feedback: List[Dict[str, Any]],
        other_responses: Dict[str, str],
        original_query: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an improved response based on peer feedback.
        
        Args:
            original_response: The role's original response
            role: The role improving their response
            peer_feedback: Feedback received from peers
            other_responses: Responses from other roles
            original_query: The original user query
            model: Optional model override
            
        Returns:
            Dict containing the improved response
        """
        role_config = ROLE_DEFINITIONS.get(role)
        model = model or settings.default_models.get(role, "openai/gpt-4o")
        
        # Format peer feedback
        feedback_text = "\n".join([
            f"- {fb.get('feedback', 'No feedback')}"
            for fb in peer_feedback
        ])
        
        # Format other responses
        other_responses_text = "\n\n".join([
            f"**{ROLE_DEFINITIONS.get(r, {}).get('name', r)}**: {resp[:500]}..."
            for r, resp in other_responses.items()
            if r != role
        ])
        
        system_prompt = f"""{role_config['system_prompt']}

You are now in the improvement round. You have received feedback from peer reviewers and have seen other council members' perspectives. Your task is to improve your original response based on this input.

Consider:
1. The feedback you received
2. Valid points from other council members
3. Any gaps or errors in your original response

Provide an improved response that addresses these points while maintaining your role's perspective."""

        prompt = f"""Original Query: {original_query}

Your Original Response:
{original_response}

Peer Feedback Received:
{feedback_text}

Other Council Members' Perspectives:
{other_responses_text}

---

Please provide your improved response, addressing the feedback and incorporating relevant insights from other perspectives."""

        response = await self.generate_response(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            role=role  # Use role's API key
        )
        
        response["role"] = role
        response["original_response"] = original_response
        
        return response
    
    async def generate_verification(
        self,
        responses: Dict[str, str],
        original_query: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a verification report checking for errors and hallucinations.
        
        Args:
            responses: All role responses to verify
            original_query: The original user query
            model: Optional model override
            
        Returns:
            Dict containing the verification report
        """
        model = model or settings.default_models.get("verifier", "anthropic/claude-3.5-sonnet")
        
        system_prompt = """You are an expert fact-checker and verification specialist. Your task is to analyze responses for:

1. Hallucinations: Information that appears fabricated or unsupported
2. Factual Errors: Statements that contradict established facts
3. Logical Inconsistencies: Arguments that contain logical flaws
4. Contradictions: Statements that conflict with each other

Provide your analysis in the following exact format:
HALLUCINATION_FLAGS: [List any hallucinations, or "None found"]
FACTUAL_ERRORS: [List any factual errors, or "None found"]
LOGICAL_INCONSISTENCIES: [List any logical issues, or "None found"]
RELIABILITY_SCORE: [0-100]
CONFIDENCE_ASSESSMENT: [Low/Medium/High] - [Brief explanation]
RECOMMENDATIONS: [List recommendations for improvement]"""

        responses_text = "\n\n".join([
            f"**{ROLE_DEFINITIONS.get(role, {}).get('name', role)}**:\n{response}"
            for role, response in responses.items()
        ])

        prompt = f"""Original Query: {original_query}

Responses to Verify:
{responses_text}

---

Please analyze these responses for hallucinations, factual errors, and logical inconsistencies."""

        response = await self.generate_response(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.2,
            role="verifier"  # Use verifier's API key
        )
        
        response["verification"] = self._parse_verification(response.get("content", ""))
        
        return response
    
    def _parse_verification(self, content: str) -> Dict[str, Any]:
        """Parse verification report from LLM response."""
        content = content or ""
        report = {
            "hallucination_flags": [],
            "factual_errors": [],
            "logical_inconsistencies": [],
            "reliability_score": 70.0,
            "confidence_assessment": "Medium",
            "recommendations": []
        }
        
        # Map section names to report keys
        section_keys = {
            "hallucinations": "hallucination_flags",
            "errors": "factual_errors",
            "inconsistencies": "logical_inconsistencies",
            "recommendations": "recommendations",
        }
        
        lines = content.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            upper_line = line.upper()
            
            if "HALLUCINATION_FLAGS:" in upper_line:
                current_section = "hallucinations"
                items = line.split(":", 1)[-1].strip()
                if items and "none" not in items.lower():
                    report["hallucination_flags"].extend([i.strip() for i in items.split(",") if i.strip()])
            elif "FACTUAL_ERRORS:" in upper_line:
                current_section = "errors"
                items = line.split(":", 1)[-1].strip()
                if items and "none" not in items.lower():
                    report["factual_errors"].extend([i.strip() for i in items.split(",") if i.strip()])
            elif "LOGICAL_INCONSISTENCIES:" in upper_line:
                current_section = "inconsistencies"
                items = line.split(":", 1)[-1].strip()
                if items and "none" not in items.lower():
                    report["logical_inconsistencies"].extend([i.strip() for i in items.split(",") if i.strip()])
            elif "RELIABILITY_SCORE:" in upper_line:
                current_section = None
                try:
                    score = line.split(":")[-1].strip().split()[0].replace("%", "")
                    report["reliability_score"] = float(score)
                except:
                    pass
            elif "CONFIDENCE_ASSESSMENT:" in upper_line:
                current_section = None
                assessment = line.split(":", 1)[-1].strip()
                report["confidence_assessment"] = assessment
            elif "RECOMMENDATIONS:" in upper_line:
                current_section = "recommendations"
                items = line.split(":", 1)[-1].strip()
                if items and "none" not in items.lower():
                    report["recommendations"].append(items)
            elif current_section and current_section in section_keys:
                # Handle multi-line items: lines starting with -, *, or numbered (1., 2., etc.)
                item = None
                if line.startswith("-") or line.startswith("*"):
                    item = line[1:].strip()
                elif len(line) > 2 and line[0].isdigit() and (line[1] == '.' or (line[1].isdigit() and line[2] == '.')):
                    # Strip leading number and dot (e.g., "1. item" or "12. item")
                    item = line.split(".", 1)[-1].strip()
                elif line and "none" not in line.lower():
                    item = line
                
                if item and "none" not in item.lower():
                    report[section_keys[current_section]].append(item)
        
        return report
    
    async def generate_synthesis(
        self,
        responses: Dict[str, str],
        peer_reviews: List[Dict[str, Any]],
        weighted_scores: Dict[str, float],
        verification_report: Dict[str, Any],
        original_query: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate the final chairman synthesis.
        
        Args:
            responses: All role responses (improved if available)
            peer_reviews: Peer review data
            weighted_scores: Weighted scores for each role
            verification_report: The verifier's report
            original_query: The original user query
            model: Optional model override
            
        Returns:
            Dict containing the chairman's synthesis
        """
        model = model or settings.default_models.get("chairman", "openai/gpt-4o")
        
        system_prompt = """You are the Chairman of an expert council. Your task is to synthesize all perspectives into a comprehensive final answer.

You must provide your synthesis in the following exact format:

FINAL_ANSWER:
[Your comprehensive, synthesized answer here]

CONSENSUS_SCORE: [0-100 - indicating level of agreement among council members]

CONFIDENCE_LEVEL: [Low/Medium/High]

KEY_POINTS:
- [Key point 1]
- [Key point 2]
- [Key point 3]

AREAS_OF_AGREEMENT:
- [Point of agreement 1]
- [Point of agreement 2]

AREAS_OF_DISAGREEMENT:
- [Point of disagreement 1]
- [Point of disagreement 2]

SYNTHESIS_METHODOLOGY:
[Brief explanation of how you weighted and combined the perspectives]"""

        # Format responses with scores
        scored_responses = "\n\n".join([
            f"**{ROLE_DEFINITIONS.get(role, {}).get('name', role)}** (Score: {weighted_scores.get(role, 0):.1f}):\n{response}"
            for role, response in responses.items()
            if role not in ["verifier", "chairman"]
        ])
        
        # Format verification summary
        ver = verification_report.get("verification", {})
        verification_summary = f"""
Reliability Score: {ver.get('reliability_score', 70)}%
Confidence: {ver.get('confidence_assessment', 'Medium')}
Issues Found: {len(ver.get('hallucination_flags', [])) + len(ver.get('factual_errors', []))}
"""

        prompt = f"""Original Query: {original_query}

Council Responses (with weighted scores):
{scored_responses}

Verification Summary:
{verification_summary}

---

Please synthesize these perspectives into a comprehensive final answer."""

        response = await self.generate_response(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=3000,
            role="chairman"  # Use chairman's API key
        )
        
        response["synthesis"] = self._parse_synthesis(response.get("content", ""))
        
        return response
    
    def _parse_synthesis(self, content: str) -> Dict[str, Any]:
        """Parse chairman synthesis from LLM response."""
        content = content or ""
        synthesis = {
            "final_answer": "",
            "consensus_score": 75.0,
            "confidence_level": "Medium",
            "key_points": [],
            "areas_of_agreement": [],
            "areas_of_disagreement": [],
            "synthesis_methodology": ""
        }
        
        lines = content.split("\n")
        current_section = None
        final_answer_lines = []

        section_headers = [
            "CONSENSUS_SCORE:",
            "CONFIDENCE_LEVEL:",
            "KEY_POINTS:",
            "AREAS_OF_AGREEMENT:",
            "AREAS_OF_DISAGREEMENT:",
            "SYNTHESIS_METHODOLOGY:",
        ]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            upper_line = stripped.upper()
            
            if "FINAL_ANSWER:" in upper_line:
                current_section = "final_answer"
                continue
            elif "CONSENSUS_SCORE:" in upper_line:
                current_section = None
                try:
                    score = stripped.split(":")[-1].strip().split()[0].replace("%", "")
                    synthesis["consensus_score"] = float(score)
                except:
                    pass
            elif "CONFIDENCE_LEVEL:" in upper_line:
                current_section = None
                level = stripped.split(":")[-1].strip()
                synthesis["confidence_level"] = level
            elif "KEY_POINTS:" in upper_line:
                current_section = "key_points"
            elif "AREAS_OF_AGREEMENT:" in upper_line:
                current_section = "agreement"
            elif "AREAS_OF_DISAGREEMENT:" in upper_line:
                current_section = "disagreement"
            elif "SYNTHESIS_METHODOLOGY:" in upper_line:
                current_section = "methodology"
                continue
            elif current_section == "final_answer" and stripped:
                if any(h in upper_line for h in section_headers):
                    current_section = None
                else:
                    final_answer_lines.append(stripped)
            elif current_section == "key_points" and stripped.startswith("-"):
                synthesis["key_points"].append(stripped[1:].strip())
            elif current_section == "agreement" and stripped.startswith("-"):
                synthesis["areas_of_agreement"].append(stripped[1:].strip())
            elif current_section == "disagreement" and stripped.startswith("-"):
                synthesis["areas_of_disagreement"].append(stripped[1:].strip())
            elif current_section == "methodology" and stripped:
                synthesis["synthesis_methodology"] += stripped + " "
        
        synthesis["final_answer"] = "\n".join(final_answer_lines).strip()
        synthesis["synthesis_methodology"] = synthesis["synthesis_methodology"].strip()

        # If FINAL_ANSWER tag is missing, fall back to text before first known section header.
        if not synthesis["final_answer"]:
            preamble = []
            for line in lines:
                stripped = line.strip()
                upper_line = stripped.upper()
                if any(h in upper_line for h in section_headers):
                    break
                if upper_line.startswith("FINAL_ANSWER:"):
                    continue
                if stripped:
                    preamble.append(stripped)

            synthesis["final_answer"] = "\n".join(preamble).strip()

        # Last resort: keep content, but remove structured section lines.
        if not synthesis["final_answer"]:
            filtered = []
            for line in lines:
                upper_line = line.strip().upper()
                if any(h in upper_line for h in section_headers):
                    continue
                filtered.append(line)
            synthesis["final_answer"] = "\n".join(filtered).strip() or content
        
        return synthesis


# Global service instance
openrouter_service = OpenRouterService()
