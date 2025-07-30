import hashlib
import json
from datetime import datetime
from typing import Dict, Set, List, Any

class MemoryManager:
    def __init__(self):
        # Initialize memory structures
        self.contacted_emails: Set[str] = set()
        self.job_fingerprints: Set[str] = set()
        self.job_urls: Set[str] = set()
        self.conversions: List[Dict[str, Any]] = []
        self.title_scores: Dict[str, Dict[str, int]] = {}
        self.company_scores: Dict[str, Dict[str, int]] = {}
        self.last_hunt_time: str = ""
    
    def create_job_fingerprint(self, job: Dict[str, Any]) -> str:
        """Create a unique fingerprint for a job posting"""
        key = f"{job.get('title', '')}_{job.get('company', '')}_{job.get('location', '')}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def is_job_processed(self, fingerprint: str) -> bool:
        """Check if a job has already been processed"""
        return fingerprint in self.job_fingerprints
    
    def mark_job_processed(self, fingerprint: str) -> None:
        """Mark a job as processed"""
        self.job_fingerprints.add(fingerprint)
    
    def is_email_contacted(self, email: str) -> bool:
        """Check if an email has already been contacted"""
        return email in self.contacted_emails
    
    def mark_email_contacted(self, email: str) -> None:
        """Mark an email as contacted"""
        self.contacted_emails.add(email)
    
    def is_url_processed(self, url: str) -> bool:
        """Check if a job URL has already been processed"""
        return url in self.job_urls
    
    def mark_url_processed(self, url: str) -> None:
        """Mark a job URL as processed"""
        self.job_urls.add(url)
    
    def record_conversion(self, lead_data: Dict[str, Any]) -> None:
        """Record a successful conversion"""
        conversion = {
            'timestamp': datetime.now().isoformat(),
            'company': lead_data.get('company', ''),
            'title': lead_data.get('title', ''),
            'email': lead_data.get('email', ''),
            'score': lead_data.get('score', 0)
        }
        self.conversions.append(conversion)
    
    def update_title_score(self, title: str, success: bool) -> None:
        """Update success rate for a specific job title"""
        if title not in self.title_scores:
            self.title_scores[title] = {'successes': 0, 'attempts': 0}
        
        self.title_scores[title]['attempts'] += 1
        if success:
            self.title_scores[title]['successes'] += 1
    
    def update_company_score(self, company: str, success: bool) -> None:
        """Update success rate for a specific company"""
        if company not in self.company_scores:
            self.company_scores[company] = {'successes': 0, 'attempts': 0}
        
        self.company_scores[company]['attempts'] += 1
        if success:
            self.company_scores[company]['successes'] += 1
    
    def get_title_success_rate(self, title: str) -> float:
        """Get success rate for a job title"""
        if title not in self.title_scores:
            return 0.5  # Default neutral score
        
        data = self.title_scores[title]
        if data['attempts'] == 0:
            return 0.5
        
        return data['successes'] / data['attempts']
    
    def get_company_success_rate(self, company: str) -> float:
        """Get success rate for a company"""
        if company not in self.company_scores:
            return 0.5  # Default neutral score
        
        data = self.company_scores[company]
        if data['attempts'] == 0:
            return 0.5
        
        return data['successes'] / data['attempts']
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            'contacted_emails_count': len(self.contacted_emails),
            'processed_jobs_count': len(self.job_fingerprints),
            'processed_urls_count': len(self.job_urls),
            'conversions_count': len(self.conversions),
            'tracked_titles_count': len(self.title_scores),
            'tracked_companies_count': len(self.company_scores),
            'last_hunt_time': self.last_hunt_time
        }
    
    def update_last_hunt_time(self) -> None:
        """Update the timestamp of the last hunt"""
        self.last_hunt_time = datetime.now().isoformat()
    
    def clear_memory(self) -> None:
        """Clear all memory data"""
        self.contacted_emails.clear()
        self.job_fingerprints.clear()
        self.job_urls.clear()
        self.conversions.clear()
        self.title_scores.clear()
        self.company_scores.clear()
        self.last_hunt_time = ""
    
    def export_memory_data(self) -> Dict[str, Any]:
        """Export all memory data for backup/analysis"""
        return {
            'contacted_emails': list(self.contacted_emails),
            'job_fingerprints': list(self.job_fingerprints),
            'job_urls': list(self.job_urls),
            'conversions': self.conversions,
            'title_scores': self.title_scores,
            'company_scores': self.company_scores,
            'last_hunt_time': self.last_hunt_time,
            'export_timestamp': datetime.now().isoformat()
        }
    
    def import_memory_data(self, data: Dict[str, Any]) -> None:
        """Import memory data from backup"""
        try:
            self.contacted_emails = set(data.get('contacted_emails', []))
            self.job_fingerprints = set(data.get('job_fingerprints', []))
            self.job_urls = set(data.get('job_urls', []))
            self.conversions = data.get('conversions', [])
            self.title_scores = data.get('title_scores', {})
            self.company_scores = data.get('company_scores', {})
            self.last_hunt_time = data.get('last_hunt_time', '')
        except Exception as e:
            raise ValueError(f"Invalid memory data format: {e}")
