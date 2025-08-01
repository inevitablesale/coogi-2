import os
import logging
import requests
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
logger = logging.getLogger(__name__)

class InstantlyManager:
    def __init__(self):
        self.api_key = os.getenv("INSTANTLY_API_KEY", "")
        self.base_url = "https://api.instantly.ai"
        
        # Email domains for rotation (you can add more)
        self.email_domains = [
            "chuck@liacgroupagency.com",
            "chuck@liacgroupworkforce.com", 
            "chuck@liacworkforce.com",
            "cole@liacgroupagency.com",
            "cole@liacgroupworkforce.com",
            "cole@liacworkforce.com",
            "contact@liacgroupagency.com",
            "contact@liacgroupworkforce.com",
            "contact@liacworkforce.com"
        ]
        self.current_domain_index = 0
        
    def create_lead_list(self, name: str, description: str = "") -> Optional[str]:
        """Create a new lead list"""
        try:
            url = f"{self.base_url}/api/v2/lead-lists"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "name": name,
                "description": description
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to create lead list: {response.status_code}")
                return None
                
            result = response.json()
            lead_list_id = result.get('id')
            logger.info(f"✅ Created lead list: {name} (ID: {lead_list_id})")
            return lead_list_id
            
        except Exception as e:
            logger.error(f"Error creating lead list: {e}")
            return None

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get specific campaign details"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/{campaign_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to get campaign {campaign_id}: {response.status_code}")
                return None
                
            campaign = response.json()
            
            # Add analytics data
            analytics = self.get_campaign_analytics(campaign_id)
            if analytics:
                campaign.update(analytics)
                
            return campaign
            
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            return None

    def activate_campaign(self, campaign_id: str) -> bool:
        """Activate a campaign"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/{campaign_id}/activate"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to activate campaign {campaign_id}: {response.status_code}")
                return False
                
            logger.info(f"✅ Activated campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error activating campaign {campaign_id}: {e}")
            return False

    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/{campaign_id}/pause"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to pause campaign {campaign_id}: {response.status_code}")
                return False
                
            logger.info(f"✅ Paused campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error pausing campaign {campaign_id}: {e}")
            return False

    def get_all_leads(self) -> List[Dict[str, Any]]:
        """Get all leads for dashboard display using the correct POST /api/v2/leads/list endpoint"""
        try:
            url = f"{self.base_url}/api/v2/leads/list"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use POST with empty body to get all leads (increase limit to get more)
            payload = {
                "limit": 100  # Get up to 100 leads instead of default 10
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract leads from the 'items' field as per API documentation
                if isinstance(data, dict) and 'items' in data:
                    leads = data['items']
                    logger.info(f"✅ Successfully retrieved {len(leads)} leads from /api/v2/leads/list")
                else:
                    logger.error(f"Unexpected response structure: {type(data)}")
                    return []
                
                # Ensure leads is a list
                if not isinstance(leads, list):
                    logger.error(f"Expected list of leads, got: {type(leads)}")
                    return []
                
                # Enhance with additional data based on API schema
                for lead in leads:
                    if isinstance(lead, dict):
                        # Map API fields to dashboard fields
                        lead['name'] = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                        lead['company'] = lead.get('company_name', 'N/A')
                        lead['title'] = lead.get('job_title', 'N/A')
                        lead['email'] = lead.get('email', 'N/A')
                        lead['score'] = lead.get('pl_value_lead', 'Medium')  # Use lead value as score
                        lead['status'] = self._get_status_text(lead.get('status', 1))
                        lead['campaign_name'] = lead.get('campaign', 'N/A')
                        lead['website'] = lead.get('website', 'N/A')
                
                return leads
            else:
                logger.error(f"Failed to get leads: {response.status_code} - {response.text}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting leads: {e}")
            return []
    
    def _get_status_text(self, status_code: int) -> str:
        """Convert status code to readable text based on API documentation"""
        status_map = {
            1: "Active",
            2: "Paused", 
            3: "Completed",
            -1: "Bounced",
            -2: "Unsubscribed",
            -3: "Skipped"
        }
        return status_map.get(status_code, "Unknown")
    
    def add_leads_to_list(self, lead_list_id: str, leads: List[Dict[str, Any]]) -> bool:
        """
        Add leads to a lead list using the correct /api/v2/leads endpoint
        """
        if not self.api_key or not lead_list_id:
            logger.warning("Missing Instantly API key or lead list ID")
            return False
            
        try:
            url = f"{self.base_url}/api/v2/leads"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            success_count = 0
            for lead in leads:
                # Format lead for the /api/v2/leads endpoint
                formatted_lead = {
                    "email": lead.get("email", ""),
                    "first_name": lead.get("name", "").split()[0] if lead.get("name") else "",
                    "last_name": " ".join(lead.get("name", "").split()[1:]) if lead.get("name") and len(lead.get("name", "").split()) > 1 else "",
                    "company_name": lead.get("company", ""),
                    "job_title": lead.get("job_title", ""),
                    "website": lead.get("company_website", ""),
                    "list_id": lead_list_id
                }
                
                # Add custom fields if they exist
                custom_fields = {}
                if lead.get("title"):
                    custom_fields["contact_title"] = lead.get("title")
                if lead.get("job_url"):
                    custom_fields["job_url"] = lead.get("job_url")
                if lead.get("score"):
                    custom_fields["lead_score"] = str(lead.get("score"))
                if lead.get("hunter_emails"):
                    custom_fields["hunter_emails"] = ", ".join(lead.get("hunter_emails", []))
                if lead.get("company_website"):
                    custom_fields["company_website"] = lead.get("company_website")
                if lead.get("job_title"):
                    custom_fields["target_job_title"] = lead.get("job_title")
                
                if custom_fields:
                    formatted_lead["custom_fields"] = custom_fields
                
                response = requests.post(url, headers=headers, json=formatted_lead, timeout=30)
                
                if response.status_code == 200:
                    success_count += 1
                    lead_data = response.json()
                    logger.info(f"✅ Created lead: {lead.get('email', 'N/A')} (ID: {lead_data.get('id', 'N/A')})")
                else:
                    logger.error(f"❌ Failed to create lead {lead.get('email', 'N/A')}: {response.status_code} - {response.text}")
            
            if success_count > 0:
                logger.info(f"✅ Successfully created {success_count}/{len(leads)} leads in list {lead_list_id}")
                return True
            else:
                logger.error(f"❌ Failed to create any leads in list {lead_list_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding leads to list: {e}")
            return False
    
    def create_campaign_with_lead_list(self, name: str, subject_line: str, message_template: str, 
                                     sender_email: str = None, sender_name: str = None, 
                                     lead_list_id: str = None) -> Optional[str]:
        """
        Create a new campaign in Instantly that references a lead list
        Returns campaign ID if successful
        """
        if not self.api_key:
            logger.warning("No Instantly API key provided")
            return None
            
        try:
            url = f"{self.base_url}/api/v2/campaigns"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            payload = {
                "name": name,
                "campaign_schedule": {
                    "schedules": [
                        {
                            "name": "Default Schedule",
                            "timing": {
                                "from": "09:00",
                                "to": "17:00"
                            },
                            "days": {
                                "0": True,  # Monday
                                "1": True,  # Tuesday
                                "2": True,  # Wednesday
                                "3": True,  # Thursday
                                "4": True,  # Friday
                                "5": False, # Saturday
                                "6": False  # Sunday
                            },
                            "timezone": "America/New_York"
                        }
                    ]
                },
                "sequences": [
                    {
                        "steps": [
                            {
                                "step": 1,
                                "subject": subject_line,
                                "body": message_template
                            }
                        ]
                    }
                ],
                "email_gap": 10,
                "random_wait_max": 5,
                "text_only": False,
                "daily_limit": 50,
                "stop_on_reply": True,
                "link_tracking": True,
                "open_tracking": True,
                "stop_on_auto_reply": False,
                "daily_max_leads": 25,
                "prioritize_new_leads": False,
                "match_lead_esp": False,
                "stop_for_company": False,
                "insert_unsubscribe_header": True,
                "allow_risky_contacts": False,
                "disable_bounce_protect": False
            }
            
            # Add email list if sender_email is provided
            if sender_email:
                payload["email_list"] = [sender_email]
            
            # Add lead list reference if provided
            if lead_list_id:
                payload["list_id"] = lead_list_id
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                campaign_id = data.get("id")
                logger.info(f"✅ Created Instantly campaign: {name} (ID: {campaign_id}) with lead list {lead_list_id}")
                return campaign_id
            else:
                logger.error(f"❌ Failed to create Instantly campaign: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating Instantly campaign: {e}")
            return None
    
    def add_leads_to_campaign(self, campaign_id: str, leads: List[Dict[str, Any]]) -> bool:
        """
        Add leads to a campaign (without sending)
        """
        if not self.api_key or not campaign_id:
            logger.warning("Missing Instantly API key or campaign ID")
            return False
            
        try:
            url = f"{self.base_url}/api/v2/campaigns/{campaign_id}/leads"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Format leads for Instantly
            formatted_leads = []
            for lead in leads:
                formatted_lead = {
                    "email": lead.get("email", ""),
                    "first_name": lead.get("name", "").split()[0] if lead.get("name") else "",
                    "last_name": " ".join(lead.get("name", "").split()[1:]) if lead.get("name") and len(lead.get("name", "").split()) > 1 else "",
                    "company": lead.get("company", ""),
                    "job_title": lead.get("job_title", ""),
                    "contact_job_title": lead.get("title", ""),  # Contact's job title
                    "custom_fields": {
                        "contact_title": lead.get("title", ""),
                        "job_url": lead.get("job_url", ""),
                        "lead_score": str(lead.get("score", 0)),
                        "hunter_emails": ", ".join(lead.get("hunter_emails", [])),
                        "company_website": lead.get("company_website", ""),
                        "target_job_title": lead.get("job_title", ""),  # Job they're hiring for
                        "contact_title": lead.get("title", "")  # For template personalization
                    }
                }
                formatted_leads.append(formatted_lead)
            
            payload = {
                "leads": formatted_leads,
                "status": "draft"  # Keep as draft - don't send yet
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 201:
                data = response.json()
                added_count = data.get("added_count", 0)
                logger.info(f"✅ Added {added_count} leads to Instantly campaign {campaign_id}")
                return True
            else:
                logger.error(f"❌ Failed to add leads to campaign: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding leads to Instantly campaign: {e}")
            return False
    
    def get_campaign_status(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get campaign status and statistics
        """
        if not self.api_key:
            return None
            
        try:
            url = f"{self.base_url}/api/v2/campaigns/{campaign_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get campaign status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting campaign status: {e}")
            return None
    
    def generate_email_template(self, job_title: str, company: str, contact_name: str = "", 
                              contact_title: str = "", company_type: str = "", tone: str = "professional") -> Dict[str, str]:
        """
        Generate targeted, concise email template for outreach with industry-specific messaging
        """
        # Create personalized subject line
        if contact_title and "recruiter" in contact_title.lower():
            subject_line = f"Re: {job_title} - Recruiting Partnership"
        elif contact_title and "hr" in contact_title.lower():
            subject_line = f"Re: {job_title} - HR Partnership"
        else:
            subject_line = f"Re: {job_title} Position at {company}"
        
        # Personalized greeting based on contact info
        if contact_name:
            greeting = f"Hi {contact_name},"
        elif contact_title:
            greeting = f"Hi {contact_title},"
        else:
            greeting = "Hi there,"
        
        # Industry-specific messaging
        industry_message = self._get_industry_specific_message(company_type, job_title, company)
        
        # Concise, targeted message with personalization
        message_template = f"""{greeting}

{industry_message}

Would you be open to a quick call to discuss your hiring needs?

Best,
[Your Name]

---
Job URL: {{job_url}}
Company: {{company}}
Position: {{job_title}}
Contact: {{contact_title}}
        """.strip()
        
        return {
            "subject_line": subject_line,
            "message_template": message_template
        }
    
    def _get_industry_specific_message(self, company_type: str, job_title: str, company: str) -> str:
        """
        Get industry-specific messaging for email templates
        """
        if company_type == "tech_startups":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have a network of talented tech professionals who thrive in fast-paced, innovative environments and would be perfect for this position."
        
        elif company_type == "established_companies":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have experienced professionals who excel in structured environments and would be great additions to your team."
        
        elif company_type == "agencies_consulting":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have consultants and agency professionals who are skilled at managing multiple clients and delivering results."
        
        elif company_type == "healthcare":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have healthcare professionals who understand the unique challenges of the industry and would be valuable to your team."
        
        elif company_type == "financial_services":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have finance professionals who understand compliance and regulatory requirements and would be excellent fits."
        
        elif company_type == "education":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have education professionals who are passionate about learning and would be great additions to your team."
        
        elif company_type == "retail_consumer":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have consumer-focused professionals who understand customer experience and would be perfect for this position."
        
        elif company_type == "manufacturing_industrial":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have industrial professionals who understand operations and would be valuable to your team."
        
        elif company_type == "media_entertainment":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have creative professionals who understand content and would be perfect for this position."
        
        elif company_type == "real_estate_construction":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have real estate and construction professionals who understand the industry and would be great fits."
        
        elif company_type == "nonprofit_government":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have mission-driven professionals who are passionate about making a difference and would be perfect for this position."
        
        elif company_type == "transportation_logistics":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have logistics professionals who understand supply chain operations and would be valuable to your team."
        
        elif company_type == "energy_utilities":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have energy professionals who understand regulatory compliance and would be excellent fits."
        
        elif company_type == "legal_professional":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have legal professionals who understand compliance and would be perfect for this position."
        
        elif company_type == "telecommunications":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have telecom professionals who understand network infrastructure and would be great additions."
        
        elif company_type == "aerospace_defense":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have aerospace professionals who understand complex systems and would be valuable to your team."
        
        elif company_type == "pharmaceuticals_biotech":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have pharma professionals who understand clinical research and would be perfect for this position."
        
        elif company_type == "food_beverage":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have food industry professionals who understand consumer preferences and would be great fits."
        
        elif company_type == "fashion_apparel":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have fashion professionals who understand brand development and would be perfect for this position."
        
        elif company_type == "gaming_interactive":
            return f"I noticed you're hiring for a {job_title} role at {company}. I have gaming professionals who understand interactive entertainment and would be excellent additions."
        
        else:
            return f"I noticed you're hiring for a {job_title} role at {company}. I have qualified candidates who would be perfect for this position."
    
    def _classify_company_type(self, company: str, job_title: str = "") -> str:
        """
        Intelligently classify company type based on company name and job context
        """
        company_lower = company.lower()
        job_lower = job_title.lower()
        
        # First, check if this is a healthcare job search
        healthcare_job_keywords = ["nurse", "rn", "lvn", "cna", "doctor", "physician", "medical", "healthcare", "clinical", "patient", "hospital", "clinic", "health", "care", "therapist", "pharmacist", "dental", "veterinary", "mental health", "behavioral"]
        
        if any(keyword in job_lower for keyword in healthcare_job_keywords):
            # For healthcare job searches, prioritize healthcare classification
            if any(keyword in company_lower for keyword in ["health", "medical", "pharma", "biotech", "healthcare", "hospital", "clinic", "therapy", "wellness", "fitness", "dental", "veterinary", "mayo", "pfizer", "moderna", "johnson", "cvs", "walgreens", "unitedhealth", "anthem", "healthcare solutions", "healthcare", "medical", "clinical", "patient", "care"]):
                return "healthcare"
            # Even if company doesn't have healthcare keywords, if job is healthcare-related, classify as healthcare
            return "healthcare"
        
        # Tech & Startups (only if not healthcare job)
        if any(keyword in company_lower for keyword in ["startup", "tech", "ai", "software", "digital", "app", "platform", "saas", "api", "cloud", "data", "analytics", "machine learning", "ml", "artificial intelligence", "openai", "stripe", "notion", "figma", "zoom", "slack", "airtable", "linear", "vercel", "netlify"]):
            return "tech_startups"
        
        # Established Companies
        elif any(keyword in company_lower for keyword in ["inc", "corp", "llc", "ltd", "company", "enterprise", "corporation", "industries", "group", "holdings", "partners", "microsoft", "apple inc", "google", "amazon", "salesforce", "oracle", "ibm", "intel", "cisco"]):
            return "established_companies"
        
        # Healthcare (check before agencies to avoid "solutions" conflict)
        elif any(keyword in company_lower for keyword in ["health", "medical", "pharma", "biotech", "healthcare", "hospital", "clinic", "therapy", "wellness", "fitness", "dental", "veterinary", "mayo", "pfizer", "moderna", "johnson", "cvs", "walgreens", "unitedhealth", "anthem", "healthcare solutions"]):
            return "healthcare"
        
        # Agencies & Consulting
        elif any(keyword in company_lower for keyword in ["agency", "consulting", "services", "advisory", "partners", "solutions", "strategies", "management", "mckinsey", "deloitte", "accenture", "bcg partners", "bain", "pwc", "ey", "kpmg"]):
            return "agencies_consulting"
        
        # Financial Services
        elif any(keyword in company_lower for keyword in ["finance", "bank", "insurance", "wealth", "investment", "capital", "credit", "lending", "mortgage", "trading", "asset", "fund", "goldman", "jpmorgan", "morgan stanley", "wells fargo", "chase", "citigroup", "state farm", "allstate", "robinhood", "stripe"]):
            return "financial_services"
        
        # Education
        elif any(keyword in company_lower for keyword in ["education", "learning", "school", "university", "college", "academy", "training", "edtech", "tutoring", "curriculum", "harvard", "stanford", "mit", "coursera", "udemy", "khan", "duolingo"]):
            return "education"
        
        # Retail & Consumer
        elif any(keyword in company_lower for keyword in ["retail", "ecommerce", "store", "shop", "marketplace", "consumer", "brand", "walmart", "target", "starbucks", "mcdonalds", "airbnb"]):
            return "retail_consumer"
        
        # Manufacturing & Industrial
        elif any(keyword in company_lower for keyword in ["manufacturing", "industrial", "factory", "production", "supply chain", "logistics", "warehouse", "distribution", "automotive", "construction", "tesla", "ford", "gm", "boeing", "caterpillar", "fedex", "ups", "dhl"]):
            return "manufacturing_industrial"
        
        # Media & Entertainment
        elif any(keyword in company_lower for keyword in ["media", "entertainment", "gaming", "publishing", "broadcasting", "streaming", "content", "creative", "design", "advertising", "marketing", "netflix", "disney", "spotify", "ea", "activision", "warner", "paramount"]):
            return "media_entertainment"
        
        # Real Estate & Construction
        elif any(keyword in company_lower for keyword in ["real estate", "property", "development", "construction", "architecture", "engineering", "infrastructure", "zillow", "redfin", "cbre", "bechtel", "fluor", "blackstone", "we work"]):
            return "real_estate_construction"
        
        # Nonprofit & Government
        elif any(keyword in company_lower for keyword in ["nonprofit", "foundation", "charity", "ngo", "government", "public", "social", "community", "advocacy", "red cross", "unicef", "un", "who", "world bank"]):
            return "nonprofit_government"
        
        # Transportation & Logistics
        elif any(keyword in company_lower for keyword in ["transportation", "logistics", "shipping", "delivery", "freight", "trucking", "railway", "airline", "cruise", "uber", "lyft", "doordash", "instacart", "grubhub"]):
            return "transportation_logistics"
        
        # Energy & Utilities
        elif any(keyword in company_lower for keyword in ["energy", "utility", "power", "electric", "gas", "oil", "renewable", "solar", "wind", "nuclear", "exxon", "chevron", "shell", "bp", "duke energy", "southern company"]):
            return "energy_utilities"
        
        # Legal & Professional Services
        elif any(keyword in company_lower for keyword in ["law", "legal", "attorney", "lawyer", "law firm", "legal services", "compliance", "regulatory", "skadden", "latham", "kirkland", "sullivan"]):
            return "legal_professional"
        
        # Telecommunications
        elif any(keyword in company_lower for keyword in ["telecom", "telecommunications", "phone", "mobile", "wireless", "internet", "isp", "at&t", "verizon", "t-mobile", "sprint", "charter"]):
            return "telecommunications"
        
        # Aerospace & Defense
        elif any(keyword in company_lower for keyword in ["aerospace", "defense", "military", "aviation", "space", "lockheed", "boeing", "northrop", "raytheon", "general dynamics", "spacex", "blue origin"]):
            return "aerospace_defense"
        
        # Pharmaceuticals & Biotech
        elif any(keyword in company_lower for keyword in ["pharma", "pharmaceutical", "biotech", "biotechnology", "drug", "medicine", "clinical", "research", "pfizer", "moderna", "johnson", "merck", "gilead sciences", "amgen", "biogen"]):
            return "pharmaceuticals_biotech"
        
        # Food & Beverage
        elif any(keyword in company_lower for keyword in ["food", "beverage", "restaurant", "catering", "dining", "cafe", "bakery", "mcdonalds", "kfc", "subway", "dominos", "pizza hut", "coca cola", "pepsi"]):
            return "food_beverage"
        
        # Fashion & Apparel
        elif any(keyword in company_lower for keyword in ["fashion", "apparel", "clothing", "wear", "style", "designer", "nike", "adidas", "under armour", "lululemon", "gap inc", "h&m", "zara", "uniqlo"]):
            return "fashion_apparel"
        
        # Gaming & Interactive Entertainment
        elif any(keyword in company_lower for keyword in ["gaming", "game", "esports", "interactive", "playstation", "xbox", "nintendo", "ea", "activision", "ubisoft", "take-two", "roblox", "epic"]):
            return "gaming_interactive"
        
        # If no specific category found, try to infer from company characteristics
        else:
            # Check for common patterns that might indicate company type
            if any(char.isdigit() for char in company) and any(keyword in company_lower for keyword in ["inc", "corp", "llc", "ltd"]):
                return "established_companies"
            elif len(company.split()) <= 2 and not any(keyword in company_lower for keyword in ["inc", "corp", "llc", "ltd", "company"]):
                return "tech_startups"  # Short names often indicate startups
            else:
                return "established_companies"  # Default to established companies
    
    def get_next_sender_email(self) -> str:
        """Get next email domain for rotation"""
        email = self.email_domains[self.current_domain_index]
        self.current_domain_index = (self.current_domain_index + 1) % len(self.email_domains)
        return email
    
    def get_sender_name_from_email(self, email: str) -> str:
        """Extract sender name from email"""
        name = email.split('@')[0].title()
        return name
    
    def create_recruiting_campaign(self, leads: List[Dict[str, Any]], 
                                 campaign_name: str = None) -> Optional[str]:
        """
        Create a complete recruiting campaign with leads
        """
        if not leads:
            logger.warning("No leads provided for campaign")
            return None
        
        # Group leads by company type for better targeting
        leads_by_company_type = {}
        for lead in leads:
            company = lead.get("company", "").lower()
            
            # Enhanced company type classification with intelligent categorization
            company_type = self._classify_company_type(company, job_title=lead.get("job_title", ""))
            
            if company_type not in leads_by_company_type:
                leads_by_company_type[company_type] = []
            leads_by_company_type[company_type].append(lead)
        
        # Create separate campaigns for each company type
        campaign_ids = []
        
        for company_type, company_leads in leads_by_company_type.items():
            if not company_leads:
                continue
                
            # Generate persistent campaign name (no timestamp)
            company_campaign_name = f"{company_type.replace('_', '_').title()}_Campaign"
            
            # Generate email template from first lead in this company type group
            first_lead = company_leads[0]
            template_data = self.generate_email_template(
                job_title=first_lead.get("job_title", ""),
                company=first_lead.get("company", ""),
                contact_name=first_lead.get("name", ""),
                contact_title=first_lead.get("title", ""),
                company_type=company_type
            )
            
            # Get rotating sender email
            sender_email = self.get_next_sender_email()
            sender_name = self.get_sender_name_from_email(sender_email)
            
            # Step 1: Find or create lead list for this company type
            lead_list_id = self.find_or_create_lead_list(company_type)
            
            if lead_list_id:
                # Step 2: Add leads to the list (always add, since lists are persistent)
                success = self.add_leads_to_list(lead_list_id, company_leads)
                if success:
                    logger.info(f"✅ Added {len(company_leads)} leads to list {lead_list_id}")
                
                # Step 3: Find or create campaign for this company type
                campaign_id = self.find_or_create_campaign(company_type, company_campaign_name, template_data, sender_email, sender_name, lead_list_id)
                
                if campaign_id:
                    logger.info(f"✅ Found/Created {company_type} campaign '{company_campaign_name}' with {len(company_leads)} leads")
                    campaign_ids.append(campaign_id)
        
        # Return the first campaign ID for backward compatibility
        return campaign_ids[0] if campaign_ids else None

    def get_lead_lists(self) -> List[Dict[str, Any]]:
        """
        Get all lead lists from Instantly
        """
        if not self.api_key:
            logger.warning("No Instantly API key provided")
            return []
            
        try:
            url = f"{self.base_url}/api/v2/lead-lists"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                logger.info(f"✅ Retrieved {len(items)} lead lists")
                return items
            else:
                logger.error(f"❌ Failed to get lead lists: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting lead lists: {e}")
            return []
    
    def find_or_create_lead_list(self, company_type: str) -> Optional[str]:
        """
        Find an existing lead list for this company type or create a new one
        Returns lead list ID
        """
        if not self.api_key:
            logger.warning("No Instantly API key provided")
            return None
            
        # Look for existing lead list with this company type
        lead_lists = self.get_lead_lists()
        lead_list_name = f"{company_type.replace('_', '_').title()}_Leads"
        
        for lead_list in lead_lists:
            if lead_list.get("name") == lead_list_name:
                lead_list_id = lead_list.get("id")
                logger.info(f"✅ Found existing lead list: {lead_list.get('name')} (ID: {lead_list_id})")
                return lead_list_id
        
        # Create new lead list if none exists
        logger.info(f"📝 Creating new lead list: {lead_list_name}")
        
        try:
            url = f"{self.base_url}/api/v2/lead-lists"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            list_payload = {
                "name": lead_list_name
            }
            
            response = requests.post(url, headers=headers, json=list_payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                lead_list_id = data.get("id")
                logger.info(f"✅ Created new lead list: {lead_list_name} (ID: {lead_list_id})")
                return lead_list_id
            else:
                logger.error(f"❌ Failed to create lead list: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating lead list: {e}")
            return None
    
    def find_or_create_campaign(self, company_type: str, campaign_name: str, template_data: Dict[str, str], 
                               sender_email: str, sender_name: str, lead_list_id: str) -> Optional[str]:
        """
        Find an existing campaign for this company type or create a new one
        Returns campaign ID
        """
        if not self.api_key:
            logger.warning("No Instantly API key provided")
            return None
            
        # Look for existing campaign with this company type
        try:
            url = f"{self.base_url}/api/v2/campaigns"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                campaigns = data.get("items", [])
                
                # Look for existing campaign with this name
                for campaign in campaigns:
                    if campaign.get("name") == campaign_name:
                        campaign_id = campaign.get("id")
                        logger.info(f"✅ Found existing campaign: {campaign.get('name')} (ID: {campaign_id})")
                        return campaign_id
                
                # Create new campaign if none exists
                logger.info(f"📝 Creating new campaign: {campaign_name}")
                
                campaign_payload = {
                    "name": campaign_name,
                    "type": "sequence",
                    "delay": 1,
                    "variants": [
                        {
                            "subject": template_data["subject_line"],
                            "body": template_data["message_template"]
                        }
                    ],
                    "subject": template_data["subject_line"],
                    "body": template_data["message_template"],
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "lead_list_id": lead_list_id,
                    "status": "draft",
                    "campaign_schedule": {
                        "schedules": [
                            {
                                "name": "Default",
                                "timezone": "America/Chicago",
                                "days": {
                                    "monday": True,
                                    "tuesday": True,
                                    "wednesday": True,
                                    "thursday": True,
                                    "friday": True,
                                    "saturday": False,
                                    "sunday": False
                                },
                                "timing": {
                                    "from": "09:00",
                                    "to": "17:00"
                                }
                            }
                        ]
                    }
                }
                
                response = requests.post(url, headers=headers, json=campaign_payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    campaign_id = data.get("id")
                    logger.info(f"✅ Created new campaign: {campaign_name} (ID: {campaign_id})")
                    return campaign_id
                else:
                    logger.error(f"❌ Failed to create campaign: {response.status_code} - {response.text}")
                    return None
            else:
                logger.error(f"❌ Failed to get campaigns: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding/creating campaign: {e}")
            return None
    
    def cleanup_old_lead_lists(self, days_old: int = 7) -> int:
        """
        Clean up lead lists older than specified days
        Returns number of lists deleted
        """
        if not self.api_key:
            logger.warning("No Instantly API key provided")
            return 0
            
        try:
            lead_lists = self.get_lead_lists()
            deleted_count = 0
            
            for lead_list in lead_lists:
                # Check if this is an old lead list (you might want to add timestamp checking)
                # For now, we'll just log the existing lists
                logger.info(f"📋 Lead list: {lead_list.get('name')} (ID: {lead_list.get('id')})")
            
            logger.info(f"📊 Found {len(lead_lists)} total lead lists")
            return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up lead lists: {e}")
            return 0

    # Dashboard Methods
    def get_all_campaigns(self) -> List[Dict[str, Any]]:
        """Get all campaigns for dashboard display using the correct GET /api/v2/campaigns endpoint"""
        try:
            url = f"{self.base_url}/api/v2/campaigns"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract campaigns from the 'items' field as per API documentation
                if isinstance(data, dict) and 'items' in data:
                    campaigns = data['items']
                    logger.info(f"✅ Successfully retrieved {len(campaigns)} campaigns from /api/v2/campaigns")
                else:
                    logger.error(f"Unexpected response structure: {type(data)}")
                    return []
                
                # Ensure campaigns is a list
                if not isinstance(campaigns, list):
                    logger.error(f"Expected list of campaigns, got: {type(campaigns)}")
                    return []
                
                # Get analytics for each campaign
                for campaign in campaigns:
                    if isinstance(campaign, dict):
                        campaign_id = campaign.get('id')
                        if campaign_id:
                            analytics = self.get_campaign_analytics(campaign_id)
                            if analytics:
                                campaign.update(analytics)
                
                return campaigns
            else:
                logger.error(f"Failed to get campaigns: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            return []

    def get_campaign_analytics(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed analytics for a specific campaign using the correct GET /api/v2/campaigns/analytics endpoint"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/analytics"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "id": campaign_id,
                "exclude_total_leads_count": "false"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                analytics = response.json()
                # The API returns an array of campaign analytics
                if analytics and len(analytics) > 0:
                    logger.info(f"✅ Successfully retrieved analytics for campaign {campaign_id}")
                    return analytics[0]  # Return first (and only) campaign analytics
                else:
                    logger.warning(f"No analytics found for campaign {campaign_id}")
                    return None
            else:
                logger.error(f"Failed to get campaign analytics {campaign_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting campaign analytics {campaign_id}: {e}")
            return None

    def get_campaign_analytics_overview(self) -> Dict[str, Any]:
        """Get overview analytics for all campaigns"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/analytics/overview"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to get campaign analytics overview: {response.status_code}")
                return {}
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting campaign analytics overview: {e}")
            return {}

    def get_daily_campaign_analytics(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get daily analytics for campaigns"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/analytics/daily"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to get daily campaign analytics: {response.status_code}")
                return []
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting daily campaign analytics: {e}")
            return []

    def get_campaign_steps_analytics(self, campaign_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get step-by-step analytics for a campaign"""
        try:
            url = f"{self.base_url}/api/v2/campaigns/analytics/steps"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {"campaign_id": campaign_id}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to get campaign steps analytics {campaign_id}: {response.status_code}")
                return []
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting campaign steps analytics {campaign_id}: {e}")
            return []

    def move_leads_to_campaign(self, lead_ids: List[str], campaign_id: str) -> bool:
        """Move leads into a specific campaign"""
        try:
            url = f"{self.base_url}/api/v2/leads/move"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "lead_ids": lead_ids,
                "campaign_id": campaign_id
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to move leads to campaign {campaign_id}: {response.status_code}")
                return False
                
            logger.info(f"✅ Moved {len(lead_ids)} leads to campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving leads to campaign {campaign_id}: {e}")
            return False

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get specific lead details"""
        try:
            url = f"{self.base_url}/api/v2/leads/{lead_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to get lead {lead_id}: {response.status_code}")
                return None
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting lead {lead_id}: {e}")
            return None

    def export_lead(self, lead_id: str) -> bool:
        """Export a lead"""
        try:
            url = f"{self.base_url}/api/v2/leads/{lead_id}/export"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to export lead {lead_id}: {response.status_code}")
                return False
                
            logger.info(f"✅ Exported lead {lead_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting lead {lead_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get Instantly.ai statistics for dashboard using proper analytics endpoints"""
        try:
            # Get overview analytics
            overview = self.get_campaign_analytics_overview()
            
            # Get campaigns with analytics
            campaigns = self.get_all_campaigns()
            leads = self.get_all_leads()
            
            # Calculate stats from analytics data
            total_campaigns = len(campaigns)
            total_leads = len(leads)
            active_campaigns = len([c for c in campaigns if c.get('campaign_status') == 1])  # 1 = Active
            
            # Calculate metrics from analytics
            total_sent = sum([c.get('sent_count', 0) for c in campaigns])
            total_opened = sum([c.get('opened_count', 0) for c in campaigns])
            total_replied = sum([c.get('replied_count', 0) for c in campaigns])
            total_clicked = sum([c.get('clicked_count', 0) for c in campaigns])
            
            # Calculate rates
            avg_open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
            avg_reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
            avg_click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
            
            return {
                "total_campaigns": total_campaigns,
                "total_leads": total_leads,
                "active_campaigns": active_campaigns,
                "avg_open_rate": avg_open_rate,
                "avg_reply_rate": avg_reply_rate,
                "avg_click_rate": avg_click_rate,
                "total_sent": total_sent,
                "total_opened": total_opened,
                "total_replied": total_replied,
                "total_clicked": total_clicked,
                "overview": overview
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_campaigns": 0,
                "total_leads": 0,
                "active_campaigns": 0,
                "avg_open_rate": 0,
                "avg_reply_rate": 0,
                "avg_click_rate": 0,
                "total_sent": 0,
                "total_opened": 0,
                "total_replied": 0,
                "total_clicked": 0,
                "overview": {}
            }

    def get_warmup_analytics(self, emails: List[str]) -> Dict[str, Any]:
        """Get warmup analytics for specific email accounts using POST /api/v2/accounts/warmup-analytics"""
        try:
            url = f"{self.base_url}/api/v2/accounts/warmup-analytics"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "emails": emails
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully retrieved warmup analytics for {len(emails)} emails")
                return data
            else:
                logger.error(f"Failed to get warmup analytics: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting warmup analytics: {e}")
            return {}

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Get all email accounts using GET /api/v2/accounts"""
        try:
            url = f"{self.base_url}/api/v2/accounts"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "limit": 100  # Get up to 100 accounts
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract accounts from the 'items' field as per API documentation
                if isinstance(data, dict) and 'items' in data:
                    accounts = data['items']
                    logger.info(f"✅ Successfully retrieved {len(accounts)} accounts from /api/v2/accounts")
                else:
                    logger.error(f"Unexpected response structure: {type(data)}")
                    return []
                
                return accounts
            else:
                logger.error(f"Failed to get accounts: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []

    def test_account_vitals(self, accounts: List[str]) -> Dict[str, Any]:
        """Test account vitals using POST /api/v2/accounts/test/vitals"""
        try:
            url = f"{self.base_url}/api/v2/accounts/test/vitals"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "accounts": accounts
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully tested vitals for {len(accounts)} accounts")
                return data
            else:
                logger.error(f"Failed to test account vitals: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error testing account vitals: {e}")
            return {}

    def verify_email(self, email: str, webhook_url: str = None) -> Dict[str, Any]:
        """Verify an email address using POST /api/v2/email-verification"""
        try:
            url = f"{self.base_url}/api/v2/email-verification"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "email": email
            }
            
            # Add webhook URL if provided
            if webhook_url:
                payload["webhook_url"] = webhook_url
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully initiated email verification for {email}")
                return data
            else:
                logger.error(f"Failed to verify email {email}: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error verifying email {email}: {e}")
            return {}

    def check_email_verification_status(self, email: str) -> Dict[str, Any]:
        """Check email verification status using GET /api/v2/email-verification/{email}"""
        try:
            url = f"{self.base_url}/api/v2/email-verification/{email}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully checked verification status for {email}")
                return data
            else:
                logger.error(f"Failed to check verification status for {email}: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error checking verification status for {email}: {e}")
            return {}

    def verify_multiple_emails(self, emails: List[str], webhook_url: str = None) -> List[Dict[str, Any]]:
        """Verify multiple email addresses"""
        results = []
        for email in emails:
            result = self.verify_email(email, webhook_url)
            results.append({
                "email": email,
                "verification": result
            })
            # Add small delay between requests to avoid rate limiting
            time.sleep(0.5)
        return results