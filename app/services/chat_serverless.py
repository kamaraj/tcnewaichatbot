"""
Lightweight Chat Service for Vercel Serverless.
Uses OpenAI API directly instead of LangChain for reduced package size.
"""
import time
import json
import re
import os
import httpx
from typing import List, Dict, Any

# Import settings
from app.config import settings


# ========== QUERY EXPANSION ==========
QUERY_EXPANSIONS = {
    "coach": ["coach", "coaching", "coaches", "instructor", "trainer", "personnel", "staff"],
    "age": ["age", "years old", "minimum age", "21", "adult", "teenager"],
    "points": ["points", "point", "score", "36", "28", "21"],
    "qualify": ["qualify", "qualified", "qualification", "eligibility"],
    "regionals": ["regionals", "regional", "finals", "zones", "nationals"],
    "medications": ["medications", "medication", "drugs", "therapeutic", "CNS"],
    "alternates": ["alternates", "alternate", "substitution", "substitute"],
    "prizelists": ["prizelists", "prize list", "prize-list", "rules"],
}


def expand_query(query: str) -> str:
    """Expand the query with synonyms and related terms."""
    query_lower = query.lower()
    expanded_terms = set()
    
    # Detect coach age queries
    has_coach_terms = any(x in query_lower for x in ["coach", "staff", "personnel"])
    has_age_terms = any(x in query_lower for x in ["age", "old", "21", "minimum", "years"])
    
    if has_coach_terms and has_age_terms:
        expanded_terms.update(["coach", "age", "21 years old", "Rule 1102.A", "minimum age"])
    
    # Add original query terms
    words = re.findall(r'\b\w+\b', query_lower)
    for word in words:
        expanded_terms.add(word)
        if word in QUERY_EXPANSIONS:
            expanded_terms.update(QUERY_EXPANSIONS[word])
    
    return query + " " + " ".join(expanded_terms)


def rerank_by_keywords(docs: list, query: str) -> list:
    """Re-rank documents by keyword relevance."""
    query_lower = query.lower()
    
    priority_keywords = {"high": [], "medium": []}
    
    has_coach_terms = any(x in query_lower for x in ["coach", "staff", "personnel"])
    has_age_terms = any(x in query_lower for x in ["age", "old", "21", "minimum", "years"])
    
    if has_coach_terms and has_age_terms:
        priority_keywords["high"] = ["1102", "21 years", "minimum age"]
        priority_keywords["medium"] = ["coach", "age", "years old"]
    elif "points" in query_lower or "qualify" in query_lower:
        priority_keywords["high"] = ["36 points", "28 points", "7201", "7203"]
        priority_keywords["medium"] = ["points", "qualify", "regionals"]
    else:
        priority_keywords["medium"] = query_lower.split()[:5]
    
    def score_doc(doc):
        content = doc.page_content.lower()
        score = 0
        for kw in priority_keywords["high"]:
            if kw in content:
                score += 100
        for kw in priority_keywords["medium"]:
            if kw in content:
                score += 10
        return score
    
    scored_docs = [(doc, score_doc(doc)) for doc in docs]
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored_docs]


SYSTEM_PROMPT = """You are an IHSA OFFICIAL RULEBOOK ANSWER REPRODUCER.

Your ONLY goal is to reproduce accurate answers from the IHSA Rulebook based on the provided context.

RULES:
1. Include ALL clauses from applicable rules
2. Preserve NEGATIVE language exactly ("NOT allowed", "may NOT", etc.)
3. Match rule reference format: "Rule 1102.A", "HU 109, 1a."
4. Do NOT add interpretations or summaries beyond the rulebook content
5. If the context doesn't contain relevant information, say: "I cannot find a specific rule addressing this in the current rulebook context."

EXAMPLES:
Question: Is there a minimum age requirement for coaches?
Answer: Yes. According to Rule 1102.A, all IHSA coaches must be at least 21 years old.

Question: How many alternates are required?
Answer: There must be at least one designated alternate. Rule 4501.

QUESTION: {input}

CONTEXT FROM RULEBOOK:
{context}

Answer:"""


async def generate_answer_serverless(query: str, db=None):
    """Generate answer using OpenAI API directly (no LangChain)."""
    start_total = time.time()
    
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")
    
    # Import the serverless vector store
    from app.services.vector import get_vector_store
    vector_store = get_vector_store()
    
    # Query expansion
    expanded_query = expand_query(query)
    print(f"📝 Original query: {query}")
    print(f"🔍 Expanded query: {expanded_query[:100]}...")
    
    # Retrieval
    start_retrieval = time.time()
    all_docs = vector_store.similarity_search(expanded_query, k=10)
    reranked_docs = rerank_by_keywords(all_docs, query)
    top_docs = reranked_docs[:5]
    retrieval_time = (time.time() - start_retrieval) * 1000
    
    # Build context
    context_text = "\n\n---\n\n".join([
        f"[Source: {doc.metadata.get('filename', 'unknown')}] {doc.page_content}" 
        for doc in top_docs
    ])
    
    # Generate answer using OpenAI API directly
    start_generation = time.time()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT.replace("{input}", query).replace("{context}", context_text)
                    },
                    {
                        "role": "user", 
                        "content": query
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }
        )
        response.raise_for_status()
        result = response.json()
    
    answer = result["choices"][0]["message"]["content"]
    
    generation_time = (time.time() - start_generation) * 1000
    total_time = (time.time() - start_total) * 1000
    
    # Clean up answer
    if answer.strip().startswith("Answer:"):
        answer = answer.strip()[7:].strip()
    
    # Extract sources
    sources = []
    context_snippets = []
    for doc in top_docs:
        filename = doc.metadata.get("filename", "unknown")
        page = doc.metadata.get("page", "N/A")
        sources.append({"filename": filename, "page": page})
        context_snippets.append({
            "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
            "source": filename,
            "page": page
        })
    
    unique_sources = list(set([s["filename"] for s in sources]))
    confidence = "high" if len(top_docs) >= 5 else "medium" if len(top_docs) >= 2 else "low"
    
    if "cannot find" in answer.lower() or "don't know" in answer.lower():
        confidence = "low"
    
    # Log query if db session provided
    if db:
        try:
            from app.models.db import QueryLog
            query_log = QueryLog(
                query_text=query,
                response_text=answer,
                retrieval_time_ms=round(retrieval_time, 2),
                generation_time_ms=round(generation_time, 2),
                total_time_ms=round(total_time, 2),
                num_chunks_retrieved=len(top_docs),
                sources_used=json.dumps(unique_sources)
            )
            db.add(query_log)
            db.commit()
        except Exception as e:
            print(f"Error logging query: {e}")
    
    return {
        "answer": answer,
        "confidence": confidence,
        "context_snippets": context_snippets,
        "sources": unique_sources,
        "metrics": {
            "retrieval_time_ms": round(retrieval_time, 2),
            "generation_time_ms": round(generation_time, 2),
            "total_time_ms": round(total_time, 2),
            "chunks_retrieved": len(top_docs)
        }
    }
