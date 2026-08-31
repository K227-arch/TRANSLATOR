import requests

greetings = [
    "Good morning",
    "Good afternoon",
    "Good evening",
    "Good night",
    "Hello",
    "How are you?",
    "How are you doing?",
    "I am fine",
    "I am doing well",
    "Welcome",
    "Goodbye",
    "See you tomorrow",
    "Thank you",
    "Thank you very much",
    "You are welcome",
    "Please",
    "Sorry",
    "Excuse me",
    "How did you sleep?",
    "I slept well",
    "How is your family?",
    "My family is fine",
    "Good morning, how are you?",
    "I am going home",
    "Have a good day",
    "See you later",
    "Take care",
]

for g in greetings:
    r = requests.post("http://localhost:8000/translate", json={"text": g, "context": ""})
    d = r.json()
    print(f'  "{g}" -> "{d.get("translation")}"')
