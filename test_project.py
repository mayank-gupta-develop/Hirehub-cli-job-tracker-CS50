import pytest
import os
from unittest.mock import patch, MagicMock
from project import clean_text, filter_jobs, scrape_jobs, save_jobs, update_status, init_db, load_tracker, get_status_label, clear_tracker


# ─────────────────────────────────────────────
#  Tests for clean_text()
# ─────────────────────────────────────────────

def test_clean_text_removes_html_tags():
    assert clean_text("<b>Software Engineer</b>") == "Software Engineer"

def test_clean_text_collapses_whitespace():
    assert clean_text("Backend   Developer\n  Remote") == "Backend Developer Remote"

def test_clean_text_empty_string():
    assert clean_text("") == ""

def test_clean_text_none_input():
    assert clean_text(None) == ""

def test_clean_text_nested_tags():
    assert clean_text("<div><p>Hello <span>World</span></p></div>") == "Hello World"

def test_clean_text_no_html():
    assert clean_text("  Hello World  ") == "Hello World"


# ─────────────────────────────────────────────
#  Tests for filter_jobs()
# ─────────────────────────────────────────────

SAMPLE_JOBS = [
    {"title": "Backend Engineer", "company": "Vercel", "location": "Remote", "url": "", "source": "RemoteOK", "status": ""},
    {"title": "Frontend Developer", "company": "Shopify", "location": "Remote", "url": "", "source": "WWR", "status": ""},
    {"title": "Node.js Developer", "company": "GitHub", "location": "Remote", "url": "", "source": "RemoteOK", "status": ""},
    {"title": "Python Engineer", "company": "Stripe", "location": "Remote", "url": "", "source": "WWR", "status": ""},
]

def test_filter_jobs_by_title_keyword():
    # 'python' should match 'Python Engineer'
    result = filter_jobs(SAMPLE_JOBS, "python")
    assert len(result) == 1
    assert result[0]["title"] == "Python Engineer"

def test_filter_jobs_token_matching():
    # 'frontend engineer' has two tokens: 'frontend' and 'engineer'
    # 'Frontend Developer' matches 'frontend' token in title -> score 20
    # 'Backend Engineer' matches 'engineer' token in title -> score 20
    # 'Python Engineer' matches 'engineer' token in title -> score 20
    result = filter_jobs(SAMPLE_JOBS, "frontend engineer")
    titles = [r["title"] for r in result]
    assert "Frontend Developer" in titles
    assert "Backend Engineer" in titles
    assert "Python Engineer" in titles

def test_filter_jobs_case_insensitive():
    result = filter_jobs(SAMPLE_JOBS, "NODE")
    assert len(result) == 1
    assert "Node.js" in result[0]["title"]

def test_filter_jobs_empty_keyword_returns_all():
    result = filter_jobs(SAMPLE_JOBS, "")
    assert len(result) == len(SAMPLE_JOBS)

def test_filter_jobs_no_match_returns_empty():
    result = filter_jobs(SAMPLE_JOBS, "java")
    assert result == []

def test_filter_jobs_empty_list():
    result = filter_jobs([], "python")
    assert result == []


# ─────────────────────────────────────────────
#  Tests for scrape_jobs()
# ─────────────────────────────────────────────

def test_scrape_jobs_returns_list():
    """scrape_jobs() should always return a list, even on network failure (falls back to demo data)."""
    with patch("project.requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")
        result = scrape_jobs("python")
    assert isinstance(result, list)

def test_scrape_jobs_filters_by_keyword():
    """scrape_jobs() should only return jobs matching the keyword from Remotive API."""
    mock_json_data = {
        "jobs": [
            {"title": "Python Engineer", "company_name": "TestCo", "candidate_required_location": "Remote", "url": "https://example.com"},
            {"title": "Java Developer",  "company_name": "OtherCo", "candidate_required_location": "Remote", "url": "https://example.com"},
        ]
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_json_data
    mock_response.raise_for_status = MagicMock()

    with patch("project.requests.get") as mock_get:
        # First call → Remotive succeeds, second call → RemoteOK skipped, third call -> Arbeitnow skipped
        mock_get.side_effect = [mock_response, Exception("skip RemoteOK"), Exception("skip Arbeitnow")]
        result = scrape_jobs("python")

    assert len(result) == 1
    assert result[0]["title"] == "Python Engineer"

def test_scrape_jobs_returns_expected_keys():
    """Each job dict from scrape_jobs() must have all required keys."""
    mock_json_data = {
        "jobs": [
            {"title": "Backend Dev", "company_name": "ACME", "candidate_required_location": "Remote", "url": "https://example.com"},
        ]
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_json_data
    mock_response.raise_for_status = MagicMock()

    with patch("project.requests.get") as mock_get:
        mock_get.side_effect = [mock_response, Exception("skip RemoteOK"), Exception("skip Arbeitnow")]
        result = scrape_jobs("backend")

    required_keys = {"title", "company", "location", "url", "source", "status"}
    for job in result:
        assert required_keys.issubset(job.keys())


# ─────────────────────────────────────────────
#  Tests for update_status() & Database
# ─────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Provides a fresh temporary database for testing."""
    db = "test_jobs.db"
    if os.path.exists(db):
        os.remove(db)
    init_db(db)
    yield db
    if os.path.exists(db):
        os.remove(db)

def get_sample_jobs():
    return [
        {"title": "Backend Engineer", "company": "Vercel", "location": "Remote", "url": "https://vercel.com", "source": "API", "status": ""},
        {"title": "Python Engineer",  "company": "Stripe", "location": "Remote", "url": "https://stripe.com", "source": "API", "status": ""},
    ]

def test_update_status_applied(mock_db):
    jobs = get_sample_jobs()
    save_jobs(jobs, mock_db)
    updated = update_status(jobs, 0, "applied", mock_db)
    assert updated[0]["status"] == "applied"
    
    # Verify persistence
    db_jobs = load_tracker(mock_db)
    assert db_jobs[0]["status"] == "applied"
    assert "date" in db_jobs[0]  # Verify date is present

def test_update_status_saved(mock_db):
    jobs = get_sample_jobs()
    save_jobs(jobs, mock_db)
    updated = update_status(jobs, 1, "saved", mock_db)
    assert updated[1]["status"] == "saved"

def test_update_status_ignored(mock_db):
    jobs = get_sample_jobs()
    save_jobs(jobs, mock_db)
    updated = update_status(jobs, 0, "ignored", mock_db)
    assert updated[0]["status"] == "ignored"

def test_update_status_invalid_status_raises_value_error(mock_db):
    jobs = get_sample_jobs()
    with pytest.raises(ValueError):
        update_status(jobs, 0, "maybe", mock_db)

def test_update_status_invalid_index_raises_index_error(mock_db):
    jobs = get_sample_jobs()
    with pytest.raises(IndexError):
        update_status(jobs, 99, "applied", mock_db)

def test_update_status_negative_index_raises_index_error(mock_db):
    jobs = get_sample_jobs()
    with pytest.raises(IndexError):
        update_status(jobs, -1, "saved", mock_db)


def test_save_and_load_tracker(mock_db):
    jobs = get_sample_jobs()
    save_jobs(jobs, mock_db)
    loaded = load_tracker(mock_db)
    assert len(loaded) == 2
    assert loaded[0]["title"] == "Backend Engineer"


# ─────────────────────────────────────────────
#  Tests for Utility & CLI UI
# ─────────────────────────────────────────────

def test_get_status_label():
    # Labels include ANSI color codes, so we check for substrings
    assert "Applied" in get_status_label("applied")
    assert "Saved" in get_status_label("saved")
    assert "Ignored" in get_status_label("ignored")
    assert "New" in get_status_label("")

def test_open_job_url_out_of_range():
    with pytest.raises(IndexError):
        from project import open_job_url
        open_job_url([], 0)

def test_show_job_details_out_of_range():
    with pytest.raises(IndexError):
        from project import show_job_details
        show_job_details([], 0)

def test_clear_tracker(mock_db):
    jobs = get_sample_jobs()
    save_jobs(jobs, mock_db)
    assert len(load_tracker(mock_db)) == 2
    clear_tracker(mock_db)
    assert len(load_tracker(mock_db)) == 0