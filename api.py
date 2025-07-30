from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging
from datetime import datetime

# Import utility modules
from utils.job_scraper import JobScraper
from utils.contact_finder import ContactFinder
from utils.email_generator import EmailGenerator
from utils.memory_manager import MemoryManager
import requests  # Add missing import for company analysis API calls

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
            
            # Get people data from SaleLeads API
            try:
                people_data = []
                people_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/people"
                headers = {
                    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", ""),
                    "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
                }
                
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)