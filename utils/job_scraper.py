import os
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
# Import jobspy conditionally - handle missing dependency gracefully
scrape_jobs = None
try:
    from jobspy import scrape_jobs
except ImportError:
    pass  # Will use demo mode
from openai import OpenAI

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
        self.demo_mode = not bool(os.getenv("OPENAI_API_KEY"))
        
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
        if self.demo_mode or not self.openai_client:
            # Fallback parsing for demo mode
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
            "location": location,
            "site_name": ["linkedin", "indeed", "zip_recruiter"],
            "job_type": "full-time",
            "results_wanted": 200,
            "keywords": keywords
        }
    
    def search_jobs(self, search_params: Dict[str, Any], max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for jobs using JobSpy or demo data"""
        if self.demo_mode:
            # Return demo jobs filtered by search term
            search_term = search_params.get("search_term", "").lower()
            filtered_jobs = []
            
            for job in self.demo_jobs:
                if (not search_term or 
                    search_term in job["title"].lower() or 
                    search_term in job["description"].lower()):
                    filtered_jobs.append(job)
            
            return filtered_jobs[:max_results]
        
        try:
            # Use JobSpy for real job scraping
            if scrape_jobs is None:
                raise ImportError("JobSpy not available")
            jobs_df = scrape_jobs(
                site_name=search_params.get("site_name", ["linkedin"]),
                search_term=search_params.get("search_term", ""),
                location=search_params.get("location", ""),
                results_wanted=min(max_results, search_params.get("results_wanted", 200)),
                hours_old=search_params.get("hours_old", 24),
                job_type=search_params.get("job_type", "full-time")
            )
            
            if jobs_df is not None and not jobs_df.empty:
                return jobs_df.to_dict('records')
            else:
                logger.warning("No jobs found with JobSpy, falling back to demo data")
                return self.demo_jobs[:max_results]
                
        except Exception as e:
            logger.error(f"Error scraping jobs: {e}")
            return self.demo_jobs[:max_results]
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from job description"""
        if self.demo_mode or not self.openai_client:
            # Fallback keyword extraction
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
