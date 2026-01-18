You are a senior full-stack engineer, ML engineer, and product designer building an MVP web app called:

“FindingMyCar”

The goal is:

A user types natural language like:
“Something like a 2018 BMW 340i but cheaper, AWD, still fast, under 35k, not boring.”

The system:

Understands intent

Converts it into structured preferences

Matches against a car database

Ranks results by “closeness”

Shows listings across the web

This is NOT a filter website.
This is an AI-driven intent-to-match system.

CORE REQUIREMENTS
1. Natural Language Intent Engine

User input examples:

“Fast but reliable under 30k”

“Something like an M340 but cheaper”

“I want fun, AWD, daily drivable, not old”

“Good in snow, still exciting, under 40k”

Build logic that extracts:

Budget (explicit or inferred)

Performance desire

Drivetrain

Size class

Style

Emotional intent (fun, luxury, boring, aggressive, comfy, etc.)

Usage (daily, track, winter, road trip)

Represent as structured JSON like:

{
budget_max: 35000,
performance_priority: 0.8,
reliability_priority: 0.6,
drivetrain: "AWD",
body_style: "sedan",
emotional_tags: ["fun", "not boring"],
reference_car: "BMW 340i 2018"
}

Use LLM to translate free-text into this structure.

2. Car Knowledge Base

Create a normalized dataset with:

Make, model, year, trim

Price range

Power, torque

Drivetrain

Body type

Reliability score

Ownership cost score

“Driving feel” tags (sporty, numb, soft, raw, etc.)

Class tags (luxury, economy, performance, etc.)

Store each car as a “feature vector.”

3. Similarity & Scoring Engine

Build a scoring system that:

Weights each feature based on user priorities

Computes a “closeness score” from 0–100

Score factors:

Price fit

Power similarity

Drivetrain match

Size match

Reliability alignment

Emotional similarity

Example output:

Audi S4 — 92% match
Genesis G70 3.3T — 89% match
Kia Stinger GT — 85% match

Each result must include:

Score

Why it matches

Where it differs

4. Listings Aggregation

System should:

Pull listings from:

One API source OR mock dataset for MVP

Normalize:

Price

Mileage

Location

Condition

Attach listings to matched car models

Show:

Best listings for each matched car

Distance from user

Price vs market average

5. UX Flow

User Flow:

User types messy human request

Show interpreted intent summary

Show ranked car matches with scores

Expand to see listings

Allow refinement:

“Cheaper”

“More reliable”

“More fun”

“Bigger”

“Sportier”

Refinement updates weights and re-ranks instantly.

TECH STACK SUGGESTION

Frontend:

Simple clean UI

One input box

Results cards

Refinement buttons

Backend:

Intent parser using LLM

Matching engine in Python or Node

Vector similarity or weighted scoring

Car database (JSON/SQLite/Postgres)

LLM Usage:

Only for intent parsing and explanation

NOT for core ranking logic

OUTPUT YOU MUST GENERATE

System architecture diagram (in text)

Data schema for car database

Intent extraction prompt template

Matching algorithm logic

API design

Frontend layout description

Step-by-step MVP build plan

Example end-to-end flow from user input to result

DESIGN PHILOSOPHY

This product must feel like:
“I don’t know cars. I know what I want. And this thing gets me.”

No dropdown hell.
No filter abuse.
No clutter.

It must:

Explain itself

Admit tradeoffs

Be fast

Be honest

You are building:
An intent-to-reality engine.

Now design and implement the full MVP plan with engineering-grade detail.