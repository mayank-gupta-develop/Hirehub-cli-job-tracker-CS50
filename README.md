📋 HireHub – A CLI-Based Job Scraper & Tracker

Author: Mayank Gupta
Course: CS50’s Introduction to Programming with Python (CS50P) – Harvard University
Final Project: 2026

GitHub Repository: 👉 https://github.com/mayank-gupta-develop/Hirehub-cli-job-tracker-CS50.git
Project Video (YouTube): 👉 https://youtu.be/1g07C8IrbzQ

⸻

📌 Description

HireHub is a command-line job scraping and tracking application built entirely in Python as my final project for CS50P. The application enables users to search for remote job opportunities across multiple online sources and manage their job application progress through a structured, persistent system.

Unlike traditional job-search methods that involve multiple browser tabs or spreadsheets, HireHub provides a centralized, efficient workflow directly in the terminal. Users can scrape jobs, filter them intelligently, store them locally, and track their application status over time.

This project reflects my ability to design and implement a complete Python-based application that integrates external APIs, database management, testing, and user interaction into a cohesive system.

⸻

🎯 Motivation and Background

As someone transitioning into software development from a BBA IT background, I wanted to build a project that was both practical and technically meaningful. While learning Python through CS50P, I realized the importance of combining programming fundamentals with real-world applications.

Job searching is a common challenge, especially when opportunities are scattered across multiple platforms. HireHub was designed to solve this problem by creating a single tool that can both discover and organize job listings efficiently.

This project combines:
	•	Python programming fundamentals from CS50P
	•	Practical use of APIs and web scraping
	•	Real-world problem-solving in job tracking

⸻

✅ Core Features

HireHub allows users to:
	•	🔍 Search and scrape jobs from multiple platforms
	•	📊 Filter results using keyword-based ranking
	•	💾 Store job listings in a local SQLite database
	•	🔄 Perform CRUD operations on job entries
	•	🏷 Update job status (Saved, Applied, Ignored)
	•	📋 View jobs in a clean tabular format
	•	🌐 Open job listings directly in a browser
	•	🧹 Clear or reset the job tracker

Each job is stored with attributes such as title, company, location, URL, date added, and status.

⸻

🛠 Technologies Used

Core Technologies
	•	Python
	•	SQLite (sqlite3)

Libraries
	•	requests
	•	beautifulsoup4
	•	tabulate
	•	pytest
	•	python-dotenv
	•	apify-client

⸻

📂 Project Structure

project/
│
├── project.py         # Main application logic (main + custom functions)
├── test_project.py    # Unit tests using pytest
├── jobs.db            # SQLite database for persistence
├── requirements.txt   # Project dependencies
├── README.md          # Project documentation


⸻

▶️ How to Run the Project
	1.	Ensure Python 3 is installed
	2.	Clone the repository
	3.	Install dependencies:

pip install -r requirements.txt


	4.	Run the application:

source venv/bin/activate    python project.py



⸻

🧠 Program Architecture

The main execution starts in the main() function inside project.py. It handles user interaction and orchestrates the overall workflow.

Key functions include:
	•	scrape_jobs() → Fetches job listings from APIs
	•	filter_jobs() → Ranks jobs based on keyword matching
	•	save_jobs() → Stores jobs in SQLite database
	•	load_tracker() → Loads saved jobs
	•	update_status() → Updates job status
	•	display_jobs() → Displays jobs in tabular format

All required functions are defined at the same level as main() to comply with CS50P requirements.

⸻

🧪 Testing

Testing is implemented in test_project.py using pytest.

Functions tested include:
	•	filter_jobs
	•	update_status
	•	save_jobs
	•	load_tracker
	•	clean_text

The tests cover:
	•	Valid and invalid inputs
	•	Edge cases
	•	Data consistency
	•	Error handling

Run tests using:

source venv/bin/activate    pytest test_project.py


⸻

💾 Database Design

HireHub uses a local SQLite database (jobs.db) to store job data.

Reasons for choosing SQLite:
	•	Lightweight and built into Python
	•	No external setup required
	•	Reliable persistence

Duplicate jobs are prevented using a uniqueness constraint based on job attributes.

⸻

🎨 Design Decisions
	•	CLI Interface: Chosen to focus on Python logic rather than frontend complexity
	•	SQLite Storage: Ensures persistence without external dependencies
	•	Keyword Ranking: Improves search relevance compared to simple matching
	•	Defensive Programming: Handles API failures gracefully
	•	Tabular Display: Enhances readability using tabulate

⸻

⚠️ Challenges Faced
	•	Handling inconsistent job data from different APIs
	•	Designing a flexible filtering system
	•	Managing database operations safely
	•	Ensuring robustness when APIs fail
	•	Writing meaningful unit tests for real-world data

⸻

📚 What I Learned

Through this project, I gained experience in:
	•	Building real-world Python applications
	•	Working with APIs and web scraping
	•	Designing database-backed systems
	•	Writing and testing modular code
	•	Structuring scalable CLI applications

⸻

🚀 Future Improvements
	•	Pagination for large job lists
	•	Advanced filtering (location, tech stack)
	•	Export to CSV/Excel
	•	Better UI (possibly web-based version)
	•	Scheduled job scraping

⸻

💭 Final Thoughts

HireHub represents my ability to take Python fundamentals and apply them to a practical, real-world problem. It goes beyond basic exercises by integrating multiple systems into a cohesive application.

This project demonstrates my readiness to build more advanced software and continue growing as a developer.

⸻

📜 Academic Honesty & Attribution

This project was developed as part of CS50P.

External libraries used:
	•	requests
	•	beautifulsoup4
	•	tabulate
	•	pytest
	•	python-dotenv
	•	apify-client

AI tools (Claude) were used as a learning aid and debugging assistant, in accordance with CS50 guidelines. All code was reviewed, understood, and implemented by me.

⸻# Hirehub-cli-job-tracker-CS50
