import asyncio
import sys
import os
import json
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from app.services.vector_store import VectorStore

async def inspect_metadata():
    vs = VectorStore()
    docs = vs._documents
    
    # Sample first 5 chunks with metadata
    samples = []
    for d in docs[:10]:
        samples.append({
            "id": d.chunk_id,
            "section": d.metadata.get("section_full"),
            "role": d.metadata.get("subject_role"),
            "tags": d.metadata.get("topic_tags"),
            "text": d.text[:100] + "..."
        })
    
    print(json.dumps(samples, indent=2))

if __name__ == "__main__":
    asyncio.run(inspect_metadata())
