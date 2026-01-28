import fitz
import sys
import re

def inspect_pdf():
    try:
        doc = fitz.open("uploads/IHSA Rulebook.pdf")
    except Exception as e:
        print(f"Error opening pdf: {e}")
        return

    targets = ["7201", "4501", "4302", "2302", "1102"]
    
    for page in doc:
        text = page.get_text()
        found = False
        for t in targets:
            if t in text:
                found = True
                break
        
        if found:
            print(f"--- Page {page.number + 1} ---")
            # Print lines containing the target
            lines = text.split('\n')
            for line in lines:
                for t in targets:
                    if t in line:
                         print(f"MATCH {t}: '{line}'")
            print("---------------------------")
            # Also print context around matches
            # print(text) 

if __name__ == "__main__":
    inspect_pdf()
