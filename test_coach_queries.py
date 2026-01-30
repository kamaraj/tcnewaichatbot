import requests
import json
import time

BASE_URL = "http://localhost:8091/api/v1"

questions = [
    # 1. The Casual Applicant (Direct)
    "How old do I have to be to coach?",
    "Can I be a coach if I'm 19?",
    "What's the cutoff age for coaching?",

    # 2. The Executive (Brief & Keyword-heavy)
    "Coach age regulations?",
    "Min age coaches.",
    "Coaching eligibility age.",

    # 3. The Concerned Parent (Safety-focused)
    "Are the coaches required to be adults?",
    "How young can a coach be in this league?",
    "Is there a rule ensuring coaches aren't just teenagers?",

    # 4. The "Rule Lawyer" / Auditor (Formal & Specific)
    "Please cite the rule regarding age qualifications for IHSA coaches.",
    "What does Rule 1102 say about age?",
    "Does the rulebook specify a minimum age for personnel under Section 1100?",

    # 5. The Confused User (Vague)
    "Age rules for staff?",
    "Do you have to be 21 to do anything?",
    "Restrictions on who can lead the team?"
]

def test_queries():
    print(f"🚀 Running {len(questions)} persona tests for 'Coach Age' rule...")
    print("-" * 60)
    
    results = []
    
    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] Asking: {q}")
        start = time.time()
        
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                params={"query": q}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "").strip()
                latency = round((time.time() - start) * 1000, 2)
                
                # Check for key phrases
                has_21 = "21" in answer
                has_rule = "1102" in answer or "1102.A" in answer
                
                status = "✅ PASS" if (has_21 and has_rule) else "⚠️  PARTIAL" if (has_21 or has_rule) else "❌ FAIL"
                
                result_entry = {
                    "query": q,
                    "status": status,
                    "answer": answer,
                    "latency_ms": latency
                }
                results.append(result_entry)
                
                print(f"Status: {status} ({latency}ms)")
                print(f"Answer: {answer[:100]}...") # Preview
                print("-" * 60)
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            break
            
    # Summary Report
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    print(f"{'QUERY':<50} | {'STATUS':<10} | {'KEYWORD CHECK'}")
    print("-" * 60)
    for r in results:
        check = "21 + Rule 1102" if "PASS" in r["status"] else "Missing info"
        print(f"{r['query']:<50} | {r['status']:<10} | {check}")
    print("=" * 60)

if __name__ == "__main__":
    test_queries()
