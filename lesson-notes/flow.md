# Find Matching Jobs: Application Flow

When a user clicks **Find matching jobs**, the application follows this flow:

**Dashboard button -> POST `/api/jobs/eea-search` -> Search selected sources -> Deduplicate results -> Apply hard filters -> Score remaining jobs against the candidate profile -> Return and display the top matches**

## 1. Collect Search Settings

The dashboard collects the user's search settings.

- **Regions:** Europe, North America, South America, Asia, and Africa are selected by default. The user can uncheck regions.
- **Date window:** The past 24 hours is the default.
- The selected date window and regions are included in the API request.
- The button changes to **Searching...** while the request is being processed.

**Relevant files:**
- [Dashboard component](../apps/web/src/components/dashboard/RecentMatchSearch.tsx#L68)
- [API request payload](../apps/web/src/lib/endpoints.ts#L34)

## 2. Authenticate the User and Start Job Discovery

The `POST /api/jobs/eea-search` endpoint:

1. Checks that the user is signed in.
2. Passes the search settings to `EEAJobSearchService`.
3. Checks whether the user has a candidate profile.

If the user does not have a candidate profile, the service returns an empty list.

**Relevant files:**
- [API route](../apps/api/app/api/jobs.py#L51)
- [Search service](../apps/api/app/services/eea_job_search_service.py#L51)

## 3. Search the Selected Job Sources

The dashboard requests results only from LinkedIn through the Apify LinkedIn scraper. Google and other job-source integrations are not used by this dashboard search.

The search criteria include:

- The selected date window.
- The selected regions.
- Up to eight skills from the candidate profile for scoring, with the top three added to LinkedIn's search keywords.

If a source encounters an error, the service logs it and continues searching the remaining sources.

**Relevant files:**
- [Source selection and search](../apps/api/app/services/eea_job_search_service.py#L70)
- [LinkedIn integration](../apps/api/app/integrations/job_sources/apify_linkedin.py#L112)

## 4. Deduplicate Results and Apply Hard Filters

After collecting results, the pipeline removes duplicates and checks each job against the hard requirements.

A job must satisfy **all** of the following conditions:

1. Match at least one of the selected regions.
2. Pass the language requirements.
3. Pass the seniority requirements.
4. Not explicitly indicate that visa sponsorship is unavailable.
5. Have a verified posting date within the selected date window.
6. Have a known applicant count below 100.
7. Have a company or ATS application link.

**Important:** A job only needs to match one of the selected regions, not all of them.

**Relevant files:**
- [Hard filters](../apps/api/app/services/eea_pipeline.py#L51)
- [Date and applicant checks](../apps/api/app/services/eea_filters.py#L396)

## 5. Score Remaining Jobs Against the Candidate Profile

Jobs that pass the hard filters are scored against the candidate profile using a deterministic scoring system.

The scorer evaluates:

- Skills.
- Experience.
- Seniority.
- Location.
- Salary.
- Domain.
- Preferences.

A job must score at least **8/10** to appear in the search results. This threshold is configurable with `MIN_FIT_SCORE_10`.

**Important:** Jobs that pass the hard requirements are persisted before the scoring cutoff is applied.

Consequently, the pipeline's **Discovered** count can be higher than the number of jobs displayed in the search results.

**Relevant files:**
- [Scoring logic](../apps/api/app/services/scoring_service.py#L122)
- [Score cutoff and persistence order](../apps/api/app/services/eea_job_search_service.py#L98)

## 6. Return and Display the Top 10 Matches

The API returns up to 10 ranked results.

The dashboard displays the following information for each matching job:

- Role.
- Company.
- Location.
- Posting date.
- Source.
- Applicant count.
- Fit score.
- Application link.

If no jobs pass the requirements, the dashboard displays:

**No matching jobs.**

The API logs also include counts by rejection reason, helping identify why a search returned no results.

**Relevant files:**
- [Result construction and logging](../apps/api/app/services/eea_job_search_service.py#L127)
- [Dashboard results table](../apps/web/src/components/dashboard/RecentMatchSearch.tsx#L178)

---

## Summary

The job discovery pipeline consists of six stages:

| Stage | Responsibility |
|---|---|
| 1. Collect settings | Capture the selected regions and date window. |
| 2. Authenticate | Verify the user and retrieve their candidate profile. |
| 3. Search | Retrieve jobs from the selected sources. |
| 4. Filter | Deduplicate results and enforce hard requirements. |
| 5. Score | Evaluate job suitability against the candidate profile. |
| 6. Return results | Display up to 10 highest-scoring matches. |