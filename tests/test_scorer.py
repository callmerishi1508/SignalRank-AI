"""
Tests for the scoring engine.

Validates that our scorer correctly:
1. Ranks ideal candidates above keyword stuffers
2. Penalizes consulting-only careers
3. Penalizes wrong-domain candidates (HR, Content, etc.)
4. Downweights inactive candidates
5. Detects CV/robotics specialists
6. Produces valid score ranges
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.scorer import score_candidate, _clamp
from backend.jd_parser import JD_PROFILE
from backend.honeypot import detect_honeypot


def make_ideal_ml_engineer():
    return {
        "candidate_id": "CAND_TEST_001",
        "profile": {
            "anonymized_name": "Test Candidate",
            "headline": "Senior ML Engineer | FAISS | Vector Search | NLP",
            "summary": "Senior ML engineer with 7 years building production retrieval and ranking systems. Expert in sentence-transformers, FAISS, and hybrid search.",
            "location": "Pune",
            "country": "India",
            "years_of_experience": 7.0,
            "current_title": "Senior ML Engineer",
            "current_company": "Flipkart",
            "current_company_size": "5001-10000",
            "current_industry": "Technology",
        },
        "career_history": [
            {
                "company": "Flipkart",
                "title": "ML Engineer",
                "start_date": "2019-06-01",
                "end_date": None,
                "duration_months": 60,
                "is_current": True,
                "industry": "Technology",
                "company_size": "5001-10000",
                "description": "Built production vector search using FAISS serving 10M queries/day. Deployed hybrid BM25+dense retrieval. Set up A/B testing framework. Reduced p95 latency by 60%. NDCG@10 improved from 0.42 to 0.71.",
            },
            {
                "company": "Swiggy",
                "title": "Data Scientist",
                "start_date": "2017-06-01",
                "end_date": "2019-05-31",
                "duration_months": 24,
                "is_current": False,
                "industry": "Technology",
                "company_size": "1001-5000",
                "description": "Built recommendation system for restaurant ranking. Deployed to 2M users. Evaluated using NDCG@10.",
            },
        ],
        "education": [{"institution": "IIT Bombay", "degree": "B.Tech", "field_of_study": "Computer Science",
                        "start_year": 2013, "end_year": 2017, "grade": "8.5/10", "tier": "tier_1"}],
        "skills": [
            {"name": "FAISS", "proficiency": "expert", "endorsements": 85, "duration_months": 36},
            {"name": "sentence-transformers", "proficiency": "expert", "endorsements": 60, "duration_months": 30},
            {"name": "Python", "proficiency": "expert", "endorsements": 150, "duration_months": 84},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 70, "duration_months": 36},
            {"name": "Elasticsearch", "proficiency": "advanced", "endorsements": 50, "duration_months": 24},
            {"name": "A/B Testing", "proficiency": "intermediate", "endorsements": 30, "duration_months": 36},
            {"name": "NDCG", "proficiency": "intermediate", "endorsements": 25, "duration_months": 48},
            {"name": "RAG", "proficiency": "advanced", "endorsements": 40, "duration_months": 18},
        ],
        "redrob_signals": {
            "profile_completeness_score": 92,
            "signup_date": "2024-01-01",
            "last_active_date": "2026-06-22",
            "open_to_work_flag": True,
            "profile_views_received_30d": 45,
            "applications_submitted_30d": 3,
            "recruiter_response_rate": 0.88,
            "avg_response_time_hours": 4.0,
            "skill_assessment_scores": {"Python": 92, "Machine Learning": 88},
            "connection_count": 350,
            "endorsements_received": 180,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 35, "max": 55},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 78,
            "search_appearance_30d": 35,
            "saved_by_recruiters_30d": 8,
            "interview_completion_rate": 0.90,
            "offer_acceptance_rate": 0.75,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


def make_keyword_stuffer_hr():
    return {
        "candidate_id": "CAND_TEST_002",
        "profile": {
            "anonymized_name": "HR Candidate",
            "headline": "HR Manager | AI Enthusiast | Python | Machine Learning | NLP",
            "summary": "HR manager with interest in AI. Has done online courses in ML.",
            "location": "Mumbai",
            "country": "India",
            "years_of_experience": 6.0,
            "current_title": "HR Manager",
            "current_company": "BigCorp",
            "current_company_size": "1001-5000",
            "current_industry": "Human Resources",
        },
        "career_history": [
            {
                "company": "BigCorp",
                "title": "HR Manager",
                "start_date": "2020-01-01",
                "end_date": None,
                "duration_months": 78,
                "is_current": True,
                "industry": "Human Resources",
                "company_size": "1001-5000",
                "description": "Managed hiring, HR ops, and employee engagement. Used Excel and HRIS tools.",
            }
        ],
        "education": [{"institution": "Mumbai University", "degree": "B.Com", "field_of_study": "Commerce",
                        "start_year": 2016, "end_year": 2019, "grade": None, "tier": "tier_3"}],
        "skills": [
            {"name": "Python", "proficiency": "beginner", "endorsements": 5, "duration_months": 3},
            {"name": "Machine Learning", "proficiency": "beginner", "endorsements": 3, "duration_months": 2},
            {"name": "AI", "proficiency": "intermediate", "endorsements": 8, "duration_months": 6},
            {"name": "NLP", "proficiency": "beginner", "endorsements": 2, "duration_months": 2},
            {"name": "FAISS", "proficiency": "beginner", "endorsements": 1, "duration_months": 1},
            {"name": "Communication", "proficiency": "expert", "endorsements": 120, "duration_months": 72},
            {"name": "Recruitment", "proficiency": "expert", "endorsements": 100, "duration_months": 72},
            {"name": "Excel", "proficiency": "expert", "endorsements": 80, "duration_months": 72},
            {"name": "embeddings", "proficiency": "beginner", "endorsements": 1, "duration_months": 1},
        ],
        "redrob_signals": {
            "profile_completeness_score": 85,
            "signup_date": "2024-03-01",
            "last_active_date": "2026-06-15",
            "open_to_work_flag": True,
            "profile_views_received_30d": 20,
            "applications_submitted_30d": 5,
            "recruiter_response_rate": 0.76,
            "avg_response_time_hours": 6.0,
            "skill_assessment_scores": {},
            "connection_count": 200,
            "endorsements_received": 100,
            "notice_period_days": 45,
            "expected_salary_range_inr_lpa": {"min": 15, "max": 25},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": False,
            "github_activity_score": -1,
            "search_appearance_30d": 10,
            "saved_by_recruiters_30d": 2,
            "interview_completion_rate": 0.80,
            "offer_acceptance_rate": -1,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


def make_inactive_strong():
    cand = make_ideal_ml_engineer()
    cand["candidate_id"] = "CAND_TEST_003"
    cand["redrob_signals"]["last_active_date"] = "2025-10-01"   # 8+ months ago
    cand["redrob_signals"]["open_to_work_flag"] = False
    cand["redrob_signals"]["recruiter_response_rate"] = 0.08
    return cand


def make_consulting_ml():
    cand = make_ideal_ml_engineer()
    cand["candidate_id"] = "CAND_TEST_004"
    cand["career_history"][0]["company"] = "TCS"
    cand["career_history"][1]["company"] = "Infosys"
    cand["profile"]["current_company"] = "TCS"
    return cand


def make_cv_specialist():
    return {
        "candidate_id": "CAND_TEST_005",
        "profile": {
            "anonymized_name": "CV Specialist",
            "headline": "Computer Vision Engineer | YOLO | OpenCV | Object Detection",
            "summary": "Expert in real-time object detection and image segmentation.",
            "location": "Bangalore",
            "country": "India",
            "years_of_experience": 6.0,
            "current_title": "Computer Vision Engineer",
            "current_company": "AutoVision",
            "current_company_size": "201-500",
            "current_industry": "Automotive",
        },
        "career_history": [
            {"company": "AutoVision", "title": "Computer Vision Engineer", "start_date": "2020-01-01",
             "end_date": None, "duration_months": 78, "is_current": True, "industry": "Automotive",
             "company_size": "201-500",
             "description": "Real-time object detection using YOLO v8. Deployed autonomous driving perception. CNN optimization."}
        ],
        "education": [{"institution": "VJTI", "degree": "B.Tech", "field_of_study": "Electronics",
                        "start_year": 2016, "end_year": 2020, "grade": None, "tier": "tier_2"}],
        "skills": [
            {"name": "Computer Vision", "proficiency": "expert", "endorsements": 90, "duration_months": 72},
            {"name": "YOLO", "proficiency": "expert", "endorsements": 70, "duration_months": 60},
            {"name": "OpenCV", "proficiency": "expert", "endorsements": 80, "duration_months": 72},
            {"name": "Object Detection", "proficiency": "expert", "endorsements": 85, "duration_months": 60},
            {"name": "Image Classification", "proficiency": "advanced", "endorsements": 60, "duration_months": 48},
            {"name": "CNN", "proficiency": "advanced", "endorsements": 65, "duration_months": 60},
            {"name": "Python", "proficiency": "advanced", "endorsements": 100, "duration_months": 72},
        ],
        "redrob_signals": {
            "profile_completeness_score": 88,
            "signup_date": "2024-06-01",
            "last_active_date": "2026-06-20",
            "open_to_work_flag": True,
            "profile_views_received_30d": 30,
            "applications_submitted_30d": 4,
            "recruiter_response_rate": 0.80,
            "avg_response_time_hours": 5.0,
            "skill_assessment_scores": {},
            "connection_count": 250,
            "endorsements_received": 150,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 20, "max": 35},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 55,
            "search_appearance_30d": 20,
            "saved_by_recruiters_30d": 5,
            "interview_completion_rate": 0.85,
            "offer_acceptance_rate": -1,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_ideal_candidate_scores_high():
    candidate = make_ideal_ml_engineer()
    score, _ = score_candidate(candidate, JD_PROFILE)
    assert score >= 0.70, f"Ideal ML engineer should score >= 0.70, got {score:.4f}"
    print(f"PASS: ideal ML engineer scored {score:.4f}")


def test_keyword_stuffer_scores_low():
    candidate = make_keyword_stuffer_hr()
    score, _ = score_candidate(candidate, JD_PROFILE)
    assert score <= 0.40, f"Keyword-stuffer HR manager should score <= 0.40, got {score:.4f}"
    print(f"PASS: keyword stuffer scored {score:.4f}")


def test_ideal_outranks_keyword_stuffer():
    ideal = make_ideal_ml_engineer()
    stuffer = make_keyword_stuffer_hr()
    score_ideal, _ = score_candidate(ideal, JD_PROFILE)
    score_stuffer, _ = score_candidate(stuffer, JD_PROFILE)
    assert score_ideal > score_stuffer, (
        f"Ideal ({score_ideal:.4f}) should beat keyword stuffer ({score_stuffer:.4f})"
    )
    print(f"PASS: ideal ({score_ideal:.4f}) > stuffer ({score_stuffer:.4f})")


def test_inactive_candidate_penalized():
    active = make_ideal_ml_engineer()
    inactive = make_inactive_strong()
    score_active, _ = score_candidate(active, JD_PROFILE)
    score_inactive, _ = score_candidate(inactive, JD_PROFILE)
    assert score_active > score_inactive, (
        f"Active ({score_active:.4f}) should beat inactive ({score_inactive:.4f})"
    )
    print(f"PASS: active ({score_active:.4f}) > inactive ({score_inactive:.4f})")


def test_consulting_only_penalized():
    ideal = make_ideal_ml_engineer()
    consulting = make_consulting_ml()
    score_ideal, _ = score_candidate(ideal, JD_PROFILE)
    score_consulting, comp_consulting = score_candidate(consulting, JD_PROFILE)
    assert score_ideal > score_consulting, (
        f"Ideal ({score_ideal:.4f}) should beat consulting-only ({score_consulting:.4f})"
    )
    assert "consulting-only career" in comp_consulting.get("penalty_reasons", []), \
        "Consulting-only candidate should have penalty reason flagged"
    print(f"PASS: ideal ({score_ideal:.4f}) > consulting ({score_consulting:.4f})")


def test_cv_specialist_penalized():
    ideal = make_ideal_ml_engineer()
    cv = make_cv_specialist()
    score_ideal, _ = score_candidate(ideal, JD_PROFILE)
    score_cv, components_cv = score_candidate(cv, JD_PROFILE)
    assert score_ideal > score_cv, (
        f"Ideal ({score_ideal:.4f}) should beat CV specialist ({score_cv:.4f})"
    )
    print(f"PASS: ideal ({score_ideal:.4f}) > CV specialist ({score_cv:.4f})")


def test_scores_in_valid_range():
    candidates = [
        make_ideal_ml_engineer(),
        make_keyword_stuffer_hr(),
        make_inactive_strong(),
        make_consulting_ml(),
        make_cv_specialist(),
    ]
    for c in candidates:
        score, _ = score_candidate(c, JD_PROFILE)
        assert 0.0 <= score <= 1.0, f"{c['candidate_id']}: score {score} out of range [0,1]"
    print("PASS: all scores in [0, 1]")


def test_honeypot_detection_overlapping_jobs():
    candidate = {
        "candidate_id": "CAND_HP_001",
        "profile": {"current_title": "ML Eng", "years_of_experience": 8},
        "career_history": [
            {"company": "A", "title": "ML Eng", "start_date": "2019-01-01", "end_date": "2023-01-01",
             "duration_months": 48, "is_current": False, "industry": "Tech", "company_size": "201-500",
             "description": "ML work."},
            {"company": "B", "title": "ML Eng", "start_date": "2019-06-01", "end_date": None,
             "duration_months": 84, "is_current": True, "industry": "Tech", "company_size": "201-500",
             "description": "More ML work."},
        ],
        "education": [{"institution": "IIT", "degree": "B.Tech", "field_of_study": "CS",
                        "start_year": 2011, "end_year": 2015, "grade": None, "tier": "tier_1"}],
        "skills": [{"name": "Python", "proficiency": "advanced", "endorsements": 50, "duration_months": 60}],
        "redrob_signals": {
            "profile_completeness_score": 85, "signup_date": "2024-01-01",
            "last_active_date": "2026-06-20", "open_to_work_flag": True,
            "profile_views_received_30d": 20, "applications_submitted_30d": 3,
            "recruiter_response_rate": 0.80, "avg_response_time_hours": 5,
            "skill_assessment_scores": {}, "connection_count": 200, "endorsements_received": 100,
            "notice_period_days": 30, "expected_salary_range_inr_lpa": {"min": 20, "max": 35},
            "preferred_work_mode": "hybrid", "willing_to_relocate": True,
            "github_activity_score": 50, "search_appearance_30d": 15,
            "saved_by_recruiters_30d": 3, "interview_completion_rate": 0.8,
            "offer_acceptance_rate": -1, "verified_email": True, "verified_phone": True,
            "linkedin_connected": True,
        },
    }
    is_hp, flags = detect_honeypot(candidate)
    assert is_hp, f"Should detect honeypot with overlapping jobs, flags: {flags}"
    print(f"PASS: honeypot detected with {len(flags)} flags")


def test_score_deterministic():
    """Same input must always produce the same output."""
    candidate = make_ideal_ml_engineer()
    score1, _ = score_candidate(candidate, JD_PROFILE)
    score2, _ = score_candidate(candidate, JD_PROFILE)
    assert score1 == score2, f"Score not deterministic: {score1} vs {score2}"
    print(f"PASS: score is deterministic ({score1:.6f})")


def run_all_tests():
    tests = [
        test_ideal_candidate_scores_high,
        test_keyword_stuffer_scores_low,
        test_ideal_outranks_keyword_stuffer,
        test_inactive_candidate_penalized,
        test_consulting_only_penalized,
        test_cv_specialist_penalized,
        test_scores_in_valid_range,
        test_honeypot_detection_overlapping_jobs,
        test_score_deterministic,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
