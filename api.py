from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging
from datetime import datetime

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
import requests  # Add missing import for company analysis API calls
import time  # Add time import for rate limiting
import json
import asyncio
import httpx

# Supabase setup (optional - will work without it)
try:
    from supabase import create_client, Client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if supabase_url and supabase_key:
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized")
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

# Real-time logging to Supabase
async def log_to_supabase(batch_id: str, message: str, level: str = "info", company: str = None):
    """Send log message directly to Supabase in real-time"""
    if not supabase:
        return
    
    try:
        log_data = {
            "batch_id": batch_id,
            "message": message,
            "level": level,
            "company": company,
            "timestamp": datetime.now().isoformat()
        }
        
        supabase.table("search_logs").insert(log_data).execute()
        
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

@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    """Serve the web UI"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
        <head><title>MindGlimpse UI</title></head>
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
        <head><title>MindGlimpse Dashboard</title></head>
        <body>
            <h1>Dashboard Not Found</h1>
            <p>The dashboard template file is missing. Please ensure templates/dashboard.html exists.</p>
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
    create_campaigns: bool = False  # Optional: automatically create Instantly campaigns
    campaign_name: Optional[str] = None  # Optional: custom campaign name
    min_score: float = 0.5  # Minimum lead score for campaign inclusion

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
        "all_env_vars": dict(os.environ)
    }

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
        # Parse query
        search_params = job_scraper.parse_query(request.query)
        
        # Override hours_old with request parameter if provided
        if request.hours_old != 720:  # If not default
            search_params['hours_old'] = request.hours_old
            logger.info(f"🔍 Overriding hours_old to {request.hours_old} hours")
        
        # Search jobs - get all available jobs
        jobs = job_scraper.search_jobs(search_params, max_results=50)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        companies_analyzed = []
        processed_count = 0
        processed_companies = set()  # Track companies we've already analyzed
        
        # Hunter.io transparency counters
        hunter_attempts = 0
        hunter_hits = 0
        
        # Initialize campaign tracking (for immediate creation)
        campaigns_created = []
        leads_added = 0
        if request.create_campaigns:
            logger.info("🎯 Will create Instantly campaigns immediately when Hunter.io emails are found")
        
        # Rate limiting: Process companies in batches to respect 20 req/min limit
        # Each company requires ~6 RapidAPI calls (1 profile + up to 5 people pages), so process max 3 companies per batch
        max_companies_per_batch = 3
        total_jobs = len(jobs)
        
        logger.info(f"Processing {total_jobs} jobs, targeting {max_companies_per_batch} companies per batch")
        
        # Process jobs until we hit our company batch limit
        companies_in_current_batch = 0
        batch_number = 1
            
        # Collect all unique companies first
        unique_companies = []
        company_jobs = {}  # Map company to their jobs
        
        for job in jobs:
            # Check if already processed
            job_fingerprint = memory_manager.create_job_fingerprint(job)
            if memory_manager.is_job_processed(job_fingerprint):
                continue
            
            company = job.get('company', '')
            
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
            
            # Add to unique companies list
            if company not in unique_companies:
                unique_companies.append(company)
                company_jobs[company] = []
            
            company_jobs[company].append(job)
        
        logger.info(f"📊 Found {len(unique_companies)} unique companies to analyze")
        
        # Process companies in batches
        for batch_start in range(0, len(unique_companies), max_companies_per_batch):
            batch_end = min(batch_start + max_companies_per_batch, len(unique_companies))
            batch_companies = unique_companies[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//max_companies_per_batch + 1}: companies {batch_start+1}-{batch_end}")
            
            # Batch OpenAI analysis for all companies in this batch
            logger.info(f"🔍 Batch analyzing {len(batch_companies)} companies with OpenAI...")
            company_analysis_results = contact_finder.batch_analyze_companies(batch_companies)
            
            # Process each company based on analysis results
            for company in batch_companies:
                analysis = company_analysis_results.get(company, {})
                company_size = analysis.get('company_size')
                linkedin_identifier = analysis.get('linkedin_identifier', company.lower().replace(" ", "-"))
                
                # Auto-blacklist if OpenAI indicates large company
                should_blacklist_openai = False
                blacklist_reason_openai = ""
                
                # Convert company_size to int if it's a string
                if company_size:
                    try:
                        company_size_int = int(company_size) if isinstance(company_size, str) else company_size
                        if company_size_int > 100:
                            should_blacklist_openai = True
                            blacklist_reason_openai = f"OpenAI indicates large company ({company_size_int} employees)"
                            logger.info(f"🗑️  Auto-blacklisting {company} - OpenAI says {company_size_int} employees")
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️  Invalid company size for {company}: {company_size}")
                
                if should_blacklist_openai:
                    blacklist_manager.add_to_blacklist(company, blacklist_reason_openai)
                    
                    # Mark all jobs for this company as processed
                    for job in company_jobs[company]:
                        job_fingerprint = memory_manager.create_job_fingerprint(job)
                        memory_manager.mark_job_processed(job_fingerprint)
                    
                    company_analysis = {
                        "company": company,
                        "job_title": company_jobs[company][0].get('title', '') if company_jobs[company] else '',
                        "job_url": company_jobs[company][0].get('job_url', '') if company_jobs[company] else '',
                        "has_ta_team": False,  # Not checked yet
                        "contacts_found": 0,
                        "top_contacts": [],
                        "hunter_emails": [],
                        "employee_roles": [],
                        "company_website": company_jobs[company][0].get('company_website') if company_jobs[company] else None,
                        "company_found": True,
                        "recommendation": "SKIP - Auto-blacklisted via OpenAI (large company)",
                        "timestamp": datetime.now().isoformat()
                    }
                    companies_analyzed.append(company_analysis)
                    continue
                
                # Now process companies that passed OpenAI analysis with RapidAPI
                # Only make RapidAPI calls for companies that weren't auto-blacklisted
                processed_count += 1
                companies_in_current_batch += 1
                
                # Process each job for this company
                for job in company_jobs[company]:
                    job_fingerprint = memory_manager.create_job_fingerprint(job)
                    memory_manager.mark_job_processed(job_fingerprint)
                    
                    # Find contacts and analyze company with RapidAPI using LinkedIn identifier
                    try:
                        description = job.get('description') or job.get('job_level') or ''
                        result = contact_finder.find_contacts(
                            company=company,
                            linkedin_identifier=linkedin_identifier,  # Use resolved LinkedIn identifier
                            role_hint=job.get('title', ''),
                            keywords=job_scraper.extract_keywords(description),
                            company_website=job.get('company_website')  # Pass website from JobSpy
                        )
                        
                        # Handle the return format (contacts, has_ta_team, employee_roles, company_found)
                        contacts, has_ta_team, employee_roles, company_found = result
                        
                        # Get company website from job data (JobSpy domain finding)
                        company_website = job.get('company_website')
                        
                        # Auto-blacklist logic - happens immediately after RapidAPI detection
                        should_blacklist = False
                        blacklist_reason = ""
                        
                        if has_ta_team:
                            should_blacklist = True
                            blacklist_reason = "Has internal TA team"
                            logger.info(f"🗑️  Auto-blacklisting {company} - has TA team")
                        
                        if should_blacklist:
                            blacklist_manager.add_to_blacklist(company, blacklist_reason)
                            # Skip Hunter.io for blacklisted companies
                            logger.info(f"⏭️  Skipping Hunter.io for {company} - auto-blacklisted")
                            hunter_emails = []
                        else:
                            # Hunter.io email discovery for target companies only
                            hunter_emails = []
                            if not has_ta_team and company_found and company_website:  # Only if no TA team AND company found AND domain found
                                hunter_attempts += 1
                                logger.info(f"📡 Attempting Hunter.io lookup for: {company}")
                                try:
                                    hunter_emails = contact_finder.find_hunter_emails_for_target_company(
                                        company=company,
                                        job_title=job.get('title', ''),
                                        employee_roles=employee_roles,
                                        company_website=company_website
                                    )
                                    # Log success only if emails were actually found
                                    if hunter_emails:
                                        hunter_hits += len(hunter_emails)
                                        logger.info(f"✅ Found {len(hunter_emails)} Hunter.io emails for {company}")
                                        
                                        # Immediately send to Instantly if requested
                                        if request.create_campaigns:
                                            logger.info(f"🚀 Immediately sending {len(hunter_emails)} emails to Instantly for {company}")
                                            try:
                                                # Create leads from Hunter.io emails
                                                leads = []
                                                for email in hunter_emails:
                                                    lead = {
                                                        "name": "Hiring Manager",
                                                        "email": email,
                                                        "company": company,
                                                        "job_title": job.get('title', ''),
                                                        "job_url": job.get('job_url', ''),
                                                        "title": "Hiring Manager",
                                                        "company_website": company_website,
                                                        "score": 0.8,
                                                        "hunter_emails": hunter_emails
                                                    }
                                                    leads.append(lead)
                                                
                                                # Create campaign immediately
                                                campaign_name = request.campaign_name or f"Immediate_{company.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                                campaign_id = instantly_manager.create_recruiting_campaign(
                                                    leads=leads,
                                                    campaign_name=campaign_name
                                                )
                                                
                                                if campaign_id:
                                                    campaigns_created.append(campaign_id)
                                                    leads_added += len(hunter_emails)
                                                    logger.info(f"✅ Immediately created Instantly campaign for {company}: {campaign_name} (ID: {campaign_id})")
                                                else:
                                                    logger.error(f"❌ Failed to immediately create Instantly campaign for {company}")
                                                    
                                            except Exception as e:
                                                logger.error(f"❌ Error immediately creating Instantly campaign for {company}: {e}")
                                    else:
                                        logger.warning(f"⚠️  No Hunter.io emails found for {company}")
                                except Exception as e:
                                    logger.error(f"Hunter.io error for {company}: {e}")
                            elif has_ta_team:
                                logger.info(f"⏭️  Skipping Hunter.io for {company} - has TA team")
                            elif not company_found:
                                logger.info(f"⏭️  Skipping Hunter.io for {company} - company not found")
                            elif not company_website:
                                logger.info(f"⏭️  Skipping Hunter.io for {company} - no domain found")
                            
                            # Create company analysis record
                            company_analysis = {
                                "company": company,
                                "job_title": job.get('title', ''),
                                "job_url": job.get('job_url', ''),
                                "has_ta_team": has_ta_team,
                                "contacts_found": len(contacts),
                                "top_contacts": contacts[:5],  # Top 5 contacts
                                "hunter_emails": hunter_emails,
                                "employee_roles": employee_roles,
                                "company_website": company_website,
                                "company_found": company_found,
                                "recommendation": "SKIP - Auto-blacklisted" if should_blacklist else "PROCESS - Target company",
                                "timestamp": datetime.now().isoformat()
                            }
                            companies_analyzed.append(company_analysis)
                            
                    except Exception as e:
                        logger.error(f"Error analyzing {company}: {e}")
                        # Create error record
                        company_analysis = {
                            "company": company,
                            "job_title": job.get('title', ''),
                            "job_url": job.get('job_url', ''),
                            "has_ta_team": False,
                            "contacts_found": 0,
                            "top_contacts": [],
                            "hunter_emails": [],
                            "employee_roles": [],
                            "company_website": job.get('company_website'),
                            "company_found": False,
                            "recommendation": f"ERROR - {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        }
                        companies_analyzed.append(company_analysis)
                
                # Wait between batches to respect rate limits
                if batch_end < len(unique_companies):
                    logger.info(f"Batch complete. Waiting 60 seconds before next batch...")
                    time.sleep(60)
            

        

        
        # Log Hunter.io summary
        logger.info(f"📊 Hunter.io Summary: {hunter_attempts} attempts, {hunter_hits} emails found")
        
        return JobSearchResponse(
            companies_analyzed=companies_analyzed,
            jobs_found=len(jobs),
            total_processed=processed_count,
            search_query=request.query,
            timestamp=datetime.now().isoformat(),
            campaigns_created=campaigns_created if campaigns_created else None,
            leads_added=leads_added
        )
        
    except Exception as e:
        logger.error(f"Error in job search: {e}")
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
                    contacts, has_ta_team, employee_roles, company_found = contact_finder.find_contacts(company, role_hint, keywords, job.get('linkedin_company_url'))
                    
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
                            company_website=job.get('company_website')
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
async def process_jobs_background(request: JobSearchRequest):
    """Process jobs in background and send results via webhook"""
    try:
        # Generate batch ID
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Mark search as active
        active_searches[batch_id] = False  # False = not cancelled
        
        # Parse query and search jobs
        search_params = job_scraper.parse_query(request.query)
        jobs = job_scraper.search_jobs(search_params, max_results=50)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
        
        # Process jobs in background (async)
        asyncio.create_task(process_jobs_background_task(batch_id, jobs, request))
        
        return {
            "status": "processing",
            "batch_id": batch_id,
            "jobs_found": len(jobs),
            "webhook_url": f"http://localhost:8000/webhook/results"
        }
        
    except Exception as e:
        logger.error(f"Error starting background processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel-search/{batch_id}")
async def cancel_search(batch_id: str):
    """Cancel an active search by batch_id"""
    try:
        if batch_id not in active_searches:
            raise HTTPException(status_code=404, detail="Search not found")
        
        # Mark search as cancelled
        active_searches[batch_id] = True
        logger.info(f"🚫 Search {batch_id} marked for cancellation")
        
        return {
            "status": "cancelled",
            "batch_id": batch_id,
            "message": "Search cancellation requested"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling search {batch_id}: {e}")
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
    """Get all active searches"""
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

async def process_jobs_background_task(batch_id: str, jobs: List[Dict], request: JobSearchRequest):
    """Background task to process jobs and send webhook results"""
    try:
        results = []
        processed_count = 0
        
        # Log start of processing
        await log_to_supabase(batch_id, f"🚀 Starting job search processing for {len(jobs)} jobs", "info")
        
        # Process jobs in batches with rate limiting
        max_jobs_per_batch = 5
        total_jobs = len(jobs)
        
        for batch_start in range(0, total_jobs, max_jobs_per_batch):
            # Check if search has been cancelled
            if batch_id in active_searches and active_searches[batch_id]:
                await log_to_supabase(batch_id, "🚫 Search was cancelled, stopping processing", "warning")
                break
            
            batch_end = min(batch_start + max_jobs_per_batch, total_jobs)
            batch_jobs = jobs[batch_start:batch_end]
            
            await log_to_supabase(batch_id, f"📦 Processing batch {batch_start//max_jobs_per_batch + 1} ({len(batch_jobs)} jobs)", "info")
            
            # Process current batch
            for job in batch_jobs:
                # Check for cancellation before each job
                if batch_id in active_searches and active_searches[batch_id]:
                    await log_to_supabase(batch_id, "🚫 Search was cancelled, stopping processing", "warning")
                    break
                
                company = job.get('company', '')
                job_title = job.get('title', '')
                
                await log_to_supabase(batch_id, f"🔍 Analyzing company: {company} - {job_title}", "info", company)
                
                # Skip enterprise companies
                enterprise_companies = ["google", "microsoft", "amazon", "apple"]
                if company and any(enterprise in company.lower() for enterprise in enterprise_companies):
                    await log_to_supabase(batch_id, f"⏭️ Skipping enterprise company: {company}", "info", company)
                    continue
                
                # Analyze company
                try:
                    contacts, has_ta_team, employee_roles, company_found = contact_finder.find_contacts(
                        company=company,
                        role_hint=job.get('title', ''),
                        keywords=job_scraper.extract_keywords(job.get('description', '')),
                        linkedin_company_url=job.get('linkedin_company_url')
                    )
                    
                    await log_to_supabase(batch_id, f"📊 Found {len(contacts)} contacts, TA team: {has_ta_team}", "info", company)
                    
                    # Hunter.io email discovery
                    if not has_ta_team and company_found:
                        await log_to_supabase(batch_id, f"📡 Attempting Hunter.io lookup for: {company}", "info", company)
                        
                        try:
                            hunter_emails = contact_finder.find_hunter_emails_for_target_company(
                                company=company,
                                job_title=job_title,
                                employee_roles=employee_roles,
                                company_website=job.get('company_website')
                            )
                            
                            if hunter_emails:
                                await log_to_supabase(batch_id, f"✅ Found {len(hunter_emails)} Hunter.io emails for {company}", "success", company)
                                
                                # Create Instantly campaign if requested
                                if request.create_campaigns:
                                    await log_to_supabase(batch_id, f"🚀 Creating Instantly campaign for {company}", "info", company)
                                    # Campaign creation logic would go here
                            else:
                                await log_to_supabase(batch_id, f"⚠️ No Hunter.io emails found for {company}", "warning", company)
                                
                        except Exception as e:
                            await log_to_supabase(batch_id, f"❌ Hunter.io error for {company}: {str(e)}", "error", company)
                    
                    # Create result
                    result = WebhookResult(
                        company=company,
                        job_title=job_title,
                        job_url=job.get('job_url', ''),
                        has_ta_team=has_ta_team,
                        contacts_found=len(contacts),
                        top_contacts=contacts[:3] if contacts else [],
                        recommendation="TARGET" if not has_ta_team else "SKIP - Has TA team",
                        hunter_emails=hunter_emails if 'hunter_emails' in locals() else [],
                        timestamp=datetime.now().isoformat()
                    )
                    
                    results.append(result)
                    processed_count += 1
                    
                    await log_to_supabase(batch_id, f"✅ Completed analysis for {company}", "success", company)
                    
                except Exception as e:
                    await log_to_supabase(batch_id, f"❌ Error analyzing {company}: {str(e)}", "error", company)
            
            # Check for cancellation before sending webhook
            if batch_id in active_searches and active_searches[batch_id]:
                await log_to_supabase(batch_id, "🚫 Search was cancelled, stopping processing", "warning")
                break
            
            # Send webhook for this batch
            webhook_data = WebhookRequest(
                batch_id=batch_id,
                results=results,
                summary={
                    "total_processed": processed_count,
                    "total_jobs": total_jobs,
                    "batch_number": batch_start // max_jobs_per_batch + 1
                },
                timestamp=datetime.now().isoformat()
            )
            
            # Send webhook (in production, this would be to your webhook URL)
            await send_webhook(webhook_data)
            
            await log_to_supabase(batch_id, f"📤 Sent webhook for batch {batch_start//max_jobs_per_batch + 1}", "info")
            
            # Wait between batches
            if batch_end < total_jobs:
                await log_to_supabase(batch_id, "⏳ Waiting 60 seconds before next batch...", "info")
                await asyncio.sleep(60)
        
        # Clean up the search from active_searches
        if batch_id in active_searches:
            del active_searches[batch_id]
        
        await log_to_supabase(batch_id, f"🎉 Background processing complete for batch {batch_id}", "success")
        
    except Exception as e:
        await log_to_supabase(batch_id, f"❌ Error in background processing: {str(e)}", "error")
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
        
        # Get batch summary
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
async def get_instantly_campaigns():
    """Get all Instantly.ai campaigns"""
    try:
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

@app.get("/instantly-stats")
async def get_instantly_stats():
    """Get Instantly.ai statistics"""
    try:
        stats = instantly_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching Instantly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)