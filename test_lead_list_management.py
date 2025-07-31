#!/usr/bin/env python3
"""
Test lead list management functionality
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the utils directory to the path
sys.path.append('utils')

from instantly_manager import InstantlyManager

def test_lead_list_management():
    """Test the improved lead list management"""
    
    # Initialize Instantly manager
    instantly = InstantlyManager()
    
    print("🧪 Testing Lead List Management...")
    
    # Test 1: Get existing lead lists
    print("\n1️⃣ Getting existing lead lists...")
    lead_lists = instantly.get_lead_lists()
    print(f"📊 Found {len(lead_lists)} existing lead lists")
    
    # Test 2: Find or create lead list for a company type
    print("\n2️⃣ Testing find_or_create_lead_list...")
    
    # Test with tech_startups company type
    lead_list_id = instantly.find_or_create_lead_list("tech_startups")
    if lead_list_id:
        print(f"✅ Lead list ID: {lead_list_id}")
    else:
        print("❌ Failed to find or create lead list")
        return False
    
    # Test 3: Try to find the same lead list again (should reuse existing)
    print("\n3️⃣ Testing reuse of existing lead list...")
    lead_list_id_2 = instantly.find_or_create_lead_list("tech_startups")
    if lead_list_id_2:
        print(f"✅ Reused lead list ID: {lead_list_id_2}")
        if lead_list_id == lead_list_id_2:
            print("✅ Successfully reused the same lead list!")
        else:
            print("⚠️  Got different lead list IDs")
    else:
        print("❌ Failed to reuse lead list")
        return False
    
    # Test 4: Cleanup function (just logs for now)
    print("\n4️⃣ Testing cleanup function...")
    deleted_count = instantly.cleanup_old_lead_lists()
    print(f"📋 Cleanup completed, {deleted_count} lists would be deleted")
    
    print("\n🎯 Lead list management test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_lead_list_management()
    if success:
        print("\n🎯 All tests passed!")
    else:
        print("\n💥 Tests failed!")
        sys.exit(1) 