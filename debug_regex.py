import re

def test_regex():
    text = """
1102 An eligible college must apply
Rule 2302-C. Memberships are non-refundable.
2302 Duties of the Regional President
4302 Care and control of horses
4501 Drawings will be by lot
7201 Riders who begin showing
    """
    
    section_pattern = re.compile(r'(?:^|\n)\s*(?:(?:Section|Rule|Article)\s+)?(\d{4})(?:\s|(?:\.[A-Z0-9]+)*)', re.IGNORECASE)
    
    print(f"Testing text length: {len(text)}")
    matches = list(section_pattern.finditer(text))
    print(f"Found {len(matches)} matches")
    
    for m in matches:
        print(f"Match: '{m.group(0)}' Group 1: '{m.group(1)}' Start: {m.start()} End: {m.end()}")

    # Mock chunking
    split_points = [m.start() for m in matches]
    split_points.append(len(text))
    
    start_idx = 0
    for i, end_idx in enumerate(split_points):
        if i == 0 and end_idx > 0:
            chunk = text[0:end_idx].strip()
            print(f"Chunk PRE: '{chunk[:20]}...'")
            start_idx = end_idx
            continue

        if end_idx == start_idx:
            continue
            
        chunk = text[start_idx:end_idx].strip()
        print(f"Chunk {i}: '{chunk[:20]}...'")
        
        # Test metadata extraction on chunk
        m_match = section_pattern.search(chunk)
        if m_match:
            print(f"  -> Extracted ID: {m_match.group(1)}")
        else:
            print(f"  -> NO ID EXTRACTED")

        start_idx = end_idx

if __name__ == "__main__":
    test_regex()
