import asyncio
import sys
import os
import json

# Add app to path
sys.path.append(os.getcwd())

from app.services.rag_service import RAGService

async def test_optimized_rag():
    print("Initializing Optimized RAG Service...")
    rag = RAGService()
    
    question = "How many points do hunt seat riders need to qualify for regionals?"
    print(f"\nProcessing Question: {question}\n")
    
    response = await rag.query(question)
    
    print("\n" + "="*80)
    print("OPTIMIZED RAG ANSWER")
    print("="*80)
    print(response.answer)
    print("\n" + "="*80)
    print("METADATA & SOURCES")
    print("="*80)
    print(f"Intent Mode: {response.metadata.get('router', {}).get('answer_mode')}")
    print(f"Subject Role: {response.metadata.get('router', {}).get('subject_role')}")
    print(f"Audit Pass: {response.metadata.get('audit_pass')}")
    print("\nSources used:")
    for s in response.sources:
        print(f"- Section {s['section']} (Page {s['page']}) [Relevance: {s['score']}]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_optimized_rag())
