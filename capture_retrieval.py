import asyncio
import sys
import os
import json

# Add app to path
sys.path.append(os.getcwd())

from app.services.rag_service import RAGService

async def capture_retrieval_data():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    question = "How many points do hunt seat riders need to qualify for regionals?"
    print(f"\nProcessing Question: {question}\n")
    
    # 1. Intent Routing
    print("[1/4] Routing Intent...")
    routing = await rag._route_intent(question)
    print(f"      Intent: {routing.get('intent')}, Expand Neighbors: {routing.get('must_expand_neighbors')}")
    
    # 2. Query Expansion
    print("[2/4] Expanding Queries...")
    queries = await rag._expand_queries(question)
    
    all_results = []
    seen_chunks = set()
    
    # 3. Vector Search
    print("[3/4] Performing Vector Search...")
    for q in queries:
        results = rag.vector_store.search(q, top_k=5)
        for r in results:
            chunk_key = f"{r.metadata.get('doc_id')}_{r.metadata.get('page')}_{r.metadata.get('chunk_index')}"
            if chunk_key not in seen_chunks:
                all_results.append(r)
                seen_chunks.add(chunk_key)
                
    # 4. Keyword Scan
    print("[4/4] Performing Keyword Scan...")
    stop_words = {"what", "how", "many", "points", "do", "need", "to", "for"}
    keywords = [w for w in question.lower().split() if len(w) > 3 and w not in stop_words]
    keyword_results = rag.vector_store.keyword_scan(keywords, limit=5)
    for r in keyword_results:
        chunk_key = f"{r.metadata.get('doc_id')}_{r.metadata.get('page')}_{r.metadata.get('chunk_index')}"
        if chunk_key not in seen_chunks:
            r.score = 0.95 # Typical score boost for keyword matches
            all_results.append(r)
            seen_chunks.add(chunk_key)

    # Sort and take top 10
    final_list = sorted(all_results, key=lambda x: x.score, reverse=True)[:10]

    print("\n" + "="*80)
    print("TOP 10 RETRIEVED CHUNKS")
    print("="*80)
    
    output_data = []
    for i, res in enumerate(final_list):
        chunk_info = {
            "index": i + 1,
            "id": f"p{res.metadata.get('page')}_c{res.metadata.get('chunk_index')}",
            "score": round(res.score, 3),
            "page": res.metadata.get('page'),
            "section": res.metadata.get('section_id'),
            "snippet": res.text[:250].replace('\n', ' ') + "..."
        }
        output_data.append(chunk_info)
        
        print(f"ID: {chunk_info['id']} | Score: {chunk_info['score']} | Sec: {chunk_info['section']} | Page: {chunk_info['page']}")
        print(f"Snippet: {chunk_info['snippet']}")
        print("-" * 50)

    # Save to a file for the user to download/inspect
    with open("retrieval_logs.json", "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved {len(output_data)} chunks to retrieval_logs.json")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(capture_retrieval_data())
