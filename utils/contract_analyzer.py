import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ContractAnalyzer:
    """Analyzes job data to identify high-value recruiting contract opportunities"""
    
    def __init__(self):
        self.urgency_keywords = [
            'urgent', 'asap', 'immediate', 'immediately', 'fast track', 
            'expedited', 'rush', 'time sensitive', 'quick start', 'rapid'
        ]
        
        self.growth_keywords = [
            'scaling', 'expanding', 'growing', 'new team', 'building team',
            'growth', 'expansion', 'rapid growth', 'fast growing'
        ]
        
        self.seniority_multipliers = {
            'senior': 1.5,
            'lead': 1.8,
            'principal': 2.0,
            'staff': 2.0,
            'director': 2.5,
            'vp': 3.0,
            'chief': 3.5,
            'head': 2.2,
            'manager': 1.3
        }

    def analyze_contract_opportunities(self, jobs: List[Dict[str, Any]], max_companies: int = 20) -> Dict[str, Any]:
        """Analyze jobs to identify high-value contract opportunities by company"""
        
        # Group jobs by company
        company_data = {}
        for job in jobs:
            company = job.get('company', '').strip()
            if not company:
                continue
                
            if company not in company_data:
                company_data[company] = {
                    'company': company,
                    'jobs': [],
                    'total_positions': 0,
                    'estimated_budget': 0,
                    'urgency_score': 0,
                    'growth_indicators': 0,
                    'seniority_score': 0,
                    'locations': set(),
                    'departments': set()
                }
            
            company_data[company]['jobs'].append(job)
        
        # Analyze each company
        contract_opportunities = []
        for company, data in company_data.items():
            opportunity = self._analyze_company_opportunity(data)
            if opportunity['contract_value_score'] > 0:
                contract_opportunities.append(opportunity)
        
        # Sort by contract value score
        contract_opportunities.sort(key=lambda x: x['contract_value_score'], reverse=True)
        
        # Limit results
        top_opportunities = contract_opportunities[:max_companies]
        
        # Generate summary  
        total_recruiting_fees = sum(opp['estimated_recruiting_fees'] for opp in top_opportunities)
        total_candidate_salaries = sum(opp['total_candidate_salaries'] for opp in top_opportunities)
        avg_positions = sum(opp['total_positions'] for opp in top_opportunities) / max(len(top_opportunities), 1)
        
        return {
            'opportunities': top_opportunities,
            'summary': {
                'total_companies_analyzed': len(company_data),
                'high_value_opportunities': len(top_opportunities),
                'total_recruiting_fees': total_recruiting_fees,
                'total_candidate_salaries': total_candidate_salaries,
                'average_positions_per_company': round(avg_positions, 1),
                'top_opportunity': top_opportunities[0] if top_opportunities else None
            },
            'timestamp': datetime.now().isoformat()
        }

    def _analyze_company_opportunity(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single company's hiring opportunity"""
        
        jobs = company_data['jobs']
        company = company_data['company']
        
        # Basic metrics
        total_positions = len(jobs)
        total_candidate_salaries = 0
        estimated_recruiting_fees = 0
        urgency_score = 0
        growth_score = 0
        seniority_score = 0
        
        # Department and location tracking
        departments = set()
        locations = set()
        role_types = set()
        
        for job in jobs:
            # Extract salary information
            salary_min = self._extract_salary(job.get('salary_min'))
            salary_max = self._extract_salary(job.get('salary_max'))
            
            # Estimate salary if not provided
            if not salary_max and not salary_min:
                estimated_salary = self._estimate_salary_from_title(job.get('title', ''))
            else:
                estimated_salary = salary_max or salary_min or 0
            
            total_candidate_salaries += estimated_salary
            
            # Calculate recruiting fee (20% average for contingency recruiting)
            recruiting_fee = estimated_salary * 0.20
            estimated_recruiting_fees += recruiting_fee
            
            # Analyze job content for signals
            job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
            
            # Urgency indicators
            urgency_score += self._count_keywords(job_text, self.urgency_keywords)
            
            # Growth indicators
            growth_score += self._count_keywords(job_text, self.growth_keywords)
            
            # Seniority scoring
            title_lower = job.get('title', '').lower()
            for level, multiplier in self.seniority_multipliers.items():
                if level in title_lower:
                    seniority_score += multiplier
            
            # Extract metadata
            if job.get('location'):
                locations.add(job.get('location'))
            
            # Extract department from title
            dept = self._extract_department(job.get('title', ''))
            if dept:
                departments.add(dept)
                
            # Extract role type
            role_type = self._extract_role_type(job.get('title', ''))
            if role_type:
                role_types.add(role_type)
        
        # Calculate contract value score  
        contract_value_score = self._calculate_contract_score(
            total_positions, estimated_recruiting_fees, urgency_score, 
            growth_score, seniority_score, len(departments)
        )
        
        # Generate recruiting pitch
        pitch = self._generate_recruiting_pitch(
            company, total_positions, estimated_recruiting_fees, 
            list(role_types), urgency_score > 0, growth_score > 0
        )
        
        return {
            'company': company,
            'total_positions': total_positions,
            'total_candidate_salaries': total_candidate_salaries,
            'estimated_recruiting_fees': estimated_recruiting_fees,
            'contract_value_score': round(contract_value_score, 1),
            'urgency_indicators': urgency_score,
            'growth_indicators': growth_score,
            'seniority_score': round(seniority_score, 1),
            'departments': list(departments),
            'locations': list(locations),
            'role_types': list(role_types),
            'recruiting_pitch': pitch,
            'jobs': [
                {
                    'title': job.get('title'),
                    'location': job.get('location'),
                    'salary_range': f"{job.get('salary_min', 'N/A')} - {job.get('salary_max', 'N/A')}",
                    'estimated_salary': self._extract_salary(job.get('salary_max')) or self._extract_salary(job.get('salary_min')) or self._estimate_salary_from_title(job.get('title', '')),
                    'recruiting_fee': (self._extract_salary(job.get('salary_max')) or self._extract_salary(job.get('salary_min')) or self._estimate_salary_from_title(job.get('title', ''))) * 0.20,
                    'job_url': job.get('job_url')
                }
                for job in jobs
            ]
        }

    def _extract_salary(self, salary_str: Any) -> int:
        """Extract numeric salary from string or return 0"""
        if not salary_str:
            return 0
        
        # Convert to string and clean
        salary_clean = str(salary_str).replace(',', '').replace('$', '').replace('k', '000')
        
        # Extract number
        numbers = re.findall(r'\d+', salary_clean)
        if numbers:
            return int(numbers[0])
        return 0

    def _estimate_salary_from_title(self, title: str) -> int:
        """Rough salary estimation based on job title"""
        title_lower = title.lower()
        
        # Base estimates by role type
        base_estimates = {
            'engineer': 120000, 'developer': 110000, 'software': 115000,
            'senior': 140000, 'lead': 160000, 'principal': 180000,
            'director': 200000, 'vp': 250000, 'manager': 130000,
            'designer': 90000, 'product': 130000, 'data': 125000,
            'marketing': 80000, 'sales': 90000, 'hr': 75000
        }
        
        estimated = 100000  # Default
        
        for keyword, salary in base_estimates.items():
            if keyword in title_lower:
                estimated = max(estimated, salary)
        
        return estimated

    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count occurrences of keywords in text"""
        count = 0
        for keyword in keywords:
            count += text.count(keyword.lower())
        return count

    def _extract_department(self, title: str) -> Optional[str]:
        """Extract department from job title"""
        title_lower = title.lower()
        
        departments = {
            'engineering': ['engineer', 'developer', 'software', 'backend', 'frontend', 'fullstack'],
            'product': ['product', 'pm'],
            'design': ['designer', 'ux', 'ui'],
            'data': ['data', 'analyst', 'scientist'],
            'marketing': ['marketing', 'growth', 'content'],
            'sales': ['sales', 'account', 'business development'],
            'operations': ['operations', 'ops', 'devops'],
            'hr': ['hr', 'people', 'talent', 'recruiter']
        }
        
        for dept, keywords in departments.items():
            if any(keyword in title_lower for keyword in keywords):
                return dept
        
        return None

    def _extract_role_type(self, title: str) -> Optional[str]:
        """Extract specific role type from title"""
        title_lower = title.lower()
        
        if 'frontend' in title_lower or 'front-end' in title_lower:
            return 'Frontend Engineer'
        elif 'backend' in title_lower or 'back-end' in title_lower:
            return 'Backend Engineer'
        elif 'fullstack' in title_lower or 'full-stack' in title_lower:
            return 'Full Stack Engineer'
        elif 'data scientist' in title_lower:
            return 'Data Scientist'
        elif 'product manager' in title_lower:
            return 'Product Manager'
        elif 'designer' in title_lower:
            return 'Designer'
        elif 'engineer' in title_lower or 'developer' in title_lower:
            return 'Software Engineer'
        
        return title.title()

    def _calculate_contract_score(self, positions: int, budget: int, urgency: int, 
                                growth: int, seniority: float, dept_diversity: int) -> float:
        """Calculate overall contract value score"""
        
        score = 0
        
        # Position volume (more positions = higher value)
        score += positions * 10
        
        # Budget factor (higher budget = higher fees)
        score += budget / 10000
        
        # Urgency multiplier (urgent hiring = premium rates)
        if urgency > 0:
            score *= 1.3
        
        # Growth multiplier (scaling companies = repeat business)
        if growth > 0:
            score *= 1.2
        
        # Seniority bonus (senior roles = higher fees)
        score += seniority * 5
        
        # Department diversity (multiple departments = larger engagement)
        score += dept_diversity * 3
        
        return score

    def _generate_recruiting_pitch(self, company: str, positions: int, recruiting_fees: int,
                                 role_types: List[str], has_urgency: bool, has_growth: bool) -> str:
        """Generate a personalized recruiting pitch"""
        
        pitch_parts = []
        
        # Opening based on volume
        if positions >= 5:
            pitch_parts.append(f"I noticed {company} is scaling rapidly with {positions} open positions")
        else:
            pitch_parts.append(f"I see {company} is hiring for {positions} key role{'s' if positions > 1 else ''}")
        
        # Fee context  
        if recruiting_fees > 50000:
            pitch_parts.append(f"representing ${recruiting_fees:,}+ in potential recruiting fees")
        
        # Role context
        if role_types:
            top_roles = role_types[:2]
            if len(top_roles) == 1:
                pitch_parts.append(f"focusing on {top_roles[0]} talent")
            else:
                pitch_parts.append(f"spanning {' and '.join(top_roles)} roles")
        
        # Urgency/growth indicators
        if has_urgency:
            pitch_parts.append("These appear to be urgent fills")
        elif has_growth:
            pitch_parts.append("suggesting significant company growth")
        
        # Value proposition
        pitch_parts.append("I specialize in placing top-tier talent for companies at your scale")
        
        return ". ".join(pitch_parts) + "."