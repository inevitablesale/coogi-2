import streamlit as st
import requests
import json
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="ContractGPT - AI Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://localhost:5000"

def check_api_health():
    """Check if the FastAPI backend is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return False, None

def search_jobs(query, max_leads=10, hours_old=24, enforce_salary=True, auto_generate_messages=False):
    """Search for jobs using the API"""
    try:
        payload = {
            "query": query,
            "max_leads": max_leads,
            "hours_old": hours_old,
            "enforce_salary": enforce_salary,
            "auto_generate_messages": auto_generate_messages
        }
        response = requests.post(f"{API_BASE_URL}/search-jobs", json=payload, timeout=30)
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

def get_memory_stats():
    """Get memory statistics from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/memory-stats", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return False, str(e)

# Custom CSS for dark theme and layout
def inject_custom_css():
    st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    
    .stApp {
        background-color: #0E1117;
    }
    
    .center-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
    }
    
    .search-container {
        background: #1E1E1E;
        border-radius: 12px;
        padding: 2rem;
        width: 100%;
        max-width: 600px;
        margin: 2rem auto;
    }
    
    .suggestion-card {
        background: #262626;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .suggestion-card:hover {
        background: #333333;
    }
    
    .sidebar-content {
        background: #1A1A1A;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .metric-card {
        background: #1E1E1E;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #00D4AA;
    }
    
    .lead-card {
        background: #1E1E1E;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #00D4AA;
    }
    
    .target-indicator {
        color: #00D4AA;
        font-weight: bold;
    }
    
    .skip-indicator {
        color: #FF6B6B;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Main app
def main():
    inject_custom_css()
    
    # Check API health
    api_healthy, health_data = check_api_health()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Coogi AI")
        st.markdown("---")
        
        # Navigation
        st.markdown("#### 📊 New Chat")
        st.markdown("#### 🎯 AI Campaigns")
        st.markdown("---")
        
        # Agents section
        st.markdown("**AGENTS**")
        st.markdown("📋 pitching recruitment...")
        st.markdown("---")
        
        # History section  
        st.markdown("**HISTORY**")
        st.markdown("📄 Show me B2B SaaS...")
        st.markdown("---")
        
        # Extension status
        st.markdown("**EXTENSION STATUS**")
        if api_healthy:
            st.markdown("🟢 **Connected**")
            st.markdown("Extension detected.")
        else:
            st.markdown("🔴 **Disconnected**") 
            st.markdown("Extension not detected.")
        
        # User info
        st.markdown("---")
        st.markdown("👤 chris@bg@gmail.com")
    
    # Main content area
    st.markdown('<div class="center-content">', unsafe_allow_html=True)
    
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔍 AI Search powered by ContractGPT")
        st.markdown("This is your command center. Tell me what kind of deals you're looking for, and I'll get to work.")
    
    # Search suggestions
    st.markdown("### 💡 Try one of these prompts:")
    
    # Create suggestion cards
    suggestions = [
        "Show me B2B SaaS companies in New York hiring for senior sales roles right now — I want to pitch recruitment support.",
        "Find remote fintech startups currently hiring software engineers — especially those with no talent acquisition team.",
        "Which companies in London are hiring for Marketing Director roles? Prioritize ones with urgent or repeated listings.",
        "I'm looking for Series A companies posting product manager roles — flag ones with high salaries or growth signals for outreach."
    ]
    
    col1, col2 = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with col1 if i % 2 == 0 else col2:
            if st.button(suggestion[:100] + "..." if len(suggestion) > 100 else suggestion, 
                        key=f"suggest_{i}", use_container_width=True):
                st.session_state.search_query = suggestion
    
    st.markdown("---")
    
    # Search input
    search_query = st.text_input(
        "Find new deals...", 
        placeholder="e.g., 'Series A fintechs in NY hiring sales leaders'",
        key="search_input",
        value=st.session_state.get('search_query', '')
    )
    
    # Advanced options in expander
    with st.expander("🔧 Advanced Search Options"):
        col1, col2, col3 = st.columns(3)
        with col1:
            max_leads = st.number_input("Max Companies", min_value=1, max_value=20, value=5)
        with col2:
            hours_old = st.selectbox("Job Age", [24, 48, 72, 168], index=2, 
                                   format_func=lambda x: f"{x} hours")
        with col3:
            auto_messages = st.checkbox("Generate Outreach Messages", value=False)
    
    if st.button("🚀 Search", type="primary", use_container_width=True):
        if search_query.strip():
            with st.spinner("🔍 Analyzing job markets and identifying opportunities..."):
                success, result = search_jobs(
                    search_query, max_leads, hours_old, False, auto_messages
                )
            
            if success and result and isinstance(result, dict):
                leads = result.get('leads', [])
                jobs_found = result.get('jobs_found', 0)
                
                st.success(f"📊 Found {jobs_found} jobs, identified {len(leads)} high-value opportunities")
                
                if leads:
                    st.markdown("## 🎯 Target Companies")
                    
                    for i, lead in enumerate(leads):
                        with st.container():
                            st.markdown(f"""
                            <div class="lead-card">
                                <h4>🏢 {lead.get('company', 'Unknown Company')}</h4>
                                <p><strong>Target Contact:</strong> {lead.get('title', 'Unknown Title')}</p>
                                <p><strong>Hiring For:</strong> {lead.get('job_title', 'Unknown Role')}</p>
                                <p><strong>Opportunity Score:</strong> {lead.get('score', 0)}/10</p>
                                <p><strong>Email:</strong> {lead.get('email', 'Use Hunter.io')}</p>
                                <p><span class="target-indicator">✅ TARGET: No internal TA team - high conversion probability</span></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if lead.get('message'):
                                with st.expander("📝 Generated Outreach Message"):
                                    st.text_area("Message", lead['message'], height=150, key=f"msg_{i}")
                            
                            job_url = lead.get('job_url')
                            if job_url:
                                st.markdown(f"[🔗 View Job Posting]({job_url})")
                            
                            st.markdown("---")
                else:
                    st.info("🔍 No high-value opportunities found. Try expanding your search criteria or location.")
            else:
                st.error(f"❌ Search failed: {result}")
        else:
            st.warning("Please enter a search query")
    
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()