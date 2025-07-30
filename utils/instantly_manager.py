import os
import logging
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class InstantlyManager:
    def __init__(self):
        self.api_key = os.getenv("INSTANTLY_API_KEY", "")
        self.base_url = "https://api.instantly.ai/api/v1"
        
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
        
    def create_campaign(self, name: str, subject_line: str, message_template: str, 
                       sender_email: str = None, sender_name: str = None) -> Optional[str]:
        """
        Create a new campaign in Instantly (without sending)
        Returns campaign ID if successful
        """
        if not self.api_key:
            logger.warning("No Instantly API key provided")
            return None
            
        try:
            url = f"{self.base_url}/campaigns"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "name": name,
                "subject_line": subject_line,
                "message_template": message_template,
                "sender_email": sender_email,
                "sender_name": sender_name,
                "status": "draft"  # Keep as draft - don't send yet
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 201:
                data = response.json()
                campaign_id = data.get("id")
                logger.info(f"✅ Created Instantly campaign: {name} (ID: {campaign_id})")
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
            url = f"{self.base_url}/campaigns/{campaign_id}/leads"
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
            url = f"{self.base_url}/campaigns/{campaign_id}"
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
                              contact_title: str = "", tone: str = "professional") -> Dict[str, str]:
        """
        Generate targeted, concise email template for outreach
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
        
        # Concise, targeted message with personalization
        message_template = f"""{greeting}

I noticed you're hiring for a {job_title} role at {company}. 

I have a network of qualified candidates who would be perfect for this position. Would you be open to a quick call to discuss your hiring needs?

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
        
        # Generate campaign name if not provided
        if not campaign_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            campaign_name = f"Recruiting_Campaign_{timestamp}"
        
        # Generate email template from first lead
        first_lead = leads[0]
        template_data = self.generate_email_template(
            job_title=first_lead.get("job_title", ""),
            company=first_lead.get("company", ""),
            contact_name=first_lead.get("name", ""),
            contact_title=first_lead.get("title", "")
        )
        
        # Get rotating sender email
        sender_email = self.get_next_sender_email()
        sender_name = self.get_sender_name_from_email(sender_email)
        
        # Create campaign
        campaign_id = self.create_campaign(
            name=campaign_name,
            subject_line=template_data["subject_line"],
            message_template=template_data["message_template"],
            sender_email=sender_email,
            sender_name=sender_name
        )
        
        if campaign_id:
            # Add leads to campaign
            success = self.add_leads_to_campaign(campaign_id, leads)
            if success:
                logger.info(f"✅ Created recruiting campaign '{campaign_name}' with {len(leads)} leads")
                return campaign_id
        
        return None 