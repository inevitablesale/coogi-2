# MCP: Master Control Program

## Overview

MCP (Master Control Program) is an automated recruiting and outreach platform built with FastAPI. The system is designed to streamline the job hunting and candidate outreach process by combining job scraping, contact finding, and automated email generation capabilities. The application has been converted from Streamlit to a REST API for Railway deployment and GitHub hosting.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **API**: FastAPI-based REST API providing endpoints for job searching, lead generation, and message creation
- **Backend Services**: Utility modules for core functionality (job scraping, contact finding, email generation, memory management)
- **Data Storage**: In-memory session state management with plans for database integration
- **External APIs**: Designed to integrate with JobSpy, RapidAPI, Hunter.io, OpenAI, and email delivery services

## Key Components

### 1. Main API Application (api.py)
- **Purpose**: FastAPI backend providing REST endpoints for all functionality
- **Architecture Decision**: Converted from Streamlit to FastAPI for better deployment on Railway and API-first architecture
- **Request/Response Models**: Uses Pydantic models for data validation and serialization

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

1. **Job Discovery**: API receives search request → JobScraper retrieves relevant positions
2. **Contact Identification**: For each job → ContactFinder locates hiring personnel
3. **Email Generation**: For each contact → EmailGenerator creates personalized outreach
4. **Memory Management**: Throughout process → MemoryManager prevents duplicates and tracks state
5. **API Response**: All data returned as JSON through RESTful endpoints

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
- **FastAPI**: Web API framework
- **Uvicorn**: ASGI server for FastAPI
- **Pydantic**: Data validation and serialization
- **Pandas**: Data manipulation and analysis
- **Requests**: HTTP client for API interactions

## Deployment Strategy

### Current State
- **Development**: FastAPI server with auto-generated documentation
- **Configuration**: Environment variables for API key management, RapidAPI key configured
- **Error Handling**: Uses live APIs with graceful fallback only for email discovery

### Production Considerations
- **Railway Deployment**: Configured with railway.json and Procfile for seamless deployment
- **Database Migration**: Memory manager designed for easy PostgreSQL integration
- **API Rate Limiting**: Built-in delays and error handling for external service limits
- **Monitoring**: Logging infrastructure in place for production monitoring
- **GitHub Integration**: Ready for version control and collaborative development

### Scalability Approach
- **Modular Design**: Each utility can be independently scaled or replaced
- **Stateless API**: RESTful design allows for horizontal scaling
- **State Management**: Memory manager can be easily migrated to Redis or database for multi-instance support

## Recent Changes (July 30, 2025)
- **Architecture Migration**: Converted from Streamlit web app to FastAPI REST API
- **Railway Configuration**: Added railway.json, Procfile, and deployment configuration
- **API Key Integration**: Configured RapidAPI key for LinkedIn scraping functionality
- **JobSpy Integration**: Updated to use external JobSpy API (https://coogi-jobspy-production.up.railway.app/jobs) for real job data
- **Live Data Pipeline**: Configured to use real data until Hunter.io step, only email discovery in demo mode
- **Streamlit Web Interface**: Added user-friendly web UI on port 8501 for job search and message generation
- **GitHub Preparation**: Added comprehensive README.md, .gitignore, and documentation
- **Environment Setup**: Created .env.example for easy configuration management
- **Company Analysis System**: Added comprehensive company analyzer with TA team detection and job data integration
- **Skip Reporting**: Implemented detailed tracking of why companies are excluded from recruiting targets
- **Rate Limiting**: Added proper RapidAPI rate limiting (2+ second delays, adaptive timing, 429 error handling)
- **Decision Maker Scoring**: Implemented weighted scoring system (C-level=10, VP=8, Director=6, Manager=4)
- **Volume Optimization**: Focus on companies without internal talent acquisition teams for higher conversion rates

The architecture prioritizes modularity and maintainability while providing a clear upgrade path from demo to production deployment. The system is designed to handle the complete recruiting workflow from job discovery through successful candidate placement.