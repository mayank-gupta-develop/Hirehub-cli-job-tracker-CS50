import sqlite3
import re
import os
import requests
import webbrowser
from bs4 import BeautifulSoup
from tabulate import tabulate
from dotenv import load_dotenv
from apify_client import ApifyClient

from datetime import date
import sys
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

DB_FILE = "jobs.db"
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")
LINKEDIN_ACTOR = "curious_coder/linkedin-jobs-scraper"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
REMOTEOK_URL = "https://remoteok.com/api"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
THE_MUSE_URL = "https://www.themuse.com/api/public/jobs"

# ─────────────────────────────────────────────
#  ANSI Colors for a Premium CLI
# ─────────────────────────────────────────────
C_RESET = "\033[0m"
C_BOLD  = "\033[1m"
C_GREEN = "\033[32m"
C_YELLOW= "\033[33m"
C_RED   = "\033[31m"
C_CYAN  = "\033[36m"
C_GRAY  = "\033[90m"

DEMO_JOBS = [
    {"title": "Python Backend Developer",     "company": "Stripe",      "location": "Remote", "url": "https://stripe.com/jobs",      "source": "Demo", "status": ""},
    {"title": "Node.js Engineer",             "company": "Vercel",      "location": "Remote", "url": "https://vercel.com/careers",   "source": "Demo", "status": ""},
    {"title": "Full Stack Developer",         "company": "GitHub",      "location": "Remote", "url": "https://github.com/about/careers", "source": "Demo", "status": ""},
    {"title": "Backend Engineer (Python)",    "company": "Shopify",     "location": "Remote", "url": "https://shopify.com/careers",  "source": "Demo", "status": ""},
    {"title": "Junior Software Engineer",     "company": "Automattic",  "location": "Remote", "url": "https://automattic.com/work-with-us", "source": "Demo", "status": ""},
    {"title": "React Developer",              "company": "Basecamp",    "location": "Remote", "url": "https://basecamp.com/about/jobs", "source": "Demo", "status": ""},
    {"title": "DevOps Engineer",              "company": "Netlify",     "location": "Remote", "url": "https://netlify.com/careers",  "source": "Demo", "status": ""},
    {"title": "Software Engineer - Backend",  "company": "Buffer",      "location": "Remote", "url": "https://buffer.com/journey",   "source": "Demo", "status": ""},
    {"title": "API Developer",               "company": "Twilio",      "location": "Remote", "url": "https://twilio.com/company/jobs", "source": "Demo", "status": ""},
    {"title": "Python Data Engineer",        "company": "Zapier",      "location": "Remote", "url": "https://zapier.com/jobs",      "source": "Demo", "status": ""},
]


def init_db(db_name=DB_FILE):
    """Initialize the SQLite database and create the jobs table if it doesn't exist."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            source TEXT,
            status TEXT,
            tags TEXT,
            date_added TEXT,
            UNIQUE(title, company, url)
        )
    """)
    # Migration: Add columns if they don't exist
    for col in [("tags", "TEXT"), ("date_added", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col[0]} {col[1]}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def clean_text(text):
    """Remove HTML tags and normalize whitespace from a string."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def filter_jobs(jobs, keyword):
    """
    Return jobs matching the keyword with a scoring-based 'Smart Search'.
    Prioritizes exact matches, then token matches in title, then tags.
    """
    if not keyword:
        return jobs

    keyword = keyword.lower()
    tokens = set(keyword.split())
    scored_jobs = []

    for job in jobs:
        score = 0
        title = job.get("title", "").lower()
        company = job.get("company", "").lower()
        tags = job.get("tags", "").lower()

        # Score exact phrase match (highest priority)
        if keyword in title:
            score += 100
        elif keyword in company:
            score += 50
        elif keyword in tags:
            score += 30

        # Score token matches
        matches = 0
        for token in tokens:
            if token in title:
                score += 20
                matches += 1
            elif token in company:
                score += 10
                matches += 1
            elif token in tags:
                score += 5
                matches += 1

        if score > 0:
            job["_score"] = score
            scored_jobs.append(job)

    # Sort by score descending
    scored_jobs.sort(key=lambda x: x["_score"], reverse=True)
    
    # Clean up score internal key
    for job in scored_jobs:
        job.pop("_score", None)

    return scored_jobs


def scrape_jobs(keyword=""):
    """
    Scrape job listings from LinkedIn (via Apify), Remotive, RemoteOK, Arbeitnow, and The Muse.
    LinkedIn is the primary source; free APIs serve as supplements.
    Falls back to demo data if all live sources are unavailable.
    Returns a filtered list of job dicts based on keyword.
    """
    jobs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # --- Source 1: LinkedIn Jobs via Apify (PRIMARY) ---
    if APIFY_API_KEY and keyword:
        try:
            print(f"  ⏳ Scraping LinkedIn for '{keyword}'... (this may take ~30s)")
            client = ApifyClient(APIFY_API_KEY)
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={requests.utils.quote(keyword)}&position=1&pageNum=0"
            run = client.actor(LINKEDIN_ACTOR).call(run_input={
                "urls": [search_url],
                "scrapeCompany": False,
                "count": 25,
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            count = 0
            for item in items:
                tags_parts = []
                if item.get("jobFunction"):
                    tags_parts.append(item["jobFunction"])
                if item.get("industries"):
                    tags_parts.append(item["industries"])
                if item.get("employmentType"):
                    tags_parts.append(item["employmentType"])
                jobs.append({
                    "title":    clean_text(item.get("title", "")),
                    "company":  clean_text(item.get("companyName", "")),
                    "location": item.get("location", "Remote") or "Remote",
                    "url":      item.get("link", ""),
                    "source":   "LinkedIn",
                    "status":   "",
                    "tags":     " ".join(tags_parts).lower()
                })
                count += 1
            if count:
                print(f"  ✓ LinkedIn: {count} jobs fetched")
        except Exception as e:
            print(f"  ⚠ LinkedIn unavailable ({type(e).__name__}: {e})")
    elif not APIFY_API_KEY:
        print(f"  {C_GRAY}ℹ LinkedIn disabled (no APIFY_API_KEY in .env){C_RESET}")

    # --- Source 2: Remotive public API ---
    try:
        params = {"search": keyword} if keyword else {}
        response = requests.get(REMOTIVE_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        for item in data.get("jobs", []):
            # Combine tags and category for better searching
            tags_list = item.get("tags", [])
            category = item.get("category", "")
            if category:
                tags_list.append(category)
            
            jobs.append({
                "title":    clean_text(item.get("title", "")),
                "company":  clean_text(item.get("company_name", "")),
                "location": item.get("candidate_required_location", "Remote") or "Remote",
                "url":      item.get("url", ""),
                "source":   "Remotive",
                "status":   "",
                "tags":     " ".join(tags_list).lower()
            })
        if jobs:
            print(f"  ✓ Remotive: {len(jobs)} jobs fetched")
    except Exception as e:
        print(f"  ⚠ Remotive unavailable ({type(e).__name__})")

    # --- Source 3: RemoteOK public API ---
    try:
        response = requests.get(REMOTEOK_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        count = 0
        for item in data[1:]:
            tags_list = item.get("tags", [])
            jobs.append({
                "title":    clean_text(item.get("position", "")),
                "company":  clean_text(item.get("company", "")),
                "location": item.get("location", "Remote") or "Remote",
                "url":      item.get("url", ""),
                "source":   "RemoteOK",
                "status":   "",
                "tags":     " ".join(tags_list).lower()
            })
            count += 1
        if count:
            print(f"  ✓ RemoteOK: {count} jobs fetched")
    except Exception as e:
        print(f"  ⚠ RemoteOK unavailable ({type(e).__name__})")

    # --- Source 4: Arbeitnow public API ---
    try:
        # Arbeitnow doesn't have a reliable keyword param, so we fetch latest and filter
        response = requests.get(ARBEITNOW_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        count = 0
        for item in data.get("data", []):
            tags_list = item.get("tags", [])
            jobs.append({
                "title":    clean_text(item.get("title", "")),
                "company":  clean_text(item.get("company_name", "")),
                "location": item.get("location", "Remote") or "Remote",
                "url":      item.get("url", ""),
                "source":   "Arbeitnow",
                "status":   "",
                "tags":     " ".join(tags_list).lower()
            })
            count += 1
        if count:
            print(f"  ✓ Arbeitnow: {count} jobs fetched")
    except Exception as e:
        print(f"  ⚠ Arbeitnow unavailable ({type(e).__name__})")

    # --- Source 5: The Muse public API (Excellent for non-tech) ---
    try:
        params = {"page": 0}
        if keyword:
            params["keyword"] = keyword
        response = requests.get(THE_MUSE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        count = 0
        for item in data.get("results", []):
            jobs.append({
                "title":    clean_text(item.get("name", "")),
                "company":  clean_text(item.get("company", {}).get("name", "")),
                "location": ", ".join([l.get("name") for l in item.get("locations", [])]),
                "url":      item.get("refs", {}).get("landing_page", ""),
                "source":   "The Muse",
                "status":   "",
                "tags":     " ".join([c.get("name") for c in item.get("categories", [])]).lower()
            })
            count += 1
        if count:
            print(f"  ✓ The Muse: {count} jobs fetched")
    except Exception as e:
        print(f"  ⚠ The Muse unavailable ({type(e).__name__})")

    # --- Fallback: demo data if all sources failed ---
    if not jobs:
        print("  ℹ Using demo data (live sources blocked on this network)\n")
        jobs = [dict(j) for j in DEMO_JOBS]

    return filter_jobs(jobs, keyword)


def save_jobs(jobs, db_name=DB_FILE):
    """Save a list of job dicts to the SQLite database. Returns count of new items."""
    if not jobs:
        return 0
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    new_count = 0
    today = date.today().strftime("%Y-%m-%d")
    for job in jobs:
        cursor.execute("""
            INSERT OR IGNORE INTO jobs (title, company, location, url, source, status, tags, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("url"),
            job.get("source"),
            job.get("status", ""),
            job.get("tags", ""),
            today
        ))
        if cursor.rowcount > 0:
            new_count += 1
    conn.commit()
    conn.close()
    return new_count


def load_tracker(db_name=DB_FILE):
    """Load jobs from the SQLite database. Returns a list of dicts."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT title, company, location, url, source, status, tags, date_added FROM jobs")
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            jobs.append({
                "title":    row[0],
                "company":  row[1],
                "location": row[2],
                "url":      row[3],
                "source":   row[4],
                "status":   row[5],
                "tags":     row[6],
                "date":     row[7]
            })
        return jobs
    except sqlite3.OperationalError:
        return []


def clear_tracker(db_name=DB_FILE):
    """Delete all jobs from the tracker."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs")
    conn.commit()
    conn.close()


def update_status(jobs, index, status, db_name=DB_FILE):
    """
    Update the application status of a job at the given index and persist to DB.
    Valid statuses: 'applied', 'saved', 'ignored', ''.
    Returns the updated jobs list.
    """
    valid_statuses = ["applied", "saved", "ignored", ""]
    if not (0 <= index < len(jobs)):
        raise IndexError("Job index out of range.")
    if status not in valid_statuses:
        raise ValueError(f"Status must be one of {valid_statuses}")
    
    job = jobs[index]
    job["status"] = status

    # Persist change to database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs SET status = ? 
        WHERE title = ? AND company = ? AND url = ?
    """, (status, job["title"], job["company"], job["url"]))
    conn.commit()
    conn.close()
    
    return jobs


def open_job_url(jobs, index):
    """Open the recruitment URL in the default system browser."""
    if not (0 <= index < len(jobs)):
        raise IndexError("Job index out of range.")
    url = jobs[index].get("url")
    if url:
        print(f"\n  🌐 Opening {C_CYAN}{url}{C_RESET} ...")
        webbrowser.open(url)
    else:
        print(f"\n  {C_RED}⚠ No URL available for this job.{C_RESET}")


def show_job_details(jobs, index):
    """Print a detailed view for a specific job."""
    if not (0 <= index < len(jobs)):
        raise IndexError("Job index out of range.")
    job = jobs[index]
    
    print(f"\n{C_BOLD}{'='*60}")
    print(f"{C_BOLD}  JOB DETAILS")
    print(f"{'='*60}{C_RESET}")
    print(f"  {C_BOLD}Title:{C_RESET}    {job['title']}")
    print(f"  {C_BOLD}Company:{C_RESET}  {job['company']}")
    print(f"  {C_BOLD}Location:{C_RESET} {job['location']}")
    print(f"  {C_BOLD}Source:{C_RESET}   {job['source']}")
    print(f"  {C_BOLD}Status:{C_RESET}   {get_status_label(job['status'])}")
    print(f"  {C_BOLD}Tags:{C_RESET}     {job.get('tags', '—')}")
    print(f"  {C_BOLD}URL:{C_RESET}      {C_CYAN}{job['url']}{C_RESET}")
    print(f"{C_BOLD}{'='*60}{C_RESET}")


def get_status_label(status):
    """Return a color-coded status label."""
    if status == "applied":
        return f"{C_GREEN}● Applied{C_RESET}"
    if status == "saved":
        return f"{C_YELLOW}● Saved{C_RESET}"
    if status == "ignored":
        return f"{C_RED}● Ignored{C_RESET}"
    return f"{C_GRAY}○ New{C_RESET}"


def display_jobs(jobs):
    """Print the jobs list as a clean formatted table in the terminal."""
    if not jobs:
        print(f"  {C_GRAY}No jobs to display.{C_RESET}")
        return
    rows = []
    for i, job in enumerate(jobs, 1):
        status_label = get_status_label(job.get("status", ""))
        date_str = job.get("date", "—")
        rows.append([
            i,
            f"{C_BOLD}{job.get('title', '')[:45]}{C_RESET}",
            job.get("company", "")[:25],
            job.get("location", "")[:15],
            date_str,
            status_label
        ])
    headers = ["#", "Title", "Company", "Location", "Date", "Status"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def main():
    print(f"\n{C_BOLD}{C_CYAN}╔══════════════════════════════════════╗")
    print("║     🔍 HireHub — Job Tracker CLI     ║")
    print(f"╚══════════════════════════════════════╝{C_RESET}\n")

    init_db()

    existing = load_tracker()
    if existing:
        print(f"📋 Found existing tracker with {C_BOLD}{len(existing)}{C_RESET} job(s).")
        choice = input("   Load existing jobs? [y/n]: ").strip().lower()
        jobs = existing if choice == "y" else None
    else:
        jobs = None

    if jobs is None:
        keyword = input(f"🔍 {C_BOLD}Enter keyword to search:{C_RESET} ").strip()
        print(f"\n📡 Fetching jobs for '{C_CYAN}{keyword}{C_RESET}'...\n")
        jobs = scrape_jobs(keyword)
        if not jobs:
            print(f"{C_RED}❌ No jobs found. Try a different keyword.{C_RESET}")
            sys.exit(1)
        print(f"{C_GREEN}✅ Found {len(jobs)} matching job(s).{C_RESET}\n")
        save_jobs(jobs)

    while True:
        display_jobs(jobs)
        print(f"\n  {C_BOLD}Options:{C_RESET}")
        print(f"  {C_BOLD}[#] status{C_RESET} → e.g., '1 applied', '2 saved', '3 ignored'")
        print(f"  {C_BOLD}o [#]{C_RESET}      → Open job in browser (e.g., 'o 1')")
        print(f"  {C_BOLD}d [#]{C_RESET}      → View job details (e.g., 'd 1')")
        print(f"  {C_BOLD}s{C_RESET}          → New search")
        print(f"  {C_BOLD}clear{C_RESET}      → Wipe tracker")
        print(f"  {C_BOLD}q{C_RESET}          → Save & quit\n")

        cmd_raw = input(f"{C_CYAN}→ {C_RESET}").strip().lower()
        if not cmd_raw:
            continue

        parts = cmd_raw.split()
        cmd = parts[0]

        if cmd == "q":
            save_jobs(jobs)
            print(f"\n💾 {C_GREEN}Tracker saved to jobs.db. Good luck! 🚀{C_RESET}\n")
            break

        elif cmd == "clear":
            confirm = input(f"  {C_RED}⚠ Are you sure you want to delete all jobs? [y/n]: {C_RESET}").strip().lower()
            if confirm == "y":
                clear_tracker()
                jobs = []
                print(f"  {C_GREEN}✅ Tracker cleared.{C_RESET}")

        elif cmd == "s":
            keyword = input(f"🔍 {C_BOLD}New keyword:{C_RESET} ").strip()
            print(f"\n📡 Fetching jobs for '{C_CYAN}{keyword}{C_RESET}'...\n")
            new_jobs = scrape_jobs(keyword)
            if not new_jobs:
                print(f"{C_RED}❌ No jobs found.{C_RESET}")
            else:
                added = save_jobs(new_jobs)
                jobs = load_tracker() # Reload from DB to get dates and combined set
                print(f"{C_GREEN}✅ Found {len(new_jobs)} jobs ({added} new).{C_RESET}")

        elif cmd == "o" and len(parts) > 1:
            try:
                idx = int(parts[1]) - 1
                open_job_url(jobs, idx)
            except (ValueError, IndexError):
                print(f"  {C_RED}⚠ Invalid job number.{C_RESET}")

        elif cmd == "d" and len(parts) > 1:
            try:
                idx = int(parts[1]) - 1
                show_job_details(jobs, idx)
            except (ValueError, IndexError):
                print(f"  {C_RED}⚠ Invalid job number.{C_RESET}")

        elif cmd.isdigit() and len(parts) > 1:
            idx = int(cmd) - 1
            status = parts[1]
            try:
                jobs = update_status(jobs, idx, status)
                print(f"  {C_GREEN}✅ Status updated!{C_RESET}")
            except (IndexError, ValueError) as e:
                print(f"  {C_RED}⚠ {e}{C_RESET}")

        else:
            print(f"  {C_GRAY}❓ Unknown command. Try 'o 1', '1 applied', or 'q'.{C_RESET}")


if __name__ == "__main__":
    main()