#!/usr/bin/env python3
"""
Blacklist Manager - Track companies to skip before making API calls
"""

import os
import json
import logging
from typing import List, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class BlacklistManager:
    def __init__(self, blacklist_file: str = "company_blacklist.json"):
        self.blacklist_file = blacklist_file
        self.blacklisted_companies: Set[str] = set()
        self.load_blacklist()
    
    def load_blacklist(self):
        """Load blacklist from file"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.blacklisted_companies = set(data.get('companies', []))
                logger.info(f"✅ Loaded {len(self.blacklisted_companies)} blacklisted companies")
            else:
                logger.info("📝 No blacklist file found, starting with empty blacklist")
        except Exception as e:
            logger.error(f"❌ Error loading blacklist: {e}")
            self.blacklisted_companies = set()
    
    def save_blacklist(self):
        """Save blacklist to file"""
        try:
            data = {
                'companies': list(self.blacklisted_companies),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.blacklist_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"✅ Saved {len(self.blacklisted_companies)} blacklisted companies")
        except Exception as e:
            logger.error(f"❌ Error saving blacklist: {e}")
    
    def is_blacklisted(self, company: str) -> bool:
        """Check if company is blacklisted"""
        company_lower = company.lower().strip()
        return company_lower in self.blacklisted_companies
    
    def add_to_blacklist(self, company: str, reason: str = ""):
        """Add company to blacklist"""
        company_lower = company.lower().strip()
        if company_lower not in self.blacklisted_companies:
            self.blacklisted_companies.add(company_lower)
            self.save_blacklist()
            logger.info(f"🗑️  Added {company} to blacklist (reason: {reason})")
        else:
            logger.info(f"⚠️  {company} already in blacklist")
    
    def remove_from_blacklist(self, company: str):
        """Remove company from blacklist"""
        company_lower = company.lower().strip()
        if company_lower in self.blacklisted_companies:
            self.blacklisted_companies.remove(company_lower)
            self.save_blacklist()
            logger.info(f"✅ Removed {company} from blacklist")
        else:
            logger.info(f"⚠️  {company} not found in blacklist")
    
    def get_blacklist(self) -> List[str]:
        """Get all blacklisted companies"""
        return list(self.blacklisted_companies)
    
    def clear_blacklist(self):
        """Clear all blacklisted companies"""
        self.blacklisted_companies.clear()
        self.save_blacklist()
        logger.info("🗑️  Cleared all blacklisted companies")
    
    def get_blacklist_stats(self) -> dict:
        """Get blacklist statistics"""
        return {
            'total_companies': len(self.blacklisted_companies),
            'companies': list(self.blacklisted_companies),
            'last_updated': datetime.now().isoformat()
        } 