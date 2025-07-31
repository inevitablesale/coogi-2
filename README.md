# MindGlimpse - Automated Recruiting Platform

An intelligent job search and lead generation platform that automatically finds, analyzes, and reaches out to potential clients.

## Features

- **Multi-City Job Search**: Searches across 55 major US cities
- **Intelligent Blacklisting**: Automatically skips companies with internal TA teams
- **Lead Generation**: Finds decision-makers and their contact information
- **Email Campaigns**: Integrates with Instantly.ai for automated outreach
- **Rate Limiting**: Optimized API calls with proper delays
- **Real-time Analysis**: Web search for accurate company data

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the server:
```bash
python api.py
```

### Railway Deployment

The app is configured for Railway deployment with:
- `railway.json` - Railway configuration
- `Procfile` - Process definition
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification

## API Endpoints

- `GET /` - Health check
- `POST /search-jobs` - Main job search endpoint
- `POST /analyze-companies` - Company analysis
- `GET /blacklist` - Blacklist management
- `POST /create-instantly-campaign` - Campaign creation

## Environment Variables

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `RAPIDAPI_KEY` - RapidAPI key
- `HUNTER_API_KEY` - Hunter.io API key
- `INSTANTLY_API_KEY` - Instantly.ai API key
- `CLEAROUT_API_KEY` - Clearout API key

## Rate Limiting

The system includes intelligent rate limiting:
- 5-second delays between JobSpy API calls
- Batch processing for RapidAPI calls
- Memory management to prevent duplicate processing 