"""Seed catalogue: academic units, demo partners and demo opportunities.

This module is plain data (no database access). `flask seed-data` writes it to MySQL,
and evaluation/evaluate_engine.py reads it directly, so both always use the same data.
Units are identified by name (the API lists them alphabetically).
"""
import os

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

# Preset technical skills: (name, category). Students pick up to 10; partners require 1 to 8.
SKILLS = [
    ("Python", "Programming"),
    ("Java", "Programming"),
    ("JavaScript", "Programming"),
    ("HTML & CSS", "Web"),
    ("React", "Web"),
    ("PHP", "Web"),
    ("Kotlin / Flutter", "Mobile"),
    ("SQL", "Data"),
    ("Power BI / Tableau", "Data"),
    ("Machine Learning", "Data"),
    ("Excel Data Analysis", "Data"),
    ("Networking (Cisco)", "Infrastructure"),
    ("Linux Administration", "Infrastructure"),
    ("Cybersecurity Fundamentals", "Infrastructure"),
    ("Cloud (AWS / Azure)", "Infrastructure"),
    ("IT Support & Troubleshooting", "Infrastructure"),
    ("Git & GitHub", "Tools"),
    ("UI/UX Design (Figma)", "Design"),
    ("Business Process Modelling", "Business"),
    ("Project Management", "Business"),
    ("Technical Writing", "Business"),
]

# Preset sectors: the career-interest options AND each internship's sector.
SECTORS = [
    "Software Development",
    "Web & Mobile Development",
    "Data Analytics & AI",
    "Networking & Cybersecurity",
    "IT Support & Infrastructure",
    "Business Analysis & IT Consulting",
    "UI/UX & Digital Media",
]

DEMO_PASSWORD = "DemoPass123"

# Default system admin. Log in on the normal Login page with the USERNAME "Admin".
# Its password is DEFAULT_ADMIN_PASSWORD from backend/.env if that meets the password rules;
# otherwise a strong random one is generated and printed ONCE when the admin is created.
DEFAULT_ADMIN = {
    "name": "Admin",                       # this is the username typed on the Login page
    "email": "admin@strathmore.edu",       # an email is still stored, because every user needs one
    "password": os.getenv("DEFAULT_ADMIN_PASSWORD"),
}

# key -> account details; opportunities below refer to partners by key.
PARTNERS = {
    "techcorp": {
        "email": "info@techcorp.co.ke",
        "organization_name": "TechCorp Kenya",
        "contact_person": "Grace Wanjiku",
        "phone": "+254 700 111 222",
    },
    "netsecure": {
        "email": "info@netsecure.co.ke",
        "organization_name": "NetSecure Ltd",
        "contact_person": "Brian Otieno",
        "phone": "+254 700 333 444",
    },
}

# Demo students (password DEMO_PASSWORD). "marks" lists the units that differ from the
# base marks; every other unit gets a varied base mark from 56 to 68 (varied on purpose,
# because 12 identical marks would trigger the "implausible entry" check).
# profile=None → an account with no profile yet, to show the empty states.
DEMO_STUDENTS = [
    {
        "email": "samuel.kamau@strathmore.edu", "admission_no": "900001",
        "first_name": "Samuel", "last_name": "Kamau", "course": "BBIT", "year_of_study": 3,
        # TC07: strongest in the Software Development units → Software Development Intern #1.
        "profile": {
            "marks": {"Object Oriented Programming": 90, "Data Structures and Algorithms": 88,
                      "Software Engineering": 80},
            "skills": ["Java", "Git & GitHub", "Python"],
            "interests": ["Software Development"],
        },
    },
    {
        "email": "diana.wanjiru@strathmore.edu", "admission_no": "900002",
        "first_name": "Diana", "last_name": "Wanjiru", "course": "BBIT", "year_of_study": 3,
        # Strong in statistics and databases. OOP 52 is below the Software Development
        # essential minimum (60), so that internship appears under "Below minimum".
        "profile": {
            "marks": {"Probability and Statistics I": 86, "Database Systems": 84,
                      "Artificial Intelligence": 72, "Object Oriented Programming": 52},
            "skills": ["Python", "SQL", "Power BI / Tableau"],
            "interests": ["Data Analytics & AI"],
        },
    },
    {
        "email": "kevin.mwangi@strathmore.edu", "admission_no": "900003",
        "first_name": "Kevin", "last_name": "Mwangi", "course": "BBIT", "year_of_study": 2,
        "profile": None,
    },
]

# Demo applications, created through the real apply() rules (no placements: those are made
# by a partner accepting). (student email, opportunity key, status, note, below-minimum ok?)
DEMO_APPLICATIONS = [
    ("samuel.kamau@strathmore.edu", "SWE", "pending",
     "I enjoy building Java applications and would love to grow as a developer on your team.",
     False),
    ("diana.wanjiru@strathmore.edu", "DATA", "shortlisted",
     "Data analysis is my passion. I have used Python, SQL and Power BI in class projects.",
     False),
    ("diana.wanjiru@strathmore.edu", "SWE", "pending",
     "I know my OOP mark is below your minimum, but I am improving my programming skills.",
     True),
]

E, D = "essential", "desirable"

# Requirements: (unit_name, importance, min_mark or None).
# Skills:       (skill_name, importance).
# The requirements deliberately differ in number of units, importance and minimum marks.
OPPORTUNITIES = [
    {
        "key": "SWE",
        "partner": "techcorp",
        "title": "Software Development Intern",
        "sector": "Software Development",
        "skills": [("Java", E), ("Git & GitHub", E), ("Python", D), ("SQL", D)],
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
        "sector": "Web & Mobile Development",
        "skills": [("JavaScript", E), ("React", E), ("HTML & CSS", E), ("Kotlin / Flutter", D)],
        "location": "Nairobi",
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
        "sector": "Data Analytics & AI",
        "skills": [("Python", E), ("SQL", E), ("Power BI / Tableau", D), ("Machine Learning", D)],
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
        "sector": "Networking & Cybersecurity",
        "skills": [("Networking (Cisco)", E), ("Linux Administration", E),
                   ("Cybersecurity Fundamentals", D), ("IT Support & Troubleshooting", D)],
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
        "sector": "Business Analysis & IT Consulting",
        "skills": [("Business Process Modelling", E), ("Project Management", E),
                   ("SQL", D), ("Technical Writing", D)],
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
