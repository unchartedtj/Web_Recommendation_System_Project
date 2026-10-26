"""The 10 standard System Usability Scale statements (Brooke, 1996), word for word.

Odd statements are positive, even statements are negative, which is why they're scored
differently (see sus_score in services.py).
"""
SUS_QUESTIONS = [
    "I think that I would like to use this system frequently.",
    "I found the system unnecessarily complex.",
    "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to be able to use this system.",
    "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.",
    "I felt very confident using the system.",
    "I needed to learn a lot of things before I could get going with this system.",
]

# The answer scale: 1 = Strongly disagree ... 5 = Strongly agree.
SCALE = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]

TARGET_SCORE = 68   # the commonly used "above average usability" benchmark
