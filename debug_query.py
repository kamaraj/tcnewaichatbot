import requests
import json

BASE_URL = "http://localhost:8091/api/v1"

def debug_query(query):
    print(f"🔍 Debugging Query: {query}")
    try:
        response = requests.post(f"{BASE_URL}/chat", params={"query": query})
        if response.status_code == 200:
            data = response.json()
            print("\n🤖 Answer:")
            print(data.get("answer"))
            print("\n📄 Retrieved Context Chunks:")
            for chunk in data.get("context_snippets", []):
                print("-" * 40)
                print(chunk.get("content"))
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    debug_query("Restrictions on who can lead the team?")
