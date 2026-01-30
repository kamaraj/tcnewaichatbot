import asyncio
import sys
import os
import json

# Add app to path
sys.path.append(os.getcwd())

from app.services.rag_service import RAGService

async def test_retrieval():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    questions = [
        "How many points do hunt seat riders need to qualify for regionals?",
        "How many alternates are required?",
        "Are medications allowed for the horses?",
        "Does the Regional President have to be a member of the USHJA?"
    ]
    
    for q in questions:
        print(f"\n\nQuestion: {q}")
        print("-" * 40)
        
        # 1. Test Routing
        print("Routing...")
        routing = await rag._route_intent(q)
        print(f"Intent: {routing}")
        
        # 2. Test Expansion
        print("Expanding queries...")
        queries = await rag._expand_queries(q)
        print(f"Queries: {queries}")
        
        # 3. Test Retrieval
        print("Searching...")
        all_results = []
        seen = set()
        for i, query in enumerate(queries):
            results = rag.vector_store.search(query, top_k=3)
            print(f"  Query {i+1} ('{query}'): Found {len(results)} results")
            for r in results:
                key = f"{r.metadata.get('doc_id')}_{r.metadata.get('chunk_index')}"
                if key not in seen:
                    print(f"    - [Score {r.score:.3f}] Sec: {r.metadata.get('section_id')} Page: {r.metadata.get('page')}")
                    print(f"      Preview: {r.text[:100]}...")
                    all_results.append(r)
                    seen.add(key)
        
        # 4. Keyword Scan
        keywords = [w for w in q.lower().split() if len(w) > 3]
        print(f"Keyword Scan: {keywords}")
        k_results = rag.vector_store.keyword_scan(keywords, limit=3)
        for r in k_results:
             key = f"{r.metadata.get('doc_id')}_{r.metadata.get('chunk_index')}"
             if key not in seen:
                print(f"    - [Keywd Match] Sec: {r.metadata.get('section_id')} Page: {r.metadata.get('page')}")
                seen.add(key)
                all_results.append(r)

        # 5. Evidence Extraction
        print("Extracting Evidence...")
        evidence = await rag._extract_evidence(q, all_results)
        print(f"Evidence: {json.dumps(evidence, indent=2)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_retrieval())
