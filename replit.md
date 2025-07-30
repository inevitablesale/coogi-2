# MCP: Master Control Program

## Overview

MCP (Master Control Program) is an automated recruiting and outreach platform built with Streamlit. The system is designed to streamline the job hunting and candidate outreach process by combining job scraping, contact finding, and automated email generation capabilities. The application currently operates in demo mode with mock data but is architected to integrate with real APIs for production use.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **Frontend**: Streamlit-based web interface providing an interactive dashboard
- **Backend Services**: Utility modules for core functionality (job scraping, contact finding, email generation, memory management)
- **Data Storage**: In-memory session state management with plans for database integration
- **External APIs**: Designed to integrate with JobSpy, RapidAPI, Hunter.io, OpenAI, and email delivery services

## Key Components

### 1. Main Application (app.py)
- **Purpose**: Streamlit frontend orchestrating all functionality
- **Architecture Decision**: Chose Streamlit for rapid prototyping and built-in UI components
- **Session Management**: Uses Streamlit's session state for maintaining user data across interactions

### 2. Job Scraper (utils/job_scraper.py)
- **Purpose**: Handles job posting discovery and filtering
- **Technology**: Integrates with JobSpy library for job scraping
- **Demo Mode**: Provides mock job data when APIs are unavailable
- **AI Integration**: Uses OpenAI for intent parsing and job relevance scoring

### 3. Contact Finder (utils/contact_finder.py)
- **Purpose**: Discovers hiring managers and decision makers at target companies
- **External APIs**: RapidAPI for LinkedIn scraping, Hunter.io for email discovery
- **Fallback Strategy**: Demo contacts ensure functionality without API keys

### 4. Email Generator (utils/email_generator.py)
- **Purpose**: Creates personalized outreach emails
- **AI Integration**: OpenAI GPT for dynamic email generation
- **Template System**: Multiple email styles (professional, friendly, direct)

### 5. Memory Manager (utils/memory_manager.py)
- **Purpose**: Prevents duplicate outreach and tracks system state
- **Architecture Decision**: In-memory storage with fingerprinting for deduplication
- **Future Enhancement**: Designed for easy migration to persistent database storage

## Data Flow

1. **Job Discovery**: User initiates search → JobScraper retrieves relevant positions
2. **Contact Identification**: For each job → ContactFinder locates hiring personnel
3. **Email Generation**: For each contact → EmailGenerator creates personalized outreach
4. **Memory Management**: Throughout process → MemoryManager prevents duplicates and tracks state
5. **User Interface**: All data flows through Streamlit session state for real-time updates

## External Dependencies

### Required APIs (Production)
- **OpenAI API**: GPT models for email generation and intent parsing
- **RapidAPI**: LinkedIn data scraping and company information
- **Hunter.io**: Email address discovery and verification
- **JobSpy**: Job posting aggregation across multiple platforms

### Optional Integrations
- **Instantly.ai**: Email delivery and campaign management
- **Supabase/PostgreSQL**: Persistent data storage and analytics

### Development Dependencies
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Requests**: HTTP client for API interactions

## Deployment Strategy

### Current State
- **Development**: Streamlit development server with demo data
- **Configuration**: Environment variables for API key management
- **Error Handling**: Graceful degradation to demo mode when APIs unavailable

### Production Considerations
- **Containerization**: Application structure supports Docker deployment
- **Database Migration**: Memory manager designed for easy PostgreSQL integration
- **API Rate Limiting**: Built-in delays and error handling for external service limits
- **Monitoring**: Logging infrastructure in place for production monitoring

### Scalability Approach
- **Modular Design**: Each utility can be independently scaled or replaced
- **Caching Strategy**: Streamlit resource caching for expensive operations
- **State Management**: Session-based architecture allows for easy multi-user support

The architecture prioritizes modularity and maintainability while providing a clear upgrade path from demo to production deployment. The system is designed to handle the complete recruiting workflow from job discovery through successful candidate placement.