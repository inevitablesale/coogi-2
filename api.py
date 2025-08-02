from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import utility modules
from utils.job_scraper import JobScraper
from utils.contact_finder import ContactFinder
from utils.email_generator import EmailGenerator
from utils.memory_manager import MemoryManager
from utils.contract_analyzer import ContractAnalyzer
from utils.instantly_manager import InstantlyManager
from utils.blacklist_manager import BlacklistManager
from utils.supabase_tracker import CompanyProcessingTracker
import requests  # Add missing import for company analysis API calls
import time  # Add time import for rate limiting
import json
import asyncio
import httpx

# Supabase setup (optional - will work without it)
try:
    from supabase import create_client, Client
    supabase_url = os.getenv("SUPABASE_URL")
    
    # Try service role key first (bypasses RLS), then fallback to anonymous key
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if supabase_url and supabase_key:
        supabase: Client = create_client(supabase_url, supabase_key)
        key_type = "service_role" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "anonymous"
        logger.info(f"✅ Supabase client initialized with {key_type} key")
    else:
        supabase = None
        logger.warning("⚠️  Supabase credentials not found - database operations disabled")
        
except ImportError:
    supabase = None
    logger.warning("⚠️  Supabase library not installed - database operations disabled")

# Rate Limiter for RapidAPI (20 requests per minute)
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

# Initialize rate limiter
rate_limiter = RateLimiter(max_requests=20, time_window=60)

# Global search cancellation tracking
active_searches = {}  # batch_id -> cancellation flag

# User authentication
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from authorization header"""
    if not authorization:
        logger.warning("No authorization header provided")
        return {"user_id": "default_user", "email": "default@example.com"}
    
    try:
        # In production, validate JWT token here
        # For now, extract user info from header if present
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            logger.info(f"Processing Bearer token: {token[:20]}...")
            
            # Try to decode JWT token (Supabase Auth)
            try:
                import jwt
                # Decode without verification for now (in production, verify with Supabase public key)
                decoded = jwt.decode(token, options={"verify_signature": False})
                logger.info(f"JWT decoded successfully: {decoded}")
                
                user_id = decoded.get("sub", "unknown")
                email = decoded.get("email", "unknown@example.com")
                
                logger.info(f"Extracted user_id: {user_id}, email: {email}")
                return {"user_id": user_id, "email": email}
                
            except Exception as jwt_error:
                logger.warning(f"JWT decode failed: {jwt_error}")
                
                # Fallback to simple token parsing for development
                if token == "default_token":
                    return {"user_id": "default_user", "email": "default@example.com"}
                else:
                    # Assume token contains user info in format "user_id:email"
                    parts = token.split(":")
                    if len(parts) == 2:
                        return {"user_id": parts[0], "email": parts[1]}
                    else:
                        # If token doesn't match expected format, use it as user_id
                        return {"user_id": token, "email": f"{token}@example.com"}
        else:
            logger.warning(f"Authorization header doesn't start with 'Bearer ': {authorization[:20]}...")
        
        return {"user_id": "default_user", "email": "default@example.com"}
    except Exception as e:
        logger.error(f"Error parsing authorization header: {e}")
        return {"user_id": "default_user", "email": "default@example.com"}

# Real-time logging to Supabase
async def log_to_supabase(batch_id: str, message: str, level: str = "info", company: str = None, 
                          job_title: str = None, job_url: str = None, processing_stage: str = None):
    """Send log message directly to Supabase in real-time"""
    if not supabase:
        return
    
    try:
        log_data = {
            "batch_id": batch_id,
            "message": message,
            "level": level,
            "company": company,
            "job_title": job_title,
            "job_url": job_url,
            "processing_stage": processing_stage,
            "timestamp": datetime.now().isoformat()
        }
        
        # Try enhanced table first, fallback to old table
        try:
            supabase.table("search_logs_enhanced").insert(log_data).execute()
        except Exception:
            # Fallback to old table
            basic_log_data = {
                "batch_id": batch_id,
                "message": message,
                "level": level,
                "company": company,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("search_logs").insert(basic_log_data).execute()
        
    except Exception as e:
        # Fallback to console logging if Supabase fails
        logger.error(f"Failed to log to Supabase: {e}")
        logger.info(f"[{batch_id}] {message}")

app = FastAPI(
    title="MCP: Master Control Program API",
    description="Automated recruiting and outreach platform API",
    version="1.0.0"
)

# Serve static files (CSS, JS, images)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    """Serve the login page"""
    try:
        with open("templates/login.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <head><title>Coogi Login</title></head>
        <body>
            <h1>Login Not Found</h1>
            <p>The login template file is missing. Please ensure templates/login.html exists.</p>
        </body>
        </html>
        """, status_code=404)

@app.get("/signup", response_class=HTMLResponse)
async def get_signup():
    """Serve the signup page"""
    try:
        with open("templates/signup.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <head><title>Coogi Signup</title></head>
        <body>
            <h1>Signup Not Found</h1>
            <p>The signup template file is missing. Please ensure templates/signup.html exists.</p>
        </body>
        </html>
        """, status_code=404)

@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    """Serve the web UI"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <head><title>Coogi UI</title></head>
        <body>
            <h1>UI Not Found</h1>
            <p>The UI template file is missing. Please ensure templates/index.html exists.</p>
        </body>
        </html>
        """, status_code=404)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the new dashboard UI"""
    try:
        with open("templates/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <head><title>Coogi Dashboard</title></head>
        <body>
            <h1>Dashboard Not Found</h1>
            <p>The dashboard template file is missing. Please ensure templates/dashboard.html exists.</p>
        </body>
        </html>
        """, status_code=404)

@app.get("/agent-detail", response_class=HTMLResponse)
async def get_agent_detail():
    """Serve the agent detail page"""
    try:
        with open("templates/agent_detail.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <head><title>Agent Detail - Coogi</title></head>
        <body>
            <h1>Agent Detail Not Found</h1>
            <p>The agent detail template file is missing. Please ensure templates/agent_detail.html exists.</p>
        </body>
        </html>
        """, status_code=404)

# Initialize services
job_scraper = JobScraper()
contact_finder = ContactFinder()
email_generator = EmailGenerator()
memory_manager = MemoryManager()
contract_analyzer = ContractAnalyzer()
instantly_manager = InstantlyManager()
blacklist_manager = BlacklistManager()
# company_analyzer = CompanyAnalyzer(rapidapi_key=os.getenv("RAPIDAPI_KEY", ""))  # Will be initialized after import

# Request/Response Models
class JobSearchRequest(BaseModel):
    query: str
    hours_old: int = 720  # Default to 1 month for broader results
    enforce_salary: bool = True
    auto_generate_messages: bool = False
    create_campaigns: bool = True  # Default to True - automatically create Instantly campaigns
    campaign_name: Optional[str] = None  # Optional: custom campaign name
    min_score: float = 0.5  # Minimum lead score for campaign inclusion
    custom_tags: Optional[List[str]] = None  # Optional: custom tags to add to leads

class Lead(BaseModel):
    name: str
    title: str
    company: str
    email: str
    job_title: str
    job_url: str
    message: str = ""
    score: float
    timestamp: str

class JobSearchResponse(BaseModel):
    companies_analyzed: List[Dict[str, Any]]
    jobs_found: int
    total_processed: int
    search_query: str
    timestamp: str
    campaigns_created: Optional[List[str]] = None  # List of campaign IDs created
    leads_added: int = 0  # Total leads added to campaigns

class RawJobSpyResponse(BaseModel):
    jobs: List[Dict[str, Any]]
    total_jobs: int
    search_query: str
    location: str
    timestamp: str

class MessageGenerationRequest(BaseModel):
    job_title: str
    company: str
    contact_title: str
    job_url: str
    tone: str = "professional"
    additional_context: str = ""

class MessageGenerationResponse(BaseModel):
    message: str
    subject_line: str
    timestamp: str

class CompanyAnalysisRequest(BaseModel):
    query: str
    include_job_data: bool = True
    max_companies: int = 10

class CompanySkipReason(BaseModel):
    company: str
    reason: str
    ta_roles: List[str]
    timestamp: str

class CompanyReport(BaseModel):
    company: str
    has_ta_team: bool
    ta_roles: List[str]
    job_count: int
    active_jobs: List[Dict[str, Any]]
    decision_makers: List[Dict[str, Any]]
    recommendation: str
    skip_reason: Optional[str]

class CompanyAnalysisResponse(BaseModel):
    target_companies: List[CompanyReport]
    skipped_companies: List[CompanySkipReason]
    summary: Dict[str, Any]
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    api_status: Dict[str, bool]
    demo_mode: bool

class ContractOpportunityRequest(BaseModel):
    query: str
    max_companies: int = 20

class ContractOpportunity(BaseModel):
    company: str
    total_positions: int
    total_candidate_salaries: int
    estimated_recruiting_fees: int
    contract_value_score: float
    urgency_indicators: int
    growth_indicators: int
    seniority_score: float
    departments: List[str]
    locations: List[str]
    role_types: List[str]
    recruiting_pitch: str
    jobs: List[Dict[str, Any]]

class ContractAnalysisResponse(BaseModel):
    opportunities: List[ContractOpportunity]
    summary: Dict[str, Any]
    timestamp: str

class InstantlyCampaignRequest(BaseModel):
    query: str
    campaign_name: Optional[str] = None
    max_leads: int = 20
    min_score: float = 0.5

class InstantlyCampaignResponse(BaseModel):
    campaign_id: Optional[str]
    campaign_name: str
    leads_added: int
    total_leads_found: int
    status: str
    timestamp: str

class CompanyJobsRequest(BaseModel):
    company_name: str
    max_pages: int = 3

class CompanyJobsResponse(BaseModel):
    company: str
    total_jobs: int
    jobs: List[Dict[str, Any]]
    timestamp: str

# Add webhook models for production architecture
class WebhookResult(BaseModel):
    company: str
    job_title: str
    job_url: str
    has_ta_team: bool
    contacts_found: int
    top_contacts: List[Dict[str, Any]]
    recommendation: str
    hunter_emails: List[str] = []
    instantly_campaign_id: Optional[str] = None
    timestamp: str

class WebhookRequest(BaseModel):
    batch_id: str
    results: List[WebhookResult]
    summary: Dict[str, Any]
    timestamp: str

# API Endpoints
@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment variables"""
    return {
        "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT SET",
        "HUNTER_API_KEY": "SET" if os.getenv("HUNTER_API_KEY") else "NOT SET", 
        "INSTANTLY_API_KEY": "SET" if os.getenv("INSTANTLY_API_KEY") else "NOT SET",
        "RAPIDAPI_KEY": "SET" if os.getenv("RAPIDAPI_KEY") else "NOT SET",
        "CLEAROUT_API_KEY": "SET" if os.getenv("CLEAROUT_API_KEY") else "NOT SET",
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": "SET" if os.getenv("SUPABASE_ANON_KEY") else "NOT SET",
        "SUPABASE_SERVICE_ROLE_KEY": "SET" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "NOT SET",
        "current_supabase_key_type": "service_role" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "anonymous",
        "supabase_client_exists": bool(supabase),
        "all_env_vars": {k: v for k, v in os.environ.items() if "SUPABASE" in k}
    }

@app.get("/debug/agents-table")
async def debug_agents_table():
    """Debug agents table access"""
    try:
        if not supabase:
            return {"error": "Supabase client not initialized"}
        
        # Test 1: Direct query without RLS
        logger.info("🔍 Testing direct agents table query...")
        direct_result = supabase.table("agents").select("*").execute()
        logger.info(f"Direct query result: {len(direct_result.data)} agents")
        
        # Test 2: Query with service role (if available)
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if service_key:
            logger.info("🔍 Testing with service role key...")
            service_client = create_client(supabase_url, service_key)
            service_result = service_client.table("agents").select("*").execute()
            logger.info(f"Service role query result: {len(service_result.data)} agents")
        else:
            logger.warning("⚠️ No service role key found")
            service_result = {"data": []}
        
        return {
            "direct_query_count": len(direct_result.data),
            "service_role_count": len(service_result.data),
            "direct_query_sample": direct_result.data[:2] if direct_result.data else [],
            "service_role_sample": service_result.data[:2] if service_result.data else [],
            "supabase_url": supabase_url,
            "has_service_key": bool(service_key),
            "has_anon_key": bool(supabase_key)
        }
        
    except Exception as e:
        logger.error(f"Error debugging agents table: {e}")
        return {"error": str(e)}

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    api_status = {
        "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
        "RapidAPI": bool(os.getenv("RAPIDAPI_KEY")),
        "Hunter.io": bool(os.getenv("HUNTER_API_KEY")),
        "Instantly.ai": bool(os.getenv("INSTANTLY_API_KEY")),
        "JobSpy_API": True  # Using external API
    }
    
    # Only email discovery is in demo mode without Hunter.io
    demo_mode = not bool(os.getenv("HUNTER_API_KEY"))
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        api_status=api_status,
        demo_mode=demo_mode
    )

@app.get("/lead-lists")
async def get_lead_lists():
    """Get all lead lists from Instantly"""
    try:
        lead_lists = instantly_manager.get_lead_lists()
        return {
            "status": "success",
            "lead_lists": lead_lists,
            "count": len(lead_lists)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/lead-lists/cleanup")
async def cleanup_lead_lists(days_old: int = 7):
    """Clean up old lead lists"""
    try:
        deleted_count = instantly_manager.cleanup_old_lead_lists(days_old)
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old lead lists"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """Search for jobs and analyze companies for recruiting opportunities"""
    try:
        # Generate batch ID for logging
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize company processing tracker
        tracker = CompanyProcessingTracker(batch_id)
        
        # Parse query
        search_params = job_scraper.parse_query(request.query)
        
        # Override hours_old with request parameter if provided
        if request.hours_old != 720:  # If not default
            search_params['hours_old'] = request.hours_old
            logger.info(f"🔍 Overriding hours_old to {request.hours_old} hours")
            await log_to_supabase(batch_id, f"🔍 Overriding hours_old to {request.hours_old} hours", "info")
        
        # Search jobs city by city and process each city's companies immediately
        await log_to_supabase(batch_id, f"🚀 Starting job search: {request.query}", "info")
        
        # Initialize tracking variables
        processed_companies = set()
        companies_analyzed = []
        campaigns_created = []
        leads_added = 0
        hunter_attempts = 0
        hunter_hits = 0
        processed_count = 0
        
        # Get jobs city by city and process each city immediately
        all_jobs = []
        total_jobs_found = 0
        
        # Process each city sequentially
        for city in job_scraper.us_cities[:10]:  # Limit to first 10 cities for testing
            await log_to_supabase(batch_id, f"🏙️ Processing city: {city}", "info")
            
            try:
                # Get jobs for this specific city
                city_jobs = job_scraper._call_jobspy_api(
                    search_term=search_params.get('search_term', ''),
                    location=city,
                    hours_old=search_params.get('hours_old', 720),
                    job_type=search_params.get('job_type', ''),
                    is_remote=search_params.get('is_remote', False),
                    site_name=search_params.get('site_name', ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"]),
                    results_wanted=search_params.get('results_wanted', 200),
                    offset=search_params.get('offset', 0),
                    distance=search_params.get('distance', 25),
                    easy_apply=search_params.get('easy_apply', False),
                    country_indeed=search_params.get('country_indeed', 'us'),
                    google_search_term=search_params.get('google_search_term', ''),
                    linkedin_fetch_description=search_params.get('linkedin_fetch_description', False),
                    verbose=search_params.get('verbose', False)
                )
                
                if not city_jobs:
                    await log_to_supabase(batch_id, f"⚠️ No jobs found in {city}", "warning")
                    continue
                
                await log_to_supabase(batch_id, f"✅ Found {len(city_jobs)} jobs in {city}", "success")
                total_jobs_found += len(city_jobs)
                
                # Process all companies in this city immediately
                city_companies_processed = 0
                for job in city_jobs:
                    # Check if already processed
                    job_fingerprint = memory_manager.create_job_fingerprint(job)
                    if memory_manager.is_job_processed(job_fingerprint):
                        continue
                    
                    company = job.get('company', '')
                    job_title = job.get('title', '')
                    job_url = job.get('job_url', '')
                    
                    # Skip if we've already analyzed this company
                    if company in processed_companies:
                        logger.info(f"Skipping {company} - already analyzed")
                        memory_manager.mark_job_processed(job_fingerprint)
                        continue
                    
                    # Check blacklist BEFORE making any API calls
                    if blacklist_manager.is_blacklisted(company):
                        logger.info(f"⏭️  Skipping {company} - blacklisted")
                        memory_manager.mark_job_processed(job_fingerprint)
                        continue
                    
                    # Process this company through the complete flow
                    await log_to_supabase(batch_id, f"🔍 Processing company: {company} - {job_title}", "info", company, job_title, job_url, "company_start")
            
                    try:
                        # STEP 1: Domain Search
                        import asyncio
                        
                        # Make domain finding call async using httpx
                        # Inline domain finding logic
                        try:
                                url = "https://api.clearout.io/public/companies/autocomplete"
                                params = {"query": company}
                                
                                logger.info(f"🌐 Making domain finding call for {company}")
                                async with httpx.AsyncClient() as client:
                                    response = await client.get(url, params=params, timeout=30.0)
                                    
                                    logger.info(f"🌐 Clearout API response status: {response.status_code}")
                                    logger.info(f"🌐 Clearout API response text: {response.text}")
                                    
                                    if response.status_code == 200:
                                        data = response.json()
                                        logger.info(f"🌐 Clearout API parsed data: {data}")
                                        
                                        if data.get('status') == 'success' and data.get('data'):
                                            # Get the best match with highest confidence
                                            best_match = None
                                            best_confidence = 0
                                            
                                            logger.info(f"🌐 Processing {len(data['data'])} companies from Clearout API")
                                            
                                            for company_data in data['data']:
                                                confidence = company_data.get('confidence_score', 0)
                                                found_domain = company_data.get('domain')
                                                logger.info(f"🌐 Company: {company_data.get('name', 'Unknown')}, Domain: {found_domain}, Confidence: {confidence}")
                                                
                                                if confidence > best_confidence and confidence >= 50:
                                                    best_confidence = confidence
                                                    best_match = found_domain
                                            
                                            if best_match:
                                                logger.info(f"🌐 Found domain for {company}: {best_match}")
                                                domain = best_match
                                            else:
                                                logger.warning(f"⚠️  No high-confidence domain found for {company} (best confidence: {best_confidence})")
                                        else:
                                            logger.warning(f"⚠️  Clearout API failed for {company}: {data.get('message', 'Unknown error')}")
                                    else:
                                        logger.warning(f"⚠️  Clearout API error for {company}: {response.status_code}")
                                
                                if not domain:
                                    logger.warning(f"⚠️  No domain found for {company}")
                                    
                        except Exception as e:
                            logger.error(f"❌ Domain finding failed for {company}: {e}")
                        
                        domain = None
                        logger.info(f"🌐 Domain result for {company}: {domain}")
                        job['company_website'] = domain
                        
                        # Log domain status before Hunter.io
                        if domain:
                            await log_to_supabase(batch_id, f"✅ Domain found for {company}: {domain}", "success", company, job_title, job_url, "domain_found")
                        else:
                            await log_to_supabase(batch_id, f"⚠️ No domain found for {company} - Hunter.io may still work with internal domain finding", "warning", company, job_title, job_url, "domain_not_found")
                
                        # STEP 2: LinkedIn Resolution (via OpenAI batch analysis)
                        analysis = contact_finder.batch_analyze_companies([company]).get(company, {})
                        linkedin_identifier = analysis.get('linkedin_identifier', company.lower().replace(" ", "-"))
                        tracker.save_linkedin_resolution(company, linkedin_identifier)
                        
                        # STEP 3: RapidAPI Analysis
                        description = job.get('description') or job.get('job_level') or ''
                        result = contact_finder.find_contacts(
                            company=company,
                            linkedin_identifier=linkedin_identifier,
                            role_hint=job_title,
                            keywords=job_scraper.extract_keywords(description),
                            company_website=domain
                        )
                        
                        contacts, has_ta_team, employee_roles, company_found = result
                        await log_to_supabase(batch_id, f"📊 Found {len(contacts)} contacts, TA team: {has_ta_team}", "info", company, job_title, job_url, "contact_analysis")
                        tracker.save_rapidapi_analysis(company, has_ta_team, contacts, employee_roles, company_found)
                        
                        # STEP 4: Hunter.io (if no TA team and company found)
                        hunter_emails = []
                        if not has_ta_team and company_found and domain:
                            await log_to_supabase(batch_id, f"📡 Attempting Hunter.io lookup for: {company} using domain: {domain}", "info", company, job_title, job_url, "hunter_lookup")
                        elif not has_ta_team and company_found and not domain:
                            await log_to_supabase(batch_id, f"📡 Attempting Hunter.io lookup for: {company} (no domain - Hunter.io will use internal domain finding)", "info", company, job_title, job_url, "hunter_lookup_no_domain")
                        else:
                            await log_to_supabase(batch_id, f"⏭️ Skipping Hunter.io for {company} (has TA team or company not found)", "info", company, job_title, job_url, "hunter_skipped")
                            
                        if not has_ta_team and company_found:
                            try:
                                hunter_emails = contact_finder.find_hunter_emails_for_target_company(
                                    company=company,
                                    job_title=job_title,
                                    employee_roles=employee_roles,
                                    company_website=domain
                                )
                                
                                if hunter_emails:
                                    await log_to_supabase(batch_id, f"✅ Found {len(hunter_emails)} Hunter.io emails for {company}", "success", company, job_title, job_url, "hunter_success")
                                    tracker.save_hunter_emails(company, job_title, job_url, hunter_emails)
                                    # Add a small delay to ensure database write completes
                                    await asyncio.sleep(1)
                                    await log_to_supabase(batch_id, f"💾 Saved {len(hunter_emails)} emails to database for {company}", "info", company, job_title, job_url, "database_save")
                                else:
                                    await log_to_supabase(batch_id, f"⚠️ No Hunter.io emails found for {company}", "warning", company, job_title, job_url, "hunter_no_emails")
                                    tracker.save_hunter_emails(company, job_title, job_url, [])
                                    
                            except Exception as e:
                                await log_to_supabase(batch_id, f"❌ Hunter.io error for {company}: {str(e)}", "error", company, job_title, job_url, "hunter_error")
                                tracker.save_hunter_emails(company, job_title, job_url, [], error=str(e))
                        
                        # STEP 5: Instantly.ai (if requested and emails found)
                        campaign_id = None
                        if request.create_campaigns and hunter_emails:
                            await log_to_supabase(batch_id, f"🚀 Creating Instantly campaign for {company}", "info", company, job_title, job_url, "instantly_start")
                            try:
                                # Call the Edge Function to send leads to Instantly.ai
                                import httpx
                                
                                # Prepare the request for the Edge Function
                                edge_function_url = f"{os.getenv('SUPABASE_URL', '')}/functions/v1/send-to-instantly"
                                
                                # Extract domain from Hunter.io emails
                                hunter_domain = None
                                if hunter_emails and len(hunter_emails) > 0:
                                    # Get domain from first email
                                    first_email = hunter_emails[0].get("email", "")
                                    if "@" in first_email:
                                        hunter_domain = first_email.split("@")[1]
                                
                                edge_function_payload = {
                                    "batch_id": batch_id,
                                    "action": "create_leads",
                                    "hunter_emails": hunter_emails,  # Pass emails directly
                                    "company": company,
                                    "job_title": job_title,
                                    "domain": hunter_domain  # Use domain from Hunter.io emails
                                }
                                
                                # Get the service role key for the Edge Function
                                service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
                                if not service_role_key:
                                    await log_to_supabase(batch_id, f"❌ SUPABASE_SERVICE_ROLE_KEY not configured", "error", company, job_title, job_url, "instantly_error")
                                    continue
                                
                                headers = {
                                    "Authorization": f"Bearer {service_role_key}",
                                    "Content-Type": "application/json"
                                }
                                
                                await log_to_supabase(batch_id, f"📡 Calling Edge Function to send {len(hunter_emails)} leads to Instantly.ai", "info", company, job_title, job_url, "instantly_edge_call")
                                
                                async with httpx.AsyncClient() as client:
                                    response = await client.post(
                                        edge_function_url,
                                        json=edge_function_payload,
                                        headers=headers,
                                        timeout=30.0
                                    )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    if result.get('success'):
                                        created_leads = result.get('created_leads', [])
                                        leads_added += len(created_leads)
                                        campaigns_created.append(result.get('summary', {}).get('campaign_id', ''))
                                        await log_to_supabase(batch_id, f"✅ Successfully sent {len(created_leads)} leads to Instantly.ai", "success", company, job_title, job_url, "instantly_success")
                                        tracker.save_instantly_campaign(company, result.get('summary', {}).get('campaign_id', ''), f"Coogi Agent - {company}", len(created_leads))
                                    else:
                                        await log_to_supabase(batch_id, f"❌ Edge Function returned error: {result.get('error', 'Unknown error')}", "error", company, job_title, job_url, "instantly_error")
                                        tracker.save_instantly_campaign(company, error=result.get('error', 'Edge Function error'))
                                else:
                                    await log_to_supabase(batch_id, f"❌ Edge Function call failed: {response.status_code} - {response.text}", "error", company, job_title, job_url, "instantly_error")
                                    tracker.save_instantly_campaign(company, error=f"Edge Function HTTP {response.status_code}")
                                    
                            except Exception as e:
                                await log_to_supabase(batch_id, f"❌ Error calling Edge Function for {company}: {str(e)}", "error", company, job_title, job_url, "instantly_error")
                                tracker.save_instantly_campaign(company, error=str(e))
                        
                        # Create company analysis record
                        recommendation = "SKIP - Has TA team" if has_ta_team else "PROCESS - Target company"
                        company_analysis = {
                            "company": company,
                            "job_title": job_title,
                            "job_url": job_url,
                            "has_ta_team": has_ta_team,
                            "contacts_found": len(contacts),
                            "top_contacts": contacts[:5],
                            "hunter_emails": hunter_emails,
                            "employee_roles": employee_roles,
                            "company_website": domain,
                            "company_found": company_found,
                            "recommendation": recommendation,
                            "timestamp": datetime.now().isoformat()
                        }
                        companies_analyzed.append(company_analysis)
                        
                        # Save company processing summary
                        tracker.save_company_summary(
                            company=company,
                            job_title=job_title,
                            job_url=job_url,
                            domain_found=bool(domain),
                            linkedin_resolved=True,
                            rapidapi_analyzed=True,
                            hunter_emails_found=bool(hunter_emails),
                            instantly_campaign_created=bool(campaign_id),
                            final_recommendation=recommendation
                        )
                        
                        await log_to_supabase(batch_id, f"✅ Completed analysis for {company}: {recommendation}", "success", company, job_title, job_url, "company_analysis_complete")
                        
                        # Mark as processed
                        processed_companies.add(company)
                        memory_manager.mark_job_processed(job_fingerprint)
                        processed_count += 1
                        
                        city_companies_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Error analyzing {company}: {e}")
                        await log_to_supabase(batch_id, f"❌ Error analyzing {company}: {str(e)}", "error", company, job_title, job_url, "company_error")
                        
                        # Save error summary
                        tracker.save_company_summary(
                            company=company,
                            job_title=job_title,
                            job_url=job_url,
                            domain_found=False,
                            linkedin_resolved=False,
                            rapidapi_analyzed=False,
                            hunter_emails_found=False,
                            instantly_campaign_created=False,
                            final_recommendation=f"ERROR - {str(e)}",
                            error=str(e)
                        )
                        
                        memory_manager.mark_job_processed(job_fingerprint)
                        continue
                
                # Log city completion
                await log_to_supabase(batch_id, f"✅ Completed {city}: {city_companies_processed} companies processed", "success")
                
            except Exception as e:
                logger.error(f"Error processing city {city}: {e}")
                await log_to_supabase(batch_id, f"❌ Error processing city {city}: {str(e)}", "error")
                continue
            
            # Rate limiting: Wait between cities
            if city != job_scraper.us_cities[:10][-1]:  # Not the last city
                await log_to_supabase(batch_id, "⏳ Rate limiting: Waiting 30 seconds before next city...", "info")
                time.sleep(30)
        
        # Final summary logging
        logger.info(f"📊 Hunter.io Summary: {hunter_attempts} attempts, {hunter_hits} emails found")
        await log_to_supabase(batch_id, f"📊 Hunter.io Summary: {hunter_attempts} attempts, {hunter_hits} emails found", "info")
        await log_to_supabase(batch_id, f"🎉 Search completed: {len(companies_analyzed)} companies analyzed", "success")
        
        return JobSearchResponse(
            companies_analyzed=companies_analyzed,
            jobs_found=total_jobs_found,
            total_processed=processed_count,
            search_query=request.query,
            timestamp=datetime.now().isoformat(),
            campaigns_created=campaigns_created if campaigns_created else None,
            leads_added=leads_added
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-message", response_model=MessageGenerationResponse)
async def generate_message(request: MessageGenerationRequest):
    """Generate personalized outreach message"""
    try:
        message = email_generator.generate_outreach(
            job_title=request.job_title,
            company=request.company,
            contact_title=request.contact_title,
            job_url=request.job_url,
            tone=request.tone,
            additional_context=request.additional_context
        )
        
        subject_line = email_generator.generate_subject_line(
            request.job_title,
            request.company
        )
        
        return MessageGenerationResponse(
            message=message,
            subject_line=subject_line,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error generating message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory-stats")
async def get_memory_stats():
    """Get memory/tracking statistics"""
    stats = memory_manager.get_memory_stats()
    return {"stats": stats, "timestamp": datetime.now().isoformat()}

@app.delete("/memory")
async def clear_memory():
    """Clear all memory data"""
    memory_manager.clear_memory()
    return {"message": "Memory cleared successfully", "timestamp": datetime.now().isoformat()}

@app.post("/analyze-companies", response_model=CompanyAnalysisResponse)
async def analyze_companies(request: CompanyAnalysisRequest):
    """Comprehensive company analysis with skip reporting and job data"""
    try:
        # Import here to avoid circular dependency
        from utils.company_analyzer import CompanyAnalyzer
        analyzer = CompanyAnalyzer(rapidapi_key=os.getenv("RAPIDAPI_KEY", ""))
        
        # Clear previous analysis
        analyzer.clear_skip_history()
        
        # Parse query and search for jobs
        search_params = job_scraper.parse_query(request.query)
        jobs = job_scraper.search_jobs(search_params, max_results=request.max_companies * 3)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        target_companies = []
        processed_companies = set()
        
        # Analyze unique companies
        for job in jobs:
            company = job.get('company', '')
            if not company or company in processed_companies:
                continue
            
            processed_companies.add(company)
            if len(processed_companies) > request.max_companies:
                break
            
            # Get people data from SaleLeads API with rate limiting
            try:
                people_data = []
                
                # Add delay between API calls to respect rate limits
                if processed_companies:  # Not the first company
                    time.sleep(2)  # 2 second delay between companies
                
                people_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/people"
                headers = {
                    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", ""),
                    "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
                }
                
                logger.info(f"Fetching people data for {company} (with rate limiting)")
                people_resp = requests.get(
                    people_url, 
                    params={"company": company, "page": 1}, 
                    headers=headers, 
                    timeout=15
                )
                
                if people_resp.status_code == 200:
                    people_response = people_resp.json()
                    if people_response.get("success", False):
                        people_data = people_response.get("data", [])
                        logger.info(f"Found {len(people_data)} people at {company}")
                elif people_resp.status_code == 429:
                    logger.warning(f"Rate limit hit for {company}, skipping detailed analysis")
                    # Still proceed with basic analysis without people data
                else:
                    logger.warning(f"People API failed for {company}: {people_resp.status_code}")
                
                # Analyze company
                analysis = analyzer.analyze_company(company, people_data)
                
                # Only include companies without TA teams as targets
                if not analysis.has_ta_team and analysis.decision_makers:
                    target_companies.append(CompanyReport(
                        company=analysis.company,
                        has_ta_team=analysis.has_ta_team,
                        ta_roles=analysis.ta_roles,
                        job_count=analysis.job_count,
                        active_jobs=analysis.active_jobs,
                        decision_makers=analysis.decision_makers,
                        recommendation=analysis.recommendation,
                        skip_reason=analysis.skip_reason
                    ))
                    
            except Exception as e:
                logger.error(f"Error analyzing company {company}: {e}")
                continue
        
        # Get skip report
        skip_report = analyzer.get_skip_report()
        skipped_companies = [
            CompanySkipReason(
                company=skip['company'],
                reason=skip['reason'],
                ta_roles=skip['ta_roles'],
                timestamp=skip['timestamp']
            )
            for skip in skip_report['skipped_companies']
        ]
        
        # Generate summary
        total_analyzed = len(processed_companies)
        summary = {
            "total_companies_analyzed": total_analyzed,
            "target_companies_found": len(target_companies),
            "companies_skipped": skip_report['total_skipped'],
            "skip_reasons": skip_report['skip_reasons'],
            "success_rate": round(len(target_companies) / max(total_analyzed, 1) * 100, 1)
        }
        
        return CompanyAnalysisResponse(
            target_companies=target_companies,
            skipped_companies=skipped_companies,
            summary=summary,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in company analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/raw-jobspy", response_model=RawJobSpyResponse)
async def get_raw_jobspy_results(request: JobSearchRequest):
    """Get raw JobSpy results without any processing - fastest response"""
    try:
        # Parse query quickly
        search_params = job_scraper.parse_query(request.query)
        
        # Get all available jobs - increased to allow more jobs from location variants
        jobs = job_scraper.search_jobs(search_params, max_results=500)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        logger.info(f"✅ Raw JobSpy results: {len(jobs)} jobs found")
        
        logger.info(f"🔍 DEBUG: Raw JobSpy search_params: {search_params}")
        logger.info(f"📍 Location from search_params: {search_params.get('location', 'N/A')}")
        logger.info(f"🔍 Search term from search_params: {search_params.get('search_term', 'N/A')}")
        logger.info(f"🏠 Is remote from search_params: {search_params.get('is_remote', 'N/A')}")
        
        return RawJobSpyResponse(
            jobs=jobs,
            total_jobs=len(jobs),
            search_query=request.query,
            location=search_params.get("location", "N/A"),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in raw JobSpy search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-jobs-fast", response_model=JobSearchResponse)
async def search_jobs_fast(request: JobSearchRequest):
    """Fast job search with immediate results - optimized for 30-second responses"""
    try:
        # Parse query quickly
        search_params = job_scraper.parse_query(request.query)
        
        # Get all available jobs
        jobs = job_scraper.search_jobs(search_params, max_results=20)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        companies_analyzed = []
        processed_count = 0
        
        # For immediate results, just return the JobSpy data without RapidAPI processing
        logger.info(f"Returning {len(jobs)} jobs from JobSpy without RapidAPI processing")
        
        # Create simple company analysis from JobSpy data
        for job in jobs[:10]:  # Limit to first 10 jobs for quick response
            company = job.get('company', '')
            if not company:
                continue
                
            company_analysis = {
                "company": company,
                "job_title": job.get('title', ''),
                "job_url": job.get('job_url', ''),
                "has_ta_team": False,  # Will be determined later
                "contacts_found": 0,
                "top_contacts": [],
                "recommendation": "PENDING - RapidAPI analysis required",
                "timestamp": datetime.now().isoformat()
            }
            
            companies_analyzed.append(company_analysis)
            processed_count += 1
            
        return JobSearchResponse(
            companies_analyzed=companies_analyzed,
            jobs_found=len(jobs),
            total_processed=processed_count,
            search_query=request.query,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in fast job search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-jobs-stream")
async def search_jobs_stream(request: JobSearchRequest):
    """Stream job search results for immediate feedback"""
    def generate_stream():
        try:
            # Initialize leads list
            leads = []
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting job search...', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Parse query and send update
            search_params = job_scraper.parse_query(request.query)
            search_term = search_params.get("search_term", request.query)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Searching for: {search_term}', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Search jobs - get all available jobs (increased from 50 to 500)
            jobs = job_scraper.search_jobs(search_params, max_results=500)
            yield f"data: {json.dumps({'type': 'jobs_found', 'count': len(jobs), 'timestamp': datetime.now().isoformat()})}\n\n"
            
            if not jobs:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No jobs found matching criteria', 'timestamp': datetime.now().isoformat()})}\n\n"
                return
            
            companies_analyzed = []
            processed_count = 0
            
            # Rate limiting: Process jobs in batches to respect 20 req/min limit
            # For streaming, process max 4 jobs per batch (balanced for real-time updates)
            max_jobs_per_batch = 4
            total_jobs = len(jobs)
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Processing {total_jobs} jobs in batches of {max_jobs_per_batch}', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Track companies we've already analyzed to avoid duplicate RapidAPI calls
            analyzed_companies = {}
            
            # Process jobs in batches
            for batch_start in range(0, total_jobs, max_jobs_per_batch):
                batch_end = min(batch_start + max_jobs_per_batch, total_jobs)
                batch_jobs = jobs[batch_start:batch_end]
                
                batch_msg = f'Processing batch {batch_start//max_jobs_per_batch + 1}: jobs {batch_start+1}-{batch_end}'
                yield f"data: {json.dumps({'type': 'status', 'message': batch_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                
                # Process jobs in current batch
                for i, job in enumerate(batch_jobs):
                    global_job_index = batch_start + i
                    company = job.get('company', '')
                    company_msg = f'Analyzing company {global_job_index+1}/{total_jobs}: {company}'
                    yield f"data: {json.dumps({'type': 'processing', 'message': company_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                    
                    # Check if already processed
                    job_fingerprint = memory_manager.create_job_fingerprint(job)
                    if memory_manager.is_job_processed(job_fingerprint):
                        skip_msg = f'Already processed: {company}'
                        yield f"data: {json.dumps({'type': 'skipped', 'message': skip_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                        continue
                    
                    # Check if we've already analyzed this company in this session
                    if company in analyzed_companies:
                        company_analysis = analyzed_companies[company]
                        has_ta_team = company_analysis['has_ta_team']
                        company_found = company_analysis['company_found']
                        contacts = company_analysis.get('contacts', [])
                        
                        if has_ta_team:
                            ta_msg = f'Skipping {company}: Has internal TA team (cached)'
                            yield f"data: {json.dumps({'type': 'skipped', 'message': ta_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                            memory_manager.mark_job_processed(job_fingerprint)
                            continue
                        
                        if not company_found:
                            contact_msg = f'Company profile not found for {company} (cached)'
                            yield f"data: {json.dumps({'type': 'skipped', 'message': contact_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                            memory_manager.mark_job_processed(job_fingerprint)
                            continue
                        
                        if not contacts:
                            contact_msg = f'No contacts found for {company} (cached)'
                            yield f"data: {json.dumps({'type': 'skipped', 'message': contact_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                            memory_manager.mark_job_processed(job_fingerprint)
                            continue
                        
                        # Process cached contacts
                        for contact in contacts[:3]:
                            email = contact_finder.find_email(contact['title'], company)
                            if email and not memory_manager.is_email_contacted(email):
                                message = ""
                                if request.auto_generate_messages:
                                    message = email_generator.generate_outreach(
                                        job_title=job.get('title', ''),
                                        company=company,
                                        contact_title=contact['title'],
                                        job_url=job.get('job_url', '')
                                    )
                                
                                score = contact_finder.calculate_lead_score(contact, job, has_ta_team)
                                lead = {
                                    "name": contact['full_name'],
                                    "title": contact['title'],
                                    "company": company,
                                    "email": email,
                                    "job_title": job.get('title', ''),
                                    "job_url": job.get('job_url', ''),
                                    "message": message,
                                    "score": score,
                                    "timestamp": datetime.now().isoformat()
                                }
                                yield f"data: {json.dumps({'type': 'lead', 'data': lead, 'timestamp': datetime.now().isoformat()})}\n\n"
                                leads.append(lead)
                        
                        memory_manager.mark_job_processed(job_fingerprint)
                        processed_count += 1
                        continue
                    
                    # Find contacts
                    role_hint = job.get('title', '')
                    keywords = [role_hint] + search_params.get('keywords', [])
                    contacts, has_ta_team, employee_roles, company_found = contact_finder.find_contacts(
                        company=company,
                        role_hint=role_hint,
                        keywords=keywords,
                        company_website=job.get('linkedin_company_url')
                    )
                    
                    # Cache the company analysis results
                    analyzed_companies[company] = {
                        'has_ta_team': has_ta_team,
                        'company_found': company_found,
                        'contacts': contacts,
                        'employee_roles': employee_roles
                    }
                    
                    if has_ta_team:
                        ta_msg = f'Skipping {company}: Has internal TA team'
                        yield f"data: {json.dumps({'type': 'skipped', 'message': ta_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                        memory_manager.mark_job_processed(job_fingerprint)
                        continue
                    
                    if not company_found:
                        contact_msg = f'Company profile not found for {company}'
                        yield f"data: {json.dumps({'type': 'skipped', 'message': contact_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                        memory_manager.mark_job_processed(job_fingerprint)
                        continue
                    
                    if not contacts:
                        contact_msg = f'No contacts found for {company}'
                        yield f"data: {json.dumps({'type': 'skipped', 'message': contact_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                        memory_manager.mark_job_processed(job_fingerprint)
                        continue
                    
                    # Process each contact
                    for contact in contacts[:3]:  # Top 3 contacts per company
                        # Find email via Hunter.io
                        email = contact_finder.find_email(contact['title'], company)
                        
                        # Only count as lead if email is found and not already contacted
                        if email and not memory_manager.is_email_contacted(email):
                            # Generate message if requested
                            message = ""
                            if request.auto_generate_messages:
                                message = email_generator.generate_outreach(
                                    job_title=job.get('title', ''),
                                    company=company,
                                    contact_title=contact['title'],
                                    job_url=job.get('job_url', '')
                                )
                            
                            # Calculate score and create lead
                            score = contact_finder.calculate_lead_score(contact, job, has_ta_team)
                            
                            lead = {
                                "name": contact['full_name'],
                                "title": contact['title'],
                                "company": company,
                                "email": email,
                                "job_title": job.get('title', ''),
                                "job_url": job.get('job_url', ''),
                                "message": message,
                                "score": score,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            # Stream the lead immediately
                            yield f"data: {json.dumps({'type': 'lead', 'data': lead, 'timestamp': datetime.now().isoformat()})}\n\n"
                            leads.append(lead)
                        

                
                # Mark job as processed
                memory_manager.mark_job_processed(job_fingerprint)
                processed_count += 1
                

            
            # Wait between batches to respect rate limits
            if batch_end < total_jobs:
                wait_msg = f'Batch complete. Waiting 60 seconds before next batch...'
                yield f"data: {json.dumps({'type': 'status', 'message': wait_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                time.sleep(60)
            
            # Send completion summary
            yield f"data: {json.dumps({'type': 'complete', 'summary': {'leads_found': len(leads), 'jobs_processed': processed_count, 'total_jobs': len(jobs)}, 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming job search: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/plain")

@app.post("/analyze-contract-opportunities", response_model=ContractAnalysisResponse)
async def analyze_contract_opportunities(request: ContractOpportunityRequest):
    """Analyze job market to identify high-value recruiting contract opportunities"""
    try:
        # Parse query and search for jobs
        search_params = job_scraper.parse_query(request.query)
        jobs = job_scraper.search_jobs(search_params, max_results=request.max_companies * 5)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        # Analyze contract opportunities with enhanced company job search
        analysis = contract_analyzer.analyze_contract_opportunities(jobs, request.max_companies, job_scraper)
        
        # Convert to response format
        opportunities = [
            ContractOpportunity(**opp) for opp in analysis['opportunities']
        ]
        
        return ContractAnalysisResponse(
            opportunities=opportunities,
            summary=analysis['summary'],
            timestamp=analysis['timestamp']
        )
        
    except Exception as e:
        logger.error(f"Error in contract opportunity analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-instantly-campaign", response_model=InstantlyCampaignResponse)
async def create_instantly_campaign(request: InstantlyCampaignRequest):
    """Create an Instantly.ai campaign with leads (without sending emails)"""
    try:
        # Parse query and search for jobs
        search_params = job_scraper.parse_query(request.query)
        jobs = job_scraper.search_jobs(search_params, max_results=request.max_leads * 3)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        leads = []
        processed_companies = set()
        
        # Process jobs to find leads
        for job in jobs:
            if len(leads) >= request.max_leads:
                break
                
            company = job.get('company', '')
            if company in processed_companies:
                continue
                
            processed_companies.add(company)
            
            # Find contacts and analyze company
            try:
                description = job.get('description') or job.get('job_level') or ''
                result = contact_finder.find_contacts(
                    company=company,
                    role_hint=job.get('title', ''),
                    keywords=job_scraper.extract_keywords(description),
                    company_website=job.get('company_website')
                )
                
                contacts, has_ta_team, employee_roles, company_found = result
                
                # Skip companies with TA teams
                if has_ta_team:
                    continue
                
                # Get Hunter.io emails
                hunter_emails = []
                if not has_ta_team and company_found and job.get('company_website'):  # Only if no TA team AND company found AND domain found
                    try:
                        hunter_emails = contact_finder.find_hunter_emails_for_target_company(
                            company=company,
                            job_title=job.get('title', ''),
                            employee_roles=employee_roles,
                            company_website=job.get('company_website'),
                            rapidapi_contacts=contacts  # Pass RapidAPI contacts for better results
                        )
                        # Log success only if emails were actually found
                        if hunter_emails:
                            logger.info(f"✅ Found {len(hunter_emails)} Hunter.io emails for {company}")
                        else:
                            logger.warning(f"⚠️  No Hunter.io emails found for {company}")
                    except Exception as e:
                        logger.error(f"Hunter.io error for {company}: {e}")
                elif has_ta_team:
                    logger.info(f"⏭️  Skipping Hunter.io for {company} - has TA team")
                elif not company_found:
                    logger.info(f"⏭️  Skipping Hunter.io for {company} - company not found")
                elif not job.get('company_website'):
                    logger.info(f"⏭️  Skipping Hunter.io for {company} - no domain found")
                
                # Create leads from contacts and emails
                for contact in contacts[:3]:  # Top 3 contacts
                    email = contact_finder.find_email(contact.get('title', ''), company)
                    if email:
                        score = contact_finder.calculate_lead_score(contact, job, has_ta_team)
                        if score >= request.min_score:
                            lead = {
                                "name": contact.get('name', ''),
                                "title": contact.get('title', ''),
                                "company": company,
                                "email": email,
                                "job_title": job.get('title', ''),
                                "job_url": job.get('job_url', ''),
                                "score": score,
                                "hunter_emails": hunter_emails,
                                "company_website": job.get('company_website', '')
                            }
                            leads.append(lead)
                
                # Add Hunter.io emails as leads if no contacts found
                if not contacts and hunter_emails:
                    for email in hunter_emails[:2]:  # Top 2 emails
                        lead = {
                            "name": "Hiring Manager",
                            "title": "Hiring Manager",
                            "company": company,
                            "email": email,
                            "job_title": job.get('title', ''),
                            "job_url": job.get('job_url', ''),
                            "score": 0.7,  # Default score for Hunter.io emails
                            "hunter_emails": hunter_emails,
                            "company_website": job.get('company_website', '')
                        }
                        leads.append(lead)
                        
            except Exception as e:
                logger.error(f"Error processing {company}: {e}")
                continue
        
        # Create Instantly campaign
        campaign_id = None
        status = "failed"
        
        if leads:
            campaign_id = instantly_manager.create_recruiting_campaign(
                leads=leads,
                campaign_name=request.campaign_name
            )
            status = "created" if campaign_id else "failed"
        else:
            status = "no_leads"
        
        return InstantlyCampaignResponse(
            campaign_id=campaign_id,
            campaign_name=request.campaign_name or f"Recruiting_Campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            leads_added=len(leads),
            total_leads_found=len(leads),
            status=status,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating Instantly campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-company-jobs", response_model=CompanyJobsResponse)
async def get_company_jobs(request: CompanyJobsRequest):
    """Get all jobs for a specific company using RapidAPI SaleLeads"""
    try:
        jobs = job_scraper.get_all_company_jobs(request.company_name, max_pages=request.max_pages)
        
        return CompanyJobsResponse(
            company=request.company_name,
            total_jobs=len(jobs),
            jobs=jobs,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error fetching company jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/results")
async def receive_webhook_results(request: WebhookRequest):
    """Receive processing results from the pipeline"""
    try:
        logger.info(f"Received webhook results for batch {request.batch_id}")
        
        # Store results in Supabase if available
        if supabase:
            try:
                # Store batch summary
                batch_data = {
                    "batch_id": request.batch_id,
                    "summary": request.summary,
                    "timestamp": request.timestamp,
                    "status": "completed"
                }
                supabase.table("batches").insert(batch_data).execute()
                
                # Store individual results
                for result in request.results:
                    result_data = {
                        "batch_id": request.batch_id,
                        "company": result.company,
                        "job_title": result.job_title,
                        "job_url": result.job_url,
                        "has_ta_team": result.has_ta_team,
                        "contacts_found": result.contacts_found,
                        "top_contacts": result.top_contacts,
                        "recommendation": result.recommendation,
                        "hunter_emails": result.hunter_emails,
                        "instantly_campaign_id": result.instantly_campaign_id,
                        "timestamp": result.timestamp
                    }
                    supabase.table("company_analysis").insert(result_data).execute()
                
                logger.info(f"✅ Stored {len(request.results)} results in Supabase for batch {request.batch_id}")
                
            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
        else:
            logger.warning("⚠️  Supabase not available - results not stored")
        
        # Log results
        for result in request.results:
            logger.info(f"Company: {result.company}, TA Team: {result.has_ta_team}, Recommendation: {result.recommendation}")
        
        return {"status": "success", "batch_id": request.batch_id}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-jobs-background")
async def process_jobs_background(request: JobSearchRequest, current_user: Dict = Depends(get_current_user)):
    """Process jobs in background and send results via webhook"""
    try:
        # Debug logging
        logger.info(f"🔍 Received request: {request}")
        logger.info(f"🔍 Request query: {request.query}")
        logger.info(f"🔍 Request hours_old: {request.hours_old}")
        logger.info(f"🔍 Request enforce_salary: {request.enforce_salary}")
        logger.info(f"🔍 Request auto_generate_messages: {request.auto_generate_messages}")
        logger.info(f"🔍 Request create_campaigns: {request.create_campaigns}")
        logger.info(f"🔍 Request campaign_name: {request.campaign_name}")
        logger.info(f"🔍 Request min_score: {request.min_score}")
        logger.info(f"🔍 Current user: {current_user}")
        
        # Generate batch ID
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Mark search as active in memory
        active_searches[batch_id] = False  # False = not cancelled
        
        # Save agent to Supabase for persistence
        logger.info(f"🔍 About to create agent data for batch_id: {batch_id}")
        try:
            agent_data = {
                "batch_id": batch_id,
                "user_id": current_user["user_id"],
                "user_email": current_user["email"],
                "query": request.query,
                "status": "created",
                "start_time": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat(),  # Ensure created_at is set
                "total_cities": 55,
                "processed_cities": 0,
                "processed_companies": 0,
                "total_jobs_found": 0,
                "hours_old": request.hours_old,
                "create_campaigns": request.create_campaigns,
                "enforce_salary": request.enforce_salary,
                "auto_generate_messages": request.auto_generate_messages,
                "min_score": request.min_score,
                # Also include the original columns for compatibility
                "name": f"Agent: {request.query[:50]}...",
                "prompt": request.query,
                "search_lookback_hours": request.hours_old,
                "max_results": 50,
                "job_type": "fulltime",
                "is_remote": True,
                "country": "us",
                "site_names": ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"],
                "distance": 25,
                "is_active": True,
                "autonomy_level": "semi-automatic",
                "run_frequency": "Manual"
            }
            
            logger.info(f"🔍 Created agent_data: {agent_data}")
            
            # Insert agent into Supabase
            try:
                logger.info(f"🔍 Attempting to save agent data: {agent_data}")
                result = supabase.table("agents").insert(agent_data).execute()
                logger.info(f"✅ Agent saved to Supabase: {batch_id}")
                logger.info(f"✅ Insert result: {result.data}")
            except Exception as table_error:
                logger.warning(f"Agents table may not exist yet: {table_error}")
                logger.info(f"⚠️ Agent {batch_id} will be processed but not saved to database")
            
        except Exception as e:
            logger.error(f"❌ Error saving agent to Supabase: {e}")
            # Continue processing even if Supabase save fails
        
        # Parse query for background processing
        search_params = job_scraper.parse_query(request.query)
        
        # Process jobs in background (async) - will search jobs per city
        asyncio.create_task(process_jobs_background_task(batch_id, [], request))
        
        return {
            "status": "processing",
            "batch_id": batch_id,
            "message": "Agent creation started",
            "query": request.query,
            "webhook_url": f"http://localhost:8000/webhook/results"
        }
        
    except Exception as e:
        logger.error(f"Error starting background processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel-search/{batch_id}")
async def cancel_search(batch_id: str):
    """Cancel an active search by batch_id"""
    try:
        # First try to cancel in-memory search
        if batch_id in active_searches:
            active_searches[batch_id] = True
            logger.info(f"🚫 Search {batch_id} marked for cancellation in memory")
        
        # Also update the agent status in database
        if supabase:
            try:
                supabase.table("agents").update({
                    "status": "cancelled",
                    "end_time": datetime.now().isoformat()
                }).eq("batch_id", batch_id).execute()
                logger.info(f"✅ Agent {batch_id} status updated to cancelled in database")
            except Exception as db_error:
                logger.warning(f"Could not update agent status in database: {db_error}")
        
        return {
            "status": "cancelled",
            "batch_id": batch_id,
            "message": "Search cancellation requested"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling search {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/agents/{batch_id}")
async def delete_agent(batch_id: str, current_user: Dict = Depends(get_current_user)):
    """Delete an agent by batch_id"""
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        # First check if agent exists and belongs to user
        agent_response = supabase.table("agents").select("*").eq("batch_id", batch_id).eq("user_id", current_user["user_id"]).execute()
        
        if not agent_response.data:
            raise HTTPException(status_code=404, detail="Agent not found or access denied")
        
        agent = agent_response.data[0]
        logger.info(f"🗑️ Deleting agent {batch_id} for user {current_user['user_id']}")
        
        # Cancel if still running
        if batch_id in active_searches:
            active_searches[batch_id] = True
            logger.info(f"🚫 Cancelled running agent {batch_id}")
        
        # Delete from database
        delete_response = supabase.table("agents").delete().eq("batch_id", batch_id).eq("user_id", current_user["user_id"]).execute()
        
        if delete_response.data:
            logger.info(f"✅ Successfully deleted agent {batch_id}")
            
            # Also clean up related data
            try:
                # Delete logs
                supabase.table("search_logs_enhanced").delete().eq("batch_id", batch_id).execute()
                logger.info(f"🧹 Cleaned up logs for agent {batch_id}")
            except Exception as log_error:
                logger.warning(f"Could not clean up logs: {log_error}")
            
            return {
                "status": "deleted",
                "batch_id": batch_id,
                "message": "Agent deleted successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete agent")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search-status/{batch_id}")
async def get_search_status(batch_id: str):
    """Get the status of a search by batch_id"""
    try:
        if batch_id not in active_searches:
            raise HTTPException(status_code=404, detail="Search not found")
        
        is_cancelled = active_searches[batch_id]
        status = "cancelled" if is_cancelled else "active"
        
        return {
            "batch_id": batch_id,
            "status": status,
            "is_cancelled": is_cancelled
        }
        
    except Exception as e:
        logger.error(f"Error getting search status for {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/active-searches")
async def get_active_searches():
    """Get all active searches from memory"""
    try:
        active = {batch_id: not cancelled for batch_id, cancelled in active_searches.items() if not cancelled}
        cancelled = {batch_id: cancelled for batch_id, cancelled in active_searches.items() if cancelled}
        
        return {
            "active_searches": list(active.keys()),
            "cancelled_searches": list(cancelled.keys()),
            "total_active": len(active),
            "total_cancelled": len(cancelled)
        }
        
    except Exception as e:
        logger.error(f"Error getting active searches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def get_agents(current_user: Dict = Depends(get_current_user)):
    """Get all agents from Supabase"""
    try:
        logger.info(f"Getting agents for user: {current_user}")
        
        if not supabase:
            logger.error("Supabase client not initialized")
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Get all agents from agents table
        logger.info(f"Querying agents table for user_id: {current_user['user_id']}")
        try:
            # First, let's see what agents exist for this user
            logger.info(f"🔍 Querying all agents from table...")
            all_agents = supabase.table("agents").select("*").execute()
            logger.info(f"All agents in table: {all_agents.data}")
            logger.info(f"Total agents found: {len(all_agents.data) if all_agents.data else 0}")
            
            # Now filter by user_id - use created_at for ordering since start_time might be null
            logger.info(f"🔍 Filtering by user_id: {current_user['user_id']}")
            result = supabase.table("agents").select("*").eq("user_id", current_user["user_id"]).order("created_at", desc=True).limit(50).execute()
            logger.info(f"Query result for user {current_user['user_id']}: {result.data}")
            logger.info(f"Filtered agents found: {len(result.data) if result.data else 0}")
            
            # Check if there are any agents at all
            if all_agents.data and len(all_agents.data) > 0:
                logger.info(f"🔍 Sample agent data: {all_agents.data[0] if all_agents.data else 'No data'}")
                # Check what user_ids exist
                user_ids = [agent.get('user_id') for agent in all_agents.data if agent.get('user_id')]
                logger.info(f"🔍 User IDs in table: {user_ids}")
            else:
                logger.warning("🔍 No agents found in table at all")
            
            # Also check if there are any agents with the batch_id we just created
            if 'batch_20250801_125402' in str(all_agents.data):
                logger.info("Found the batch_id in the table!")
            else:
                logger.warning("The batch_id was not found in the table")
                
        except Exception as table_error:
            logger.warning(f"Agents table may not exist yet: {table_error}")
            # Return empty result if table doesn't exist
            return {
                "agents": [],
                "total_agents": 0,
                "message": "No agents found. Create your first agent to get started!"
            }
        
        agents = []
        for agent in result.data:
            agents.append({
                "batch_id": agent["batch_id"],
                "user_id": agent.get("user_id", "unknown"),
                "user_email": agent.get("user_email", "unknown"),
                "query": agent["query"],
                "status": agent["status"],
                "start_time": agent.get("start_time") or agent.get("created_at", ""),
                "end_time": agent.get("end_time"),
                "total_cities": agent["total_cities"],
                "processed_cities": agent["processed_cities"],
                "processed_companies": agent["processed_companies"],
                "total_jobs_found": agent["total_jobs_found"],
                "hours_old": agent["hours_old"],
                "create_campaigns": agent["create_campaigns"]
            })
        
        logger.info(f"Returning {len(agents)} agents")
        return {
            "agents": agents,
            "total_agents": len(agents)
        }
        
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_jobs_background_task(batch_id: str, jobs: List[Dict], request: JobSearchRequest):
    """Background task to process jobs with city-by-city flow: City → Companies → Contacts → Next City"""
    try:
        results = []
        processed_count = 0
        campaigns_created = []
        leads_added = 0
        
        # Initialize tracker for this batch
        tracker = CompanyProcessingTracker(batch_id)
        
        # Log start of processing
        await log_to_supabase(batch_id, f"🚀 Starting city-by-city processing for query: {request.query}", "info")
        
        # Update agent status to "processing"
        try:
            supabase.table("agents").update({
                "status": "processing",
                "start_time": datetime.now().isoformat()
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.error(f"❌ Error updating agent status: {e}")
        
        # Get search parameters for city-by-city processing
        search_params = job_scraper.parse_query(request.query)
        await log_to_supabase(batch_id, f"📋 Parsed search parameters: {search_params}", "info")
        
        # Define cities to process (all 55 major US cities)
        cities_to_process = [
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
        await log_to_supabase(batch_id, f"🏙️ Will process {len(cities_to_process)} cities: {', '.join(cities_to_process)}", "info")
        
        for city_index, city in enumerate(cities_to_process):
            # Check if search has been cancelled
            if batch_id in active_searches and active_searches[batch_id]:
                await log_to_supabase(batch_id, "🚫 Search was cancelled, stopping processing", "warning")
                break
            
            await log_to_supabase(batch_id, f"🏙️ Processing city {city_index + 1}/{len(cities_to_process)}: {city}", "info")
            
            try:
                # Step 1: Search jobs in this city
                await log_to_supabase(batch_id, f"🔍 Step 1: Searching jobs in {city} for query: {request.query}", "info")
                
                city_jobs = job_scraper._call_jobspy_api(
                    search_term=search_params.get("search_term", request.query),
                    location=city,
                    hours_old=request.hours_old,
                    job_type=search_params.get("job_type", "fulltime"),
                    is_remote=search_params.get("is_remote", True),
                    site_name=search_params.get("site_name", ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"]),
                    results_wanted=50,  # Limit per city for faster processing
                    offset=0,
                    distance=25,
                    easy_apply=False,
                    country_indeed="us",
                    google_search_term="",
                    linkedin_fetch_description=True,
                    verbose=False
                )
                
                await log_to_supabase(batch_id, f"✅ Step 1 Complete: Found {len(city_jobs)} jobs in {city}", "success")
                
                # Update total jobs found
                try:
                    supabase.table("agents").update({
                        "total_jobs_found": supabase.table("agents").select("total_jobs_found").eq("batch_id", batch_id).execute().data[0]["total_jobs_found"] + len(city_jobs)
                    }).eq("batch_id", batch_id).execute()
                except Exception as e:
                    logger.error(f"❌ Error updating total jobs: {e}")
                
                # Step 2: Process companies from this city
                processed_companies = set()
                city_companies = []
                
                # Extract unique companies from jobs
                for job in city_jobs:
                    company = job.get('company', '')
                    if company and company not in processed_companies:
                        processed_companies.add(company)
                        city_companies.append({
                            'company': company,
                            'job': job
                        })
                
                await log_to_supabase(batch_id, f"📊 Step 2: Found {len(city_companies)} unique companies in {city}", "info")
                
                # Process each company in the city
                for company_index, company_data in enumerate(city_companies):
                    # Check for cancellation before each company
                    if batch_id in active_searches and active_searches[batch_id]:
                        await log_to_supabase(batch_id, "🚫 Search was cancelled, stopping processing", "warning")
                        break
                    
                    company = company_data['company']
                    job = company_data['job']
                    job_title = job.get('title', '')
                    job_url = job.get('job_url', '')
                    
                    # Check if company has already been analyzed in previous batches
                    try:
                        existing_analysis = supabase.table("company_analysis").select("*").eq("company", company).order("timestamp", desc=True).limit(1).execute()
                        
                        if existing_analysis.data:
                            existing = existing_analysis.data[0]
                            await log_to_supabase(batch_id, f"⏭️ Skipping {company} - already analyzed in batch {existing['batch_id']} (recommendation: {existing['recommendation']})", "info", company)
                            continue
                    except Exception as e:
                        await log_to_supabase(batch_id, f"⚠️ Error checking existing analysis for {company}: {str(e)}", "warning", company)
                    
                    await log_to_supabase(batch_id, f"🏢 Step 2: Processing company {company_index + 1}/{len(city_companies)}: {company} in {city}", "info", company)
                    
                    # Step 2a: Check blacklist
                    await log_to_supabase(batch_id, f"⚫ Step 2a: Checking blacklist for {company}", "info", company)
                    
                    # Skip enterprise companies
                    enterprise_companies = ["google", "microsoft", "amazon", "apple"]
                    if company and any(enterprise in company.lower() for enterprise in enterprise_companies):
                        await log_to_supabase(batch_id, f"⏭️ Step 2a: Skipping enterprise company: {company} (blacklisted)", "info", company)
                        continue
                    
                    await log_to_supabase(batch_id, f"✅ Step 2a: {company} passed blacklist check", "success", company)
                    
                    # Step 2b: Domain finding
                    await log_to_supabase(batch_id, f"🌐 Step 2b: Finding domain for {company}", "info", company)
                    company_website = job.get('company_website')
                    
                    # If no website in job data, try to find domain using Clearout API
                    if not company_website:
                        try:
                            url = "https://api.clearout.io/public/companies/autocomplete"
                            params = {"query": company}
                            
                            import httpx
                            async with httpx.AsyncClient() as client:
                                response = await client.get(url, params=params, timeout=30.0)
                                
                                if response.status_code == 200:
                                    data = response.json()
                                    if data.get('status') == 'success' and data.get('data'):
                                        # Get the best match with highest confidence
                                        best_match = None
                                        best_confidence = 0
                                        
                                        for company_data in data['data']:
                                            confidence = company_data.get('confidence_score', 0)
                                            if confidence > best_confidence and confidence >= 50:
                                                best_confidence = confidence
                                                best_match = company_data.get('domain')
                                        
                                        if best_match:
                                            company_website = best_match
                                            await log_to_supabase(batch_id, f"✅ Step 2b: Found domain via Clearout API: {company_website}", "success", company)
                                        else:
                                            await log_to_supabase(batch_id, f"⚠️ Step 2b: No high-confidence domain found for {company} (best confidence: {best_confidence})", "warning", company)
                                    else:
                                        await log_to_supabase(batch_id, f"⚠️ Step 2b: Clearout API failed for {company}: {data.get('message', 'Unknown error')}", "warning", company)
                                else:
                                    await log_to_supabase(batch_id, f"⚠️ Step 2b: Clearout API error for {company}: {response.status_code}", "warning", company)
                        except Exception as e:
                            await log_to_supabase(batch_id, f"❌ Step 2b: Domain finding failed for {company}: {str(e)}", "error", company)
                    
                    if company_website:
                        await log_to_supabase(batch_id, f"✅ Step 2b: Using website: {company_website}", "success", company)
                    else:
                        await log_to_supabase(batch_id, f"⚠️ Step 2b: No website found for {company}", "warning", company)
                    
                    # Step 2c: LinkedIn company page resolution
                    await log_to_supabase(batch_id, f"🔗 Step 2c: Resolving LinkedIn page for {company}", "info", company)
                    
                    # Step 3: Find contacts for this company
                    await log_to_supabase(batch_id, f"👥 Step 3: Finding contacts for {company}", "info", company)
                    
                    try:
                        contacts, has_ta_team, employee_roles, company_found = contact_finder.find_contacts(
                            company=company,
                            role_hint=job.get('title', ''),
                            keywords=job_scraper.extract_keywords(job.get('description', '')),
                            company_website=company_website
                        )
                        
                        await log_to_supabase(batch_id, f"📊 Step 3: Found {len(contacts)} contacts, TA team: {has_ta_team} for {company}", "info", company)
                        
                        # Step 3a: RapidAPI calls logging
                        await log_to_supabase(batch_id, f"📡 Step 3a: RapidAPI calls completed for {company}", "info", company)
                        
                        # Step 3b: Hunter.io email discovery
                        hunter_emails = []
                        if not has_ta_team and company_found:
                            await log_to_supabase(batch_id, f"🎯 Step 3b: Attempting Hunter.io lookup for {company} (no TA team found)", "info", company)
                            
                            try:
                                hunter_emails = contact_finder.find_hunter_emails_for_target_company(
                                    company=company,
                                    job_title=job_title,
                                    employee_roles=employee_roles,
                                    company_website=company_website
                                )
                                
                                if hunter_emails:
                                    await log_to_supabase(batch_id, f"✅ Step 3b: Found {len(hunter_emails)} Hunter.io emails for {company}", "success", company)
                                    await log_to_supabase(batch_id, f"📧 Hunter.io emails: {[email.get('email', 'N/A') for email in hunter_emails]}", "info", company)
                                    tracker.save_hunter_emails(company, job_title, job_url, hunter_emails)
                                else:
                                    await log_to_supabase(batch_id, f"⚠️ Step 3b: No Hunter.io emails found for {company}", "warning", company)
                                    tracker.save_hunter_emails(company, job_title, job_url, [])
                                    
                            except Exception as e:
                                await log_to_supabase(batch_id, f"❌ Step 3b: Hunter.io error for {company}: {str(e)}", "error", company)
                                tracker.save_hunter_emails(company, job_title, job_url, [], error=str(e))
                        else:
                            await log_to_supabase(batch_id, f"⏭️ Step 3b: Skipping Hunter.io for {company} (has TA team or company not found)", "info", company)
                        
                        # Step 3c: Instantly campaign creation
                        await log_to_supabase(batch_id, f"🔍 Step 3c Debug: create_campaigns={request.create_campaigns}, hunter_emails_count={len(hunter_emails) if hunter_emails else 0}", "info", company)
                        if request.create_campaigns and hunter_emails:
                            await log_to_supabase(batch_id, f"🚀 Step 3c: Creating Instantly campaign for {company}", "info", company)
                            
                            try:
                                # Call the Edge Function to send leads to Instantly.ai
                                import httpx
                                
                                # Prepare the request for the Edge Function
                                edge_function_url = f"{os.getenv('SUPABASE_URL', '')}/functions/v1/send-to-instantly"
                                
                                # Extract domain from Hunter.io emails
                                hunter_domain = None
                                if hunter_emails and len(hunter_emails) > 0:
                                    # Get domain from first email
                                    first_email = hunter_emails[0].get("email", "")
                                    if "@" in first_email:
                                        hunter_domain = first_email.split("@")[1]
                                
                                edge_function_payload = {
                                    "batch_id": batch_id,
                                    "action": "create_leads",
                                    "hunter_emails": hunter_emails,  # Pass emails directly
                                    "company": company,
                                    "job_title": job_title,
                                    "domain": hunter_domain  # Use domain from Hunter.io emails
                                }
                                
                                # Get the service role key for the Edge Function
                                service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
                                if not service_role_key:
                                    await log_to_supabase(batch_id, f"❌ SUPABASE_SERVICE_ROLE_KEY not configured", "error", company, job_title, job_url, "instantly_error")
                                    continue
                                
                                headers = {
                                    "Authorization": f"Bearer {service_role_key}",
                                    "Content-Type": "application/json"
                                }
                                
                                await log_to_supabase(batch_id, f"📡 Calling Edge Function to send {len(hunter_emails)} leads to Instantly.ai", "info", company, job_title, job_url, "instantly_edge_call")
                                
                                async with httpx.AsyncClient() as client:
                                    response = await client.post(
                                        edge_function_url,
                                        json=edge_function_payload,
                                        headers=headers,
                                        timeout=30.0
                                    )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    if result.get('success'):
                                        created_leads = result.get('created_leads', [])
                                        leads_added += len(created_leads)
                                        campaigns_created.append(result.get('summary', {}).get('campaign_id', ''))
                                        await log_to_supabase(batch_id, f"✅ Successfully sent {len(created_leads)} leads to Instantly.ai", "success", company, job_title, job_url, "instantly_success")
                                        tracker.save_instantly_campaign(company, result.get('summary', {}).get('campaign_id', ''), f"Coogi Agent - {company}", len(created_leads))
                                    else:
                                        await log_to_supabase(batch_id, f"❌ Edge Function returned error: {result.get('error', 'Unknown error')}", "error", company, job_title, job_url, "instantly_error")
                                        tracker.save_instantly_campaign(company, error=result.get('error', 'Edge Function error'))
                                else:
                                    await log_to_supabase(batch_id, f"❌ Edge Function call failed: {response.status_code} - {response.text}", "error", company, job_title, job_url, "instantly_error")
                                    tracker.save_instantly_campaign(company, error=f"Edge Function HTTP {response.status_code}")
                                    
                            except Exception as e:
                                await log_to_supabase(batch_id, f"❌ Error calling Edge Function for {company}: {str(e)}", "error", company, job_title, job_url, "instantly_error")
                                tracker.save_instantly_campaign(company, error=str(e))
                        
                        elif request.create_campaigns:
                            await log_to_supabase(batch_id, f"⏭️ Step 3c: Skipping Instantly campaign for {company} (no Hunter emails)", "info", company)
                        
                        # Create result
                        result = WebhookResult(
                            company=company,
                            job_title=job_title,
                            job_url=job.get('job_url', ''),
                            has_ta_team=has_ta_team if has_ta_team is not None else False,
                            contacts_found=len(contacts),
                            top_contacts=contacts[:3] if contacts else [],
                            recommendation="TARGET" if not has_ta_team else "SKIP - Has TA team",
                            hunter_emails=[email_info["email"] for email_info in hunter_emails] if hunter_emails else [],
                            timestamp=datetime.now().isoformat()
                        )
                        
                        results.append(result)
                        processed_count += 1
                        
                        # Update processed companies count
                        try:
                            supabase.table("agents").update({
                                "processed_companies": supabase.table("agents").select("processed_companies").eq("batch_id", batch_id).execute().data[0]["processed_companies"] + 1
                            }).eq("batch_id", batch_id).execute()
                        except Exception as e:
                            logger.error(f"❌ Error updating processed companies: {e}")
                        
                        await log_to_supabase(batch_id, f"✅ Step 3 Complete: Finished analysis for {company} in {city}", "success", company)
                        
                    except Exception as e:
                        await log_to_supabase(batch_id, f"❌ Step 3 Error: Error analyzing {company}: {str(e)}", "error", company)
                    
                    # Add 3-second delay between companies (except for the last company in the city)
                    if company_index < len(city_companies) - 1:
                        await log_to_supabase(batch_id, f"⏳ Waiting 3 seconds before next company...", "info")
                        await asyncio.sleep(3)
                
                await log_to_supabase(batch_id, f"✅ City Complete: Finished processing {city} - {len(processed_companies)} companies analyzed", "success")
                
                # Update processed cities count
                try:
                    supabase.table("agents").update({
                        "processed_cities": supabase.table("agents").select("processed_cities").eq("batch_id", batch_id).execute().data[0]["processed_cities"] + 1
                    }).eq("batch_id", batch_id).execute()
                except Exception as e:
                    logger.error(f"❌ Error updating processed cities: {e}")
                
                # Rate limiting between cities
                if city_index < len(cities_to_process) - 1:
                    await log_to_supabase(batch_id, f"⏳ Waiting 2 seconds before next city...", "info")
                    await asyncio.sleep(2)
                    
            except Exception as e:
                await log_to_supabase(batch_id, f"❌ Error processing city {city}: {str(e)}", "error")
                continue
        
        # Check if search was cancelled during processing
        if batch_id in active_searches and active_searches[batch_id]:
            await log_to_supabase(batch_id, f"🚫 Agent was cancelled during processing. Analyzed {processed_count} companies across {len(cities_to_process)} cities", "warning")
            
            # Update agent status to cancelled
            try:
                supabase.table("agents").update({
                    "status": "cancelled",
                    "end_time": datetime.now().isoformat(),
                    "processed_companies": processed_count,
                    "processed_cities": len(cities_to_process)
                }).eq("batch_id", batch_id).execute()
                logger.info(f"✅ Agent {batch_id} marked as cancelled")
            except Exception as e:
                logger.error(f"❌ Error updating agent cancellation status: {e}")
        else:
            # Send final webhook with all results
            await log_to_supabase(batch_id, f"🎉 Processing complete! Analyzed {processed_count} companies across {len(cities_to_process)} cities", "success")
            
            # Update agent status to completed
            try:
                supabase.table("agents").update({
                    "status": "completed",
                    "end_time": datetime.now().isoformat(),
                    "processed_companies": processed_count,
                    "processed_cities": len(cities_to_process)
                }).eq("batch_id", batch_id).execute()
                logger.info(f"✅ Agent {batch_id} marked as completed")
            except Exception as e:
                logger.error(f"❌ Error updating agent completion status: {e}")
        
        # Only send webhook for completed agents, not cancelled ones
        if not (batch_id in active_searches and active_searches[batch_id]):
            webhook_data = WebhookRequest(
                batch_id=batch_id,
                results=results,
                summary={
                    "total_companies": processed_count,
                    "total_cities": len(cities_to_process),
                    "target_companies": len([r for r in results if r.recommendation == "TARGET"]),
                    "skipped_companies": len([r for r in results if "SKIP" in r.recommendation])
                },
                timestamp=datetime.now().isoformat()
            )
            
            await send_webhook(webhook_data)
        
        # Clean up
        if batch_id in active_searches:
            del active_searches[batch_id]
            
    except Exception as e:
        logger.error(f"Error in background task: {e}")
        await log_to_supabase(batch_id, f"❌ Background task error: {str(e)}", "error")
        
        # Clean up on error
        if batch_id in active_searches:
            del active_searches[batch_id]

async def send_webhook(webhook_data: WebhookRequest):
    """Send webhook to configured endpoint"""
    try:
        # In production, this would be your webhook URL
        webhook_url = "http://localhost:8000/webhook/results"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=webhook_data.dict(),
                headers={"Content-Type": "application/json"}
            )
            
        logger.info(f"Webhook sent successfully: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error sending webhook: {e}")

@app.get("/batch/{batch_id}")
async def get_batch_results(batch_id: str):
    """Get results for a specific batch"""
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        # First try to get agent from agents table
        agent_response = supabase.table("agents").select("*").eq("batch_id", batch_id).execute()
        
        if agent_response.data:
            agent = agent_response.data[0]
            logger.info(f"✅ Found agent for batch {batch_id}: {agent}")
            
            # Get logs for this batch
            try:
                logs_response = supabase.table("search_logs_enhanced").select("*").eq("batch_id", batch_id).order("timestamp", desc=True).limit(100).execute()
                logs = logs_response.data
            except Exception:
                logs = []
            
            # Get hunter_emails for this batch
            try:
                hunter_emails_response = supabase.table("hunter_emails").select("*").eq("batch_id", batch_id).order("timestamp", desc=True).execute()
                hunter_emails = hunter_emails_response.data
            except Exception:
                hunter_emails = []
            
            return {
                "agent": agent,
                "logs": logs,
                "hunter_emails": hunter_emails,
                "total_logs": len(logs),
                "total_hunter_emails": len(hunter_emails),
                "batch_id": batch_id,
                "status": agent.get("status", "unknown"),
                "query": agent.get("query", ""),
                "total_jobs_found": agent.get("total_jobs_found", 0),
                "processed_companies": agent.get("processed_companies", 0),
                "processed_cities": agent.get("processed_cities", 0)
            }
        
        # Fallback to old batches table
        batch_response = supabase.table("batches").select("*").eq("batch_id", batch_id).execute()
        
        if not batch_response.data:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Get batch results
        results_response = supabase.table("company_analysis").select("*").eq("batch_id", batch_id).execute()
        
        return {
            "batch": batch_response.data[0],
            "results": results_response.data,
            "total_results": len(results_response.data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching batch results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batches")
async def get_all_batches(limit: int = 10, offset: int = 0):
    """Get all batches with pagination"""
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        response = supabase.table("batches").select("*").order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "batches": response.data,
            "total": len(response.data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching batches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blacklist")
async def get_blacklist():
    """Get all blacklisted companies"""
    return blacklist_manager.get_blacklist_stats()

@app.post("/blacklist/add")
async def add_to_blacklist(company: str, reason: str = ""):
    """Add company to blacklist"""
    blacklist_manager.add_to_blacklist(company, reason)
    return {"message": f"Added {company} to blacklist", "reason": reason}

@app.delete("/blacklist/remove")
async def remove_from_blacklist(company: str):
    """Remove company from blacklist"""
    blacklist_manager.remove_from_blacklist(company)
    return {"message": f"Removed {company} from blacklist"}

@app.delete("/blacklist/clear")
async def clear_blacklist():
    """Clear all blacklisted companies"""
    blacklist_manager.clear_blacklist()
    return {"message": "Cleared all blacklisted companies"}

@app.get("/companies/target")
async def get_target_companies(limit: int = 20, offset: int = 0):
    """Get companies marked as TARGET (no TA team)"""
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Supabase not configured")
        
        response = supabase.table("company_analysis").select("*").eq("recommendation", "TARGET").order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "target_companies": response.data,
            "total": len(response.data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching target companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{batch_id}")
async def get_search_logs(batch_id: str, limit: int = 100):
    """Get real-time logs for a specific search batch"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    try:
        # Try enhanced table first, fallback to old table
        try:
            response = supabase.table("search_logs_enhanced").select("*").eq("batch_id", batch_id).order("timestamp", desc=True).limit(limit).execute()
        except Exception:
            response = supabase.table("search_logs").select("*").eq("batch_id", batch_id).order("timestamp", desc=True).limit(limit).execute()
        
        return {"logs": response.data}
    except Exception as e:
        logger.error(f"Error fetching logs for batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def get_all_logs(limit: int = 100, offset: int = 0):
    """Get all search logs from Supabase"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    try:
        # Try enhanced table first, fallback to old table
        try:
            response = supabase.table("search_logs_enhanced").select("*").order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
        except Exception:
            response = supabase.table("search_logs").select("*").order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
        
        return {"logs": response.data}
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent-history/{query}")
async def get_agent_history(query: str, limit: int = 10):
    """Get history of agents for a specific query"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    try:
        # Get batches for this query
        response = supabase.table("batches").select("*").ilike("summary", f"%{query}%").order("timestamp", desc=True).limit(limit).execute()
        
        agent_history = []
        for batch in response.data:
            # Get logs for this batch
            logs_response = supabase.table("search_logs").select("*").eq("batch_id", batch["batch_id"]).order("timestamp", desc=True).limit(50).execute()
            
            agent_history.append({
                "batch_id": batch["batch_id"],
                "timestamp": batch["timestamp"],
                "status": batch["status"],
                "summary": batch["summary"],
                "logs_count": len(logs_response.data),
                "recent_logs": logs_response.data[:5]  # Last 5 logs
            })
        
        return {
            "query": query,
            "total_runs": len(agent_history),
            "history": agent_history
        }
    except Exception as e:
        logger.error(f"Error fetching agent history for {query}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent-templates")
async def get_agent_templates():
    """Get all agent templates"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    try:
        response = supabase.table("agent_templates").select("*").order("name").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching agent templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard-stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    try:
        # Get stats from the view
        response = supabase.table("agent_dashboard_stats").select("*").execute()
        if response.data:
            return response.data[0]
        else:
            return {
                "active_agents": 0,
                "total_runs": 0,
                "total_jobs": 0,
                "avg_success_rate": 0.0,
                "avg_duration": 0
            }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent-activity")
async def get_recent_activity(limit: int = 10):
    """Get recent agent activity"""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    
    try:
        response = supabase.table("recent_agent_activity").select("*").limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Instantly.ai Integration Endpoints
@app.get("/instantly-campaigns")
async def get_instantly_campaigns(batch_id: Optional[str] = None):
    """Get all Instantly.ai campaigns, optionally filtered by batch_id"""
    try:
        if batch_id:
            # Get campaigns for specific batch from our database
            if supabase:
                try:
                    response = supabase.table("instantly_campaigns").select("*").eq("batch_id", batch_id).execute()
                    campaigns = []
                    for campaign in response.data:
                        # Get additional details from Instantly.ai if campaign_id exists
                        if campaign.get("campaign_id"):
                            try:
                                instantly_campaign = instantly_manager.get_campaign(campaign["campaign_id"])
                                if instantly_campaign:
                                    campaigns.append({
                                        "id": campaign["campaign_id"],
                                        "name": campaign["campaign_name"] or instantly_campaign.get("name", "Unknown"),
                                        "status": instantly_campaign.get("status", "unknown"),
                                        "leads_count": campaign["leads_added"],
                                        "batch_id": campaign["batch_id"],
                                        "company": campaign["company"],
                                        "created_at": campaign["timestamp"]
                                    })
                                else:
                                    # Fallback to database data
                                    campaigns.append({
                                        "id": campaign["campaign_id"],
                                        "name": campaign["campaign_name"] or "Unknown",
                                        "status": "unknown",
                                        "leads_count": campaign["leads_added"],
                                        "batch_id": campaign["batch_id"],
                                        "company": campaign["company"],
                                        "created_at": campaign["timestamp"]
                                    })
                            except Exception as e:
                                logger.warning(f"Could not fetch Instantly campaign {campaign['campaign_id']}: {e}")
                                # Fallback to database data
                                campaigns.append({
                                    "id": campaign["campaign_id"],
                                    "name": campaign["campaign_name"] or "Unknown",
                                    "status": "unknown",
                                    "leads_count": campaign["leads_added"],
                                    "batch_id": campaign["batch_id"],
                                    "company": campaign["company"],
                                    "created_at": campaign["timestamp"]
                                })
                    return campaigns
                except Exception as e:
                    logger.error(f"Error fetching campaigns for batch {batch_id}: {e}")
                    return []
            else:
                return []
        else:
            # Return all campaigns from Instantly.ai (original behavior)
            campaigns = instantly_manager.get_all_campaigns()
            return campaigns
    except Exception as e:
        logger.error(f"Error fetching Instantly campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-campaigns/{campaign_id}")
async def get_instantly_campaign(campaign_id: str):
    """Get specific Instantly.ai campaign"""
    try:
        campaign = instantly_manager.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except Exception as e:
        logger.error(f"Error fetching Instantly campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/instantly-campaigns/{campaign_id}/activate")
async def activate_instantly_campaign(campaign_id: str):
    """Activate an Instantly.ai campaign"""
    try:
        result = instantly_manager.activate_campaign(campaign_id)
        return {"message": "Campaign activated successfully", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Error activating Instantly campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/instantly-campaigns/{campaign_id}/pause")
async def pause_instantly_campaign(campaign_id: str):
    """Pause an Instantly.ai campaign"""
    try:
        result = instantly_manager.pause_campaign(campaign_id)
        return {"message": "Campaign paused successfully", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Error pausing Instantly campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-leads")
async def get_instantly_leads():
    """Get all leads from Instantly.ai"""
    try:
        leads = instantly_manager.get_all_leads()
        return leads
    except Exception as e:
        logger.error(f"Error fetching Instantly leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-campaigns/{campaign_id}/leads")
async def get_instantly_campaign_leads(campaign_id: str):
    """Get leads for a specific Instantly.ai campaign"""
    try:
        logger.info(f"🔍 API: Getting leads for campaign {campaign_id}")
        leads = instantly_manager.get_leads_for_campaign(campaign_id)
        logger.info(f"📊 API: Retrieved {len(leads)} leads for campaign {campaign_id}")
        logger.info(f"📋 API: First few leads: {leads[:3] if leads else 'No leads'}")
        return {"campaign_id": campaign_id, "leads": leads, "total_leads": len(leads)}
    except Exception as e:
        logger.error(f"Error fetching leads for campaign {campaign_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-leads/{lead_id}")
async def get_instantly_lead(lead_id: str):
    """Get specific lead from Instantly.ai"""
    try:
        lead = instantly_manager.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except Exception as e:
        logger.error(f"Error fetching Instantly lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/instantly-leads/{lead_id}/export")
async def export_instantly_lead(lead_id: str):
    """Export a lead from Instantly.ai"""
    try:
        result = instantly_manager.export_lead(lead_id)
        return {"message": "Lead exported successfully", "lead_id": lead_id}
    except Exception as e:
        logger.error(f"Error exporting Instantly lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/instantly-campaigns/{campaign_id}/export")
async def export_campaign_leads(campaign_id: str, format: str = "csv"):
    """Export all leads from a campaign"""
    try:
        leads = instantly_manager.get_leads_for_campaign(campaign_id)
        if not leads:
            raise HTTPException(status_code=404, detail="No leads found for this campaign")
        
        if format.lower() == "csv":
            # Generate CSV content
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Name", "Email", "Company", "Title", "LinkedIn URL", 
                "Score", "Status", "Email Verified", "Verification Score"
            ])
            
            # Write data
            for lead in leads:
                writer.writerow([
                    lead.get("name", ""),
                    lead.get("email", ""),
                    lead.get("company", ""),
                    lead.get("title", ""),
                    lead.get("linkedin_url", ""),
                    lead.get("score", ""),
                    lead.get("status", ""),
                    lead.get("email_verified", False),
                    lead.get("verification_score", 0)
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "message": f"Successfully exported {len(leads)} leads",
                "campaign_id": campaign_id,
                "format": "csv",
                "content": csv_content,
                "filename": f"campaign_{campaign_id}_leads.csv"
            }
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv'")
            
    except Exception as e:
        logger.error(f"Error exporting campaign leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-analytics/real-time")
async def get_real_time_analytics():
    """Get real-time campaign analytics"""
    try:
        # Get all campaigns
        campaigns = instantly_manager.get_all_campaigns()
        
        real_time_data = {
            "total_campaigns": len(campaigns),
            "active_campaigns": 0,
            "total_leads": 0,
            "total_sent": 0,
            "total_opened": 0,
            "total_replied": 0,
            "total_clicked": 0,
            "campaigns": []
        }
        
        for campaign in campaigns:
            campaign_id = campaign.get("id")
            if campaign_id:
                # Get campaign analytics
                analytics = instantly_manager.get_campaign_analytics(campaign_id)
                if analytics:
                    campaign_data = {
                        "id": campaign_id,
                        "name": campaign.get("name", ""),
                        "status": campaign.get("status", ""),
                        "leads_count": analytics.get("leads_count", 0),
                        "sent_count": analytics.get("sent_count", 0),
                        "opened_count": analytics.get("opened_count", 0),
                        "replied_count": analytics.get("replied_count", 0),
                        "clicked_count": analytics.get("clicked_count", 0),
                        "open_rate": analytics.get("open_rate", 0),
                        "reply_rate": analytics.get("reply_rate", 0),
                        "click_rate": analytics.get("click_rate", 0)
                    }
                    
                    real_time_data["campaigns"].append(campaign_data)
                    real_time_data["total_leads"] += campaign_data["leads_count"]
                    real_time_data["total_sent"] += campaign_data["sent_count"]
                    real_time_data["total_opened"] += campaign_data["opened_count"]
                    real_time_data["total_replied"] += campaign_data["replied_count"]
                    real_time_data["total_clicked"] += campaign_data["clicked_count"]
                    
                    if campaign_data["status"] == "active":
                        real_time_data["active_campaigns"] += 1
        
        return real_time_data
        
    except Exception as e:
        logger.error(f"Error getting real-time analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-stats")
async def get_instantly_stats():
    """Get Instantly.ai statistics"""
    try:
        stats = instantly_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching Instantly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-analytics/overview")
async def get_instantly_analytics_overview():
    """Get Instantly.ai analytics overview"""
    try:
        overview = instantly_manager.get_campaign_analytics_overview()
        return overview
    except Exception as e:
        logger.error(f"Error fetching Instantly analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-analytics/daily")
async def get_instantly_daily_analytics(start_date: str = None, end_date: str = None):
    """Get Instantly.ai daily analytics"""
    try:
        daily_analytics = instantly_manager.get_daily_campaign_analytics(start_date, end_date)
        return {"daily_analytics": daily_analytics}
    except Exception as e:
        logger.error(f"Error fetching Instantly daily analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-analytics/campaign/{campaign_id}/steps")
async def get_instantly_campaign_steps_analytics(campaign_id: str, start_date: str = None, end_date: str = None):
    """Get step-by-step analytics for a specific campaign"""
    try:
        steps_analytics = instantly_manager.get_campaign_steps_analytics(campaign_id, start_date, end_date)
        return {"campaign_id": campaign_id, "steps_analytics": steps_analytics}
    except Exception as e:
        logger.error(f"Error fetching Instantly campaign steps analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/instantly-leads/move")
async def move_leads_to_campaign(lead_ids: List[str], campaign_id: str):
    """Move leads to a specific campaign"""
    try:
        success = instantly_manager.move_leads_to_campaign(lead_ids, campaign_id)
        if success:
            return {"message": f"Successfully moved {len(lead_ids)} leads to campaign {campaign_id}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to move leads to campaign")
    except Exception as e:
        logger.error(f"Error moving leads to campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instantly-lead-lists")
async def get_instantly_lead_lists():
    """Get all lead lists"""
    try:
        lead_lists = instantly_manager.get_lead_lists()
        return {"lead_lists": lead_lists}
    except Exception as e:
        logger.error(f"Error fetching Instantly lead lists: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/instantly-lead-lists")
async def create_instantly_lead_list(request: dict):
    """Create a new lead list"""
    try:
        name = request.get("name", "")
        description = request.get("description", "")
        lead_list_id = instantly_manager.create_lead_list(name, description)
        if lead_list_id:
            return {"message": f"Successfully created lead list: {name}", "lead_list_id": lead_list_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create lead list")
    except Exception as e:
        logger.error(f"Error creating Instantly lead list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)