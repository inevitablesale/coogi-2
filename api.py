from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import utility modules
from utils.job_scraper import JobScraper
from utils.contact_finder import ContactFinder
from utils.email_generator import EmailGenerator
from utils.memory_manager import MemoryManager
from utils.contract_analyzer import ContractAnalyzer
import requests  # Add missing import for company analysis API calls
import time  # Add time import for rate limiting
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP: Master Control Program API",
    description="Automated recruiting and outreach platform API",
    version="1.0.0"
)

# Initialize services
job_scraper = JobScraper()
contact_finder = ContactFinder()
email_generator = EmailGenerator()
memory_manager = MemoryManager()
contract_analyzer = ContractAnalyzer()
# company_analyzer = CompanyAnalyzer(rapidapi_key=os.getenv("RAPIDAPI_KEY", ""))  # Will be initialized after import

# Request/Response Models
class JobSearchRequest(BaseModel):
    query: str
    max_leads: int = 10
    hours_old: int = 24
    enforce_salary: bool = True
    auto_generate_messages: bool = False

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
    leads: List[Lead]
    jobs_found: int
    total_processed: int
    search_query: str
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

class CompanyJobsRequest(BaseModel):
    company_name: str
    max_pages: int = 3

class CompanyJobsResponse(BaseModel):
    company: str
    total_jobs: int
    jobs: List[Dict[str, Any]]
    timestamp: str

# API Endpoints
@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    api_status = {
        "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
        "RapidAPI": True,  # Using configured key
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

@app.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """Search for jobs and generate leads"""
    try:
        # Parse query
        search_params = job_scraper.parse_query(request.query)
        
        # Search jobs
        jobs = job_scraper.search_jobs(search_params, max_results=request.max_leads * 5)
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        leads = []
        processed_count = 0
        
        for job in jobs[:request.max_leads]:
            processed_count += 1
            
            # Check if already processed
            job_fingerprint = memory_manager.create_job_fingerprint(job)
            if memory_manager.is_job_processed(job_fingerprint):
                continue
            
            # Find contacts
            description = job.get('description') or job.get('job_level') or ''
            contacts, has_ta_team = contact_finder.find_contacts(
                company=job.get('company', ''),
                role_hint=job.get('title', ''),
                keywords=job_scraper.extract_keywords(description)
            )
            
            for contact in contacts[:2]:  # Top 2 contacts per job
                # Find email
                email = contact_finder.find_email(
                    contact['title'], 
                    job.get('company', '')
                )
                
                if email and not memory_manager.is_email_contacted(email):
                    # Generate outreach message if requested
                    message = ""
                    if request.auto_generate_messages:
                        message = email_generator.generate_outreach(
                            job_title=job.get('title', ''),
                            company=job.get('company', ''),
                            contact_title=contact['title'],
                            job_url=job.get('job_url', '')
                        )
                    
                    # Calculate lead score
                    score = contact_finder.calculate_lead_score(contact, job, has_ta_team)
                    
                    lead = Lead(
                        name=contact['full_name'],
                        title=contact['title'],
                        company=job.get('company', ''),
                        email=email,
                        job_title=job.get('title', ''),
                        job_url=job.get('job_url', ''),
                        message=message,
                        score=score,
                        timestamp=datetime.now().isoformat()
                    )
                    leads.append(lead)
            
            # Mark job as processed
            job_fingerprint = memory_manager.create_job_fingerprint(job)
            memory_manager.mark_job_processed(job_fingerprint)
        
        return JobSearchResponse(
            leads=leads,
            jobs_found=len(jobs),
            total_processed=processed_count,
            search_query=request.query,
            timestamp=datetime.now().isoformat()
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
    return memory_manager.get_memory_stats()

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

@app.post("/search-jobs-fast")
async def search_jobs_fast(request: JobSearchRequest):
    """Fast job search with immediate results - optimized for 30-second responses"""
    try:
        # Parse query quickly
        search_params = job_scraper.parse_query(request.query)
        
        # Get fewer jobs for faster processing
        jobs = job_scraper.search_jobs(search_params, max_results=min(request.max_leads * 2, 10))
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found matching criteria")
        
        leads = []
        processed_count = 0
        for i, job in enumerate(jobs):
            if processed_count >= request.max_leads:
                break
                
            company = job.get('company', '')
            
            # Pre-filter enterprise companies to avoid wasting API calls
            enterprise_companies = ["google", "microsoft", "amazon", "apple", "meta", "facebook", "netflix", "tesla", "lockheed martin", "general dynamics", "boeing", "ibm", "oracle", "salesforce", "adobe", "intel", "nvidia", "uber", "airbnb", "twitter", "linkedin", "paypal", "jpmorgan", "goldman sachs", "morgan stanley"]
            
            if any(enterprise in company.lower() for enterprise in enterprise_companies):
                logger.warning(f"⚠️  SKIP: {company} is enterprise company - guaranteed TA team")
                continue
            
            # Skip processed jobs quickly
            job_fingerprint = memory_manager.create_job_fingerprint(job)
            if memory_manager.is_job_processed(job_fingerprint):
                continue
                
            processed_count += 1
            logger.info(f"Processing job {processed_count}: {job.get('title')} at {company}")
                
            # Find contacts with timeout
            contacts, has_ta_team = contact_finder.find_contacts(company, job.get('title', ''), [])
            
            # Skip companies with TA teams immediately
            if has_ta_team:
                logger.warning(f"⚠️  SKIP: {company} has internal TA team - low conversion probability")
                memory_manager.mark_job_processed(job_fingerprint)
                continue
                
            # Process only the top contact for speed - but only if we have real data
            if contacts:
                contact = contacts[0]
                email = contact_finder.find_email(contact['full_name'], company)
                
                # Only create leads with real email addresses
                if email and email != "contact@google.com" and "@" in email and not email.startswith("contact@"):
                    score = contact_finder.calculate_lead_score(contact, job, has_ta_team)
                    
                    lead = {
                        "name": contact['full_name'],
                        "title": contact['title'],
                        "company": company,
                        "email": email,
                        "job_title": job.get('title', ''),
                        "job_url": job.get('job_url', ''),
                        "message": "",
                        "score": score,
                        "timestamp": datetime.now().isoformat()
                    }
                    leads.append(lead)
                else:
                    logger.warning(f"Skipping {company}: No valid email found for {contact['full_name']}")
            
            memory_manager.mark_job_processed(job_fingerprint)
            
        return {
            "leads": leads,
            "summary": {
                "leads_found": len(leads),
                "jobs_processed": len(jobs[:request.max_leads]),
                "total_jobs": len(jobs)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in fast job search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-jobs-stream")
async def search_jobs_stream(request: JobSearchRequest):
    """Stream job search results for immediate feedback"""
    def generate_stream():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting job search...', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Parse query and send update
            search_params = job_scraper.parse_query(request.query)
            search_term = search_params.get("search_term", request.query)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Searching for: {search_term}', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Search jobs and stream progress
            jobs = job_scraper.search_jobs(search_params, max_results=request.max_leads * 3)
            yield f"data: {json.dumps({'type': 'jobs_found', 'count': len(jobs), 'timestamp': datetime.now().isoformat()})}\n\n"
            
            if not jobs:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No jobs found matching criteria', 'timestamp': datetime.now().isoformat()})}\n\n"
                return
            
            leads = []
            processed_count = 0
            
            for i, job in enumerate(jobs[:request.max_leads]):
                company = job.get('company', '')
                company_msg = f'Analyzing company {i+1}/{min(len(jobs), request.max_leads)}: {company}'
                yield f"data: {json.dumps({'type': 'processing', 'message': company_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                
                # Check if already processed
                job_fingerprint = memory_manager.create_job_fingerprint(job)
                if memory_manager.is_job_processed(job_fingerprint):
                    skip_msg = f'Already processed: {company}'
                    yield f"data: {json.dumps({'type': 'skipped', 'message': skip_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                    continue
                
                # Find contacts
                role_hint = job.get('title', '')
                keywords = [role_hint] + search_params.get('keywords', [])
                contacts, has_ta_team = contact_finder.find_contacts(company, role_hint, keywords)
                
                if has_ta_team:
                    ta_msg = f'Skipping {company}: Has internal TA team'
                    yield f"data: {json.dumps({'type': 'skipped', 'message': ta_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                    memory_manager.mark_job_processed(job_fingerprint)
                    continue
                
                if not contacts:
                    contact_msg = f'No contacts found for {company}'
                    yield f"data: {json.dumps({'type': 'skipped', 'message': contact_msg, 'timestamp': datetime.now().isoformat()})}\n\n"
                    memory_manager.mark_job_processed(job_fingerprint)
                    continue
                
                # Process each contact
                for contact in contacts[:2]:  # Limit to top 2 contacts per company
                    email = contact_finder.find_email(contact['full_name'], company)
                    if not email:
                        continue
                    
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
                
                processed_count += 1
                memory_manager.mark_job_processed(job_fingerprint)
            
            # Send final summary
            yield f"data: {json.dumps({'type': 'complete', 'summary': {'leads_found': len(leads), 'jobs_processed': processed_count, 'total_jobs': len(jobs)}, 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming job search: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)