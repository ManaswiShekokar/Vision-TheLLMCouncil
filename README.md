# 🏛️ LLM Council

A multi-LLM collaborative reasoning system that simulates an expert committee solving problems together through structured deliberation, peer review, and synthesis.

## Overview

LLM Council orchestrates multiple Large Language Models, each assigned a specific role, to generate higher-quality answers through:

- **Structured Deliberation**: Multi-stage process with clear workflow
- **Role-Based Reasoning**: Each LLM has a unique perspective
- **Anonymous Peer Review**: Unbiased evaluation of responses
- **Multi-Round Improvement**: Iterative refinement based on feedback
- **Weighted Consensus Scoring**: Merit-based influence on final answer
- **Verifier Validation**: Error and hallucination detection
- **Chairman Synthesis**: Authoritative final answer

## Council Roles

| Role | Description |
|------|-------------|
| 📚 **Researcher** | Provides factual explanations and background knowledge |
| 🔍 **Critic** | Identifies weaknesses, incorrect assumptions, or logical errors |
| 💡 **Creative Thinker** | Suggests innovative ideas or alternative viewpoints |
| 🛠️ **Practical Advisor** | Focuses on real-world implementation and actionable solutions |
| ✅ **Verifier** | Checks for hallucinations, logical inconsistencies, and factual errors |
| 👔 **Chairman** | Synthesizes all responses into the final comprehensive answer |

## Workflow

```
User Query
    ↓
Stage 1: Role-Based Responses (parallel)
    ↓
Stage 2: Anonymous Peer Review
    ↓
Stage 3: Multi-Round Improvement
    ↓
Stage 4: Weighted Consensus Scoring
    ↓
Stage 5: Verifier Validation
    ↓
Stage 6: Chairman Synthesis
    ↓
Final Answer + Consensus Score
```

## Installation

### 1. Clone or Download

```bash
cd LLMCouncil
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example config
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Edit .env and add your OpenRouter API key
```

### 5. Get OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/)
2. Create an account
3. Navigate to [API Keys](https://openrouter.ai/keys)
4. Create a new key and add it to your `.env` file

## Running the Application

### Start the Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Deliberation Page**: http://localhost:8000/deliberate

## API Usage

### Full Deliberation

```bash
curl -X POST http://localhost:8000/api/deliberate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the best practices for building scalable web applications?",
    "enable_peer_review": true,
    "enable_verification": true,
    "deliberation_rounds": 1
  }'
```

### Python Client Example

```python
import asyncio
from app.services.orchestrator import CouncilOrchestrator

async def main():
    orchestrator = CouncilOrchestrator()
    
    session = await orchestrator.run_full_deliberation(
        query="What is the future of artificial intelligence?",
        enable_peer_review=True,
        enable_verification=True,
        deliberation_rounds=1
    )
    
    print(f"Final Answer: {session.chairman_synthesis.final_answer}")
    print(f"Consensus Score: {session.chairman_synthesis.consensus_score}%")
    print(f"Confidence Level: {session.chairman_synthesis.confidence_level}")

asyncio.run(main())
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/deliberate` | POST | Run full deliberation |
| `/api/session/{id}` | GET | Get session data |
| `/api/session/{id}/trace` | GET | Get reasoning trace |
| `/api/config` | GET | Get configuration |
| `/api/roles` | GET | Get available roles |
| `/api/models` | GET | Get available models |
| `/api/health` | GET | Health check |

### Step-by-Step API

For more control, use individual stage endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/deliberate/start` | POST | Create new session |
| `/api/deliberate/{id}/initial-responses` | POST | Generate initial responses |
| `/api/deliberate/{id}/peer-review` | POST | Run peer review |
| `/api/deliberate/{id}/improve` | POST | Run improvement round |
| `/api/deliberate/{id}/verify` | POST | Run verification |
| `/api/deliberate/{id}/synthesize` | POST | Run chairman synthesis |

## Configuration

### Model Configuration

You can customize which models handle each role:

```python
model_config = {
    "researcher": "openai/gpt-4o",
    "critic": "anthropic/claude-3.5-sonnet",
    "creative_thinker": "meta-llama/llama-3.1-70b-instruct",
    "practical_advisor": "mistralai/mistral-large",
    "verifier": "anthropic/claude-3.5-sonnet",
    "chairman": "openai/gpt-4o"
}
```

### Scoring Weights

Default scoring weights for peer review:

```python
scoring_weights = {
    "accuracy": 0.30,      # 30%
    "clarity": 0.20,       # 20%
    "completeness": 0.25,  # 25%
    "reasoning": 0.25      # 25%
}
```

## Project Structure

```
LLMCouncil/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── README.md              # This file
│
├── app/
│   ├── __init__.py
│   ├── config.py          # Settings and role definitions
│   ├── models.py          # Pydantic data models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py     # OpenRouter API integration
│   │   ├── scoring_service.py # Weighted scoring calculations
│   │   └── orchestrator.py    # Council deliberation coordinator
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py         # REST API endpoints
│   │   └── pages.py       # HTML page routes
│   │
│   ├── templates/
│   │   ├── base.html      # Base template
│   │   ├── index.html     # Home page
│   │   ├── deliberate.html# Main deliberation interface
│   │   ├── session.html   # Session details page
│   │   └── about.html     # About page
│   │
│   └── static/
│       ├── css/
│       │   └── style.css  # Stylesheet
│       └── js/
│           ├── main.js    # Common JavaScript
│           └── deliberate.js  # Deliberation page logic
│
└── example.py             # Example usage script
```

## Features

- ✅ Multi-LLM collaboration
- ✅ Role-based reasoning system
- ✅ Anonymous peer review
- ✅ Multi-round deliberation
- ✅ Weighted scoring system
- ✅ Verifier error detection layer
- ✅ Chairman synthesis
- ✅ Transparency and reasoning trace
- ✅ Side-by-side comparison of responses
- ✅ Modular system to add new models
- ✅ Web interface with real-time updates
- ✅ REST API for programmatic access

## Future Enhancements

- [ ] RAG support for memory/context
- [ ] Custom role definitions
- [ ] Response caching
- [ ] Session persistence
- [ ] User authentication
- [ ] Rate limiting
- [ ] Streaming responses
- [ ] Export to PDF/Markdown


