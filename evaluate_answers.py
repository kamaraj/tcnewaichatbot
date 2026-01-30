import re
import sys
import os
import asyncio
import json

# Add app to path
sys.path.append(os.getcwd())

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.services.rag_service import RAGService

def parse_test_file(file_path):
    cases = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by "Question:"
    # This is a simple heuristic.
    # regex for Question: ... Expected Answer: ...
    
    # We want to capture the text after Question: until Expected Answer:
    # and Expected Answer: until Answer: or next Question or end of file
    
    pattern = re.compile(r'Question:\s*(.*?)\s*Expected Answer:\s*(.*?)\s*(?:Answer:|Partial Response|Bad Response|Good Response|$)', re.DOTALL | re.IGNORECASE)
    
    # Iterating implies we might miss overlapping matches if not careful.
    # But usually these are sequential.
    
    # Let's try splitting by "Question:" first
    parts = re.split(r'(?:^|\n)Question:\s*', content)
    
    for part in parts[1:]: # Skip preamble
        # part contains the question and expected answer
        # Find "Expected Answer:"
        ea_split = re.split(r'(?:^|\n)Expected Answer:\s*', part, maxsplit=1)
        if len(ea_split) < 2:
             continue
             
        question = ea_split[0].strip()
        rest = ea_split[1]
        
        # content of expected answer ends at "Answer:" or "Partial Response" or "Bad Response" or empty line block
        # Actually, let's just stop at "Answer:"
        
        answer_split = re.split(r'(?:^|\n)Answer:\s*', rest, maxsplit=1)
        expected = answer_split[0].strip()
        
        cases.append({
            "question": question,
            "expected": expected
        })
        
    return cases

async def evaluate():
    print("Loading RAG Service...", flush=True)
    rag = RAGService()
    
    cases = parse_test_file("expectedanswer.txt")
    print(f"Found {len(cases)} test cases.", flush=True)
    
    results = []
    
    for i, case in enumerate(cases):
        q = case["question"]
        expected = case["expected"]
        
        print(f"\n" + "-"*40, flush=True)
        print(f"[{i+1}/{len(cases)}] Q: {q}", flush=True)
        
        try:
            response = await rag.query(q)
            actual = response.answer
            sources = response.sources
            
            print(f"EXPECTED: {expected}", flush=True)
            print(f"ACTUAL  : {actual}", flush=True)
            
            # Simple check: Does actual answer contain section numbers from expected?
            expected_nums = set(re.findall(r'\d{3,4}', expected))
            actual_nums = set(re.findall(r'\d{3,4}', actual))
            
            common = expected_nums.intersection(actual_nums)
            missing = expected_nums - actual_nums
            
            match_score = "LOW"
            if not expected_nums:
                 match_score = "N/A (No rules in expected)"
            elif not missing:
                 match_score = "PERFECT (All rules found)"
            elif common:
                 match_score = f"PARTIAL (Found {common}, Missing {missing})"
            else:
                 match_score = f"FAIL (Found {actual_nums}, Expected {expected_nums})"
            
            print(f"RESULT: {match_score}", flush=True)
            print(f"SOURCES: {[s['section'] for s in sources]}", flush=True)
            
            results.append({
                "question": q,
                "expected": expected,
                "actual": actual,
                "score": match_score,
                "sources": sources
            })
            
            # Small delay to respect rate limits
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"Error: {e}", flush=True)
            results.append({
                "question": q,
                "error": str(e)
            })
            await asyncio.sleep(5) # Longer wait on error

    # Save report
    with open("eval_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nEvaluation complete. Saved to eval_report.json")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(evaluate())
