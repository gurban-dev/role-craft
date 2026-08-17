"""Deterministic job match scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.models import CandidateProfile, Job
from app.models.enums import MatchRecommendation

SENIORITY_RANK = {
    "intern": 0,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
    "lead": 4,
    "manager": 4,
}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+#.\s]", " ", text.lower())


def _tokenize(items: list[Any]) -> set[str]:
    result: set[str] = set()
    for item in items:
        if isinstance(item, str):
            result.add(_norm(item).strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("skill") or item.get("technology")
            if name:
                result.add(_norm(str(name)).strip())
    return {s for s in result if s}


def _extract_job_skills(job: Job) -> set[str]:
    skills = _tokenize(job.technologies) | _tokenize(job.requirements)
    desc = _norm(job.description or "")
    for token in [
        "python",
        "typescript",
        "javascript",
        "react",
        "next.js",
        "fastapi",
        "django",
        "flask",
        "postgresql",
        "redis",
        "aws",
        "gcp",
        "azure",
        "kubernetes",
        "docker",
        "terraform",
        "go",
        "rust",
        "java",
        "kotlin",
        "swift",
        "sql",
        "graphql",
        "node.js",
        "celery",
        "playwright",
    ]:
        if token in desc:
            skills.add(token)
    return skills


def _infer_seniority(text: str) -> str:
    t = text.lower()
    for level in ["principal", "staff", "lead", "senior", "junior", "intern", "manager"]:
        if level in t:
            return level
    return "mid"


@dataclass
class ScoreResult:
    overall_score: float
    skill_match: float
    experience_match: float
    location_match: float
    seniority_match: float
    salary_match: float
    domain_match: float
    preference_match: float
    required_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    weaknesses: list[str]
    explanation: str
    score_breakdown: dict[str, Any]
    recommendation: MatchRecommendation
    fit_score_10: float = 0.0


class ScoringService:
    def __init__(
        self,
        settings: Settings | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.weights = weights or {
            "technical": self.settings.weight_technical,
            "experience": self.settings.weight_experience,
            "seniority": self.settings.weight_seniority,
            "location": self.settings.weight_location,
            "domain": self.settings.weight_domain,
            "salary": self.settings.weight_salary,
            "preference": self.settings.weight_preference,
        }

    def score(self, job: Job, profile: CandidateProfile) -> ScoreResult:
        job_skills = _extract_job_skills(job)
        candidate_skills = _tokenize(profile.skills)
        if not job_skills:
            skill_score = 0.5
            missing: list[str] = []
            matched: list[str] = []
        else:
            matched = sorted(job_skills & candidate_skills)
            missing = sorted(job_skills - candidate_skills)
            skill_score = len(matched) / max(len(job_skills), 1)

        years_needed = self._years_required(
            job.description + " " + " ".join(map(str, job.requirements))
        )
        if years_needed <= 0:
            experience_score = 0.7
        else:
            ratio = profile.years_experience / years_needed
            experience_score = max(0.0, min(1.0, ratio))

        job_seniority = _infer_seniority(f"{job.title} {job.description}")
        cand_seniority = profile.seniority_level.lower()
        seniority_score = self._seniority_score(cand_seniority, job_seniority)

        location_score = self._location_score(job, profile)
        salary_score = self._salary_score(job, profile)
        domain_score = self._domain_score(job, profile)
        preference_score = self._preference_score(job, profile)

        w = self.weights
        overall = (
            w["technical"] * skill_score
            + w["experience"] * experience_score
            + w["seniority"] * seniority_score
            + w["location"] * location_score
            + w["domain"] * domain_score
            + w["salary"] * salary_score
            + w["preference"] * preference_score
        )
        overall = round(min(1.0, max(0.0, overall)), 4)

        fit_10 = self._fit_score_10(
            skill_score=skill_score,
            experience_score=experience_score,
            seniority_score=seniority_score,
            missing=missing,
            job_skills=job_skills,
            matched=matched,
        )

        strengths = []
        weaknesses = []
        if skill_score >= 0.7:
            strengths.append(f"Strong technical overlap ({len(matched)} skills)")
        if missing:
            weaknesses.append(f"Missing skills: {', '.join(missing[:8])}")
        if experience_score >= 0.8:
            strengths.append("Experience meets or exceeds requirements")
        elif experience_score < 0.5:
            weaknesses.append("Years of experience below typical requirement")
        if location_score >= 0.8:
            strengths.append("Location/remote preference aligned")
        if location_score < 0.4:
            weaknesses.append("Location/remote mismatch")

        recommendation = self._recommend(overall)
        explanation = (
            f"Overall match {overall:.0%} ({recommendation.value}). "
            f"Fit Score {fit_10:.1f}/10. "
            f"Technical {skill_score:.0%}, experience {experience_score:.0%}, "
            f"seniority {seniority_score:.0%}, location {location_score:.0%}."
        )
        breakdown = {
            "weights": w,
            "components": {
                "technical": skill_score,
                "experience": experience_score,
                "seniority": seniority_score,
                "location": location_score,
                "domain": domain_score,
                "salary": salary_score,
                "preference": preference_score,
            },
            "matched_skills": matched,
            "job_seniority": job_seniority,
            "candidate_seniority": cand_seniority,
            "years_required": years_needed,
            "fit_score_10": fit_10,
        }
        return ScoreResult(
            overall_score=overall,
            skill_match=round(skill_score, 4),
            experience_match=round(experience_score, 4),
            location_match=round(location_score, 4),
            seniority_match=round(seniority_score, 4),
            salary_match=round(salary_score, 4),
            domain_match=round(domain_score, 4),
            preference_match=round(preference_score, 4),
            required_skills=sorted(job_skills),
            missing_skills=missing,
            strengths=strengths,
            weaknesses=weaknesses,
            explanation=explanation,
            score_breakdown=breakdown,
            recommendation=recommendation,
            fit_score_10=fit_10,
        )

    def _fit_score_10(
        self,
        *,
        skill_score: float,
        experience_score: float,
        seniority_score: float,
        missing: list[str],
        job_skills: set[str],
        matched: list[str],
    ) -> float:
        """Strict 0–10 Fit Score; missing mandatory skills reduce the score."""
        base = (
            0.45 * skill_score
            + 0.25 * experience_score
            + 0.20 * seniority_score
            + 0.10 * (1.0 if matched else 0.4)
        ) * 10.0
        if job_skills and missing:
            miss_ratio = len(missing) / max(len(job_skills), 1)
            base -= min(3.5, miss_ratio * 4.0)
        if seniority_score < 0.45:
            base -= 1.5
        if experience_score < 0.5:
            base -= 1.0
        return round(min(10.0, max(0.0, base)), 1)

    def _recommend(self, score: float) -> MatchRecommendation:
        threshold = self.settings.min_match_score
        if score >= max(threshold, 0.85):
            return MatchRecommendation.READY_TO_APPLY
        if score >= threshold:
            return MatchRecommendation.STRONG_MATCH
        if score >= threshold - 0.15:
            return MatchRecommendation.REVIEW
        if score >= 0.35:
            return MatchRecommendation.LOW_MATCH
        return MatchRecommendation.REJECTED

    @staticmethod
    def _years_required(text: str) -> float:
        match = re.search(r"(\d+)\+?\s*\+?\s*years?", text.lower())
        if match:
            return float(match.group(1))
        return 0.0

    @staticmethod
    def _seniority_score(candidate: str, job: str) -> float:
        c = SENIORITY_RANK.get(candidate, 2)
        j = SENIORITY_RANK.get(job, 2)
        diff = abs(c - j)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.75
        if diff == 2:
            return 0.45
        return 0.2

    @staticmethod
    def _location_score(job: Job, profile: CandidateProfile) -> float:
        remote = (job.remote_status or "").lower()
        pref = (profile.remote_preference or "").lower()
        if "remote" in remote and pref in {"remote", "hybrid", "any"}:
            return 1.0
        loc = (job.location or "").lower()
        preferred = [str(x).lower() for x in (profile.preferred_locations or [])]
        if any(p and p in loc for p in preferred):
            return 1.0
        if not loc and not remote:
            return 0.6
        if pref == "any":
            return 0.7
        return 0.35

    @staticmethod
    def _salary_score(job: Job, profile: CandidateProfile) -> float:
        if profile.salary_min is None or job.salary_max is None:
            return 0.6
        if job.salary_max >= profile.salary_min:
            return 1.0
        if job.salary_max >= profile.salary_min * 0.85:
            return 0.6
        return 0.2

    @staticmethod
    def _domain_score(job: Job, profile: CandidateProfile) -> float:
        blob = _norm(
            " ".join(
                [
                    profile.professional_summary or "",
                    " ".join(str(x) for x in profile.work_history or []),
                ]
            )
        )
        company_blob = _norm(f"{job.company} {job.title} {job.description[:500]}")
        keywords = [w for w in company_blob.split() if len(w) > 4][:20]
        if not keywords:
            return 0.5
        hits = sum(1 for k in keywords if k in blob)
        return min(1.0, hits / max(5, len(keywords) * 0.3))

    @staticmethod
    def _preference_score(job: Job, profile: CandidateProfile) -> float:
        types = [str(t).lower() for t in (profile.employment_types or [])]
        if not types:
            return 0.7
        desc = (job.description or "").lower()
        if any(t in desc for t in types):
            return 1.0
        return 0.5
