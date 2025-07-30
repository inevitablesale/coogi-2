import os
import logging
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ContactFinder:
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.hunter_api_key = os.getenv("HUNTER_API_KEY", "")
        
    def find_contacts(self, company: str = "", role_hint: str = "", keywords: List[str] = None, 
                     company_website: Optional[str] = None) -> Tuple[List[Dict], bool, List[str], bool]:
        """
        Find contacts for a company using RapidAPI
        Returns: (contacts, has_ta_team, employee_roles, company_found)
        """
        logger.info(f"🔍 Finding contacts for: {company}")
        
        if not company:
            logger.warning("No company name provided")
            return [], False, [], False
        
        try:
            # Call RapidAPI to get company profile
            profile_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/profile"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
            }
            
            # Try to find LinkedIn company name using OpenAI if needed
            linkedin_company_name = company
            if not company.startswith("linkedin.com/company/"):
                try:
                    import openai
                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a LinkedIn company name resolver. Given a company name, return the exact LinkedIn company identifier. Return only the identifier, nothing else. Examples: 'Microsoft' -> 'microsoft', 'Apple Inc' -> 'apple', 'Google' -> 'google'"},
                            {"role": "user", "content": f"Find LinkedIn company identifier for: {company}"}
                        ],
                        temperature=0.1
                    )
                    linkedin_company_name = response.choices[0].message.content.strip()
                    logger.info(f"OpenAI resolved {company} to LinkedIn name: {linkedin_company_name}")
                except Exception as e:
                    logger.warning(f"OpenAI resolution failed for {company}: {e}")
            
            # Get company profile
            profile_response = requests.get(
                profile_url,
                params={"company": linkedin_company_name},
                headers=headers,
                timeout=15
            )
            
            if profile_response.status_code != 200:
                logger.warning(f"Company profile not found for {company}: {profile_response.status_code}")
                return [], False, [], False
            
            profile_data = profile_response.json()
            if not profile_data.get("success", False):
                logger.warning(f"Company profile API failed for {company}")
                return [], False, [], False
            
            company_profile = profile_data.get("data", {})
            company_found = True
            
            # Check employee count
            employee_count = company_profile.get("employee_count", 0)
            if employee_count and employee_count >= 50:
                logger.info(f"Company {company} has {employee_count} employees - likely has HR/TA team")
                return [], True, [], company_found
            
            # Get company people
            people_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/people"
            people_response = requests.get(
                people_url,
                params={"company": linkedin_company_name, "page": 1},
                headers=headers,
                timeout=15
            )
            
            contacts = []
            has_ta_team = False
            employee_roles = []
            
            if people_response.status_code == 200:
                people_data = people_response.json()
                if people_data.get("success", False):
                    people = people_data.get("data", [])
                    
                    # Check for TA team roles
                    ta_keywords = ["talent acquisition", "recruiter", "hiring", "hr", "human resources"]
                    for person in people:
                        title = person.get("title", "").lower()
                        if any(keyword in title for keyword in ta_keywords):
                            has_ta_team = True
                            employee_roles.append(person.get("title", ""))
                    
                    # If no TA team found, these are good contacts
                    if not has_ta_team:
                        contacts = people[:5]  # Top 5 contacts
                        employee_roles = [person.get("title", "") for person in people[:10]]
                    
                    logger.info(f"Found {len(people)} people at {company}, TA team: {has_ta_team}")
            
            logger.info(f"📊 Found {len(contacts)} contacts, has_ta_team: {has_ta_team}")
            return contacts, has_ta_team, employee_roles, company_found
            
        except Exception as e:
            logger.error(f"Error finding contacts for {company}: {e}")
            return [], False, [], False
        
    def find_hunter_emails_for_target_company(self, company: str, job_title: str = "", employee_roles: List[str] = None, company_website: Optional[str] = None) -> List[str]:
        """
        Find emails for a company using Hunter.io
        """
        logger.info(f"🔍 Finding Hunter.io emails for: {company}")
        
        if not self.hunter_api_key:
            logger.warning("No Hunter.io API key provided")
            return []
        
        try:
            # Use company website if provided, otherwise try to find domain
            domain = company_website
            if not domain:
                # Try to extract domain from company name
                domain = f"{company.lower().replace(' ', '').replace('.', '')}.com"
            
            # Call Hunter.io API
            hunter_url = "https://api.hunter.io/v2/domain-search"
            params = {
                "domain": domain,
                "api_key": self.hunter_api_key,
                "limit": 3
            }
            
            response = requests.get(hunter_url, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Hunter.io API failed for {company}: {response.status_code}")
                return []
            
            data = response.json()
            emails = []
            
            if data.get("data", {}).get("emails"):
                for email_data in data["data"]["emails"]:
                    email = email_data.get("value", "")
                    if email:
                        emails.append(email)
            
            logger.info(f"📧 Found {len(emails)} Hunter.io emails for {company}")
            return emails
            
        except Exception as e:
            logger.error(f"Error finding Hunter.io emails for {company}: {e}")
            return []
        
    def find_email(self, contact_title: str, company: str) -> Optional[str]:
        """Find email for a specific contact"""
        logger.info(f"🔍 Finding email for {contact_title} at {company}")
        
        # Mock implementation - in real implementation this would call Hunter.io
        # For now, return a sample email
        sample_email = f"{contact_title.lower().replace(' ', '.')}@{company.lower().replace(' ', '')}.com"
        return sample_email
        
    def calculate_lead_score(self, contact: Dict[str, Any], job: Dict[str, Any], has_ta_team: bool) -> float:
        """Calculate a score for how good a lead is"""
        logger.info(f"📊 Calculating lead score for {contact.get('name', 'Unknown')}")
        
        # Mock implementation - in real implementation this would use ML
        # For now, return a random score between 0.5 and 1.0
        import random
        score = random.uniform(0.5, 1.0)
        return round(score, 2) 