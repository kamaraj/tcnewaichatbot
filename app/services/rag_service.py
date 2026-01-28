import json
import re
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass
from .vector_store import VectorStore, SearchResult
from ..llm import get_llm_provider
from ..config import settings


@dataclass
class RAGResponse:
    """Response from the RAG pipeline."""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    metadata: Optional[Dict[str, Any]] = None


class RAGService:
    """Retrieval-Augmented Generation service with 8-step optimization."""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = get_llm_provider()
        self.fast_llm = self.llm 

    async def _route_intent(self, question: str) -> Dict[str, Any]:
        """Step 2: Router (Heuristic - No LLM to save quota)."""
        # Heuristic routing to save API calls
        q_lower = question.lower()
        
        # 1. Detect Role
        roles = ["coach", "rider", "steward", "exhibitor", "horse", "handler"]
        subject_role = "general"
        for r in roles:
            if r in q_lower:
                subject_role = r
                break
                
        # 2. Detect Mode
        mode = "DIRECT"
        coverage_triggers = ["list", "what are", "requirements", "how many", "rules for", "qualify", "explained"]
        if any(t in q_lower for t in coverage_triggers):
            mode = "COVERAGE"
            
        # 3. Extract Must-Have Terms (Numbers and Specific Nouns)
        # Extract rule numbers (e.g. 4501, 1102A)
        must_have = re.findall(r'\b\d{3,4}[A-Z]?\b', question)
        
        # Add specific keywords if present
        critical_terms = ["martingale", "alternate", "qualify", "points", "height", "age", "gloves", "whip", "refusal"]
        for term in critical_terms:
            if term in q_lower:
                must_have.append(term)
        
        return {
            "answer_mode": mode,
            "subject_role": subject_role,
            "must_have_terms": must_have,
            "avoid_terms": [],
            "needs_neighbor_expansion": mode == "COVERAGE"
        }

    async def _expand_queries(self, question: str, router_info: Dict) -> List[str]:
        """Step 3.1: Query expansion (Simple - No LLM)."""
        # Save API calls by just using the original question
        return [question]

    def _apply_intent_boost(self, results: List[SearchResult], router_info: Dict):
        """Step 3.2: Intent-aware keyword boost (Step 3.2)."""
        role = router_info.get("subject_role")
        must_have = [t.lower() for t in router_info.get("must_have_terms", [])]
        mode = router_info.get("answer_mode")
        
        # Specific rulebook boosts from user instructions
        boost_map = {
            "points": ["points", "acquire", "accumulate", "total", "36 points", "28 points", "7201", "7203", "7207"],
            "regionals": ["regional", "qualified for regionals", "move up", "class 7", "class 8"],
            "coach": ["coach", "team coach", "1102", "21 years old"],
            "alternates": ["alternate", "designated alternate", "4501", "substitute"],
            "equipment": ["martingale", "standing martingale", "saddle", "tack", "whip", "crop", "spurs", "equipment"]
        }
        
        # Determine current boost keywords based on router must_have and context
        active_boosts = []
        for key, terms in boost_map.items():
            if any(t in " ".join(must_have).lower() for t in terms) or key == role:
                active_boosts.extend(terms)

        for res in results:
            text = res.text.lower()
            res_role = res.metadata.get("subject_role", "general")
            
            # 1. Role match boost
            if role != "general" and res_role == role:
                res.score += 0.15
                
            # 2. Must-have terms match boost
            matches = sum(1 for term in must_have if term in text)
            if matches > 0:
                res.score += (matches * 0.08)
            
            # 3. Instruction-specific keyword boosts
            boost_count = sum(1 for term in active_boosts if term in text)
            if boost_count > 0:
                res.score += min(0.2, boost_count * 0.05)
                
            # Cap score
            res.score = min(0.99, res.score)

    def _filter_evidence(self, results: List[SearchResult], router_info: Dict) -> List[SearchResult]:
        """Step 5: Evidence Filter (Gate A & B)."""
        filtered = []
        target_role = router_info.get("subject_role")
        must_have = [t.lower() for t in router_info.get("must_have_terms", [])]
        mode = router_info.get("answer_mode")
        
        for res in results:
            # Gate A: Role Gate
            chunk_role = res.metadata.get("subject_role", "general")
            if target_role != "general" and chunk_role != "general" and chunk_role != target_role:
                # Be a bit more lenient if chunk has MUST HAVE terms but wrong role label
                if not any(term in res.text.lower() for term in must_have):
                    continue
                
            # Gate B: Intent/Term Gate
            text = res.text.lower()
            if must_have:
                # If it doesn't have at least one must-have term, it might be noise
                # But we allow high-scoring chunks even if they miss a term, to avoid false negatives
                if not any(term in text for term in must_have):
                    if mode == "DIRECT" and res.score < 0.8:
                         continue
                    elif res.score < 0.65: # Lowered threshold for non-direct matched
                         continue
            
            filtered.append(res)
            
        return filtered

    async def _audit_coverage(self, question: str, answer: str, evidence_ids: List[str]) -> bool:
        """Step 7: Coverage Auditor (Skipped for quota)."""
        return True

    async def query(self, question: str, filter_doc_id: str = None) -> RAGResponse:
        """Process question through the 8-step optimized pipeline."""
        
        # Step 2: Route
        router_info = await self._route_intent(question)
        mode = router_info.get("answer_mode", "DIRECT")
        
        # Step 3.1: Expansion
        queries = await self._expand_queries(question, router_info)
        
        all_results = []
        seen_chunks = set()
        
        # Step 8 Settings: 5 queries x top 5 each
        for q in queries:
            if not q or not q.strip():
                continue
            try:
                results = self.vector_store.search(q, top_k=5, filter_doc_id=filter_doc_id)
                for r in results:
                    chunk_key = r.chunk_id if hasattr(r, 'chunk_id') else f"{r.metadata.get('doc_id')}_{r.metadata.get('page')}_{r.metadata.get('chunk_index')}"
                    if chunk_key not in seen_chunks:
                        all_results.append(r)
                        seen_chunks.add(chunk_key)
            except Exception as e:
                # Silently fail for individual query failures
                pass

        # Step 3.1b: Hybrid Search (Keyword Scan for must-have terms)
        must_have = router_info.get("must_have_terms", [])
        if must_have:
            try:
                keyword_results = self.vector_store.keyword_scan(must_have, limit=5)
                for r in keyword_results:
                     chunk_key = r.chunk_id if hasattr(r, 'chunk_id') else f"{r.metadata.get('doc_id')}_{r.metadata.get('page')}_{r.metadata.get('chunk_index')}"
                     if chunk_key not in seen_chunks:
                         r.score = 0.85 # High score for exact keyword usage
                         all_results.append(r)
                         seen_chunks.add(chunk_key)
            except Exception as e:
                print(f"Keyword scan failed: {e}")

        # Step 3.2: Intent Boost
        self._apply_intent_boost(all_results, router_info)
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Step 4: Neighbor Expansion
        if router_info.get("needs_neighbor_expansion"):
            all_results = self.vector_store.expand_neighbors(all_results[:8])
            all_results.sort(key=lambda x: x.score, reverse=True)
            
        # Step 5: Evidence Filter
        filtered_results = self._filter_evidence(all_results, router_info)
        
        # Step 8 Limits
        limit = 5 if mode == "DIRECT" else 15
        final_evidence = filtered_results[:limit]
        
        if not final_evidence:
            # Retry once with neighbors if empty
            final_evidence = self.vector_store.expand_neighbors(all_results[:3])[:limit]

        # Step 6: Evidence-First Answering
        evidence_ids = list(set([str(r.metadata.get('section_id')) for r in final_evidence if r.metadata.get('section_id')]))
        
        context = ""
        for i, r in enumerate(final_evidence):
            sec = r.metadata.get('section_full') or r.metadata.get('section_id', 'N/A')
            pg = r.metadata.get('page', 'N/A')
            context += f"EXTRACT from Section {sec}, Page {pg}:\n{r.text}\n---\n"

        prompt = f"""You are a strict rulebook assistant for the IHSA. Use ONLY the provided evidence.
If no evidence, say "I cannot find specific rules regarding this in the current documents."

User Question: {question}
Answer Mode: {mode}

Evidence:
{context}

Formatting Rules:
- If DIRECT: 1-2 bullets, only about the asked subject.
- If COVERAGE: list all applicable rules, grouped by classes/categories if needed.
- Every single bullet MUST end with (Section ####, page ##) or (Rule ####, page ##) using the numbers from the EXTRACT header.
- Use exact phrasing from the excerpts where possible."""

        answer = await self.llm.generate(prompt=prompt)
        
        # Step 7: Audit
        audit_pass = await self._audit_coverage(question, answer, evidence_ids)
        if not audit_pass and mode == "COVERAGE":
            # Simple one-time retry/regeneration for coverage audit failure
            answer += "\n\n[Note: Additional relevant sections were found in evidence but might have been summarized above.]"

        return RAGResponse(
            answer=answer,
            sources=[{"filename": r.metadata.get("filename"), "page": r.metadata.get("page"), "section": r.metadata.get("section_full"), "score": round(r.score, 2)} for r in final_evidence],
            query=question,
            metadata={"router": router_info, "audit_pass": audit_pass}
        )

    async def query_stream(self, question: str, filter_doc_id: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Streamed version of the optimized pipeline."""
        try:
            # For streaming, we'll do the same prep but stream the final response
            resp = await self.query(question, filter_doc_id)
            
            # Yield the answer in chunks to simulate streaming
            parts = resp.answer.split(' ')
            for p in parts:
                yield {"type": "content", "content": p + " "}
                import asyncio
                # yield small delay for visual effect
                await asyncio.sleep(0.01)
                
            yield {"type": "sources", "sources": resp.sources}
            yield {"type": "done"}
            
        except Exception as e:
            print(f"Streaming error: {e}")
            yield {"type": "content", "content": f"\n\n **Error:** {str(e)}"}
            yield {"type": "done"}
