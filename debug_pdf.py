
import pypdf
import os

pdf_path = "/Users/tangentcloud/kamaraj/TCBot/data/uploads/04571139-3c70-4f41-8b2b-d124de8c1177_IHSA Rulebook.pdf"

if not os.path.exists(pdf_path):
    # Try finding any IHSA Rulebook in uploads
    uploads_dir = "/Users/tangentcloud/kamaraj/TCBot/data/uploads"
    for f in os.listdir(uploads_dir):
        if "IHSA Rulebook.pdf" in f:
            pdf_path = os.path.join(uploads_dir, f)
            break

print(f"Reading {pdf_path}")
reader = pypdf.PdfReader(pdf_path)
text = ""
for page in reader.pages:
    text += page.extract_text()

keywords = ["7201", "7203", "7207", "4302", "3401.J", "4501", "5401"]
for kw in keywords:
    print(f"\n--- Searching for {kw} ---")
    pos = text.find(kw)
    if pos != -1:
        print(text[max(0, pos-200):pos+400])
    else:
        print("Not found")
