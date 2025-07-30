import os
import requests
import logging
from typing import List, Dict, Any, Tuple, Optional
import time

logger = logging.getLogger(__name__)

class ContactFinder:
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "9fc749430dmsh203a8a9d7a08955p1eec7djsnb30f69ff59c7")
        self.hunter_api_key = os.getenv("HUNTER_API_KEY")
        if not self.hunter_api_key:
            logger.warning("🚫 Hunter.io API key not found - email discovery unavailable")
        if not self.rapidapi_key:
            logger.warning("🚫 RapidAPI key not found - contact discovery unavailable")
        
        # Title ranking for contact prioritization
        self.title_rank = {
            "cto": 5, "chief": 5, "vp": 4, "head": 3, "director": 2, 
            "manager": 1, "senior": 3, "lead": 2, "founder": 5, "ceo": 5
        }
        
        # Rate limiter for RapidAPI (20 requests per minute)
        self.rate_limiter = self._create_rate_limiter()
    
    def _create_rate_limiter(self):
        """Create a rate limiter for RapidAPI calls"""
        class RateLimiter:
            def __init__(self, max_requests=20, time_window=60):
                self.max_requests = max_requests
                self.time_window = time_window
                self.requests = []
            
            def can_make_request(self):
                """Check if we can make a request without hitting rate limit"""
                now = time.time()
                # Remove requests older than time_window
                self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
                return len(self.requests) < self.max_requests
            
            def record_request(self):
                """Record that a request was made"""
                self.requests.append(time.time())
            
            def wait_if_needed(self):
                """Wait if we're at the rate limit"""
                if not self.can_make_request():
                    wait_time = self.time_window - (time.time() - self.requests[0])
                    if wait_time > 0:
                        logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                self.record_request()
        
        return RateLimiter(max_requests=20, time_window=60)
    
    def find_contacts(self, company: str, role_hint: str, keywords: List[str]) -> Tuple[List[Dict[str, Any]], bool]:
        """Find company contacts and determine if they have a talent acquisition team"""
        try:
            # Check if company name is valid
            if not company or company.strip() == "":
                logger.warning(f"Invalid company name: {company}")
                return [], False
                
            # Always try RapidAPI first for real LinkedIn data
            contacts, has_ta_team = self._get_contacts_from_rapidapi(company, role_hint, keywords)
            
            # VOLUME OPTIMIZATION: Skip companies with TA teams unless specifically requested
            if has_ta_team:
                logger.info(f"⚠️  SKIP RECOMMENDATION: {company} has internal talent acquisition - low conversion probability")
                return [], True  # Return empty contacts to signal skip
            else:
                logger.info(f"🎯 TARGET COMPANY: {company} - no TA team, high conversion opportunity")
                return contacts, False
                
        except Exception as e:
            logger.error(f"Error finding contacts for {company}: {e}")
            logger.error(f"RapidAPI unavailable for {company} - no fallback data")
            return [], False
    

    
    def _get_contacts_from_rapidapi(self, company: str, role_hint: str, keywords: List[str]) -> Tuple[List[Dict[str, Any]], bool]:
        """Get company contacts from RapidAPI SaleLeads LinkedIn scraper"""
        try:
            logger.info(f"Attempting RapidAPI contact discovery for company: {company}")
            
            # Step 1: Get company profile first to get company ID and employee count
            profile_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/profile"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
            }
            
            # Get company profile to verify company exists and get company ID
            logger.info(f"Calling SaleLeads API profile endpoint for: {company}")
            # Rate limit check before API call
            self.rate_limiter.wait_if_needed()
            profile_resp = requests.get(profile_url, params={"company": company}, headers=headers, timeout=15)
            logger.info(f"SaleLeads API profile response: {profile_resp.status_code}")
            
            if profile_resp.status_code != 200:
                logger.warning(f"SaleLeads API profile failed with status {profile_resp.status_code}: {profile_resp.text[:200]}")
                logger.error(f"SaleLeads API profile unavailable for {company} - company not found")
                return [], False
                
            profile_data = profile_resp.json()
            
            # Check if the profile API call was successful
            if not profile_data.get("success", False):
                logger.warning(f"SaleLeads API profile returned unsuccessful response for {company}")
                logger.info(f"🎯 TARGET COMPANY: {company} - company profile not found")
                return [], False
            
            # Extract company ID and employee count
            company_profile = profile_data.get("data", {})
            company_id = company_profile.get("id")
            company_verified = company_profile.get("verified", False)
            employee_count = company_profile.get("employee_count", 0)
            
            if not company_id:
                logger.warning(f"No company ID found for {company}")
                return [], False
                
            logger.info(f"✅ Company profile found for {company} (ID: {company_id}, Verified: {company_verified}, Employees: {employee_count})")
            
            # Step 2: Two-Tier TA Team Detection
            # Tier 1: Employee Count Check + Company Profile Clues
            
            # Check employee count first
            if employee_count >= 20:
                logger.warning(f"🚫 TIER 1 - EMPLOYEE COUNT: {company} has {employee_count} employees - likely has TA team")
                return [], True
            
            # Check company profile clues for large companies (even if employee_count is missing)
            company_name = (company_profile.get("name") or "").lower()
            company_industry = (company_profile.get("industry") or "").lower()
            
            # Large company indicators
            large_company_indicators = [
                "inc", "corp", "corporation", "enterprises", "holdings", "group", "international", 
                "global", "worldwide", "national", "federal", "government", "university", "college",
                "hospital", "medical center", "health system", "bank", "financial"
            ]
            
            # Check if company name or industry suggests large company
            is_likely_large = any(indicator in company_name for indicator in large_company_indicators) or \
                             any(indicator in company_industry for indicator in large_company_indicators)
            
            if is_likely_large and employee_count == 0:
                logger.warning(f"🚫 TIER 1 - LARGE COMPANY CLUES: {company} has indicators of large company - likely has TA team")
                return [], True
            
            # Handle cases where employee_count is missing (0) - be conservative
            # For companies with missing employee count, proceed to Tier 2 analysis
            if employee_count == 0:
                logger.warning(f"⚠️  TIER 1 - MISSING EMPLOYEE COUNT: {company} - proceeding to role analysis")
            
            logger.info(f"✅ TIER 1 - EMPLOYEE COUNT: {company} has {employee_count} employees - proceeding to role analysis")
            
            # Tier 2: Role Analysis (using /api/v1/company/people)
            people_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/people"
            
            # Limit to checking max 2 pages (20 roles max) regardless of employee count
            pages_to_check = 2
            logger.info(f"Checking {pages_to_check} pages (max 20 roles) for {company}")
            
            all_people = []
            ta_roles_found = []
            roles_checked = 0
            
            # Check multiple pages to ensure we analyze all employees (max 20 roles)
            for page in range(1, pages_to_check + 1):
                logger.info(f"Calling SaleLeads API people endpoint for company ID: {company_id}, page: {page}")
                # Rate limit check before API call
                self.rate_limiter.wait_if_needed()
                people_resp = requests.get(people_url, params={"company_id": company_id, "page": page}, headers=headers, timeout=15)
                logger.info(f"SaleLeads API response for page {page}: {people_resp.status_code}")
                
                if people_resp.status_code != 200:
                    logger.warning(f"SaleLeads API failed with status {people_resp.status_code}: {people_resp.text[:200]}")
                    break
                    
                people_data = people_resp.json()
                
                # Check if the API call was successful
                if not people_data.get("success", False):
                    logger.warning(f"SaleLeads API returned unsuccessful response for page {page}")
                    break
                
                page_people = people_data.get("data", [])
                all_people.extend(page_people)
                roles_checked += len(page_people)
                
                # Check for TA roles in this page's people data
                ta_keywords = ["talent", "recruiter", "recruiting", "people ops", "hr", "human resources", "people partner", "talent acquisition", "talent partner", "people operations", "hiring", "recruitment"]
                
                for person in page_people:
                    title = (person.get("title") or "").lower()
                    for keyword in ta_keywords:
                        if keyword in title:
                            ta_roles_found.append(title)
                
                # If we found TA roles, we can stop checking more pages
                if ta_roles_found:
                    logger.warning(f"🚫 TA ROLES DETECTED on page {page}: {ta_roles_found}")
                    break
                
                # Stop if we've checked 20 roles
                if roles_checked >= 20:
                    logger.info(f"Reached 20 roles limit on page {page}")
                    break
                
                # If this page has fewer people than expected, we've reached the end
                if len(page_people) < 10:
                    logger.info(f"Reached end of people data on page {page}")
                    break
            
            logger.info(f"Found {len(all_people)} total people at {company} (checked {roles_checked} roles)")
            
            if ta_roles_found:
                unique_roles = list(set(ta_roles_found))[:5]
                logger.warning(f"🚫 TIER 2 - TA ROLES DETECTED: {unique_roles}")
                return [], True
            
            # ✅ TARGET: Passed both filters - no TA team detected
            logger.info(f"✅ TIER 2 - NO TA ROLES: {company} passed both filters - ideal target for recruiters")
            
            # Step 3: Enhanced Intelligence (only for TARGET companies)
            # Get job count: /api/v1/company/job-count
            job_count = self._get_company_job_count(company_id, headers)
            logger.info(f"📊 Company job count: {job_count} active positions")
            
            # Get job details: /api/v1/company/jobs (optional - for additional intelligence)
            # job_details = self._get_company_jobs(company_id, headers, max_jobs=5)
            
            # Filter and score contacts
            contacts = []
            for person in all_people[:10]:  # Limit to top 10 contacts
                if person.get("full_name") and person.get("title"):
                    contact_score = self._calculate_contact_score(person, role_hint, keywords)
                    contacts.append({
                        "full_name": person.get("full_name", ""),
                        "title": person.get("title", ""),
                        "score": contact_score,
                        "company": company
                    })
            
            # Sort by score (highest first)
            contacts.sort(key=lambda x: x["score"], reverse=True)
            
            return contacts, False  # No TA team detected
            
        except Exception as e:
            logger.error(f"Error in RapidAPI contact discovery for {company}: {e}")
            return [], False

    def _get_company_job_count(self, company_id: str, headers: Dict[str, str]) -> int:
        """Get company job count from RapidAPI"""
        try:
            job_count_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/job-count"
            logger.info(f"Calling SaleLeads API job count endpoint for company ID: {company_id}")
            
            # Rate limit check before API call
            self.rate_limiter.wait_if_needed()
            job_count_resp = requests.get(job_count_url, params={"company_id": company_id}, headers=headers, timeout=15)
            
            if job_count_resp.status_code == 200:
                job_count_data = job_count_resp.json()
                if job_count_data.get("success", False):
                    total_jobs = job_count_data.get("data", {}).get("total", 0)
                    logger.info(f"✅ Job count API successful: {total_jobs} total jobs")
                    return total_jobs
                else:
                    logger.warning(f"Job count API returned unsuccessful response")
                    return 0
            else:
                logger.warning(f"Job count API failed with status {job_count_resp.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting job count: {e}")
            return 0

    def _get_company_jobs(self, company_id: str, headers: Dict[str, str], max_jobs: int = 10) -> List[Dict[str, Any]]:
        """Get company jobs from RapidAPI"""
        try:
            jobs_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/jobs"
            logger.info(f"Calling SaleLeads API jobs endpoint for company ID: {company_id}")
            
            # Rate limit check before API call
            self.rate_limiter.wait_if_needed()
            jobs_resp = requests.get(
                jobs_url, 
                params={
                    "company_id": company_id,
                    "page": 1,
                    "sort_by": "recent",
                    "date_posted": "anytime"
                }, 
                headers=headers, 
                timeout=15
            )
            
            if jobs_resp.status_code == 200:
                jobs_data = jobs_resp.json()
                if jobs_data.get("success", False):
                    jobs = jobs_data.get("data", [])
                    logger.info(f"Found {len(jobs)} jobs at company")
                    return jobs[:max_jobs]
                else:
                    logger.warning(f"SaleLeads API jobs returned unsuccessful response")
                    return []
            else:
                logger.warning(f"SaleLeads API jobs failed with status {jobs_resp.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting company jobs: {e}")
            return []

    def _calculate_contact_score(self, contact: Dict[str, Any], role_hint: str, keywords: List[str]) -> float:
        """Calculate relevance score for a contact"""
        title = (contact.get("title") or "").lower()
        score = 0
        
        # Base score from title rank
        for word in title.split():
            if word in self.title_rank:
                score += self.title_rank[word]
        
        # Bonus for role hint match
        if role_hint and role_hint.lower() in title:
            score += 3
        
        # Bonus for keyword matches
        for keyword in keywords:
            if keyword and keyword.lower() in title:
                score += 1
        
        return score
    
    def find_email(self, title: str, company: str) -> Optional[str]:
        """Find email address using Hunter.io API only"""
        if not self.hunter_api_key:
            logger.warning(f"🚫 EMAIL DISCOVERY UNAVAILABLE: Hunter.io API key required for {title} at {company}")
            return None
        
        try:
            return self._find_email_with_hunter(title, company)
        except Exception as e:
            logger.error(f"Error finding email for {title} at {company}: {e}")
            return None
    

    
    def _find_email_with_hunter(self, title: str, company: str) -> Optional[str]:
        """Find email address using Hunter.io API"""
        try:
            # Extract domain from company name (simplified)
            if not company:
                return None
            domain = f"{company.lower().replace(' ', '').replace('inc', '').replace('corp', '')}.com"
            
            url = "https://api.hunter.io/v2/domain-search"
            params = {
                "domain": domain,
                "api_key": self.hunter_api_key,
                "position": title,
                "limit": 5
            }
            
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                emails = data.get("data", {}).get("emails", [])
                for e in emails:
                    if e.get("confidence", 0) > 50:  # Only high confidence emails
                        return e.get("value")
            
            return None
        except Exception as e:
            logger.error(f"Hunter.io API error: {e}")
            return None
    
    def calculate_lead_score(self, contact: Dict[str, Any], job: Dict[str, Any], has_ta_team: bool) -> float:
        """Calculate a lead quality score"""
        score = 0.0
        
        # Base score from contact title
                    title = (contact.get("title") or "").lower()
        for word in title.split():
            if word in self.title_rank:
                score += self.title_rank[word]
        
        # Company size bonus (approximate based on job posting frequency)
        company = job.get("company", "")
        if len(company) > 20:  # Longer names often indicate larger companies
            score += 1
        
        # Talent acquisition team bonus
        if has_ta_team:
            score += 2
        
        # Job posting freshness
        if job.get("date_posted"):
            score += 1
        
        # Salary information available
        if job.get("salary"):
            score += 0.5
        
        return min(score, 10.0)  # Cap at 10
