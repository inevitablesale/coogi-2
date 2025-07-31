import os
import logging
import requests
import json
import time
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ProxyManager:
    """Manages rotating proxies for API calls"""
    
    def __init__(self):
        self.proxies = []
        self.current_proxy_index = 0
        self.last_proxy_refresh = 0
        self.proxy_refresh_interval = 300  # 5 minutes
        # Don't load proxies during initialization to avoid blocking startup
        # They will be loaded on first use
    
    def _load_free_proxies(self):
        """Load free proxies from various sources"""
        try:
            # Free proxy list from multiple sources
            proxy_sources = [
                "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
            ]
            
            for source in proxy_sources:
                try:
                    response = requests.get(source, timeout=5)
                    if response.status_code == 200:
                        proxy_lines = response.text.strip().split('\n')
                        for line in proxy_lines:
                            if ':' in line and line.strip():
                                # Format: ip:port
                                proxy = line.strip()
                                if self._test_proxy(proxy):
                                    self.proxies.append(proxy)
                                    logger.info(f"✅ Added working proxy: {proxy}")
                except Exception as e:
                    logger.warning(f"Failed to load proxies from {source}: {e}")
            
            # Add some reliable free proxies as fallback
            fallback_proxies = [
                "http://proxy.proxycrawl.com:8080",
                "http://proxy.proxycrawl.com:8081",
                "http://proxy.proxycrawl.com:8082"
            ]
            
            for proxy in fallback_proxies:
                if self._test_proxy(proxy):
                    self.proxies.append(proxy)
            
            logger.info(f"🔄 Loaded {len(self.proxies)} working proxies")
            
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
            # Fallback to no proxies
            self.proxies = []
            logger.info("🔄 Will use direct connections (no proxies)")
    
    def _test_proxy(self, proxy: str) -> bool:
        """Test if a proxy is working"""
        try:
            proxies = {"http": proxy, "https": proxy}
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy in rotation"""
        # Only load proxies if we haven't tried yet and haven't loaded any
        if not self.proxies and self.last_proxy_refresh == 0:
            # Start loading proxies in background (non-blocking)
            try:
                self._load_free_proxies()
            except Exception as e:
                logger.warning(f"Failed to load proxies: {e}")
                self.proxies = []
        
        # If no proxies available, return None (will use direct connection)
        if not self.proxies:
            return None
        
        # Refresh proxies if needed
        if time.time() - self.last_proxy_refresh > self.proxy_refresh_interval:
            try:
                self._load_free_proxies()
            except Exception as e:
                logger.warning(f"Failed to refresh proxies: {e}")
        
        # Get next proxy
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        return {"http": proxy, "https": proxy}
    
    def mark_proxy_failed(self, proxy_dict: Dict[str, str]):
        """Mark a proxy as failed and remove it"""
        if not proxy_dict:
            return
        
        failed_proxy = proxy_dict.get("http", "") or proxy_dict.get("https", "")
        if failed_proxy in self.proxies:
            self.proxies.remove(failed_proxy)
            logger.warning(f"❌ Removed failed proxy: {failed_proxy}")
            
            # If we're running low on proxies, refresh
            if len(self.proxies) < 5:
                self._load_free_proxies()

class JobScraper:
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.proxy_manager = ProxyManager()
        
        # US cities for comprehensive search
        self.us_cities = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
            "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
            "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC",
            "San Francisco, CA", "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Washington, DC",
            "Boston, MA", "El Paso, TX", "Nashville, TN", "Detroit, MI", "Oklahoma City, OK",
            "Portland, OR", "Las Vegas, NV", "Memphis, TN", "Louisville, KY", "Baltimore, MD",
            "Milwaukee, WI", "Albuquerque, NM", "Tucson, AZ", "Fresno, CA", "Sacramento, CA",
            "Mesa, AZ", "Kansas City, MO", "Atlanta, GA", "Long Beach, CA", "Colorado Springs, CO",
            "Raleigh, NC", "Miami, FL", "Virginia Beach, VA", "Omaha, NE", "Oakland, CA",
            "Minneapolis, MN", "Tampa, FL", "Tulsa, OK", "Arlington, TX", "New Orleans, LA",
            "Wichita, KS", "Cleveland, OH", "Bakersfield, CA", "Aurora, CO", "Anaheim, CA"
        ]
        
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse user query using OpenAI to extract JobSpy parameters
        """
        logger.info(f"🔍 Parsing query: {query}")
        
        try:
            # Use OpenAI to parse the query
            import openai
            
            system_prompt = """
            You are a job search parameter parser. Given a user's job search query, extract the relevant parameters for JobSpy API.
            
            Return a JSON object with these fields:
            - search_term: The main job title/role being searched for
            - location: Specific city/state or "United States" for nationwide
            - hours_old: How far back to search (default 720 for 1 month)
            - job_type: "fulltime", "parttime", "internship", or "contract"
            - is_remote: true/false based on remote work preference
            - site_name: Array of job boards ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"] for US
            - results_wanted: Number of results per site (default 200)
            - offset: Starting position (default 0)
            - distance: Search radius in miles (default 25)
            - easy_apply: true/false for easy apply filter
            - country_indeed: "us" for United States
            - google_search_term: Specific Google search term if needed
            - linkedin_fetch_description: true for detailed descriptions
            - verbose: false for production
            
            IMPORTANT: If a specific city/state is mentioned in the query, use that exact location. Only use "United States" if no specific location is mentioned or if the query explicitly asks for nationwide/remote jobs.
            
            Examples:
            - "python developers in san francisco" → {"search_term": "python developer", "location": "San Francisco, CA", "is_remote": false}
            - "remote software engineers" → {"search_term": "software engineer", "location": "United States", "is_remote": true}
            - "marketing managers in new york" → {"search_term": "marketing manager", "location": "New York, NY", "is_remote": false}
            - "lawyer attorney in new york" → {"search_term": "lawyer attorney", "location": "New York, NY", "is_remote": false}
            - "nurses in chicago" → {"search_term": "nurse", "location": "Chicago, IL", "is_remote": false}
            """
            
            # Initialize OpenAI client with API key
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Parse this job search query: {query}"}
                ],
                temperature=0.1
            )
            
            # Parse the response
            content = response.choices[0].message.content
            import json
            parsed_params = json.loads(content)
            
            # Set defaults for missing fields
            defaults = {
                "hours_old": 720,
                "job_type": "fulltime",
                "is_remote": True,
                "site_name": ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"],
                "results_wanted": 200,
                "offset": 0,
                "distance": 25,
                "easy_apply": False,
                "country_indeed": "us",
                "google_search_term": "",
                "linkedin_fetch_description": True,
                "verbose": False
            }
            
            # Merge with defaults
            for key, default_value in defaults.items():
                if key not in parsed_params:
                    parsed_params[key] = default_value
            
            logger.info(f"✅ Parsed query parameters: {parsed_params}")
            return parsed_params
            
        except Exception as e:
            logger.error(f"Error parsing query with OpenAI: {e}")
            # Fallback to basic parsing
            return {
                "search_term": query,
                "location": "United States",
                "hours_old": 720,
                "job_type": "fulltime",
                "is_remote": True,
                "site_name": ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"],
                "results_wanted": 200,
                "offset": 0,
                "distance": 25,
                "easy_apply": False,
                "country_indeed": "us",
                "google_search_term": "",
                "linkedin_fetch_description": True,
                "verbose": False
            }
        
    def search_jobs(self, search_params: Dict[str, Any] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for jobs using JobSpy API with city variant strategy
        Accepts either a search_params dictionary or individual parameters
        """
        # Handle both dictionary and individual parameters
        if search_params is not None:
            # Extract parameters from dictionary
            search_term = search_params.get("search_term", "")
            location = search_params.get("location", "United States")
            hours_old = search_params.get("hours_old", 720)
            job_type = search_params.get("job_type", "fulltime")
            is_remote = search_params.get("is_remote", True)
            site_name = search_params.get("site_name", ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"])
            results_wanted = search_params.get("results_wanted", 200)
            offset = search_params.get("offset", 0)
            distance = search_params.get("distance", 25)
            easy_apply = search_params.get("easy_apply", False)
            country_indeed = search_params.get("country_indeed", "us")
            google_search_term = search_params.get("google_search_term", "")
            linkedin_fetch_description = search_params.get("linkedin_fetch_description", True)
            verbose = search_params.get("verbose", False)
            max_results = search_params.get("max_results", 500)
        else:
            # Use individual parameters
            search_term = kwargs.get("search_term", "")
            location = kwargs.get("location", "United States")
            hours_old = kwargs.get("hours_old", 720)
            job_type = kwargs.get("job_type", "fulltime")
            is_remote = kwargs.get("is_remote", True)
            site_name = kwargs.get("site_name", ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"])
            results_wanted = kwargs.get("results_wanted", 200)
            offset = kwargs.get("offset", 0)
            distance = kwargs.get("distance", 25)
            easy_apply = kwargs.get("easy_apply", False)
            country_indeed = kwargs.get("country_indeed", "us")
            google_search_term = kwargs.get("google_search_term", "")
            linkedin_fetch_description = kwargs.get("linkedin_fetch_description", True)
            verbose = kwargs.get("verbose", False)
            max_results = kwargs.get("max_results", 500)
        
        logger.info(f"🔍 Searching jobs: {search_term} in {location}")
        
        # Default site names for US searches
        if site_name is None:
            site_name = ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"]
        
        all_jobs = []
        processed_companies = set()
        processed_company_domains = {}  # Cache domains by company name
        
        # Search across multiple US cities for better coverage
        if location.lower() in ["united states", "us", "usa"]:
            # Search across all US cities for comprehensive coverage
            search_locations = self.us_cities
            logger.info(f"🏙️  Searching across {len(search_locations)} US cities")
        else:
            search_locations = [location]
            logger.info(f"🏙️  Searching in {location}")
            
        # Search each city and collect unique jobs with rate limiting
        for i, search_location in enumerate(search_locations):
            try:
                logger.info(f"🌐 Calling your JobSpy API for {search_term} in {search_location}")
                
                # Call JobSpy API for this location
                city_jobs = self._call_jobspy_api(
                    search_term=search_term,
                    location=search_location,
                    hours_old=hours_old,
                    job_type=job_type,
                    is_remote=is_remote,
                    site_name=site_name,
                    results_wanted=results_wanted,
                    offset=offset,
                    distance=distance,
                    easy_apply=easy_apply,
                    country_indeed=country_indeed,
                    google_search_term=google_search_term,
                    linkedin_fetch_description=linkedin_fetch_description,
                    verbose=verbose
                )
                
                # Process jobs from this city
                for job in city_jobs:
                    company = job.get('company', '')
                    job_key = f"{job.get('title', '')}-{company}-{job.get('job_url', '')}"
                    
                    if company and job_key not in processed_companies:
                        processed_companies.add(job_key)
                        
                        # Add domain finding for company website (cache by company name)
                        if not job.get('company_website'):
                            if company not in processed_company_domains:
                                processed_company_domains[company] = self._find_company_domain(company)
                            job['company_website'] = processed_company_domains[company]
                        
                        all_jobs.append(job)
                
                logger.info(f"✅ Your JobSpy API returned {len(city_jobs)} jobs (total: {len(all_jobs)}) for {search_location}")
                
                # Rate limiting: Add delay between API calls to avoid overwhelming the server
                if i < len(search_locations) - 1:  # Don't delay after the last city
                    delay = 5  # 5 seconds between calls (increased from 2)
                    logger.info(f"⏳ Rate limiting: Waiting {delay} seconds before next city...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error searching in {search_location}: {e}")
                continue
        
        logger.info(f"📊 Total unique jobs found: {len(all_jobs)}")
        return all_jobs[:max_results]
        
    def _call_jobspy_api(self, search_term: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        """Make actual JobSpy API call to your Railway endpoint with proxy rotation"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Your custom JobSpy API endpoint
                url = "https://coogi-jobspy-production.up.railway.app/jobs"
                
                params = {
                    "query": search_term,
                    "location": location,
                    "hours_old": kwargs.get('hours_old', 720),
                    "job_type": kwargs.get('job_type', 'fulltime'),
                    "is_remote": kwargs.get('is_remote', True),
                    "site_name": kwargs.get('site_name', ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"]),
                    "results_wanted": kwargs.get('results_wanted', 200),
                    "offset": kwargs.get('offset', 0),
                    "distance": kwargs.get('distance', 50),
                    "easy_apply": kwargs.get('easy_apply', False),
                    "country_indeed": kwargs.get('country_indeed', 'us'),
                    "google_search_term": kwargs.get('google_search_term', ''),
                    "linkedin_fetch_description": kwargs.get('linkedin_fetch_description', True),
                    "verbose": kwargs.get('verbose', 1)
                }
                
                # Get a proxy for the API call (non-blocking)
                proxy_dict = self.proxy_manager.get_next_proxy()
                if not proxy_dict:
                    logger.info("🌐 Making direct JobSpy API call (no proxies available)")
                    proxy_dict = None
                else:
                    proxy_info = f" via proxy {list(proxy_dict.values())[0]}"
                    logger.info(f"🌐 Calling your JobSpy API for {search_term} in {location}{proxy_info}")
                
                logger.info(f"🌐 Making JobSpy API request to {url}")
                response = requests.get(url, params=params, proxies=proxy_dict, timeout=30)
                logger.info(f"🌐 JobSpy API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get('jobs', [])
                    total_jobs = data.get('total_jobs', 0)
                    logger.info(f"✅ Your JobSpy API returned {len(jobs)} jobs (total: {total_jobs}) for {location}")
                    return jobs
                else:
                    logger.error(f"❌ JobSpy API error: {response.status_code} - {response.text}")
                    if proxy_dict:
                        self.proxy_manager.mark_proxy_failed(proxy_dict)
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"🔄 Retrying... (attempt {retry_count + 1}/{max_retries})")
                        time.sleep(2)  # Brief delay before retry
                    continue
                    
            except requests.exceptions.Timeout as e:
                logger.error(f"❌ JobSpy API timeout: {e}")
                if proxy_dict:
                    self.proxy_manager.mark_proxy_failed(proxy_dict)
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying after timeout... (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(2)  # Brief delay before retry
                continue
            except requests.exceptions.ConnectionError as e:
                logger.error(f"❌ JobSpy API connection error: {e}")
                if proxy_dict:
                    self.proxy_manager.mark_proxy_failed(proxy_dict)
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying after connection error... (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(2)  # Brief delay before retry
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ JobSpy API request error: {e}")
                if proxy_dict:
                    self.proxy_manager.mark_proxy_failed(proxy_dict)
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying after request error... (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(2)  # Brief delay before retry
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error in JobSpy API call: {e}")
                return []
        
        logger.error(f"❌ JobSpy API call failed after {max_retries} retries")
        return []
            
    def _find_company_domain(self, company_name: str) -> Optional[str]:
        """Find company website domain using Clearout API with proxy rotation"""
        try:
            url = "https://api.clearout.io/public/companies/autocomplete"
            params = {"query": company_name}
            
            # Get a proxy for the API call (non-blocking)
            proxy_dict = self.proxy_manager.get_next_proxy()
            if not proxy_dict:
                logger.info("🌐 Making direct domain finding call (no proxies available)")
                proxy_dict = None
            
            response = requests.get(url, params=params, proxies=proxy_dict, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('data'):
                    # Get the best match with highest confidence
                    best_match = None
                    best_confidence = 0
                    
                    for company in data['data']:
                        confidence = company.get('confidence_score', 0)
                        if confidence > best_confidence and confidence >= 50:
                            best_confidence = confidence
                            best_match = company.get('domain')
                    
                    if best_match:
                        logger.info(f"🌐 Found domain for {company_name}: {best_match}")
                        return best_match
            
            logger.warning(f"⚠️  No domain found for {company_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Domain finding failed for {company_name}: {e}")
            if proxy_dict:
                self.proxy_manager.mark_proxy_failed(proxy_dict)
            return None
        
    def extract_keywords(self, job_description: str) -> List[str]:
        """Extract keywords from job description"""
        # Mock implementation - in real implementation this would use NLP
        # For now, return some common keywords
        common_keywords = ["python", "developer", "software", "engineering", "programming"]
        return common_keywords 