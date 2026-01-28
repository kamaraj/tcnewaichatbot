import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.services.rag_service import RAGService

async def evaluate_preview():
    print("Initializing RAG...")
    rag = RAGService()
    
    questions = [
        "How long do you have to catch in liberty?",
        "How can you be disqualified from in hand obstacle?"
    ]
    
    for q in questions:
        print(f"\nQuestion: {q}")
        response = await rag.query(q)
        print(f"Answer: {response.answer}")
        print("Sources:")
        for s in response.sources:
            print(f" - {s['filename']} (Page {s['page']}, Section {s['section_id']}) Score: {s['relevance_score']}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(evaluate_preview())
