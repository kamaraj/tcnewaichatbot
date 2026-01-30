import requests
import csv
import time
from datetime import datetime

API_URL = "http://localhost:8091/api/v1/chat"

# Define the 25 Core Topics and their variations
TOPICS = [
    {
        "topic": "Coach Age Requirement (Rule 1102)",
        "variations": [
            ("Standard", "How old do I have to be to coach?"),
            ("Casual", "Can I be a coach if I'm 19?"),
            ("Formal", "What are the age eligibility requirements for an IHSA coach under Rule 1102?"),
            ("Scenario", "My assistant is 20 years old, can they be the designated coach for the show?")
        ]
    },
    {
        "topic": "Online Prize Lists (Rule 5401)",
        "variations": [
            ("Standard", "When must online prizelists be posted?"),
            ("Casual", "Deadline for emailing prize lists?"),
            ("Formal", "According to Section 5401, what isn the procedural timeframe for distributing online prize lists?"),
            ("Negative", "Can I send the prize list just 1 week before the closing date?")
        ]
    },
    {
        "topic": "Young Hunter Heights (HU111)",
        "variations": [
            ("Standard", "How high do Young Hunters jump?"),
            ("Specific", "What is the jump height for a 6-year-old Young Hunter?"),
            ("Formal", "Please list the fence height specifications for the Young Hunter division."),
            ("Comparison", "Do 5-year-old and 7-year-old Young Hunters jump the same height?")
        ]
    },
    {
        "topic": "Alternates Requirement (Rule 4501)",
        "variations": [
            ("Standard", "How many alternates are required?"),
            ("Casual", "Do we need an alternate rider?"),
            ("Formal", "What does Rule 4501 state regarding the designation of alternates?"),
            ("Scenario", "If we have a full team, is an alternate still mandatory?")
        ]
    },
    {
        "topic": "Showmanship Gloves",
        "variations": [
            ("Standard", "Do I need gloves for Showmanship?"),
            ("Casual", "Are gloves required in showmanship classes?"),
            ("Formal", "Is the wearing of gloves mandatory or optional in COOL Showmanship?"),
            ("Scenario", "I forgot my gloves, can I still compete in Showmanship?")
        ]
    },
    {
        "topic": "Liberty Catch Time",
        "variations": [
            ("Standard", "How long do I have to catch my horse in Liberty?"),
            ("Casual", "What's the time limit for catching in Liberty?"),
            ("Formal", "What is the specific catch time duration allocated in the Liberty class?"),
            ("Scenario", "If it takes me 3 minutes to halt my horse in Liberty, am I disqualified?")
        ]
    },
    {
        "topic": "Walk Fences Height (HU 109)",
        "variations": [
            ("Standard", "How high are walk fences?"),
            ("Casual", "Max height for walk rails?"),
            ("Formal", "What are the dimensional restrictions for walk fences in schooling areas?"),
            ("Comparison", "Are walk rails allowed to be higher than 12 inches?")
        ]
    },
    {
        "topic": "Large Pony Hunter Height",
        "variations": [
            ("Standard", "How high do large pony hunters jump?"),
            ("Casual", "Jump height for large ponies?"),
            ("Formal", "Specify the fence heights for the Regular Pony Hunter Division for large ponies."),
            ("Specific", "Does a large pony jump 3'0\" or 2'9\"?")
        ]
    },
    {
        "topic": "In Hand Obstacle Disqualification",
        "variations": [
            ("Standard", "How can you be disqualified from in hand obstacle?"),
            ("Casual", "What gets you kicked out of in-hand obstacle?"),
            ("Formal", "List the infractions that result in disqualification from the In Hand Obstacle class."),
            ("Scenario", "If I carry a crop in the in-hand obstacle class, will I be disqualified?")
        ]
    },
    {
        "topic": "Small Pony Height Limit",
        "variations": [
            ("Standard", "How tall is a small pony?"),
            ("Casual", "Max height for a small pony?"),
            ("Formal", "What is the measurement limit for a pony to be classified as 'Small' under HU 141?"),
            ("Scenario", "My pony is 12.3 hands, is it a small pony?")
        ]
    },
    {
        "topic": "Hunt Seat Regionals Qualification",
        "variations": [
            ("Standard", "How many points do hunt seat riders need to qualify for regionals?"),
            ("Casual", "Points needed for regionals in hunt seat?"),
            ("Formal", "Cite the point accumulation requirements for qualifying for Hunt Seat Regionals."),
            ("Specific", "Do Class 7 and 8 riders need 36 points or 28 points for Regionals?")
        ]
    },
    {
        "topic": "Standing Martingales",
        "variations": [
            ("Standard", "Are standing martingales allowed in hunter divisions?"),
            ("Casual", "Can I use a standing martingale in hunters?"),
            ("Formal", "What are the restrictions on martingale use in over fences classes?"),
            ("Scenario", "Is a running martingale allowed if used in the conventional manner?")
        ]
    },
    {
        "topic": "Hunt Seat Coach Eligibility",
        "variations": [
            ("Standard", "Who can be a hunt seat coach?"),
            ("Casual", "Qualifications for hunt seat coaches?"),
            ("Formal", "What are the membership and certification requirements for a Hunt Seat coach?"),
            ("Scenario", "Can a professional rider be our hunt seat coach without other memberships?")
        ]
    },
    {
        "topic": "Coach Insurance",
        "variations": [
            ("Standard", "Do I need insurance to be a coach?"),
            ("Casual", "Is insurance required for coaches?"),
            ("Formal", "Does the IHSA require coaches to hold personal liability insurance?"),
            ("Scenario", "I don't have personal insurance, can I still coach?")
        ]
    },
    {
        "topic": "Head Coach Requirements",
        "variations": [
            ("Standard", "What are the requirements for a head coach?"),
            ("Casual", "Head coach rules?"),
            ("Formal", "Detail the responsibilities and requirements for an IHSA Head Coach."),
            ("Scenario", "Can an undergraduate student be the Head Coach?")
        ]
    },
    {
        "topic": "Multiple Coaches",
        "variations": [
            ("Standard", "Can a college have multiple coaches?"),
            ("Casual", "Is it okay to have more than one coach?"),
            ("Formal", "Does the rulebook permit a single institution to designate multiple coaches?"),
            ("Scenario", "We want to have a jumping coach and a flat coach, is that allowed?")
        ]
    },
    {
        "topic": "Substituting a Coach",
        "variations": [
            ("Standard", "Can I substitute a coach for a show?"),
            ("Casual", "What if our coach can't make it to the show?"),
            ("Formal", "What is the procedure for appointing a substitute coach according to the rules?"),
            ("Scenario", "Our coach is sick, can we bring a sub?")
        ]
    },
    {
        "topic": "Coach Membership Deadline",
        "variations": [
            ("Standard", "What is the deadline for coach membership?"),
            ("Casual", "When do coaches need to register by?"),
            ("Formal", "State the deadline for submitting coach membership forms."),
            ("Scenario", "If I join in February, can I still coach for the spring season?")
        ]
    },
    {
        "topic": "Liability Waiver",
        "variations": [
            ("Standard", "Do coaches need to sign a liability waiver?"),
            ("Casual", "Is there a waiver for coaches?"),
            ("Formal", "Is the execution of a liability waiver a mandatory prerequisite for coaching?"),
            ("Scenario", "I refused to sign the waiver, can I enter the ring?")
        ]
    },
    {
        "topic": "USHJA Membership",
        "variations": [
            ("Standard", "Is USHJA membership required for coaches?"),
            ("Casual", "Do coaches need to join USHJA?"),
            ("Formal", "Is current membership with the USHJA mandatory for Hunt Seat coaches?"),
            ("Scenario", "I am an AQHA member, do I still need USHJA for hunt seat?")
        ]
    },
    {
        "topic": "Point Rider Rule",
        "variations": [
            ("Standard", "What is the rule for point riders?"),
            ("Casual", "How do point riders work?"),
            ("Formal", "Explain the regulations governing the designation of Point Riders."),
            ("Scenario", "Can I change my point rider after the show starts?")
        ]
    },
    {
        "topic": "Martingale Flat Classes",
        "variations": [
            ("Standard", "Can I use a martingale in flat classes?"),
            ("Casual", "Are martingales allowed on the flat?"),
            ("Formal", "Is the use of any martingale permitted in under saddle classes?"),
            ("Scenario", "My horse needs a martingale for safety, can I use it in the flat class?")
        ]
    },
    {
        "topic": "Flash Nosebands",
        "variations": [
            ("Standard", "Are flash nosebands allowed?"),
            ("Casual", "Can I use a flash noseband?"),
            ("Formal", "Does the rulebook permit the use of flash nosebands in diverse classes?"),
            ("Scenario", "I have a flash attachment on my bridle, is that legal?")
        ]
    },
    {
        "topic": "Rider Fall",
        "variations": [
            ("Standard", "What happens if a rider falls off?"),
            ("Casual", "Penalty for falling off?"),
            ("Formal", "What is the consequence of a rider's fall during the competition?"),
            ("Scenario", "If I fall off but get back on, can I finish my round?")
        ]
    },
    {
        "topic": "Re-ride Lame Horse",
        "variations": [
            ("Standard", "Can I re-ride if my horse is lame?"),
            ("Casual", "Do I get a re-ride for a lame horse?"),
            ("Formal", "Under what conditions is a re-ride granted for equine lameness?"),
            ("Scenario", "My horse felt off at the trot, can I ask for a re-ride?")
        ]
    }
]

def generate_report():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"qa_report_{timestamp}.csv"
    
    print(f"Generating QA Report: {filename}")
    print(f"Total Topics: {len(TOPICS)}")
    print("--------------------------------------------------")

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Topic', 'Variation_Type', 'Question', 'Bot_Answer', 'Response_Time_ms']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for item in TOPICS:
            topic = item['topic']
            print(f"Testing Topic: {topic}")
            
            for var_type, question in item['variations']:
                try:
                    # Call API
                    start_time = time.time()
                    response = requests.post(
                        API_URL, 
                        params={"query": question}  # Note: API uses query param based on chat.html logic
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get('answer', 'No answer field')
                        duration = round((end_time - start_time) * 1000, 2)
                    else:
                        answer = f"ERROR: {response.status_code} - {response.text}"
                        duration = 0
                    
                    # Write row
                    writer.writerow({
                        'Topic': topic,
                        'Variation_Type': var_type,
                        'Question': question,
                        'Bot_Answer': answer,
                        'Response_Time_ms': duration
                    })
                    
                    # Small sleep to be polite to the local server
                    # time.sleep(0.1)
                    
                except Exception as e:
                    print(f"  Error on question '{question}': {e}")
                    writer.writerow({
                        'Topic': topic,
                        'Variation_Type': var_type,
                        'Question': question,
                        'Bot_Answer': f"EXCEPTION: {e}",
                        'Response_Time_ms': 0
                    })
    
    print("--------------------------------------------------")
    print(f"Completed. Saved to {filename}")

if __name__ == "__main__":
    generate_report()
