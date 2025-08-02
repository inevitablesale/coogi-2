"""
Supabase tracking utilities for company processing flow
"""

import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
else:
    supabase = None

class CompanyProcessingTracker:
    """Track each step of company processing in Supabase"""
    
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
    
    def save_domain_search(self, company: str, domain: Optional[str] = None, error: Optional[str] = None):
        """Save domain search results"""
        if not supabase:
            return
        
        try:
            data = {
                "batch_id": self.batch_id,
                "company": company,
                "domain": domain,
                "search_success": domain is not None,
                "search_error": error,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("domain_search_results").insert(data).execute()
        except Exception as e:
            print(f"Error saving domain search: {e}")
    
    def save_linkedin_resolution(self, company: str, linkedin_identifier: Optional[str] = None, error: Optional[str] = None):
        """Save LinkedIn resolution results"""
        if not supabase:
            return
        
        try:
            data = {
                "batch_id": self.batch_id,
                "company": company,
                "linkedin_identifier": linkedin_identifier,
                "resolution_success": linkedin_identifier is not None,
                "resolution_error": error,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("linkedin_resolution").insert(data).execute()
        except Exception as e:
            print(f"Error saving LinkedIn resolution: {e}")
    
    def save_rapidapi_analysis(self, company: str, has_ta_team: bool, contacts: List[Dict], 
                              employee_roles: List[str], company_found: bool, error: Optional[str] = None):
        """Save RapidAPI analysis results"""
        if not supabase:
            return
        
        try:
            data = {
                "batch_id": self.batch_id,
                "company": company,
                "has_ta_team": has_ta_team,
                "contacts_found": len(contacts),
                "top_contacts": contacts[:5] if contacts else [],
                "employee_roles": employee_roles,
                "company_found": company_found,
                "analysis_success": error is None,
                "analysis_error": error,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("rapidapi_analysis").insert(data).execute()
        except Exception as e:
            print(f"Error saving RapidAPI analysis: {e}")
    
    def save_hunter_emails(self, company: str, job_title: str, job_url: str, 
                          emails: List[Dict], error: Optional[str] = None):
        """Save Hunter.io email results"""
        if not supabase:
            return
        
        try:
            # Extract domain from the first email if available
            domain = None
            if emails and len(emails) > 0:
                # Try to get domain from email address
                first_email = emails[0].get("email", "")
                if "@" in first_email:
                    domain = first_email.split("@")[1]
                # Or use company website if available
                elif emails[0].get("company"):
                    domain = emails[0].get("company")
            
            data = {
                "batch_id": self.batch_id,
                "company": company,
                "job_title": job_title,
                "job_url": job_url,
                "emails_found": len(emails),
                "email_list": emails,  # Save structured email data
                "domain": domain,  # Add domain information
                "search_success": error is None,
                "search_error": error,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("hunter_emails").insert(data).execute()
        except Exception as e:
            print(f"Error saving Hunter emails: {e}")
    
    def save_instantly_campaign(self, company: str, campaign_id: Optional[str] = None, 
                              campaign_name: Optional[str] = None, leads_added: int = 0, 
                              error: Optional[str] = None):
        """Save Instantly.ai campaign results"""
        if not supabase:
            return
        
        try:
            data = {
                "batch_id": self.batch_id,
                "company": company,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "leads_added": leads_added,
                "campaign_success": campaign_id is not None,
                "campaign_error": error,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("instantly_campaigns").insert(data).execute()
        except Exception as e:
            print(f"Error saving Instantly campaign: {e}")
    
    def save_company_summary(self, company: str, job_title: str, job_url: str, 
                           domain_found: bool, linkedin_resolved: bool, rapidapi_analyzed: bool,
                           hunter_emails_found: bool, instantly_campaign_created: bool,
                           final_recommendation: str, error: Optional[str] = None):
        """Save company processing summary"""
        if not supabase:
            return
        
        try:
            data = {
                "batch_id": self.batch_id,
                "company": company,
                "job_title": job_title,
                "job_url": job_url,
                "domain_found": domain_found,
                "linkedin_resolved": linkedin_resolved,
                "rapidapi_analyzed": rapidapi_analyzed,
                "hunter_emails_found": hunter_emails_found,
                "instantly_campaign_created": instantly_campaign_created,
                "final_recommendation": final_recommendation,
                "processing_success": error is None,
                "processing_error": error,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("company_processing_summary").insert(data).execute()
        except Exception as e:
            print(f"Error saving company summary: {e}")
    
    def get_company_flow(self, company: str) -> Optional[Dict]:
        """Get complete flow data for a company"""
        if not supabase:
            return None
        
        try:
            response = supabase.table("company_processing_flow").select("*").eq("batch_id", self.batch_id).eq("company", company).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting company flow: {e}")
            return None
    
    def get_batch_summary(self) -> List[Dict]:
        """Get summary of all companies in this batch"""
        if not supabase:
            return []
        
        try:
            response = supabase.table("company_processing_flow").select("*").eq("batch_id", self.batch_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting batch summary: {e}")
            return [] 