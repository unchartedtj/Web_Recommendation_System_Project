"""Seed catalogue: academic units, demo partners and demo opportunities.

This module is plain data (no database access). `flask seed-data` writes it to MySQL,
and evaluation/evaluate_engine.py reads it directly, so both always use the same data.
Units are identified by name (the API lists them alphabetically).
"""

# The 12 catalogue units. Students enter a grade for every one of them.
UNITS = [
    "Object Oriented Programming",
    "Data Structures and Algorithms",
    "Software Engineering",
    "Database Systems",
    "Web Application Development",
    "Mobile Application Development",
    "Probability and Statistics I",
    "Artificial Intelligence",
    "Computer Networks",
    "Operating Systems",
    "Business Systems Analysis",
    "IT Project Management",
]

DEMO_PASSWORD = "DemoPass123"

# key -> account details; opportunities below refer to partners by key.
PARTNERS = {
    "techcorp": {
        "email": "techcorp.demo@wbl.local",
        "organization_name": "TechCorp Kenya (Demo)",
        "contact_person": "Grace Wanjiku",
        "phone": "+254 700 111 222",
    },
    "netsecure": {
        "email": "netsecure.demo@wbl.local",
        "organization_name": "NetSecure Ltd (Demo)",
        "contact_person": "Brian Otieno",
        "phone": "+254 700 333 444",
    },
}

E, D = "essential", "desirable"

# Requirements: (unit_name, importance, min_mark or None).
# The requirements deliberately differ in number of units, importance and minimum marks.
OPPORTUNITIES = [
    {
        "key": "SWE",
        "partner": "techcorp",
        "title": "Software Development Intern",
        "sector": "Software Engineering",
        "location": "Nairobi",
        "duration_months": 3,
        "slots": 3,
        "description": "Build and test features for our products alongside senior developers.",
        "requirements": [("Object Oriented Programming", E, 60),
                         ("Data Structures and Algorithms", E, 55),
                         ("Software Engineering", D, None)],
    },
    {
        "key": "WEB",
        "partner": "techcorp",
        "title": "Web & Mobile App Development Intern",
        "sector": "Web & Mobile",
        "location": "Nairobi (hybrid)",
        "duration_months": 3,
        "slots": 2,
        "description": "Build responsive web front-ends and cross-platform mobile app features.",
        "requirements": [("Web Application Development", E, 60),
                         ("Mobile Application Development", E, 60),
                         ("Database Systems", D, None)],
    },
    {
        "key": "DATA",
        "partner": "techcorp",
        "title": "Data Analytics & AI Intern",
        "sector": "Data & AI",
        "location": "Nairobi",
        "duration_months": 3,
        "slots": 2,
        "description": "Clean and analyse business data and help prototype machine learning models.",
        "requirements": [("Probability and Statistics I", E, 60),
                         ("Database Systems", E, 55),
                         ("Artificial Intelligence", D, None)],
    },
    {
        "key": "NET",
        "partner": "netsecure",
        "title": "Networking & IT Support Intern",
        "sector": "Infrastructure",
        "location": "Nairobi",
        "duration_months": 6,
        "slots": 2,
        "description": "Support network operations, servers and end-user IT for client sites.",
        "requirements": [("Computer Networks", E, 55),
                         ("Operating Systems", E, 55)],
    },
    {
        "key": "BA",
        "partner": "netsecure",
        "title": "IT Business / Systems Analyst Intern",
        "sector": "Business IT",
        "location": "Mombasa",
        "duration_months": 3,
        "slots": 2,
        "description": "Gather requirements, model processes and support IT project delivery.",
        "requirements": [("Business Systems Analysis", E, None),
                         ("IT Project Management", E, None),
                         ("Database Systems", D, None),
                         ("Software Engineering", D, None)],
    },
]
