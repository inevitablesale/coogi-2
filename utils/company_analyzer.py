import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class CompanySkipReason:
    company: str
    reason: str
    ta_roles: List[str]
    timestamp: str

@dataclass
class CompanyAnalysis:
    company: str
    has_ta_team: bool
    ta_roles: List[str]
    job_count: int
    active_jobs: List[Dict[str, Any]]
    decision_makers: List[Dict[str, Any]]
    recommendation: str
    skip_reason: Optional[str]

class CompanyAnalyzer:
    def __init__(self, rapidapi_key: str):
        self.rapidapi_key = rapidapi_key
        self.skipped_companies = []
        
    def analyze_company(self, company: str, people_data: List[Dict[str, Any]]) -> CompanyAnalysis:
        """Comprehensive company analysis for recruiting opportunity assessment"""
        
        # Check for talent acquisition team
        has_ta_team, ta_roles = self._detect_talent_acquisition_team(people_data)
        
        # Get company jobs data if no TA team
        job_count = 0
        active_jobs = []
        if not has_ta_team:
            job_count, active_jobs = self._get_company_jobs(company)
        
        # Identify decision makers
        decision_makers = self._identify_decision_makers(people_data)
        
        # Generate recommendation
        recommendation, skip_reason = self._generate_recommendation(
            company, has_ta_team, ta_roles, job_count, len(decision_makers)
        )
        
        # Track skipped companies
        if skip_reason:
            self.skipped_companies.append(CompanySkipReason(
                company=company,
                reason=skip_reason,
                ta_roles=ta_roles,
                timestamp=datetime.now().isoformat()
            ))
            logger.info(f"⏭️  SKIPPED {company}: {skip_reason}")
        else:
            logger.info(f"🎯 TARGET {company}: {recommendation}")
        
        return CompanyAnalysis(
            company=company,
            has_ta_team=has_ta_team,
            ta_roles=ta_roles,
            job_count=job_count,
            active_jobs=active_jobs[:5],  # Top 5 recent jobs
            decision_makers=decision_makers[:5],  # Top 5 decision makers
            recommendation=recommendation,
            skip_reason=skip_reason
        )
    
    def _detect_talent_acquisition_team(self, people: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """Detect talent acquisition team and return roles"""
        ta_keywords = [
            "talent", "recruiter", "recruiting", "people ops", "hr", 
            "human resources", "people partner", "talent acquisition", 
            "talent partner", "people operations", "staffing"
        ]
        
        ta_roles_found = []
        for person in people:
            title = (person.get("title") or "").lower()
            for keyword in ta_keywords:
                if keyword in title:
                    ta_roles_found.append(person.get("title", ""))
        
        unique_ta_roles = list(set(ta_roles_found))
        return len(unique_ta_roles) > 0, unique_ta_roles
    
    def _get_company_jobs(self, company: str) -> tuple[int, List[Dict[str, Any]]]:
        """Get company jobs from SaleLeads API"""
        try:
            jobs_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/jobs"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
            }
            
            logger.info(f"Getting job data for {company}")
            response = requests.get(
                jobs_url, 
                params={"company": company, "page": 1}, 
                headers=headers, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    jobs = data.get("data", [])
                    job_count = data.get("total", len(jobs))
                    logger.info(f"Found {job_count} active jobs at {company}")
                    return job_count, jobs
                else:
                    logger.warning(f"SaleLeads jobs API returned unsuccessful response for {company}")
            else:
                logger.warning(f"SaleLeads jobs API failed for {company}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting jobs for {company}: {e}")
        
        return 0, []
    
    def _identify_decision_makers(self, people: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify and rank decision makers"""
        decision_makers = []
        
        for person in people:
            title = (person.get("title") or "").lower()
            score = 0
            
            # Score based on decision-making authority
            if any(role in title for role in ["cto", "ceo", "founder", "chief"]):
                score = 10
            elif any(role in title for role in ["vp", "vice president"]):
                score = 8
            elif any(role in title for role in ["director", "head"]):
                score = 6
            elif any(role in title for role in ["manager", "lead", "principal"]):
                score = 4
            elif any(role in title for role in ["senior", "sr"]):
                score = 2
            
            if score >= 4:  # Only high-level decision makers
                decision_makers.append({
                    "title": person.get("title", ""),
                    "decision_score": score
                })
        
        # Sort by decision score
        decision_makers.sort(key=lambda x: x["decision_score"], reverse=True)
        return decision_makers
    
    def _generate_recommendation(self, company: str, has_ta_team: bool, ta_roles: List[str], 
                                job_count: int, decision_maker_count: int) -> tuple[str, Optional[str]]:
        """Generate recruiting recommendation and skip reason if applicable"""
        
        # Skip if has TA team
        if has_ta_team:
            return "", f"Internal TA team detected: {', '.join(ta_roles[:3])}"
        
        # Skip if no decision makers found
        if decision_maker_count == 0:
            return "", "No decision makers identified"
        
        # Skip if very few jobs (low hiring activity)
        if job_count > 0 and job_count < 3:
            return "", f"Low hiring activity: only {job_count} active jobs"
        
        # High opportunity recommendations
        if job_count >= 10:
            return f"HIGH PRIORITY: {job_count} active jobs, {decision_maker_count} decision makers", None
        elif job_count >= 5:
            return f"MEDIUM PRIORITY: {job_count} active jobs, {decision_maker_count} decision makers", None
        else:
            return f"TARGET: {decision_maker_count} decision makers identified", None
    
    def get_skip_report(self) -> Dict[str, Any]:
        """Generate report of skipped companies"""
        skip_counts = {}
        for skip in self.skipped_companies:
            reason = skip.reason.split(":")[0]  # Get main reason category
            skip_counts[reason] = skip_counts.get(reason, 0) + 1
        
        return {
            "total_skipped": len(self.skipped_companies),
            "skip_reasons": skip_counts,
            "skipped_companies": [
                {
                    "company": skip.company,
                    "reason": skip.reason,
                    "ta_roles": skip.ta_roles,
                    "timestamp": skip.timestamp
                }
                for skip in self.skipped_companies[-20:]  # Last 20 skipped
            ]
        }
    
    def clear_skip_history(self):
        """Clear skip history for new analysis session"""
        self.skipped_companies = []