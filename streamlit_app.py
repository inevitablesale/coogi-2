import streamlit as st
import requests
import json
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="MCP: Master Control Program",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://0.0.0.0:5000"

def check_api_health():
    """Check if the FastAPI backend is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return False, None

def search_jobs_streaming(query, max_leads=10, hours_old=24, enforce_salary=True, auto_generate_messages=False, status_container=None):
    """Search for jobs using streaming API with live status updates"""
    try:
        params = {
            "query": query,
            "max_leads": max_leads,
            "hours_old": hours_old,
            "enforce_salary": enforce_salary,
            "auto_generate_messages": auto_generate_messages
        }
        
        # Stream the response for real-time updates
        response = requests.get(f"{API_BASE_URL}/search-jobs-stream", params=params, stream=True, timeout=60)
        
        if response.status_code != 200:
            return False, None
            
        leads = []
        summary = {}
        
        for line in response.iter_lines():
            if line:
                try:
                    # Parse each streaming line
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data = json.loads(line_text[6:])  # Remove 'data: ' prefix
                        
                        if data.get('type') == 'status' and status_container:
                            # Update status display
                            with status_container:
                                st.write(f"🔄 {data.get('message', '')}")
                                
                        elif data.get('type') == 'lead':
                            # New lead found
                            lead_data = data.get('data', {})
                            leads.append(lead_data)
                            if status_container:
                                with status_container:
                                    st.write(f"✅ Found lead: {lead_data.get('name', 'Unknown')} at {lead_data.get('company', 'Unknown')}")
                                    
                        elif data.get('type') == 'summary':
                            # Final summary
                            summary = data.get('data', {})
                            if status_container:
                                with status_container:
                                    st.write(f"🎯 **Search Complete**: {summary.get('leads_found', 0)} leads from {summary.get('jobs_processed', 0)} jobs")
                                    
                except json.JSONDecodeError:
                    continue
                    
        return True, {
            'leads': leads,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
    except requests.exceptions.RequestException as e:
        return False, str(e)

def search_jobs(query, max_leads=10, hours_old=24, enforce_salary=True, auto_generate_messages=False):
    """Search for jobs using the fast API (fallback for non-streaming)"""
    try:
        payload = {
            "query": query,
            "max_leads": max_leads,
            "hours_old": hours_old,
            "enforce_salary": enforce_salary,
            "auto_generate_messages": auto_generate_messages
        }
        
        # Use fast endpoint for better performance within timeout limits
        response = requests.post(f"{API_BASE_URL}/search-jobs-fast", json=payload, timeout=30)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return False, str(e)

def generate_message(job_title, company, contact_title, job_url, tone="professional"):
    """Generate a message using the API"""
    try:
        payload = {
            "job_title": job_title,
            "company": company,
            "contact_title": contact_title,
            "job_url": job_url,
            "tone": tone
        }
        response = requests.post(f"{API_BASE_URL}/generate-message", json=payload, timeout=15)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return False, str(e)

def analyze_companies(query, max_companies=10, include_job_data=True):
    """Analyze companies for recruiting opportunities"""
    try:
        payload = {
            "query": query,
            "max_companies": max_companies,
            "include_job_data": include_job_data
        }
        response = requests.post(f"{API_BASE_URL}/analyze-companies", json=payload, timeout=120)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return False, str(e)

def get_memory_stats():
    """Get memory statistics from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/memory-stats", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return False, str(e)

# Main app
def main():
    st.title("🤖 MCP: Master Control Program")
    st.write("### Automated Recruiting & Outreach Platform")
    
    # Check API health
    api_healthy, health_data = check_api_health()
    
    if not api_healthy:
        st.error("❌ FastAPI backend is not running. Please start the API server first.")
        st.code("python api.py")
        st.stop()
    
    # Display API status
    with st.sidebar:
        st.header("🔧 System Status")
        if health_data and isinstance(health_data, dict):
            api_status = health_data.get("api_status", {})
            for service, status in api_status.items():
                icon = "✅" if status else "❌"
                st.write(f"{icon} {service}")
            
            demo_mode = health_data.get("demo_mode", False)
            if demo_mode:
                st.warning("🔄 Email discovery in demo mode")
            else:
                st.success("🚀 All systems operational")
        
        # Memory stats
        st.header("📊 Statistics")
        stats_success, stats_data = get_memory_stats()
        if stats_success and stats_data and isinstance(stats_data, dict):
            st.metric("Jobs Processed", stats_data.get("processed_jobs_count", 0))
            st.metric("Contacts Found", stats_data.get("contacted_emails_count", 0))
            st.metric("Messages Generated", stats_data.get("conversions_count", 0))
    
    # Main interface
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Job Search", "🏢 Company Analysis", "✉️ Message Generator", "📈 Analytics"])
    
    with tab1:
        st.header("Job Search & Lead Generation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            query = st.text_input(
                "Search Query", 
                placeholder="e.g., software engineer remote, data scientist NYC, marketing manager startup",
                help="Describe the type of job you're looking for"
            )
        
        with col2:
            max_leads = st.number_input("Max Leads", min_value=1, max_value=50, value=10)
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            hours_old = st.selectbox("Job Age", [24, 48, 72, 168], index=0, format_func=lambda x: f"{x} hours")
        
        with col4:
            enforce_salary = st.checkbox("Require Salary Info", value=True)
        
        with col5:
            auto_messages = st.checkbox("Auto-generate Messages", value=False)
        
        # Add streaming option
        stream_updates = st.checkbox("Show Live Progress", value=True, help="Display real-time status updates during search")
        
        if st.button("🚀 Search Jobs", type="primary", use_container_width=True):
            if not query.strip():
                st.error("Please enter a search query")
            else:
                if stream_updates:
                    # Use streaming search with live updates
                    status_container = st.empty()
                    progress_container = st.container()
                    
                    with status_container:
                        st.info("🔄 Initializing job search...")
                    
                    success, result = search_jobs_streaming(
                        query, max_leads, hours_old, enforce_salary, auto_messages, 
                        status_container=progress_container
                    )
                else:
                    # Use regular search
                    with st.spinner("Searching for jobs and contacts..."):
                        success, result = search_jobs(
                            query, max_leads, hours_old, enforce_salary, auto_messages
                        )
                
                if success and result and isinstance(result, dict):
                    # Show final summary
                    summary = result.get('summary', {})
                    leads = result.get('leads', [])
                    
                    if summary:
                        jobs_found = summary.get('total_jobs', 0)
                        jobs_processed = summary.get('jobs_processed', 0) 
                        leads_found = summary.get('leads_found', len(leads))
                        st.success(f"✅ Search Complete: {leads_found} leads from {jobs_processed} jobs (found {jobs_found} total)")
                    else:
                        st.success(f"Found {result.get('jobs_found', 0)} jobs, generated {len(leads)} leads")
                    
                    # Display results
                    if leads:
                        st.header("📋 Generated Leads")
                        
                        for i, lead in enumerate(leads):
                            with st.expander(f"Lead {i+1}: {lead.get('name', 'Unknown')} at {lead.get('company', 'Unknown')}", expanded=i==0):
                                col_a, col_b = st.columns(2)
                                
                                with col_a:
                                    st.write(f"**Name:** {lead.get('name', 'N/A')}")
                                    st.write(f"**Title:** {lead.get('title', 'N/A')}")
                                    st.write(f"**Company:** {lead.get('company', 'N/A')}")
                                    st.write(f"**Email:** {lead.get('email', 'N/A')}")
                                    st.write(f"**Score:** {lead.get('score', 0)}/10")
                                
                                with col_b:
                                    st.write(f"**Job:** {lead.get('job_title', 'N/A')}")
                                    job_url = lead.get('job_url', '')
                                    if job_url:
                                        st.write(f"**Job URL:** [View Position]({job_url})")
                                    st.write(f"**Timestamp:** {lead.get('timestamp', 'N/A')}")
                                
                                message = lead.get('message', '')
                                if message:
                                    st.write("**Generated Message:**")
                                    st.text_area(f"Message for {lead.get('name', 'Contact')}", message, height=150, key=f"msg_{i}")
                    else:
                        st.info("No leads generated. Try adjusting your search criteria.")
                
                elif success:
                    st.warning("Search completed but no results found")
                else:
                    st.error(f"Search failed: {result}")
    
    with tab2:
        st.header("🏢 Company Analysis & Skip Report")
        st.write("Analyze companies to identify those without internal TA teams for high-conversion recruiting")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            analysis_query = st.text_input(
                "Job Search Query", 
                placeholder="e.g., software engineer, data scientist, marketing manager",
                help="Enter job titles to find companies hiring for these roles"
            )
        
        with col2:
            max_companies = st.number_input("Max Companies", min_value=1, max_value=20, value=5)
        
        col3, col4 = st.columns(2)
        with col3:
            include_job_data = st.checkbox("Include Job Data", value=True, help="Fetch current job postings for companies")
        
        if st.button("🔍 Analyze Companies", type="primary", use_container_width=True):
            if not analysis_query.strip():
                st.error("Please enter a search query")
            else:
                with st.spinner("Analyzing companies for recruiting opportunities..."):
                    success, result = analyze_companies(analysis_query, max_companies, include_job_data)
                
                if success and result and isinstance(result, dict):
                    st.success("Company analysis completed!")
                    
                    # Summary metrics
                    summary = result.get('summary', {})
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Companies Analyzed", summary.get('total_companies_analyzed', 0))
                    with col2:
                        st.metric("Target Companies", summary.get('target_companies_found', 0))
                    with col3:
                        st.metric("Companies Skipped", summary.get('companies_skipped', 0))
                    with col4:
                        st.metric("Success Rate", f"{summary.get('success_rate', 0)}%")
                    
                    # Target companies
                    target_companies = result.get('target_companies', [])
                    if target_companies:
                        st.subheader("🎯 Target Companies (No TA Team)")
                        for i, company in enumerate(target_companies):
                            with st.expander(f"🏢 {company.get('company', '')} - {company.get('recommendation', '')}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write("**Decision Makers:**")
                                    decision_makers = company.get('decision_makers', [])
                                    for dm in decision_makers:
                                        score = dm.get('decision_score', 0)
                                        title = dm.get('title', '')
                                        score_icon = "⭐" * (score // 2)
                                        st.write(f"{score_icon} {title} (Score: {score})")
                                
                                with col2:
                                    if company.get('job_count', 0) > 0:
                                        st.write(f"**Active Jobs:** {company.get('job_count', 0)}")
                                        active_jobs = company.get('active_jobs', [])[:3]
                                        for job in active_jobs:
                                            st.write(f"• {job.get('title', 'Job Title')}")
                                    else:
                                        st.write("**Active Jobs:** None found")
                    else:
                        st.info("No target companies found. All companies have internal TA teams or no decision makers.")
                    
                    # Skip report
                    st.subheader("📊 Company Skip Report")
                    skipped_companies = result.get('skipped_companies', [])
                    skip_reasons = summary.get('skip_reasons', {})
                    
                    if skip_reasons:
                        # Skip reasons chart
                        for reason, count in skip_reasons.items():
                            st.write(f"**{reason}:** {count} companies")
                    
                    # Recent skipped companies
                    if skipped_companies:
                        st.write("**Recently Skipped Companies:**")
                        for skip in skipped_companies[-5:]:  # Show last 5
                            company = skip.get('company', '')
                            reason = skip.get('reason', '')
                            ta_roles = skip.get('ta_roles', [])
                            
                            if ta_roles:
                                st.write(f"• **{company}**: {reason} ({', '.join(ta_roles[:2])})")
                            else:
                                st.write(f"• **{company}**: {reason}")
                
                elif success:
                    st.warning("Analysis completed but no results found")
                else:
                    st.error(f"Analysis failed: {result}")
    
    with tab3:
        st.header("Message Generator")
        st.write("Generate personalized outreach messages for specific contacts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            job_title = st.text_input("Job Title", placeholder="Senior Software Engineer")
            company = st.text_input("Company", placeholder="TechCorp Inc")
        
        with col2:
            contact_title = st.text_input("Contact Title", placeholder="VP of Engineering")
            job_url = st.text_input("Job URL", placeholder="https://company.com/jobs/123")
        
        tone = st.selectbox("Message Tone", ["professional", "friendly", "direct"], index=0)
        
        if st.button("✨ Generate Message", type="primary"):
            if not all([job_title, company, contact_title]):
                st.error("Please fill in job title, company, and contact title")
            else:
                with st.spinner("Generating personalized message..."):
                    success, result = generate_message(job_title, company, contact_title, job_url, tone)
                
                if success and result and isinstance(result, dict):
                    st.success("Message generated successfully!")
                    st.write("**Subject:**")
                    st.code(result.get('subject_line', 'No subject'))
                    st.write("**Message:**")
                    st.text_area("Generated Message", result.get('message', 'No message'), height=300)
                else:
                    st.error(f"Message generation failed: {result}")
    
    with tab4:
        st.header("Platform Analytics")
        
        stats_success, stats_data = get_memory_stats()
        if stats_success and stats_data and isinstance(stats_data, dict):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Jobs Processed",
                    stats_data.get("processed_jobs_count", 0),
                    help="Total number of job postings analyzed"
                )
            
            with col2:
                st.metric(
                    "Contacts Found",
                    stats_data.get("contacted_emails_count", 0),
                    help="Number of unique contacts discovered"
                )
            
            with col3:
                st.metric(
                    "Messages Generated",
                    stats_data.get("conversions_count", 0),
                    help="Total outreach messages created"
                )
            
            with col4:
                st.metric(
                    "Companies Tracked",
                    stats_data.get("tracked_companies_count", 0),
                    help="Unique companies in database"
                )
            
            # Performance summary
            st.subheader("📊 Performance Summary")
            
            processed_jobs = stats_data.get("processed_jobs_count", 0)
            if processed_jobs > 0:
                contacted_emails = stats_data.get("contacted_emails_count", 0)
                conversion_rate = (contacted_emails / processed_jobs) * 100
                st.metric("Lead Conversion Rate", f"{conversion_rate:.1f}%")
            
            last_hunt = stats_data.get("last_hunt_time", "")
            if last_hunt:
                st.write(f"**Last Search:** {last_hunt}")
            
            # Clear memory option
            st.subheader("🗑️ System Management")
            if st.button("Clear Memory", help="Reset all tracking data"):
                try:
                    response = requests.delete(f"{API_BASE_URL}/memory", timeout=5)
                    if response.status_code == 200:
                        st.success("Memory cleared successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to clear memory")
                except requests.exceptions.RequestException:
                    st.error("Could not connect to API")
        else:
            st.error("Could not load analytics data")

if __name__ == "__main__":
    main()