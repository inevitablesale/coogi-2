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
        self.jobspy_api_url = "https://coogi-jobspy-production.up.railway.app/jobs"
        
        if not self.openai_client:
            logger.warning("🚫 OpenAI API key not found - AI query parsing unavailable")
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse recruiter query using AI to extract search parameters"""
        if not self.openai_client:
            # Basic parsing when OpenAI not available
            return self._fallback_parse_query(query)
        
        system_prompt = """
        You are an expert recruiting AI with deep knowledge of job markets and recruiting terminology. 
        
        ROLE: Extract precise search parameters from recruiting queries with high accuracy.
        
        EXAMPLES:
        Input: "Find me senior software engineers in fintech startups in NYC"
        Output: {"search_term": "senior software engineer", "location": "New York", "industry": "fintech", "company_size": "startup", "keywords": ["senior", "software", "engineer", "fintech"]}
        
        Input: "Marketing managers for B2B SaaS companies, remote OK"
        Output: {"search_term": "marketing manager", "location": "remote", "industry": "B2B SaaS", "keywords": ["marketing", "manager", "B2B", "SaaS"]}
        
        Input: "Data scientists with ML experience in healthcare"
        Output: {"search_term": "data scientist", "industry": "healthcare", "keywords": ["data", "scientist", "machine learning", "ML", "healthcare"]}
        
        Given a recruiter query, extract and return JSON with:
        - search_term: primary job title/role (required)
        - location: specific location or "remote" (extract from common abbreviations like NYC=New York, SF=San Francisco)
        - industry: sector/industry if mentioned (fintech, healthcare, SaaS, etc)
        - company_size: startup, mid-size, enterprise if indicated
        - keywords: array of relevant search terms and skills
        - seniority: junior, mid, senior, principal, director if specified
        
        Be precise and extract all relevant context. Default location to "United States" if not specified.
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
            search_term = search_params.get("search_term", "software engineer")
            location = search_params.get("location", "")
            
            # Try broader search if no location specified
            if not location:
                location = "United States"
            
            # Add company size filter for startup targeting
            company_size_filter = ""
            if "startup" in search_term.lower() or "startup" in search_params.get("keywords", []):
                company_size_filter = "startup"
            
            api_params = {
                "query": search_term,
                "location": location,
                "sites": ",".join(search_params.get("site_name", ["linkedin", "indeed", "zip_recruiter"])),
                "enforce_annual_salary": search_params.get("enforce_annual_salary", False),  # Less restrictive
                "results_wanted": min(max_results, search_params.get("results_wanted", 100)),
                "hours_old": search_params.get("hours_old", 72)  # Broader time range
            }
            
            # Add company size if specified
            if company_size_filter:
                api_params["company_size"] = company_size_filter
            
            logger.info(f"Calling JobSpy API with params: {api_params}")
            response = requests.get(self.jobspy_api_url, params=api_params, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"JobSpy API response structure: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                
                # Handle the new API response format
                if isinstance(response_data, dict) and "jobs" in response_data:
                    jobs_list = response_data["jobs"]
                    total_jobs = response_data.get("total_jobs", len(jobs_list))
                    logger.info(f"JobSpy API found {total_jobs} total jobs, processing {len(jobs_list)} jobs")
                elif isinstance(response_data, list):
                    jobs_list = response_data
                else:
                    logger.error("Unexpected API response format - no fallback data available")
                    return []
                
                if jobs_list and len(jobs_list) > 0:
                    # Convert API response to our expected format
                    formatted_jobs = []
                    
                    for job in jobs_list[:max_results]:
                        formatted_job = {
                            "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "location": self._format_location(job),
                            "description": job.get("description", job.get("job_level", "")),
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
                    logger.error("No jobs found from JobSpy API - no fallback data available")
                    return []
            else:
                logger.error(f"JobSpy API returned status {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error calling JobSpy API: {e}")
            return []
    
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
        location_data = job.get("location", "")
        
        # Handle both string and dict location formats
        if isinstance(location_data, dict):
            city = location_data.get("city", "")
            state = location_data.get("state", "")
            country = location_data.get("country", "")
            parts = [part for part in [city, state, country] if part]
            return ", ".join(parts) if parts else ""
        elif isinstance(location_data, str):
            return location_data
        else:
            return ""
    

    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from job description"""
        if not text:
            return []
            
        if not self.openai_client:
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
        if not text:
            return []
            
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
