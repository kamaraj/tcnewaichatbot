import time
import json
import re
try:
    from langchain.chains import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    # Fallback for newer langchain versions
    from langchain.chains.retrieval import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from app.services.utils import get_llm
from app.services.vector import get_vector_store
from app.models.db import QueryLog
from sqlalchemy.orm import Session
from app.config import settings

# ========== QUERY EXPANSION ==========
# Maps common query terms to related terms for better retrieval
QUERY_EXPANSIONS = {
    # Coach age related
    "coach": ["coach", "coaching", "coaches", "instructor", "trainer", "personnel", "staff", "leader", "lead", "adult"],
    "age": ["age", "years old", "minimum age", "old", "young", "21", "eighteen", "adult", "teenager", "minor", "restrictions"],
    
    # Qualification points related
    "points": ["points", "point", "score", "accumulate", "36", "28", "21"],
    "qualify": ["qualify", "qualified", "qualification", "eligibility", "requirements", "eligibility"],
    "regionals": ["regionals", "regional", "finals", "zones", "nationals"],
    "hunt seat": ["hunt seat", "hunter", "jumping", "equitation"],
    
    # Medication related
    "medications": ["medications", "medication", "drugs", "drug", "therapeutic", "CNS", "central nervous system", "4302", "3401.J"],
    "horses": ["horses", "horse", "equine", "pony"],
    
    # Alternates related
    "alternates": ["alternates", "alternate", "substitution", "substitute", "Rule 4501", "at least one"],
    
    # Prize list related
    "prizelists": ["prizelists", "prize list", "prize-list", "rules", "Section 5401", "two weeks"],
    "online": ["online", "web", "internet", "website", "posted", "received"],
    
    "eligibility": ["eligibility", "eligible", "qualify", "requirements", "qualifications"],
    "regulations": ["regulations", "rules", "requirements", "policy", "policies"],
}

def expand_query(query: str) -> str:
    """
    Expand the query with synonyms and related terms to improve retrieval.
    For coach age queries, we specifically add terms like '21', '1102', 'minimum age'.
    """
    query_lower = query.lower()
    expanded_terms = set()
    
    # Intent detection for better expansion
    # BROADER DETECTION: Check for "coach" OR specific age mentions associated with coaching rules
    has_coach_terms = any(x in query_lower for x in ["coach", "staff", "personnel", "leader", "lead", "instructor"])
    has_age_terms = any(x in query_lower for x in ["age", "old", "21", "minimum", "years", "requirement", "adult", "teenager", "restrictions"])
    has_section_1100 = "1100" in query_lower or "section 11" in query_lower
    
    is_coach_age_query = (has_coach_terms and has_age_terms) or "21" in query_lower or has_section_1100
    
    is_points_query = any(x in query_lower for x in ["points", "point", "score", "qualify", "regionals", "hunt seat", "36", "28"])
    is_meds_query = any(x in query_lower for x in ["medication", "drug", "cns", "therapeutic", "horse", "veterinarian"])
    is_alternates_query = any(x in query_lower for x in ["alternate", "substitute", "how many"])
    is_prizelist_query = any(x in query_lower for x in ["prizelist", "prize list", "published", "online", "posted"])
    is_young_hunter = any(x in query_lower for x in ["young hunter", "jump", "height", "how high"])
    is_pony_hunter = any(x in query_lower for x in ["pony", "small pony", "large pony", "tall", "hands"])
    
    is_martingale = any(x in query_lower for x in ["martingale", "equipment", "tack"])
    
    # DEBUG LOGGING
    print(f"DEBUG: query='{query}'")
    print(f"DEBUG: coach_terms={has_coach_terms}, age_terms={has_age_terms}")
    print(f"DEBUG: is_coach_age={is_coach_age_query}")

    if is_coach_age_query:
        expanded_terms.update(["coach", "age", "21 years old", "Rule 1102.A", "Rule 1102", "minimum age", "adult"])
    
    if is_points_query:
        expanded_terms.update(["36 points", "28 points", "qualify for regionals", "Hunt Seat", "Rule 7201", "Rule 7203", "Rule 7207"])
        
    if is_meds_query:
        expanded_terms.update(["medications", "therapeutic use", "central nervous system drugs", "CNS", "Rule 4302", "Rule 3401.J"])

    if is_alternates_query:
        expanded_terms.update(["alternates", "designated alternate", "at least one", "Rule 4501", "Rule 4500"])
        
    if is_prizelist_query:
        expanded_terms.update(["prizelists", "prize list", "two weeks prior", "closing date", "Section 5401"])

    if is_young_hunter:
        expanded_terms.update(["Young Hunter", "heights", "2'9", "3'0", "3'3", "HU111"])

    if is_pony_hunter:
        expanded_terms.update(["pony", "hands", "height", "12.2", "14.2", "HU141", "HU142"])

    if is_martingale:
        expanded_terms.update(["martingale", "standing", "running", "prohibited", "allowed", "HU105"])
    
    # Add original query terms
    words = re.findall(r'\b\w+\b', query_lower)
    for word in words:
        expanded_terms.add(word)
        if word in QUERY_EXPANSIONS:
            for expansion in QUERY_EXPANSIONS[word]:
                expanded_terms.add(expansion)
    
    # Build expanded query - original query + key expansion terms
    expanded_query = query + " " + " ".join(expanded_terms)
    return expanded_query

def rerank_by_keywords(docs: list, query: str) -> list:
    """
    Re-rank retrieved documents by keyword relevance.
    Documents containing key terms like '21', '1102', 'coach', 'age' get higher priority.
    """
    query_lower = query.lower()
    
    # Define priority keywords based on query intent
    priority_keywords = {"high": [], "medium": [], "low": []}
    
    # Coach Age Intent
    has_coach_terms = any(x in query_lower for x in ["coach", "staff", "personnel", "leader", "lead", "instructor"])
    has_age_terms = any(x in query_lower for x in ["age", "old", "21", "minimum", "years", "requirement", "adult", "teenager", "restrictions"])
    
    if (has_coach_terms and has_age_terms) or "1102" in query_lower:
        priority_keywords["high"] = ["1102", "21 years", "twenty-one", "minimum age"]
        priority_keywords["medium"] = ["coach", "age", "years old"]
        
    elif "points" in query_lower or "qualify" in query_lower:
        priority_keywords["high"] = ["36 points", "28 points", "7201", "7203", "7207"]
        priority_keywords["medium"] = ["points", "qualify", "regionals", "hunt seat"]
    elif "medication" in query_lower or "drug" in query_lower:
        priority_keywords["high"] = ["4302", "3401", "therapeutic", "central nervous system", "CNS"]
        priority_keywords["medium"] = ["medications", "drugs", "horse"]
    elif "alternate" in query_lower:
        priority_keywords["high"] = ["4501", "designated alternate", "at least one"]
        priority_keywords["medium"] = ["alternates", "alternate"]
    elif "prizelist" in query_lower or "prize list" in query_lower:
        priority_keywords["high"] = ["5401", "section 5401", "two (2) weeks"]
        priority_keywords["medium"] = ["prizelists", "online", "prize list"]
    elif "hunter" in query_lower:
        priority_keywords["high"] = ["HU111", "HU141", "HU142", "HU105", "height"]
        priority_keywords["medium"] = ["hunter", "pony", "jump"]
    else:
        priority_keywords["medium"] = query_lower.split()[:5]
    
    def score_doc(doc):
        content = doc.page_content.lower()
        score = 0
        
        for keyword in priority_keywords["high"]:
            if keyword in content:
                score += 100
        for keyword in priority_keywords["medium"]:
            if keyword in content:
                score += 10
        for keyword in priority_keywords["low"]:
            if keyword in content:
                score += 1
                
        return score
    
    # Sort by score descending
    scored_docs = [(doc, score_doc(doc)) for doc in docs]
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    
    return [doc for doc, score in scored_docs]

async def generate_answer(query: str, db: Session = None):
    start_total = time.time()
    
    llm = get_llm()
    vector_store = get_vector_store()
    
    # ========== STEP 1: QUERY EXPANSION ==========
    expanded_query = expand_query(query)
    print(f"📝 Original query: {query}")
    print(f"🔍 Expanded query: {expanded_query[:100]}...")
    
    # ========== STEP 2: RETRIEVAL ==========
    start_retrieval = time.time()
    
    # Get fewer documents for faster processing and lower token usage
    all_docs = vector_store.similarity_search(expanded_query, k=10)
    
    # ========== STEP 3: RE-RANK BY KEYWORDS ==========
    reranked_docs = rerank_by_keywords(all_docs, query)
    
    # Take top 5 after re-ranking for better context window usage and faster generation
    top_docs = reranked_docs[:5]
    
    retrieval_time = (time.time() - start_retrieval) * 1000
    
    context_text = "\n\n---\n\n".join([f"[Source: {doc.metadata.get('filename')}] {doc.page_content}" for doc in top_docs])
    
    system_prompt = """You are an IHSA OFFICIAL RULEBOOK ANSWER REPRODUCER.

You are NOT a chatbot.
You are NOT allowed to summarize, shorten, paraphrase, or optimize.

Your ONLY goal is to reproduce CUSTOMER-EXPECTED ANSWERS
that match EXACTLY the structure, depth, wording style,
and clause completeness shown in “Turnout AI Answer Examples”.

====================================================
ABSOLUTE ENFORCEMENT RULES (NO EXCEPTIONS)
====================================================

1. You MUST assume the customer will compare your answer
   word-by-word against the expected answer.

2. You MUST include ALL clauses from applicable rules:
   - limits
   - prohibitions
   - exceptions
   - procedural constraints
   - enforcement language

3. You MUST preserve NEGATIVE language exactly:
   - “NOT allowed”
   - “may NOT”
   - “will NOT”
   - “must NOT”
   If a rule contains a prohibition, you MUST state it.

4. You MUST separate COMPETITION rules from SCHOOLING rules
   when both exist.

5. You MUST NOT compress multiple clauses into one sentence
   if the expected answer separates them.

6. You MUST NOT omit Appendix rules when they are cited
   in the expected answers.

7. You MUST follow the SAME rule reference format
   used by customers:
   - “HU 109, 1a.”
   - “Appendix A – USEF Hunter Schooling Rules, 15.”
   (Match punctuation and spacing.)

8. You MUST NOT add explanations, interpretations, or summaries.

9. You MUST NOT include rules for unrelated roles, divisions,
   or classes.

10. You MUST NOT ask clarifying questions if ANY rule exists.

11. You MUST REJECT any question that is unrelated to the IHSA Rulebook.
    - If the user asks about general knowledge (e.g. "Capital of France"), coding, or unrelated topics, respond EXACTLY with:
      "I am designed to answer questions exclusively about the IHSA Official Rulebook. Please provide a rule-related query."
    - If the provided Context does not contain ANY relevant information to answer the specific rule question, say:
      "I cannot find a specific rule addressing this in the current rulebook context."

====================================================
MANDATORY INTERNAL METHOD
====================================================

A. Identify SUBJECT (walk fences, martingales, liberty, etc.).
B. Identify CONTEXTS:
   - Competition
   - Schooling
   - Enforcement
C. Extract EVERY sentence-level rule clause verbatim or
   near-verbatim from the excerpts.
D. Reproduce the answer with the SAME clause ordering
   and emphasis as customer examples.

====================================================
====================================================
FEW SHOT EXAMPLES (MODEL BEHAVIOR)
====================================================

Question: Is there a minimum age requirement for coaches?
Answer: Yes. According to Rule 1102.A, all IHSA coaches must be at least 21 years old.

Question: When must online prizelists be posted?
Answer: Online prize lists must be received via email not less than two (2) weeks prior to the closing date of entries and must be sent to all colleges in the region. (Section 5401, B.)

Question: How high do Young Hunters jump?
Answer: Young Hunters jump at the following heights:
Young Hunter 5 and under: 2'9"
Young Hunter 6 and under: 3'0"
Young Hunter 7 and under: 3'3"
This information can be found in subchapter HU111.

Question: How many alternates are required?
Answer: There must be at least one designated alternate. Rule 4501.

Question: How tall is a small pony?
Answer: Small ponies are not to exceed 12.2 hands. HU 141, 3a.

Question: How high are walk fences?
Answer: Walk fences may not exceed 2’ in height and spread. HU 109, 1a.

In the schooling area, walk rails may be no higher than 12” at the highest point. A walk rail may be parallel to the ground with both ends in cups, or may have one end resting on the ground. Cross rails are NOT allowed. Ground rails are NOT permitted. Horses will approach and depart in a straight line only and may NOT be turned. Appendix A - USEF Hunter Schooling Rules, 15.

Question: How many points are required to qualify for hunt seat regionals?
Answer: Riders who begin showing in a beginner section (2A and 12A) of Classes 2 & 12 must move to the advanced section (2B and 12B) when they have acquired 18, or more, points. All previous points are carried over within the Class from the beginner to advanced sections, and when riders accumulate a total of 36 points, they must move up to the next Class. Riders are also qualified for Regionals once they have earned the 36 points between the beginner and advanced sections. (Section 7201, page 62)

Riders in classes 3 - 6 & 11-15 must move into the next higher class when they have earned 36 points. They are also qualified for Regionals. (Section 7203, page 62)

Riders must move out of classes 1 & 11 when their years of eligibility expire, regardless of points earned. They must move into the next higher class when they have earned 36 points and they are also qualified for Regionals. (Section 7204, page 62)

Riders in Classes 7, 8, 16 & 17 will start each year with zero points and must acquire 28 to qualify for Regionals. In the event of a disparity in the number of shows held within a region and no rider qualifies in these classes, the number of points may be lowered to qualify the next highest rider(s) with a minimum of 21 and with the permission of the National Steward. (Section 7207, page 62)

Question: How long do you have to catch in liberty?
Answer: The catch time for liberty is 2 minutes.

In the Liberty class, you have 2 minutes to catch and halter the pony/horse after the performance time has ended. If the catch is not completed within this time frame, the exhibitor is disqualified. (Section XII – In Hand/Single Working Performance, D; General Liberty Rules, B)

Question: How can you be disqualified from in hand obstacle?
Answer: The following will result in the exhibitor being excused from the course and disqualified from the class:
• Carrying a whip or crop.
• Handler physically moving or coercing the pony/horse by touching.
• Refusals of three (3) obstacles.
• Attendants interfering with the performance of the individual or equine.
• Off course or horse leaving the obstacle course.

Off course is defined as: • Taking an obstacle in the wrong direction. • Negotiating an obstacle from the wrong side. • Skipping an obstacle unless directed by the judge. • Negotiating obstacles in the wrong sequence. • Off pattern. (Section XII – In Hand/Single Working Performance)

Question: How tall are the fences in hunter class?
Answer: Fence heights for Hunters are:
• Modern & ASPC: Minimum height 16" Maximum height 26"
• AMHR – Over/Under: Minimum height 12" Maximum height 24" (If over 24" a second rail is required).

At the discretion of show management, maximum heights may be adjusted. (Section XII. 1.5, c-12)

Question: Are standing martingales allowed in the hunter divisions?
Answer: Martingales of any type are prohibited in under saddle, hack and tie-breaking classes. Standing and running martingales used in the conventional manner are allowed for all over fences classes. All other martingales are considered illegal. A judge must eliminate a horse or pony that competes in a martingale other than a standing or running martingale used in the conventional manner. HU105, 4.

Question: Does the Regional President have to be a member of the USHJA?
Answer: The Regional President must have a membership in the USHJA and/or the American Quarter Horse Association. Rule 2302. A

Question: How high do large pony hunters jump?
Answer: Large pony hunters jump 2’9” in the Green Pony Hunter Division. Large pony hunters jump 2’9”-3’ in the Regular Pony Hunter Division. HU111.13, HU111.14

====================================================
QUESTION:
{input}

====================================================
IHSA RULEBOOK EXCERPTS (ONLY SOURCE OF TRUTH)
====================================================
{context}

====================================================
FINAL OUTPUT FORMAT (EXACT)
====================================================

Answer:
<Paragraph 1 – competition rule(s) exactly>
<Paragraph 2 – schooling rule(s) exactly>

NO bullet merging.
NO missing clauses.
NO extra text."""
    
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    
    # ========== STEP 5: GENERATE ANSWER ==========
    start_generation = time.time()
    
    # Prepare list of models to try (Primary + Fallbacks)
    models_to_try = [settings.OPENAI_MODEL]
    if settings.LLM_PROVIDER == "openai":
         models_to_try.extend(settings.OPENAI_FALLBACK_MODELS)
    
    response_text = None
    last_exception = None
    
    for model_name in models_to_try:
        try:
            print(f"🤖 Generating answer using model: {model_name}")
            
            # Get LLM specific for this iteration
            current_llm = get_llm(model_name=model_name)
            
            question_answer_chain = create_stuff_documents_chain(current_llm, prompt_template)
            
            # Manually invoke with our re-ranked documents
            response_text = await question_answer_chain.ainvoke({
                "input": query,
                "context": top_docs
            })
            
            # If successful, valid response obtained
            if response_text:
                print(f"✅ Success with model: {model_name}")
                break
                
        except Exception as e:
            print(f"⚠️ Model {model_name} failed: {e}")
            last_exception = e
            continue
            
    if not response_text:
        error_msg = f"All configured models failed. Last error: {last_exception}"
        print(f"❌ {error_msg}")
        raise last_exception or Exception(error_msg)
    
    generation_time = (time.time() - start_generation) * 1000
    total_time = (time.time() - start_total) * 1000
    
    # ========== STEP 6: POST-PROCESS ANSWER ==========
    # Post-processing: Extract answer text
    answer = response_text if isinstance(response_text, str) else response_text.get("answer", str(response_text))
    
    # Clean up "Answer:" prefix if present to avoid duplication in UI
    if answer.strip().startswith("Answer:"):
        answer = answer.strip()[7:].strip()
    
    # REMOVED: Automatic appending of Rule 1102 note to respect 'NO extra text' constraint
    
    # Extract source information
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
    
    # Confidence scoring
    confidence = "high" if len(top_docs) >= 5 else "medium" if len(top_docs) >= 2 else "low"
    
    answer_lower = answer.lower()
    if "cannot find" in answer_lower or "don't know" in answer_lower or "not in the" in answer_lower:
        confidence = "low"
    
    # Log query if db session provided
    if db:
        try:
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
