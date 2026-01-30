import fitz
import sys

def debug_page_15():
    doc = fitz.open("uploads/IHSA Rulebook.pdf")
    page = doc[14] # 0-indexed, so 15th page
    text = page.get_text("text")
    print(f"--- Raw Text Page 15 ({len(text)} chars) ---")
    print(repr(text))
    print("--- End Raw Text ---")

if __name__ == "__main__":
    debug_page_15()
