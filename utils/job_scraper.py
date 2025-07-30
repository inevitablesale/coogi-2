import os
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
# Use external JobSpy API instead of local library
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
        self.ai_demo_mode = not bool(os.getenv("OPENAI_API_KEY"))
        self.jobspy_api_url = "https://coogi-jobspy-production.up.railway.app/jobs"
        
        # Demo jobs for testing
        self.demo_jobs = [
            {
                "title": "Senior Software Engineer",
                "company": "TechCorp Inc",
                "location": "San Francisco, CA",
                "description": "We are looking for a senior software engineer with experience in Python, React, and AWS. B2B SaaS experience preferred. Strong problem-solving skills and ability to work in a fast-paced environment.",
                "job_url": "https://linkedin.com/jobs/demo1",
                "salary": "$120,000 - $180,000",
                "date_posted": "2025-07-29"
            },
            {
                "title": "Product Manager",
                "company": "StartupXYZ",
                "location": "New York, NY", 
                "description": "Join our growing team as a Product Manager. Experience with enterprise software and B2B sales required. You'll be responsible for product strategy and roadmap planning.",
                "job_url": "https://linkedin.com/jobs/demo2",
                "salary": "$100,000 - $150,000",
                "date_posted": "2025-07-28"
            },
            {
                "title": "Sales Director",
                "company": "Enterprise Solutions",
                "location": "Austin, TX",
                "description": "Lead our sales team in the enterprise space. Experience with SaaS and B2B sales required. Proven track record of meeting revenue targets and building high-performing teams.",
                "job_url": "https://linkedin.com/jobs/demo3",
                "salary": "$130,000 - $200,000",
                "date_posted": "2025-07-27"
            },
            {
                "title": "Marketing Manager",
                "company": "GrowthCo",
                "location": "Remote",
                "description": "Looking for a creative marketing manager to drive our digital marketing efforts. Experience with content marketing, SEO, and marketing automation required.",
                "job_url": "https://linkedin.com/jobs/demo4",
                "salary": "$80,000 - $120,000",
                "date_posted": "2025-07-26"
            },
            {
                "title": "DevOps Engineer",
                "company": "CloudTech",
                "location": "Seattle, WA",
                "description": "Join our infrastructure team as a DevOps Engineer. Experience with AWS, Docker, Kubernetes, and CI/CD pipelines required. Help us scale our platform to millions of users.",
                "job_url": "https://linkedin.com/jobs/demo5",
                "salary": "$110,000 - $160,000",
                "date_posted": "2025-07-25"
            }
        ]
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse recruiter query using AI to extract search parameters"""
        if self.ai_demo_mode or not self.openai_client:
            # Fallback parsing when OpenAI not available
            return self._fallback_parse_query(query)
        
        system_prompt = """
        You are a recruiter assistant. Given a prompt like 'Find me sales jobs in fintech in NYC', return a JSON with:
        - search_term: the main job title/role to search for
        - location: the location to search in
        - site_name: array of sites, default ["linkedin", "indeed", "zip_recruiter"]
        - job_type: full-time, contract, etc.
        - country_indeed: if relevant (US, UK, etc.)
        - results_wanted: default 200
        - keywords: array of relevant skills/technologies mentioned
        
        Return only valid JSON without any markdown formatting.
        """
        
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            else:
                return self._fallback_parse_query(query)
        except Exception as e:
            logger.error(f"Error parsing query with AI: {e}")
            return self._fallback_parse_query(query)
    
    def _fallback_parse_query(self, query: str) -> Dict[str, Any]:
        """Fallback query parsing without AI"""
        query_lower = query.lower()
        
        # Simple keyword detection
        search_term = query
        location = ""
        keywords = []
        
        # Location detection
        locations = ["san francisco", "nyc", "new york", "austin", "seattle", "remote", "boston", "chicago"]
        for loc in locations:
            if loc in query_lower:
                location = loc
                break
        
        # Role detection
        roles = ["engineer", "manager", "director", "developer", "designer", "analyst", "sales", "marketing"]
        for role in roles:
            if role in query_lower:
                search_term = role
                break
        
        return {
            "search_term": search_term,
            "location": location if location else "remote",
            "site_name": ["linkedin", "indeed", "zip_recruiter"],
            "job_type": "fulltime",
            "results_wanted": 100,
            "enforce_annual_salary": True,
            "keywords": keywords
        }
    
    def search_jobs(self, search_params: Dict[str, Any], max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for jobs using external JobSpy API or demo data"""
        try:
            # Use external JobSpy API for real job scraping
            api_params = {
                "query": search_params.get("search_term", "software engineer"),
                "location": search_params.get("location", "remote"),
                "sites": ",".join(search_params.get("site_name", ["linkedin", "indeed", "zip_recruiter"])),
                "enforce_annual_salary": search_params.get("enforce_annual_salary", True),
                "results_wanted": min(max_results, search_params.get("results_wanted", 100)),
                "hours_old": search_params.get("hours_old", 24)
            }
            
            logger.info(f"Calling JobSpy API with params: {api_params}")
            response = requests.get(self.jobspy_api_url, params=api_params, timeout=30)
            
            if response.status_code == 200:
                jobs_data = response.json()
                if jobs_data and len(jobs_data) > 0:
                    # Convert API response to our expected format
                    formatted_jobs = []
                    jobs_list = jobs_data if isinstance(jobs_data, list) else [jobs_data]
                    
                    for job in jobs_list:
                        if len(formatted_jobs) >= max_results:
                            break
                            
                        formatted_job = {
                            "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "location": self._format_location(job),
                            "description": job.get("description", ""),
                            "job_url": job.get("job_url", ""),
                            "salary": self._format_salary(job),
                            "date_posted": job.get("date_posted", ""),
                            "job_type": job.get("job_type", ""),
                            "site": job.get("site", "")
                        }
                        formatted_jobs.append(formatted_job)
                    
                    logger.info(f"Successfully retrieved {len(formatted_jobs)} jobs from JobSpy API")
                    return formatted_jobs
                else:
                    logger.warning("No jobs found from JobSpy API, falling back to demo data")
                    return self._get_demo_jobs_filtered(search_params, max_results)
            else:
                logger.error(f"JobSpy API returned status {response.status_code}: {response.text}")
                return self._get_demo_jobs_filtered(search_params, max_results)
                
        except Exception as e:
            logger.error(f"Error calling JobSpy API: {e}")
            return self._get_demo_jobs_filtered(search_params, max_results)
    
    def _format_salary(self, job: Dict[str, Any]) -> str:
        """Format salary information from job data"""
        min_amount = job.get("min_amount")
        max_amount = job.get("max_amount")
        interval = job.get("interval", "yearly")
        
        try:
            if min_amount and max_amount:
                return f"${min_amount:,} - ${max_amount:,} ({interval})"
            elif min_amount:
                return f"${min_amount:,}+ ({interval})"
            elif max_amount:
                return f"Up to ${max_amount:,} ({interval})"
            else:
                return ""
        except (ValueError, TypeError):
            return ""
    
    def _format_location(self, job: Dict[str, Any]) -> str:
        """Format location information from job data"""
        location_data = job.get("location", {})
        if isinstance(location_data, dict):
            city = location_data.get("city", "")
            state = location_data.get("state", "")
            country = location_data.get("country", "")
            
            parts = [part for part in [city, state, country] if part]
            return ", ".join(parts) if parts else ""
        else:
            return str(location_data) if location_data else ""
    
    def _get_demo_jobs_filtered(self, search_params: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Get filtered demo jobs"""
        search_term = search_params.get("search_term", "").lower()
        filtered_jobs = []
        
        for job in self.demo_jobs:
            if (not search_term or 
                search_term in job["title"].lower() or 
                search_term in job["description"].lower()):
                filtered_jobs.append(job)
        
        return filtered_jobs[:max_results]
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from job description"""
        if self.ai_demo_mode or not self.openai_client:
            # Fallback keyword extraction when OpenAI not available
            return self._fallback_extract_keywords(text)
        
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Extract 3-5 keywords describing core skills or functions in this job post. Return as a JSON array of strings."},
                    {"role": "user", "content": text[:3000]}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                return result.get("keywords", [])
            else:
                return self._fallback_extract_keywords(text)
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return self._fallback_extract_keywords(text)
    
    def _fallback_extract_keywords(self, text: str) -> List[str]:
        """Fallback keyword extraction without AI"""
        text_lower = text.lower()
        
        # Common tech and business keywords
        keywords = []
        tech_keywords = ["python", "javascript", "react", "aws", "docker", "kubernetes", "sql", "api", "saas", "b2b"]
        business_keywords = ["sales", "marketing", "product", "strategy", "growth", "analytics", "crm", "leadership"]
        
        all_keywords = tech_keywords + business_keywords
        
        for keyword in all_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        return keywords[:5]  # Return max 5 keywords
