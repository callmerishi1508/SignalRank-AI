#!/usr/bin/env python3
"""
Generate synthetic candidates.jsonl for pipeline testing.

Generates a realistic mix including:
  - True positives: Senior ML/AI engineers with embeddings/retrieval experience
  - Keyword stuffers: HR managers, Content writers with AI skill keywords
  - Consulting-only: Real ML skills but TCS/Infosys career
  - Inactive perfect-paper: Strong ML but haven't logged in for 9 months
  - CV/robotics: Image recognition specialists with no NLP
  - Honeypots: Profiles with impossible timelines or perfect-everything signals
  - Mid-tier: Data scientists with partial ML fit
  - Juniors: Under-experienced but promising
  - Adjacent: Software engineers who've done some ML

Usage:
    python scripts/generate_test_data.py --n 5000 --out data/raw/candidates.jsonl
"""

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path


SEED = 42
random.seed(SEED)

REFERENCE_DATE = date(2026, 6, 25)


def _rand_date(years_back_min: int, years_back_max: int) -> str:
    days = random.randint(years_back_min * 365, years_back_max * 365)
    d = REFERENCE_DATE - timedelta(days=days)
    return d.isoformat()


def _rand_date_after(start_str: str, min_months: int, max_months: int) -> str:
    start = date.fromisoformat(start_str)
    days = random.randint(min_months * 30, max_months * 30)
    return (start + timedelta(days=days)).isoformat()


def _company_size() -> str:
    return random.choice([
        "11-50", "51-200", "201-500", "501-1000",
        "1001-5000", "5001-10000", "10001+"
    ])


def _make_skill(name: str, proficiency: str, endorsements: int, duration: int) -> dict:
    return {
        "name": name,
        "proficiency": proficiency,
        "endorsements": endorsements,
        "duration_months": duration,
    }


def _make_job(company: str, title: str, start: str, end: str, industry: str,
              description: str, is_current: bool = False) -> dict:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end) if not is_current else REFERENCE_DATE
    duration_months = max(1, int((end_d - start_d).days / 30.44))
    return {
        "company": company,
        "title": title,
        "start_date": start,
        "end_date": None if is_current else end,
        "duration_months": duration_months,
        "is_current": is_current,
        "industry": industry,
        "company_size": _company_size(),
        "description": description,
    }


def _redrob_signals(
    last_active_days_ago: int = 3,
    open_to_work: bool = True,
    response_rate: float = 0.85,
    notice_period: int = 30,
    github: float = 75.0,
    interview_rate: float = 0.90,
    offer_rate: float = 0.80,
    profile_completeness: float = 92.0,
) -> dict:
    last_active = (REFERENCE_DATE - timedelta(days=last_active_days_ago)).isoformat()
    signup = (REFERENCE_DATE - timedelta(days=random.randint(200, 800))).isoformat()
    return {
        "profile_completeness_score": profile_completeness,
        "signup_date": signup,
        "last_active_date": last_active,
        "open_to_work_flag": open_to_work,
        "profile_views_received_30d": random.randint(10, 80),
        "applications_submitted_30d": random.randint(1, 8),
        "recruiter_response_rate": round(response_rate, 2),
        "avg_response_time_hours": round(random.uniform(1, 24), 1),
        "skill_assessment_scores": {
            "Python": round(random.uniform(75, 98), 1),
            "Machine Learning": round(random.uniform(70, 95), 1),
        },
        "connection_count": random.randint(100, 800),
        "endorsements_received": random.randint(20, 200),
        "notice_period_days": notice_period,
        "expected_salary_range_inr_lpa": {
            "min": random.choice([18, 22, 25, 30]),
            "max": random.choice([35, 40, 45, 55]),
        },
        "preferred_work_mode": random.choice(["hybrid", "remote", "flexible"]),
        "willing_to_relocate": random.choice([True, True, False]),
        "github_activity_score": round(github, 1),
        "search_appearance_30d": random.randint(5, 50),
        "saved_by_recruiters_30d": random.randint(0, 15),
        "interview_completion_rate": round(interview_rate, 2),
        "offer_acceptance_rate": round(offer_rate, 2),
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True,
    }


# ─── Archetype factories ─────────────────────────────────────────────────────

def make_true_positive(cid: str) -> dict:
    """Senior ML/AI/Search engineer — should rank high."""
    yoe = random.uniform(5.5, 9.0)
    title_options = [
        "Senior ML Engineer", "Senior AI Engineer", "Applied ML Engineer",
        "NLP Engineer", "Search Engineer", "Ranking Engineer",
        "Applied Scientist", "Research Engineer - ML",
    ]
    current_title = random.choice(title_options)
    companies = ["Flipkart", "Swiggy", "Zomato", "Cred", "Razorpay", "Meesho",
                 "ShareChat", "Juspay", "Clevertap", "Springworks"]
    company = random.choice(companies)
    start1 = _rand_date(9, 11)
    end1 = _rand_date_after(start1, 24, 36)
    start2 = _rand_date_after(end1, 1, 3)
    end2 = _rand_date_after(start2, 24, 42)
    start3 = _rand_date_after(end2, 1, 3)

    location = random.choice(["Pune", "Noida", "Bangalore", "Hyderabad", "Mumbai"])

    skills = [
        _make_skill("FAISS", "expert", random.randint(40, 120), 36),
        _make_skill("sentence-transformers", "expert", random.randint(30, 90), 30),
        _make_skill("Python", "expert", random.randint(80, 200), int(yoe * 12)),
        _make_skill("Elasticsearch", "advanced", random.randint(20, 80), 24),
        _make_skill("NLP", "advanced", random.randint(25, 90), 30),
        _make_skill("PyTorch", "advanced", random.randint(30, 100), 28),
        _make_skill("RAG", "advanced", random.randint(10, 50), 18),
        _make_skill("NDCG Evaluation", "intermediate", random.randint(10, 40), 24),
        _make_skill("A/B Testing", "intermediate", random.randint(15, 60), 20),
        _make_skill("Scikit-learn", "expert", random.randint(50, 150), int(yoe * 10)),
    ]

    career = [
        _make_job(
            "TechCorp India", "Data Scientist",
            start1, end1, "Technology",
            "Built recommendation engine using collaborative filtering. Deployed to 2M users. Evaluated using NDCG@10.",
        ),
        _make_job(
            company, "ML Engineer",
            start2, end2, "Technology",
            "Designed and deployed production vector search using FAISS. Reduced retrieval latency from 200ms to 18ms at 10M QPS. Implemented hybrid BM25+dense retrieval. Set up A/B testing framework.",
        ),
        _make_job(
            random.choice(["Redrob", "Ola", "Groww", "CRED", "Urban Company"]),
            current_title, start3, None, "Technology",
            "Owning the ML ranking layer for candidate-JD matching. Building embedding-based retrieval with sentence-transformers. Designed offline NDCG evaluation pipeline. Mentoring 2 junior ML engineers.",
            is_current=True,
        ),
    ]

    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": f"{current_title} | Embeddings | Vector Search | Ranking Systems",
            "summary": f"Senior ML engineer with {yoe:.1f} years building production retrieval and ranking systems. Expert in dense embeddings, FAISS-based vector search, and LLM-based reranking. Strong track record of shipping ranking improvements with measurable recruiter-engagement gains.",
            "location": location,
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": current_title,
            "current_company": career[-1]["company"],
            "current_company_size": "51-200",
            "current_industry": "Technology",
        },
        "career_history": career,
        "education": [{
            "institution": random.choice(["IIT Bombay", "IIT Delhi", "BITS Pilani", "NIT Trichy", "IIIT Hyderabad"]),
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "start_year": int(REFERENCE_DATE.year - yoe - 4),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": "8.5/10",
            "tier": "tier_1",
        }],
        "skills": skills,
        "certifications": [{"name": "AWS Machine Learning Specialty", "issuer": "Amazon", "year": 2024}],
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(1, 14),
            open_to_work=True,
            response_rate=random.uniform(0.70, 0.95),
            notice_period=random.randint(15, 45),
            github=random.uniform(60, 95),
        ),
    }


def make_keyword_stuffer(cid: str) -> dict:
    """HR/Content/Marketing person with lots of AI keywords — should rank LOW."""
    wrong_titles = ["HR Manager", "Content Writer", "Marketing Manager",
                    "Graphic Designer", "Operations Manager", "Accountant",
                    "Sales Executive", "Project Manager"]
    current_title = random.choice(wrong_titles)
    yoe = random.uniform(4.0, 12.0)

    skills = [
        _make_skill("Python", "intermediate", random.randint(5, 30), 6),
        _make_skill("Machine Learning", "beginner", random.randint(3, 20), 3),
        _make_skill("AI", "intermediate", random.randint(5, 25), 6),
        _make_skill("NLP", "beginner", random.randint(2, 15), 2),
        _make_skill("Data Analysis", "intermediate", random.randint(10, 50), 24),
        _make_skill("Excel", "expert", random.randint(30, 100), int(yoe * 10)),
        _make_skill("Communication", "expert", random.randint(50, 150), int(yoe * 12)),
        _make_skill("Recruitment", "expert", random.randint(40, 120), int(yoe * 10)),
    ]

    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": f"{current_title} | AI Enthusiast | Python | Machine Learning",
            "summary": "Experienced professional with expertise in operations and people management. Learning Python and AI on the side. Certified in multiple HR platforms.",
            "location": random.choice(["Mumbai", "Delhi", "Chennai", "Kolkata"]),
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": current_title,
            "current_company": random.choice(["BigCorp", "MegaFirm", "IndiaInc"]),
            "current_company_size": "1001-5000",
            "current_industry": "Human Resources",
        },
        "career_history": [
            _make_job(
                "BigCorp", current_title,
                _rand_date(int(yoe) + 1, int(yoe) + 2),
                None, "Human Resources",
                f"Managing {current_title.lower()} activities. Coordinated with cross-functional teams. Used Excel and data tools to track metrics.",
                is_current=True,
            )
        ],
        "education": [{
            "institution": "Mumbai University",
            "degree": "B.Com",
            "field_of_study": "Commerce",
            "start_year": int(REFERENCE_DATE.year - yoe - 3),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": None,
            "tier": "tier_3",
        }],
        "skills": skills,
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(2, 20),
            open_to_work=True,
            response_rate=random.uniform(0.50, 0.90),
            notice_period=random.randint(30, 90),
            github=-1,
        ),
    }


def make_consulting_ml(cid: str) -> dict:
    """Real ML skills but entire career at TCS/Infosys/Wipro — should be penalized."""
    yoe = random.uniform(5.0, 9.0)
    consulting_firms = ["TCS", "Infosys", "Wipro", "Cognizant", "Accenture"]
    skills = [
        _make_skill("Python", "advanced", random.randint(30, 100), int(yoe * 10)),
        _make_skill("Machine Learning", "advanced", random.randint(25, 80), int(yoe * 8)),
        _make_skill("TensorFlow", "intermediate", random.randint(15, 60), 24),
        _make_skill("NLP", "intermediate", random.randint(10, 40), 18),
        _make_skill("SQL", "expert", random.randint(40, 120), int(yoe * 12)),
        _make_skill("Pandas", "advanced", random.randint(30, 90), int(yoe * 10)),
    ]
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": "ML Engineer | Python | TensorFlow | NLP",
            "summary": f"ML engineer with {yoe:.1f} years of experience at leading IT services firms. Delivered ML solutions for banking and insurance clients.",
            "location": random.choice(["Chennai", "Pune", "Hyderabad"]),
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": "Senior ML Engineer",
            "current_company": random.choice(consulting_firms),
            "current_company_size": "10001+",
            "current_industry": "Information Technology",
        },
        "career_history": [
            _make_job(
                random.choice(consulting_firms), "ML Engineer",
                _rand_date(int(yoe) + 1, int(yoe) + 2), None,
                "Information Technology",
                "Developed ML models for client projects. Text classification and sentiment analysis. Deployed on client cloud environments.",
                is_current=True,
            )
        ],
        "education": [{
            "institution": "Anna University",
            "degree": "B.E.",
            "field_of_study": "Computer Science",
            "start_year": int(REFERENCE_DATE.year - yoe - 4),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": "7.8/10",
            "tier": "tier_2",
        }],
        "skills": skills,
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(5, 30),
            open_to_work=True,
            response_rate=random.uniform(0.50, 0.80),
            notice_period=random.randint(60, 90),
            github=random.uniform(10, 40),
        ),
    }


def make_inactive_strong(cid: str) -> dict:
    """Strong ML/AI engineer but inactive — should be downweighted."""
    yoe = random.uniform(6.0, 10.0)
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": "Senior AI Engineer | FAISS | Vector Search | NLP",
            "summary": f"Senior AI engineer with {yoe:.1f} years in production ML. Built vector search systems at scale. Currently not actively job-seeking.",
            "location": "Bangalore",
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": "Senior AI Engineer",
            "current_company": "Ola",
            "current_company_size": "1001-5000",
            "current_industry": "Technology",
        },
        "career_history": [
            _make_job(
                "Ola", "Senior AI Engineer",
                _rand_date(int(yoe) + 1, int(yoe) + 2), None,
                "Technology",
                "Built production semantic search using FAISS serving 5M queries/day. Deployed hybrid retrieval system. Reduced p95 latency by 60%.",
                is_current=True,
            )
        ],
        "education": [{
            "institution": "IIT Madras",
            "degree": "M.Tech",
            "field_of_study": "AI",
            "start_year": int(REFERENCE_DATE.year - yoe - 2),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": None,
            "tier": "tier_1",
        }],
        "skills": [
            _make_skill("FAISS", "expert", 85, 30),
            _make_skill("Python", "expert", 150, int(yoe * 12)),
            _make_skill("NLP", "advanced", 60, 30),
            _make_skill("Vector Search", "expert", 70, 28),
        ],
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(200, 300),  # very inactive
            open_to_work=False,
            response_rate=random.uniform(0.05, 0.15),
            notice_period=random.randint(60, 90),
            github=random.uniform(20, 50),
        ),
    }


def make_cv_specialist(cid: str) -> dict:
    """Computer vision / robotics engineer without NLP/IR — should be penalized."""
    yoe = random.uniform(4.0, 8.0)
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": "Computer Vision Engineer | Object Detection | YOLO | OpenCV",
            "summary": f"CV engineer with {yoe:.1f} years in image recognition and autonomous systems. Strong background in YOLO, OpenCV, and real-time inference.",
            "location": random.choice(["Pune", "Bangalore", "Hyderabad"]),
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": "Computer Vision Engineer",
            "current_company": "AutoTech Innovations",
            "current_company_size": "201-500",
            "current_industry": "Automotive",
        },
        "career_history": [
            _make_job(
                "AutoTech Innovations", "Computer Vision Engineer",
                _rand_date(int(yoe) + 1, int(yoe) + 2), None,
                "Automotive",
                "Developed real-time object detection using YOLO v8. Deployed autonomous driving perception stack. Optimized CNN models for edge inference.",
                is_current=True,
            )
        ],
        "education": [{
            "institution": "VJTI Mumbai",
            "degree": "B.Tech",
            "field_of_study": "Electronics",
            "start_year": int(REFERENCE_DATE.year - yoe - 4),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": "8.1/10",
            "tier": "tier_2",
        }],
        "skills": [
            _make_skill("Computer Vision", "expert", 80, int(yoe * 12)),
            _make_skill("OpenCV", "expert", 90, int(yoe * 10)),
            _make_skill("YOLO", "advanced", 60, 30),
            _make_skill("Object Detection", "expert", 70, int(yoe * 10)),
            _make_skill("Image Classification", "advanced", 50, 24),
            _make_skill("CNN", "advanced", 65, 30),
            _make_skill("Python", "advanced", 100, int(yoe * 12)),
            _make_skill("TensorFlow", "intermediate", 40, 24),
        ],
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(3, 30),
            open_to_work=True,
            response_rate=random.uniform(0.60, 0.90),
        ),
    }


def make_honeypot(cid: str) -> dict:
    """Profile with impossible timeline — should be detected and scored near zero."""
    hp_type = random.choice(["overlapping_jobs", "future_graduation", "all_maxed"])

    if hp_type == "overlapping_jobs":
        start1 = "2020-01-15"
        end1 = "2023-06-30"
        start2 = "2021-03-01"  # overlaps with job 1 by >1 year
        return {
            "candidate_id": cid,
            "profile": {
                "anonymized_name": f"Candidate {cid}",
                "headline": "ML Engineer | Deep Learning | Python",
                "summary": "Experienced ML engineer with production experience.",
                "location": "Pune", "country": "India",
                "years_of_experience": 8.0,
                "current_title": "ML Engineer",
                "current_company": "TechCo",
                "current_company_size": "501-1000",
                "current_industry": "Technology",
            },
            "career_history": [
                _make_job("CompanyA", "ML Engineer", start1, end1, "Technology", "ML work at CompanyA."),
                _make_job("CompanyB", "Senior ML Engineer", start2, None, "Technology", "Led ML team.", is_current=True),
            ],
            "education": [{"institution": "IIT Bombay", "degree": "B.Tech", "field_of_study": "CS",
                           "start_year": 2012, "end_year": 2016, "grade": None, "tier": "tier_1"}],
            "skills": [_make_skill("Python", "expert", 150, 96), _make_skill("ML", "expert", 120, 84)],
            "redrob_signals": _redrob_signals(),
        }

    elif hp_type == "future_graduation":
        return {
            "candidate_id": cid,
            "profile": {
                "anonymized_name": f"Candidate {cid}",
                "headline": "ML Engineer",
                "summary": "ML engineer.",
                "location": "Delhi", "country": "India",
                "years_of_experience": 7.0,
                "current_title": "Senior ML Engineer",
                "current_company": "DataCo",
                "current_company_size": "201-500",
                "current_industry": "Technology",
            },
            "career_history": [
                _make_job("DataCo", "ML Engineer", "2017-06-01", None, "Technology",
                          "Production ML work.", is_current=True),
            ],
            "education": [{
                "institution": "Delhi University",
                "degree": "B.Tech",
                "field_of_study": "CS",
                "start_year": 2016,
                "end_year": 2024,  # graduated after career started
                "grade": None,
                "tier": "tier_2",
            }],
            "skills": [_make_skill("Python", "expert", 100, 84)],
            "redrob_signals": _redrob_signals(),
        }

    else:  # all_maxed
        return {
            "candidate_id": cid,
            "profile": {
                "anonymized_name": f"Candidate {cid}",
                "headline": "Perfect ML Engineer | Expert Everything",
                "summary": "Perfect candidate in every way.",
                "location": "Pune", "country": "India",
                "years_of_experience": 8.0,
                "current_title": "ML Engineer",
                "current_company": "BestCo",
                "current_company_size": "1001-5000",
                "current_industry": "Technology",
            },
            "career_history": [
                _make_job("BestCo", "ML Engineer", "2018-01-01", None, "Technology",
                          "Perfect work everywhere always.", is_current=True),
            ],
            "education": [{"institution": "IIT Delhi", "degree": "B.Tech", "field_of_study": "CS",
                           "start_year": 2014, "end_year": 2018, "grade": "10.0/10", "tier": "tier_1"}],
            "skills": [
                _make_skill(skill, "expert", 999, 96)
                for skill in ["Python", "FAISS", "NLP", "ML", "Deep Learning", "RAG"]
            ],
            "redrob_signals": {
                **_redrob_signals(),
                "profile_completeness_score": 100,
                "recruiter_response_rate": 1.0,
                "interview_completion_rate": 1.0,
                "offer_acceptance_rate": 1.0,
                "github_activity_score": 100,
            },
        }


def make_mid_tier_ds(cid: str) -> dict:
    """Data scientist with some ML fit but not specialized in retrieval."""
    yoe = random.uniform(3.0, 7.0)
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": "Data Scientist | ML | Python | SQL",
            "summary": f"Data scientist with {yoe:.1f} years in analytics and ML. Built classification and regression models. Some experience with NLP.",
            "location": random.choice(["Hyderabad", "Pune", "Bangalore", "Noida"]),
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": "Senior Data Scientist",
            "current_company": random.choice(["Myntra", "PayTM", "PolicyBazaar", "Naukri"]),
            "current_company_size": "1001-5000",
            "current_industry": "Technology",
        },
        "career_history": [
            _make_job(
                random.choice(["Naukri", "Quikr", "MakeMyTrip"]),
                "Data Scientist",
                _rand_date(int(yoe) + 1, int(yoe) + 2), None,
                "Technology",
                f"Built ML models for fraud detection and customer churn. Used sklearn, XGBoost. Some NLP for text classification. A/B tested recommendations.",
                is_current=True,
            )
        ],
        "education": [{
            "institution": random.choice(["NIT Warangal", "BITS Goa", "VIT Vellore"]),
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "start_year": int(REFERENCE_DATE.year - yoe - 4),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": "7.5/10",
            "tier": "tier_2",
        }],
        "skills": [
            _make_skill("Python", "advanced", random.randint(40, 120), int(yoe * 12)),
            _make_skill("Machine Learning", "advanced", random.randint(30, 90), int(yoe * 10)),
            _make_skill("SQL", "expert", random.randint(50, 150), int(yoe * 12)),
            _make_skill("Scikit-learn", "advanced", random.randint(30, 90), int(yoe * 10)),
            _make_skill("XGBoost", "intermediate", random.randint(20, 60), 24),
            _make_skill("NLP", "beginner", random.randint(5, 25), 12),
        ],
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(3, 45),
            open_to_work=random.choice([True, False]),
            response_rate=random.uniform(0.40, 0.80),
            notice_period=random.randint(30, 90),
            github=random.uniform(15, 55),
        ),
    }


def make_junior_strong(cid: str) -> dict:
    """Junior ML engineer 2-4 years, promising but below experience bar."""
    yoe = random.uniform(2.0, 4.0)
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": "Junior ML Engineer | NLP | Python | Hugging Face",
            "summary": f"ML engineer with {yoe:.1f} years. Strong NLP background. Built text ranking models. Eager to work on production retrieval systems.",
            "location": random.choice(["Noida", "Pune", "Bangalore"]),
            "country": "India",
            "years_of_experience": round(yoe, 1),
            "current_title": "ML Engineer",
            "current_company": random.choice(["Leadsquared", "Darwinbox", "Freshworks"]),
            "current_company_size": "201-500",
            "current_industry": "Technology",
        },
        "career_history": [
            _make_job(
                "Startup", "ML Engineer",
                _rand_date(int(yoe) + 1, int(yoe) + 2), None,
                "Technology",
                "Built NLP pipelines for text classification. Experimented with sentence-transformers. Deployed model serving API on AWS.",
                is_current=True,
            )
        ],
        "education": [{
            "institution": "IIIT Allahabad",
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "start_year": int(REFERENCE_DATE.year - yoe - 4),
            "end_year": int(REFERENCE_DATE.year - yoe),
            "grade": "8.8/10",
            "tier": "tier_2",
        }],
        "skills": [
            _make_skill("Python", "advanced", random.randint(20, 70), int(yoe * 12)),
            _make_skill("NLP", "intermediate", random.randint(10, 40), int(yoe * 8)),
            _make_skill("sentence-transformers", "intermediate", random.randint(5, 25), 12),
            _make_skill("PyTorch", "beginner", random.randint(5, 20), 12),
            _make_skill("Hugging Face", "intermediate", random.randint(8, 30), 12),
        ],
        "redrob_signals": _redrob_signals(
            last_active_days_ago=random.randint(1, 10),
            open_to_work=True,
            response_rate=random.uniform(0.70, 0.95),
            notice_period=random.randint(15, 30),
            github=random.uniform(50, 90),
        ),
    }


# ─── Main generator ─────────────────────────────────────────────────────────

ARCHETYPE_WEIGHTS = {
    "true_positive": 0.08,      # 8% — ideal candidates
    "keyword_stuffer": 0.25,    # 25% — trap candidates
    "consulting_ml": 0.12,      # 12% — consulting-only ML
    "inactive_strong": 0.05,    # 5% — strong but unavailable
    "cv_specialist": 0.08,      # 8% — wrong domain
    "honeypot": 0.015,          # 1.5% — impossible profiles
    "mid_tier_ds": 0.30,        # 30% — partial fit data scientists
    "junior_strong": 0.085,     # 8.5% — promising juniors
}

ARCHETYPE_FACTORIES = {
    "true_positive": make_true_positive,
    "keyword_stuffer": make_keyword_stuffer,
    "consulting_ml": make_consulting_ml,
    "inactive_strong": make_inactive_strong,
    "cv_specialist": make_cv_specialist,
    "honeypot": make_honeypot,
    "mid_tier_ds": make_mid_tier_ds,
    "junior_strong": make_junior_strong,
}


def generate_candidates(n: int) -> list:
    archetypes = list(ARCHETYPE_WEIGHTS.keys())
    weights = [ARCHETYPE_WEIGHTS[a] for a in archetypes]

    chosen = random.choices(archetypes, weights=weights, k=n)
    candidates = []
    for i, archetype in enumerate(chosen):
        cid = f"CAND_{i:07d}"
        try:
            cand = ARCHETYPE_FACTORIES[archetype](cid)
            candidates.append(cand)
        except Exception as e:
            print(f"Warning: failed to generate {archetype} {cid}: {e}")

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic candidates.jsonl for testing")
    parser.add_argument("--n", type=int, default=5000, help="Number of candidates to generate")
    parser.add_argument("--out", default="data/raw/candidates.jsonl", help="Output path")
    args = parser.parse_args()

    print(f"Generating {args.n} synthetic candidates...")
    candidates = generate_candidates(args.n)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for cand in candidates:
            f.write(json.dumps(cand, ensure_ascii=False) + "\n")

    print(f"Written {len(candidates)} candidates to {args.out}")

    # Print archetype distribution
    from collections import Counter
    titles = [c["profile"]["current_title"] for c in candidates]
    print("\nTop titles in generated data:")
    for title, count in Counter(titles).most_common(10):
        print(f"  {count:4d}  {title}")


if __name__ == "__main__":
    main()
