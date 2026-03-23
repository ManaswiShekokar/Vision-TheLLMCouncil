"""
LLM Council - Example Usage Script

This script demonstrates how to use the LLM Council programmatically.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.orchestrator import CouncilOrchestrator
from app.config import settings


async def run_example():
    """Run an example deliberation."""
    
    # Check for API key
    if not settings.openrouter_api_key:
        print("=" * 60)
        print("ERROR: OPENROUTER_API_KEY not set!")
        print()
        print("Please set your OpenRouter API key:")
        print("  1. Copy .env.example to .env")
        print("  2. Edit .env and add your API key")
        print("  3. Get a key from https://openrouter.ai/keys")
        print("=" * 60)
        return
    
    print("=" * 60)
    print("🏛️  LLM Council - Example Deliberation")
    print("=" * 60)
    print()
    
    # Create orchestrator
    orchestrator = CouncilOrchestrator()
    
    # Example query
    query = """
    What are the key considerations when designing a microservices architecture 
    for a large-scale e-commerce platform?
    """
    
    print(f"Query: {query.strip()}")
    print()
    print("Starting deliberation...")
    print("-" * 60)
    
    try:
        # Run full deliberation
        session = await orchestrator.run_full_deliberation(
            query=query,
            enable_peer_review=True,
            enable_verification=True,
            deliberation_rounds=1
        )
        
        # Print results
        print()
        print("=" * 60)
        print("📊 RESULTS")
        print("=" * 60)
        print()
        
        print("📚 INITIAL RESPONSES:")
        print("-" * 40)
        for role, response in session.initial_responses.items():
            print(f"\n{response.role_name} ({response.model_used}):")
            print(f"  {response.response[:300]}...")
        
        print()
        print("⚖️ WEIGHTED SCORES:")
        print("-" * 40)
        for role, score in session.weighted_scores.items():
            print(f"  {role}: {score:.2f}/10")
        
        if session.verification_report:
            print()
            print("✅ VERIFICATION REPORT:")
            print("-" * 40)
            print(f"  Reliability Score: {session.verification_report.overall_reliability_score}%")
            print(f"  Confidence: {session.verification_report.confidence_assessment}")
            print(f"  Hallucinations: {len(session.verification_report.hallucination_flags)}")
            print(f"  Factual Errors: {len(session.verification_report.factual_errors)}")
        
        if session.chairman_synthesis:
            print()
            print("=" * 60)
            print("👔 CHAIRMAN'S FINAL ANSWER")
            print("=" * 60)
            print()
            print(session.chairman_synthesis.final_answer)
            print()
            print("-" * 40)
            print(f"Consensus Score: {session.chairman_synthesis.consensus_score:.1f}%")
            print(f"Confidence Level: {session.chairman_synthesis.confidence_level}")
            print()
            
            if session.chairman_synthesis.key_points:
                print("Key Points:")
                for point in session.chairman_synthesis.key_points:
                    print(f"  • {point}")
        
        print()
        print("=" * 60)
        print(f"Processing Time: {session.processing_time_seconds:.2f} seconds")
        print(f"Total Tokens Used: {session.total_tokens_used}")
        print(f"Session ID: {session.session_id}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during deliberation: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    print()
    print("=" * 60)
    print("  LLM Council - Multi-LLM Collaborative Reasoning System")
    print("=" * 60)
    print()
    
    # Run example
    asyncio.run(run_example())


if __name__ == "__main__":
    main()
