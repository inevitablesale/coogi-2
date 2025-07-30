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
        # Use real APIs until Hunter.io - only demo mode for email discovery
        self.demo_mode = False
        self.email_demo_mode = not bool(self.hunter_api_key)
        
        # Demo contacts for testing
        self.demo_contacts = {
            "TechCorp Inc": [
                {"full_name": "John Smith", "title": "VP of Engineering", "url": "https://linkedin.com/in/johnsmith"},
                {"full_name": "Lisa Chen", "title": "Head of Talent Acquisition", "url": "https://linkedin.com/in/lisachen"}
            ],
            "StartupXYZ": [
                {"full_name": "Sarah Johnson", "title": "Head of People", "url": "https://linkedin.com/in/sarahjohnson"},
                {"full_name": "Mike Rodriguez", "title": "CTO", "url": "https://linkedin.com/in/mikerodriguez"}
            ],
            "Enterprise Solutions": [
                {"full_name": "Mike Davis", "title": "Chief Technology Officer", "url": "https://linkedin.com/in/mikedavis"},
                {"full_name": "Jennifer Brown", "title": "Director of Recruiting", "url": "https://linkedin.com/in/jenniferbrown"}
            ],
            "GrowthCo": [
                {"full_name": "Alex Wilson", "title": "VP of Marketing", "url": "https://linkedin.com/in/alexwilson"},
                {"full_name": "Emma Thompson", "title": "People Operations Manager", "url": "https://linkedin.com/in/emmathompson"}
            ],
            "CloudTech": [
                {"full_name": "David Kim", "title": "Engineering Manager", "url": "https://linkedin.com/in/davidkim"},
                {"full_name": "Rachel Green", "title": "Head of Talent", "url": "https://linkedin.com/in/rachelgreen"}
            ]
        }
        
        self.demo_emails = {
            "john.smith": "john.smith@techcorp.com",
            "lisa.chen": "lisa.chen@techcorp.com",
            "sarah.johnson": "sarah.johnson@startupxyz.com",
            "mike.rodriguez": "mike.rodriguez@startupxyz.com",
            "mike.davis": "mike.davis@enterprisesolutions.com",
            "jennifer.brown": "jennifer.brown@enterprisesolutions.com",
            "alex.wilson": "alex.wilson@growthco.com",
            "emma.thompson": "emma.thompson@growthco.com",
            "david.kim": "david.kim@cloudtech.com",
            "rachel.green": "rachel.green@cloudtech.com"
        }
        
        # Title ranking for contact prioritization
        self.title_rank = {
            "cto": 5, "chief": 5, "vp": 4, "head": 3, "director": 2, 
            "manager": 1, "senior": 3, "lead": 2, "founder": 5, "ceo": 5
        }
    
    def find_contacts(self, company: str, role_hint: str, keywords: List[str]) -> Tuple[List[Dict[str, Any]], bool]:
        """Find company contacts and determine if they have a talent acquisition team"""
        try:
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
            # Only fall back to demo data if RapidAPI fails
            return self._get_demo_contacts(company, role_hint, keywords)
    
    def _get_demo_contacts(self, company: str, role_hint: str, keywords: List[str]) -> Tuple[List[Dict[str, Any]], bool]:
        """Get demo contacts for testing"""
        contacts = self.demo_contacts.get(company, [])
        
        # Rank contacts based on relevance
        ranked_contacts = []
        for contact in contacts:
            score = self._calculate_contact_score(contact, role_hint, keywords)
            ranked_contacts.append((score, contact))
        
        # Sort by score and return top contacts
        ranked_contacts.sort(reverse=True, key=lambda x: x[0])
        final_contacts = [contact for _, contact in ranked_contacts]
        
        # Check if has talent acquisition team
        has_ta_team = any("talent" in contact["title"].lower() or "recruiting" in contact["title"].lower() 
                         for contact in contacts)
        
        return final_contacts, has_ta_team
    
    def _get_contacts_from_rapidapi(self, company: str, role_hint: str, keywords: List[str]) -> Tuple[List[Dict[str, Any]], bool]:
        """Get company contacts from RapidAPI SaleLeads LinkedIn scraper"""
        try:
            logger.info(f"Attempting RapidAPI contact discovery for company: {company}")
            people_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/people"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
            }
            
            # Get company people directly by company name
            logger.info(f"Calling SaleLeads API people endpoint for: {company}")
            people_resp = requests.get(people_url, params={"company": company, "page": 1}, headers=headers, timeout=15)
            logger.info(f"SaleLeads API response: {people_resp.status_code}")
            
            if people_resp.status_code != 200:
                logger.warning(f"SaleLeads API failed with status {people_resp.status_code}: {people_resp.text[:200]}")
                logger.info(f"SaleLeads API unavailable, using demo contacts for {company}")
                return self._get_demo_contacts(company, role_hint, keywords)
                
            people_data = people_resp.json()
            
            # Check if the API call was successful
            if not people_data.get("success", False):
                logger.warning(f"SaleLeads API returned unsuccessful response for {company}")
                return self._get_demo_contacts(company, role_hint, keywords)
            
            people = people_data.get("data", [])
            logger.info(f"Found {len(people)} people from SaleLeads API for {company}")

            # Check for talent acquisition team FIRST (volume optimization)
            has_ta_team = self._has_talent_acquisition_team(people)
            
            # PRIORITY CONTACT IDENTIFICATION for companies WITHOUT TA teams
            role_hint_safe = (role_hint or "").lower()
            keywords_safe = [k.lower() for k in keywords if k] if keywords else []
            
            # High-value contacts for recruiter outreach (decision makers, not HR)
            target_roles = ["cto", "ceo", "founder", "vp", "director", "head", "lead", "manager", "principal", "senior"]
            hiring_roles = ["engineering", "tech", "product", "development"] + keywords_safe + [role_hint_safe]
            
            ranked = []
            
            for p in people:
                title = (p.get("title") or "").lower()
                
                # Calculate decision-maker score
                score = 0
                
                # High priority: C-level and VPs (decision makers)
                if any(role in title for role in ["cto", "ceo", "founder", "chief"]):
                    score += 10
                elif any(role in title for role in ["vp", "vice president"]):
                    score += 8
                elif any(role in title for role in ["director", "head"]):
                    score += 6
                elif any(role in title for role in ["manager", "lead", "principal"]):
                    score += 4
                elif any(role in title for role in ["senior", "sr"]):
                    score += 2
                
                # Bonus for technical roles (likely to understand hiring needs)
                if any(tech in title for tech in hiring_roles):
                    score += 3
                
                # Include high-scoring contacts (decision makers and technical leaders)
                if score >= 2:  # Only quality contacts
                    ranked.append((score, {
                        "full_name": "Contact",  # Generic name for privacy
                        "title": p.get("title") or "Unknown Title",
                        "url": "",  # Remove LinkedIn URLs for privacy
                        "decision_score": score
                    }))
            
            # Sort by decision-maker score - prioritize highest-value contacts
            ranked_sorted = sorted(ranked, key=lambda x: x[0], reverse=True)[:5]  # Top 5 decision makers
            contacts = [p for _, p in ranked_sorted]
            
            # Log role summary for Hunter.io searches later
            all_titles = [p.get("title") for p in people if p.get("title")]
            unique_titles = list(set(all_titles))[:15] if all_titles else ["No titles found"]
            
            if contacts:
                top_contact_titles = [c["title"] for c in contacts]
                logger.info(f"🎯 TOP TARGETS for {company}: {top_contact_titles}")
                logger.info(f"📧 Hunter search roles: {unique_titles}")
            else:
                logger.info(f"⚠️  No decision makers found at {company}")
            
            logger.info(f"SaleLeads API found {len(contacts)} high-value contacts for {company}")
            return contacts, has_ta_team
            
        except Exception as e:
            logger.error(f"SaleLeads API error for {company}: {e}")
            logger.info(f"Falling back to demo data for {company}")
            return self._get_demo_contacts(company, role_hint, keywords)
    
    def _calculate_contact_score(self, contact: Dict[str, Any], role_hint: str, keywords: List[str]) -> float:
        """Calculate relevance score for a contact"""
        title = contact.get("title", "").lower()
        score = 0
        
        # Base score from title rank
        for word in title.split():
            if word in self.title_rank:
                score += self.title_rank[word]
        
        # Bonus for role hint match
        if role_hint.lower() in title:
            score += 3
        
        # Bonus for keyword matches
        for keyword in keywords:
            if keyword.lower() in title:
                score += 1
        
        return score
    
    def _has_talent_acquisition_team(self, people: List[dict]) -> bool:
        """Check if company has a talent acquisition team - critical for recruiter contract decisions"""
        ta_keywords = ["talent", "recruiter", "recruiting", "people ops", "hr", "human resources", "people partner", "talent acquisition", "talent partner", "people operations"]
        
        ta_roles_found = []
        for person in people:
            title = (person.get("title") or "").lower()
            for keyword in ta_keywords:
                if keyword in title:
                    ta_roles_found.append(title)
        
        # Log the talent acquisition roles found for recruiter decision-making
        if ta_roles_found:
            unique_roles = list(set(ta_roles_found))[:5]  # Remove duplicates, show top 5
            logger.info(f"❌ SKIP: Internal TA team detected - {unique_roles}")
            return True
        else:
            logger.info(f"✅ TARGET: No TA team - direct hiring opportunity")
            return False
    
    def find_email(self, title: str, company: str) -> Optional[str]:
        """Find email address using Hunter.io API or demo data"""
        if self.email_demo_mode:
            return self._get_demo_email(title, company)
        
        try:
            return self._find_email_with_hunter(title, company)
        except Exception as e:
            logger.error(f"Error finding email for {title} at {company}: {e}")
            return self._get_demo_email(title, company)
    
    def _get_demo_email(self, title: str, company: str) -> Optional[str]:
        """Get demo email based on title and company"""
        # Create a simple mapping based on name/title
        name_key = title.lower().replace(" ", ".").split("@")[0]
        
        # Try to find matching demo email
        for key, email in self.demo_emails.items():
            if key in name_key or any(word in key for word in name_key.split(".")):
                return email
        
        # Generate a plausible email if no match found
        domain = company.lower().replace(" ", "").replace("inc", "").replace("corp", "")
        if "startup" in domain:
            domain = "startupxyz"
        elif "enterprise" in domain:
            domain = "enterprisesolutions"
        elif "growth" in domain:
            domain = "growthco"
        elif "cloud" in domain:
            domain = "cloudtech"
        elif "tech" in domain:
            domain = "techcorp"
        
        name_part = name_key.split(".")[0] if "." in name_key else name_key[:8]
        return f"{name_part}@{domain}.com"
    
    def _find_email_with_hunter(self, title: str, company: str) -> Optional[str]:
        """Find email address using Hunter.io API"""
        try:
            # Extract domain from company name (simplified)
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
        title = contact.get("title", "").lower()
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
