import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any, Optional
import time
import re

# Import utility modules
from utils.job_scraper import JobScraper
from utils.contact_finder import ContactFinder
from utils.email_generator import EmailGenerator
from utils.memory_manager import MemoryManager

# Patch all .lower() calls to be safe
with open(__file__, 'r') as f:
    code = f.read()
code = re.sub(r'([\w\)\]"]+)\.lower\(\)', r'(\1 or "").lower()', code)
with open(__file__, 'w') as f:
    f.write(code)
# Manual patch for any missed cases:
# ... etc ...

# Page configuration
st.set_page_config(
    page_title="MCP: Master Control Program",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize utilities
@st.cache_resource
def initialize_services():
    """Initialize all service classes"""
    job_scraper = JobScraper()
    contact_finder = ContactFinder()
    email_generator = EmailGenerator()
    memory_manager = MemoryManager()
    return job_scraper, contact_finder, email_generator, memory_manager

job_scraper, contact_finder, email_generator, memory_manager = initialize_services()

# Initialize session state
if 'leads' not in st.session_state:
    st.session_state.leads = []
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'contacted_emails' not in st.session_state:
    st.session_state.contacted_emails = set()

# Main title and description
st.title("🎯 MCP: Master Control Program")
st.markdown("**Automated Recruiting & Outreach Platform**")

# Check API status
api_status = {
    "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
    "RapidAPI": bool(os.getenv("RAPIDAPI_KEY")),
    "Hunter.io": bool(os.getenv("HUNTER_API_KEY")),
    "Instantly.ai": bool(os.getenv("INSTANTLY_API_KEY"))
}

# Sidebar for API status and settings
with st.sidebar:
    st.header("🔧 System Status")
    
    demo_mode = not all(api_status.values())
    if demo_mode:
        st.warning("⚠️ Demo Mode Active")
        st.caption("Some API keys missing - using demo data")
    else:
        st.success("✅ All APIs Connected")
    
    st.subheader("API Status")
    for service, status in api_status.items():
        icon = "✅" if status else "❌"
        st.caption(f"{icon} {service}")
    
    st.divider()
    
    # Memory stats
    st.subheader("📊 Session Stats")
    st.metric("Leads Generated", len(st.session_state.leads))
    st.metric("Emails Contacted", len(st.session_state.contacted_emails))
    
    if st.button("🗑️ Clear Session Data"):
        st.session_state.leads = []
        st.session_state.search_history = []
        st.session_state.contacted_emails = set()
        st.rerun()

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Job Hunt", "📋 Lead Dashboard", "📧 Outreach", "📈 Analytics"])

with tab1:
    st.header("Job Search & Lead Generation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Search form
        with st.form("job_search_form"):
            query = st.text_input(
                "Search Query", 
                placeholder="e.g., 'Find me senior software engineer jobs in San Francisco'",
                help="Describe what type of jobs you're looking for"
            )
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                max_leads = st.number_input("Max Leads", min_value=1, max_value=50, value=10)
            with col_b:
                hours_old = st.number_input("Max Age (hours)", min_value=1, max_value=168, value=24)
            with col_c:
                enforce_salary = st.checkbox("Require Salary Info", value=True)
            
            auto_send = st.checkbox("Auto-generate outreach messages", value=False)
            
            search_submitted = st.form_submit_button("🚀 Start Hunt", type="primary")
    
    with col2:
        st.subheader("Search Tips")
        st.info("""
        **Examples:**
        - "Python developer jobs in NYC"
        - "Sales director positions at SaaS companies"
        - "Product manager roles in fintech"
        """)
    
    if search_submitted and query:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Parse query
            status_text.text("🧠 Parsing search query...")
            progress_bar.progress(10)
            search_params = job_scraper.parse_query(query)
            
            # Step 2: Search jobs
            status_text.text("🔍 Searching for jobs...")
            progress_bar.progress(30)
            jobs = job_scraper.search_jobs(search_params, max_results=max_leads*5)
            
            if not jobs:
                st.warning("No jobs found matching your criteria.")
            else:
                st.success(f"Found {len(jobs)} job postings")
                
                # Step 3: Process each job
                new_leads = []
                for i, job in enumerate(jobs[:max_leads]):
                    progress = 30 + (60 * (i + 1) / len(jobs[:max_leads]))
                    progress_bar.progress(int(progress))
                    status_text.text(f"🎯 Processing job {i+1}/{min(len(jobs), max_leads)}: {job.get('company', 'Unknown')}")
                    
                    # Check if already processed
                    job_fingerprint = memory_manager.create_job_fingerprint(job)
                    if memory_manager.is_job_processed(job_fingerprint):
                        continue
                    
                    # Find contacts
                    contacts, has_ta_team = contact_finder.find_contacts(
                        company=job.get('company', ''),
                        role_hint=job.get('title', ''),
                        keywords=job_scraper.extract_keywords(job.get('description', ''))
                    )
                    
                    for contact in contacts[:2]:  # Top 2 contacts per job
                        # Find email
                        email = contact_finder.find_email(
                            contact['title'], 
                            job.get('company', '')
                        )
                        
                        if email and email not in st.session_state.contacted_emails:
                            # Generate outreach message if requested
                            message = ""
                            if auto_send:
                                message = email_generator.generate_outreach(
                                    job_title=job.get('title', ''),
                                    company=job.get('company', ''),
                                    contact_title=contact['title'],
                                    job_url=job.get('job_url', '')
                                )
                            
                            # Calculate lead score
                            score = contact_finder.calculate_lead_score(contact, job, has_ta_team)
                            
                            lead = {
                                'name': contact['full_name'],
                                'title': contact['title'],
                                'company': job.get('company', ''),
                                'email': email,
                                'message': message,
                                'job_url': job.get('job_url', ''),
                                'job_title': job.get('title', ''),
                                'score': score,
                                'timestamp': datetime.now().isoformat(),
                                'contacted': False
                            }
                            new_leads.append(lead)
                    
                    # Mark job as processed
                    memory_manager.mark_job_processed(job_fingerprint)
                    
                    time.sleep(0.1)  # Rate limiting
                
                # Step 4: Save results
                progress_bar.progress(100)
                status_text.text("✅ Hunt complete!")
                
                st.session_state.leads.extend(new_leads)
                st.session_state.search_history.append({
                    'query': query,
                    'timestamp': datetime.now().isoformat(),
                    'leads_found': len(new_leads),
                    'jobs_processed': len(jobs[:max_leads])
                })
                
                if new_leads:
                    st.success(f"🎉 Generated {len(new_leads)} new leads!")
                    
                    # Show preview of results
                    st.subheader("Preview of New Leads")
                    preview_df = pd.DataFrame(new_leads[:5])[['name', 'title', 'company', 'score']]
                    st.dataframe(preview_df, use_container_width=True)
                else:
                    st.info("No new leads found - all contacts may have been previously identified.")
                    
        except Exception as e:
            st.error(f"Error during job hunt: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()

with tab2:
    st.header("Lead Management Dashboard")
    
    if not st.session_state.leads:
        st.info("No leads generated yet. Use the Job Hunt tab to find leads.")
    else:
        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            score_filter = st.slider("Minimum Score", 0.0, 10.0, 0.0, 0.1)
        with col2:
            company_filter = st.selectbox(
                "Filter by Company", 
                ["All"] + list(set([lead['company'] for lead in st.session_state.leads]))
            )
        with col3:
            contacted_filter = st.selectbox("Contact Status", ["All", "Not Contacted", "Contacted"])
        
        # Apply filters
        filtered_leads = st.session_state.leads.copy()
        if score_filter > 0:
            filtered_leads = [l for l in filtered_leads if l['score'] >= score_filter]
        if company_filter != "All":
            filtered_leads = [l for l in filtered_leads if l['company'] == company_filter]
        if contacted_filter == "Not Contacted":
            filtered_leads = [l for l in filtered_leads if not l['contacted']]
        elif contacted_filter == "Contacted":
            filtered_leads = [l for l in filtered_leads if l['contacted']]
        
        # Display leads
        st.subheader(f"Leads ({len(filtered_leads)})")
        
        for i, lead in enumerate(filtered_leads):
            with st.expander(f"🎯 {lead['name']} - {lead['title']} @ {lead['company']} (Score: {lead['score']:.1f})"):
                col_a, col_b = st.columns([3, 1])
                
                with col_a:
                    st.write(f"**Email:** {lead['email']}")
                    st.write(f"**Job:** {lead['job_title']}")
                    st.write(f"**URL:** {lead['job_url']}")
                    if lead['message']:
                        st.write("**Generated Message:**")
                        st.write(lead['message'])
                
                with col_b:
                    if st.button(f"Mark Contacted", key=f"contact_{i}"):
                        st.session_state.leads[st.session_state.leads.index(lead)]['contacted'] = True
                        st.session_state.contacted_emails.add(lead['email'])
                        st.rerun()
                    
                    if st.button(f"Copy Email", key=f"copy_{i}"):
                        st.write(f"```{lead['email']}```")
        
        # Export functionality
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Leads to CSV"):
                df = pd.DataFrame(filtered_leads)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📥 Export Messages"):
                messages_data = []
                for lead in filtered_leads:
                    if lead['message']:
                        messages_data.append({
                            'to': lead['email'],
                            'subject': f"Regarding {lead['job_title']} position at {lead['company']}",
                            'message': lead['message']
                        })
                
                if messages_data:
                    df = pd.DataFrame(messages_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Messages CSV",
                        data=csv,
                        file_name=f"messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

with tab3:
    st.header("Outreach Message Generator")
    
    # Select a lead for message generation
    if not st.session_state.leads:
        st.info("No leads available. Generate leads first in the Job Hunt tab.")
    else:
        # Lead selection
        lead_options = [f"{lead['name']} - {lead['title']} @ {lead['company']}" for lead in st.session_state.leads]
        selected_lead_idx = st.selectbox("Select Lead", range(len(lead_options)), format_func=lambda x: lead_options[x])
        
        if selected_lead_idx is not None:
            selected_lead = st.session_state.leads[selected_lead_idx]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Generate Outreach Message")
                
                # Message generation form
                with st.form("message_generation"):
                    custom_context = st.text_area(
                        "Additional Context (optional)",
                        placeholder="Any specific information you want to include in the message..."
                    )
                    
                    message_tone = st.selectbox(
                        "Message Tone",
                        ["Professional", "Friendly", "Direct", "Casual"]
                    )
                    
                    generate_message = st.form_submit_button("✨ Generate Message", type="primary")
                
                if generate_message:
                    with st.spinner("Generating personalized message..."):
                        try:
                            message = email_generator.generate_outreach(
                                job_title=selected_lead['job_title'],
                                company=selected_lead['company'],
                                contact_title=selected_lead['title'],
                                job_url=selected_lead['job_url'],
                                tone=message_tone.lower(),
                                additional_context=custom_context
                            )
                            
                            st.success("Message generated!")
                            st.text_area("Generated Message", message, height=200)
                            
                            # Update the lead with the new message
                            st.session_state.leads[selected_lead_idx]['message'] = message
                            
                            # Copy button
                            if st.button("📋 Copy to Clipboard"):
                                # This would need additional JavaScript for true clipboard functionality
                                st.code(message, language="text")
                                
                        except Exception as e:
                            st.error(f"Error generating message: {str(e)}")
            
            with col2:
                st.subheader("Lead Details")
                st.write(f"**Name:** {selected_lead['name']}")
                st.write(f"**Title:** {selected_lead['title']}")
                st.write(f"**Company:** {selected_lead['company']}")
                st.write(f"**Email:** {selected_lead['email']}")
                st.write(f"**Score:** {selected_lead['score']:.1f}")
                st.write(f"**Job:** {selected_lead['job_title']}")
                
                if selected_lead.get('message'):
                    st.subheader("Current Message")
                    st.text_area("", selected_lead['message'], height=150, disabled=True)

with tab4:
    st.header("Analytics & Performance")
    
    if not st.session_state.leads and not st.session_state.search_history:
        st.info("No data available yet. Start hunting for jobs to see analytics.")
    else:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Leads", len(st.session_state.leads))
        with col2:
            contacted_count = len([l for l in st.session_state.leads if l['contacted']])
            st.metric("Contacted", contacted_count)
        with col3:
            avg_score = sum([l['score'] for l in st.session_state.leads]) / len(st.session_state.leads) if st.session_state.leads else 0
            st.metric("Avg Score", f"{avg_score:.1f}")
        with col4:
            st.metric("Searches", len(st.session_state.search_history))
        
        if st.session_state.leads:
            # Score distribution
            st.subheader("Lead Score Distribution")
            scores = [lead['score'] for lead in st.session_state.leads]
            score_df = pd.DataFrame({'scores': scores})
            st.bar_chart(score_df['scores'])
            
            # Company breakdown
            st.subheader("Leads by Company")
            company_counts = {}
            for lead in st.session_state.leads:
                company = lead['company']
                company_counts[company] = company_counts.get(company, 0) + 1
            
            if company_counts:
                company_data = list(company_counts.items())
                company_df = pd.DataFrame(company_data, columns=['Company', 'Count'])
                company_df = company_df.sort_values('Count', ascending=False).head(10)
                st.bar_chart(company_df.set_index('Company')['Count'])
        
        if st.session_state.search_history:
            # Search history
            st.subheader("Search History")
            history_df = pd.DataFrame(st.session_state.search_history)
            st.dataframe(history_df, use_container_width=True)

# Footer
st.divider()
st.caption("MCP: Master Control Program - Automated Recruiting Platform")
if demo_mode:
    st.caption("⚠️ Running in demo mode - configure API keys for full functionality")
