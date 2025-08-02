import os
import logging
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
import time # Added for retry mechanism

logger = logging.getLogger(__name__)

class ContactFinder:
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.hunter_api_key = os.getenv("HUNTER_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
    def check_ta_team_with_openai(self, company: str) -> Optional[bool]:
        """Check if company has TA team using OpenAI's knowledge base first"""
        try:
            import openai
            # Initialize OpenAI client with API key
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a company HR structure analyzer. Given a company name, determine if they likely have a DEDICATED internal talent acquisition/recruiting team (not just general HR). Return ONLY 'yes', 'no', or 'unknown'. Only large companies (>500 employees) typically have dedicated TA teams. Small companies (<100 employees) typically don't have dedicated TA teams - they may have general HR but not dedicated recruiters."},
                    {"role": "user", "content": f"Does {company} likely have a DEDICATED internal talent acquisition/recruiting team (not just general HR)? Consider company size and industry."}
                ],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip().lower()
            
            if result == 'yes':
                logger.info(f"🤖 OpenAI thinks {company} has TA team")
                return True
            elif result == 'no':
                logger.info(f"🤖 OpenAI thinks {company} doesn't have TA team")
                return False
            else:
                logger.info(f"🤔 OpenAI doesn't know if {company} has TA team")
                return None
                
        except Exception as e:
            logger.error(f"Error checking TA team with OpenAI for {company}: {e}")
            return None
    
    def find_contacts(self, company: str = "", linkedin_identifier: str = "", role_hint: str = "", keywords: List[str] = None, 
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
            # Step 1: LinkedIn company name resolution
            logger.info(f"🔗 Step 1: Resolving LinkedIn company name for {company}")
            
            # Call RapidAPI to get company profile
            profile_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/profile"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
            }
            
            # Use provided LinkedIn identifier or fall back to company name
            linkedin_company_name = linkedin_identifier if linkedin_identifier else company
            if not linkedin_identifier and not company.startswith("linkedin.com/company/"):
                try:
                    import openai
                    # Initialize OpenAI client with API key
                    client = openai.OpenAI(api_key=self.openai_api_key)
                    
                    logger.info(f"🤖 Using OpenAI to resolve LinkedIn name for {company}")
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a LinkedIn company name resolver. Given a company name, return the exact LinkedIn company identifier. Return only the identifier, nothing else. Examples: 'Microsoft' -> 'microsoft', 'Apple Inc' -> 'apple', 'Google' -> 'google'"},
                            {"role": "user", "content": f"Find LinkedIn company identifier for: {company}"}
                        ],
                        temperature=0.1
                    )
                    linkedin_company_name = response.choices[0].message.content.strip()
                    logger.info(f"✅ OpenAI resolved {company} to LinkedIn name: {linkedin_company_name}")
                except Exception as e:
                    logger.warning(f"❌ OpenAI resolution failed for {company}: {e}")
            
            # Step 2: RapidAPI company profile call
            logger.info(f"📡 Step 2: Calling RapidAPI for company profile: {linkedin_company_name}")
            
            # Get company profile
            profile_response = requests.get(
                profile_url,
                params={"company": linkedin_company_name},
                headers=headers,
                timeout=15
            )
            
            logger.info(f"📡 RapidAPI response status: {profile_response.status_code}")
            
            if profile_response.status_code != 200:
                logger.warning(f"❌ Company profile not found for {company}: {profile_response.status_code}")
                logger.warning(f"❌ RapidAPI error response: {profile_response.text}")
                return [], False, [], False
            
            try:
                profile_data = profile_response.json()
                logger.info(f"📡 RapidAPI response data: {profile_data}")
            except Exception as e:
                logger.error(f"❌ Failed to parse RapidAPI response for {company}: {e}")
                logger.error(f"❌ Raw response: {profile_response.text}")
                return [], False, [], False
            
            if not profile_data.get("success", False):
                logger.warning(f"❌ RapidAPI returned error for {company}: {profile_data}")
                return [], False, [], False
            
            logger.info(f"✅ Step 2 Complete: RapidAPI profile found for {company}")
            
            # Step 3: Extract company information
            logger.info(f"📊 Step 3: Extracting company information for {company}")
            
            company_info = profile_data.get("data", {})
            logger.info(f"📊 Company info structure: {company_info}")
            company_found = bool(company_info)
            
            if not company_found:
                logger.warning(f"❌ No company data found for {company}")
                return [], False, [], False
            
            # Extract employee count and other info
            employee_count = company_info.get("employee_count", 0)
            industry = company_info.get("industry", "")
            description = company_info.get("description", "")
            
            logger.info(f"📊 Company info - Employees: {employee_count}, Industry: {industry}")
            
            # Step 4: Check for TA team using OpenAI
            logger.info(f"🤖 Step 4: Checking for TA team using OpenAI for {company}")
            
            has_ta_team = self.check_ta_team_with_openai(company)
            
            if has_ta_team is True:
                logger.info(f"✅ {company} has TA team (OpenAI)")
            elif has_ta_team is False:
                logger.info(f"❌ {company} does not have TA team (OpenAI)")
            else:
                logger.info(f"❓ {company} TA team status unknown (OpenAI)")
            
            # Step 5: Extract employee roles
            logger.info(f"👥 Step 5: Extracting employee roles for {company}")
            
            employee_roles = []
            if company_info.get("employees"):
                for employee in company_info["employees"][:10]:  # Limit to first 10 employees
                    title = employee.get("title", "")
                    if title:
                        employee_roles.append(title)
            
            logger.info(f"👥 Found {len(employee_roles)} employee roles for {company}")
            
            # Step 6: Create contact list
            logger.info(f"📋 Step 6: Creating contact list for {company}")
            
            contacts = []
            if company_info.get("employees"):
                for employee in company_info["employees"][:5]:  # Limit to first 5 employees
                    contact = {
                        "name": employee.get("name", ""),
                        "title": employee.get("title", ""),
                        "company": company,
                        "linkedin_url": employee.get("profile_url", ""),
                        "location": employee.get("location", ""),
                        "score": 0.5  # Default score
                    }
                    contacts.append(contact)
            
            logger.info(f"✅ Step 6 Complete: Created {len(contacts)} contacts for {company}")
            
            # Extract LinkedIn URL from company info
            linkedin_url = company_info.get("linkedin_url", "")
            if linkedin_url:
                logger.info(f"🔗 Found LinkedIn URL: {linkedin_url}")
            
            return contacts, has_ta_team, employee_roles, company_found
            
        except Exception as e:
            logger.error(f"❌ Error finding contacts for {company}: {e}")
            return [], False, [], False
        
    def find_hunter_emails_for_target_company(self, company: str, job_title: str = "", employee_roles: List[str] = None, company_website: Optional[str] = None) -> List[Dict[str, str]]:
        """Find emails for a target company using Hunter.io"""
        logger.info(f"🎯 Starting Hunter.io email discovery for {company}")
        
        if not self.hunter_api_key:
            logger.warning("❌ No Hunter.io API key configured")
            return []
        
        try:
            # Step 1: Find company domain
            logger.info(f"🌐 Step 1: Finding domain for {company}")
            
            domain = None
            if company_website:
                domain = self._extract_domain_from_url(company_website)
                logger.info(f"✅ Found domain from website: {domain}")
            else:
                domain = self._find_company_domain(company)
                if domain:
                    logger.info(f"✅ Found domain via search: {domain}")
                else:
                    logger.warning(f"❌ No domain found for {company}")
                    return []
            
            # Step 2: Search for emails on the domain
            logger.info(f"📧 Step 2: Searching for emails on {domain}")
            
            search_url = "https://api.hunter.io/v2/domain-search"
            params = {
                "domain": domain,
                "company": company,
                "type": "personal",  # Only get personal emails, filter out generic ones
                "limit": 3,  # Limit to 3 emails maximum
                "api_key": self.hunter_api_key
            }
            
            response = requests.get(search_url, params=params, timeout=15)
            logger.info(f"📧 Hunter.io response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Hunter.io API error: {response.status_code}")
                return []
            
            data = response.json()
            logger.info(f"📧 Hunter.io raw response: {data}")
            emails = data.get("data", {}).get("emails", [])
            
            logger.info(f"📧 Found {len(emails)} personal emails from Hunter.io")
            
            # Step 3: Process emails (no need to filter generics since type=personal)
            logger.info(f"🎯 Step 3: Processing personal emails for {company}")
            
            filtered_emails = []
            for i, email in enumerate(emails):
                logger.info(f"📧 Processing email object {i}: {email}")
                # Hunter.io uses "value" field for the email address
                email_data = email.get("value", "") or email.get("email", "") or email.get("address", "")
                confidence = email.get("confidence", 0)
                sources = email.get("sources", [])
                
                # Get name, title, and LinkedIn URL from Hunter.io
                first_name = email.get("first_name", "")
                last_name = email.get("last_name", "")
                position = email.get("position", "")
                linkedin_url = email.get("linkedin", "")
                
                logger.info(f"📧 Email {i}: {email_data}, Confidence: {confidence}, Sources: {len(sources)}")
                logger.info(f"📧 Person details: {first_name} {last_name}, Position: {position}, LinkedIn: {linkedin_url}")
                
                # Filter for high-confidence emails (no need to filter generics since type=personal)
                if confidence > 50 and email_data:
                    # Create full name - try to extract from email if Hunter.io doesn't provide it
                    full_name = f"{first_name} {last_name}".strip()
                    if not full_name or full_name == "None None" or full_name == "":
                        # Try to extract name from email address
                        email_lower = email_data.lower()
                        username = email_lower.split('@')[0] if '@' in email_lower else ""
                        
                        if '.' in username and len(username) > 3:
                            # Common pattern: firstname.lastname@domain.com
                            name_parts = username.replace('_', ' ').replace('.', ' ').replace('-', ' ')
                            name_parts = [part.capitalize() for part in name_parts.split() if len(part) > 1]
                            if name_parts:
                                full_name = ' '.join(name_parts)
                                first_name = name_parts[0] if len(name_parts) > 0 else ""
                                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ""
                        else:
                            full_name = "Hiring Manager"  # Fallback if no name provided
                    
                    email_info = {
                        "email": email_data,
                        "name": full_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "title": position if position else "Hiring Manager",
                        "confidence": confidence,
                        "company": company  # Add company information
                    }
                    
                    # Add LinkedIn URL if available
                    if linkedin_url:
                        email_info["linkedin_url"] = linkedin_url
                        logger.info(f"✅ Added LinkedIn URL: {linkedin_url}")
                    
                    filtered_emails.append(email_info)
                    logger.info(f"✅ Added personal email: {email_data} (name: {full_name}, title: {position}, LinkedIn: {linkedin_url})")
                else:
                    logger.info(f"❌ Skipped email: {email_data} (confidence: {confidence})")
            
            logger.info(f"✅ Step 3 Complete: Processed {len(filtered_emails)} personal emails")
            
            return filtered_emails
            
        except Exception as e:
            logger.error(f"❌ Hunter.io error for {company}: {e}")
            return []
    
    def _filter_real_person_emails(self, emails: List[str]) -> List[str]:
        """
        Filter out generic/bullshit emails and keep only real person emails
        """
        # List of generic email prefixes to filter out
        generic_prefixes = [
            "info", "hello", "contact", "support", "help", "admin", "webmaster", 
            "postmaster", "abuse", "security", "noreply", "no-reply", "donotreply",
            "mail", "email", "sales", "marketing", "press", "media", "pr", "hr",
            "jobs", "careers", "recruiting", "talent", "hiring", "apply", "applications",
            "feedback", "suggestions", "complaints", "billing", "accounts", "finance",
            "legal", "compliance", "privacy", "terms", "service", "customer", "client",
            "general", "main", "office", "reception", "frontdesk", "receptionist",
            "team", "group", "department", "division", "unit", "section", "branch",
            "subsidiary", "corporate", "headquarters", "main", "primary", "secondary",
            "backup", "emergency", "urgent", "immediate", "priority", "vip", "executive",
            "management", "leadership", "board", "directors", "officers", "partners"
        ]
        
        real_emails = []
        for email in emails:
            email_lower = email.lower()
            username = email_lower.split('@')[0] if '@' in email_lower else ""
            
            # Skip if it's a generic email
            if any(prefix in username for prefix in generic_prefixes):
                logger.info(f"🚫 Filtered out generic email: {email}")
                continue
            
            # Skip if it's too short (likely fake)
            if len(username) < 3:
                logger.info(f"🚫 Filtered out short email: {email}")
                continue
            
            # Skip if it contains numbers only (likely fake)
            if username.isdigit():
                logger.info(f"🚫 Filtered out numeric email: {email}")
                continue
            
            # Skip if it's just initials (likely not useful)
            if len(username) <= 2 and username.isalpha():
                logger.info(f"🚫 Filtered out initials email: {email}")
                continue
            
            # Skip if it contains common fake patterns
            if any(pattern in username for pattern in ["test", "demo", "example", "sample", "fake", "dummy"]):
                logger.info(f"🚫 Filtered out fake pattern email: {email}")
                continue
            
            # Keep real person emails
            logger.info(f"✅ Keeping real person email: {email}")
            real_emails.append(email)
        
        return real_emails
        
    def find_email(self, contact_title: str, company: str) -> Optional[str]:
        """Find email for a specific contact"""
        logger.info(f"🔍 Finding email for {contact_title} at {company}")
        
        # Mock implementation - in real implementation this would call Hunter.io
        # For now, return a sample email
        sample_email = f"{contact_title.lower().replace(' ', '.')}@{company.lower().replace(' ', '')}.com"
        return sample_email
        
    def check_company_size_with_openai(self, company: str) -> Optional[int]:
        """Check company size using OpenAI's knowledge base first"""
        try:
            import openai
            # Initialize OpenAI client with API key
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a company size analyzer. Given a company name, return ONLY the approximate number of employees as a number, or 'unknown' if you don't know. Examples: 'Microsoft' -> '221000', 'Apple' -> '164000', 'Small Startup Inc' -> 'unknown'"},
                    {"role": "user", "content": f"What is the approximate number of employees at {company}? Return only the number or 'unknown'."}
                ],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            
            if result.lower() == 'unknown':
                logger.info(f"🤔 OpenAI doesn't know size of {company}")
                return None
            
            try:
                employee_count = int(result)
                logger.info(f"📊 OpenAI knows {company} has ~{employee_count} employees")
                return employee_count
            except ValueError:
                logger.warning(f"⚠️  OpenAI returned invalid number for {company}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking company size with OpenAI for {company}: {e}")
            return None
    
    def batch_analyze_companies(self, companies: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch analyze multiple companies with OpenAI to estimate size and resolve LinkedIn identifiers"""
        logger.info(f"🔍 Batch analyzing {len(companies)} companies with OpenAI...")
        
        try:
            import openai
            
            # Initialize OpenAI client with API key
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            # Create a single prompt for all companies
            companies_text = "\n".join([f"- {company}" for company in companies])
            
            system_prompt = """You are a company analyzer. For each company, determine:
1. What is the approximate employee count? (number or 'unknown')
2. What is the LinkedIn company identifier? (exact identifier like 'microsoft', 'apple', etc.)

Return a JSON object with company names as keys and objects with 'company_size' (number or null) and 'linkedin_identifier' (string) as values.

Example format:
{
  "Microsoft": {"company_size": 221000, "linkedin_identifier": "microsoft"},
  "Small Startup": {"company_size": 50, "linkedin_identifier": "small-startup"}
}"""
            
            user_prompt = f"Analyze these companies:\n{companies_text}"
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            import json
            analysis_results = json.loads(result)
            
            logger.info(f"✅ Batch analysis complete for {len(companies)} companies")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in batch company analysis: {e}")
            # Fallback to individual analysis
            results = {}
            for company in companies:
                results[company] = {
                    "company_size": self.check_company_size_with_openai(company),
                    "linkedin_identifier": company.lower().replace(" ", "-")
                }
            return results
    
    def search_linkedin_company_page(self, company: str) -> Optional[int]:
        """
        Search for LinkedIn company page and extract employee count using web search
        Returns the employee count if found, None otherwise
        """
        try:
            import openai
            # Initialize OpenAI client with API key
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            # Use OpenAI's web search capability to find LinkedIn company page
            search_query = f"{company} LinkedIn company page employees"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a web search assistant. Search for the LinkedIn company page and extract the employee count. Return ONLY the number of employees as an integer, or 'unknown' if not found. Do not include any other text."},
                    {"role": "user", "content": f"Search for {company}'s LinkedIn company page and find their employee count. Return only the number."}
                ],
                tools=[{"type": "web_search"}],
                tool_choice={"type": "function", "function": {"name": "web_search"}},
                temperature=0.1
            )
            
            # Extract the employee count from the response
            content = response.choices[0].message.content.strip()
            
            # Try to extract a number from the response
            import re
            numbers = re.findall(r'\d+', content)
            if numbers:
                # Take the largest number as it's likely the employee count
                employee_count = max(int(num) for num in numbers)
                logger.info(f"🌐 Web search found {company} has {employee_count} employees")
                return employee_count
            else:
                logger.info(f"🌐 Web search couldn't find employee count for {company}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching LinkedIn page for {company}: {e}")
            return None

    def get_employee_count(self, company: str) -> Optional[int]:
        """Get employee count for a company - try web search first, then OpenAI, then RapidAPI"""
        logger.info(f"🔍 Getting employee count for: {company}")
        
        # Try web search first for most accurate data
        web_count = self.search_linkedin_company_page(company)
        if web_count:
            return web_count
        
        # If web search fails, try OpenAI for quick check
        logger.info(f"🌐 Web search failed for {company}, trying OpenAI...")
        openai_count = self.check_company_size_with_openai(company)
        if openai_count:
            return openai_count
        
        # If OpenAI doesn't know, fall back to RapidAPI
        logger.info(f"🔍 OpenAI doesn't know {company} size, checking RapidAPI...")
        try:
            # Use the same LinkedIn resolution logic as find_contacts
            linkedin_company_name = company
            if not company.startswith("linkedin.com/company/"):
                try:
                    import openai
                    # Initialize OpenAI client with API key
                    client = openai.OpenAI(api_key=self.openai_api_key)
                    
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a LinkedIn company name resolver. Given a company name, return the exact LinkedIn company identifier. Return only the identifier, nothing else. Examples: 'Microsoft' -> 'microsoft', 'Apple Inc' -> 'apple', 'Google' -> 'google'"},
                            {"role": "user", "content": f"Find LinkedIn company identifier for: {company}"}
                        ],
                        temperature=0.1
                    )
                    linkedin_company_name = response.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"OpenAI resolution failed for {company}: {e}")
            
            # Get company profile
            profile_url = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/company/profile"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "fresh-linkedin-scraper-api.p.rapidapi.com"
            }
            
            profile_response = requests.get(
                profile_url,
                params={"company": linkedin_company_name},
                headers=headers,
                timeout=15
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                if profile_data.get("success", False):
                    company_profile = profile_data.get("data", {})
                    employee_count = company_profile.get("employee_count")
                    if employee_count:
                        logger.info(f"📊 RapidAPI: {company} has {employee_count} employees")
                        return employee_count
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting employee count for {company}: {e}")
            return None
    
    def calculate_lead_score(self, contact: Dict[str, Any], job: Dict[str, Any], has_ta_team: bool) -> float:
        """Calculate a score for how good a lead is"""
        logger.info(f"📊 Calculating lead score for {contact.get('name', 'Unknown')}")
        
        # Mock implementation - in real implementation this would use ML
        # For now, return a random score between 0.5 and 1.0
        import random
        score = random.uniform(0.5, 1.0)
        return round(score, 2)
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from a URL"""
        try:
            if not url:
                return None
            
            # Remove protocol if present
            if url.startswith(('http://', 'https://')):
                url = url.split('://', 1)[1]
            
            # Remove path and query parameters
            domain = url.split('/')[0]
            
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain if domain else None
        except Exception as e:
            logger.error(f"Error extracting domain from URL {url}: {e}")
            return None
    
    def _find_company_domain(self, company_name: str) -> Optional[str]:
        """Find company website domain using Clearout API"""
        try:
            url = "https://api.clearout.io/public/companies/autocomplete"
            params = {"query": company_name}
            
            logger.info(f"🌐 Making domain finding call for {company_name}")
            response = requests.get(url, params=params, timeout=30)  # Increased timeout to 30 seconds
            
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
                    else:
                        logger.warning(f"⚠️  No domain found for {company_name}")
                        return None
                else:
                    logger.warning(f"⚠️  Clearout API failed for {company_name}: {data.get('message', 'Unknown error')}")
                    return None
            else:
                logger.warning(f"⚠️  Clearout API error for {company_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding domain for {company_name}: {e}")
            return None 