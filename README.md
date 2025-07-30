# MCP: Master Control Program - Recruiting Automation API

A FastAPI-based recruiting automation platform that scrapes job postings, finds contact information, and generates personalized outreach messages.

## Features

- **Job Scraping**: Search multiple job boards (LinkedIn, Indeed, ZipRecruiter)
- **Contact Discovery**: Find hiring managers and decision makers using LinkedIn scraping
- **Email Generation**: Create personalized outreach messages using AI
- **Lead Scoring**: Intelligent scoring system to prioritize contacts
- **Memory Management**: Prevent duplicate outreach and track performance

## API Endpoints

### GET `/`
Health check endpoint with API status information

### POST `/search-jobs`
Search for jobs and generate leads
```json
{
  "query": "Find me software engineer jobs in San Francisco",
  "max_leads": 10,
  "hours_old": 24,
  "enforce_salary": true,
  "auto_generate_messages": false
}
```

### POST `/generate-message`
Generate personalized outreach message
```json
{
  "job_title": "Senior Software Engineer",
  "company": "TechCorp",
  "contact_title": "VP of Engineering",
  "job_url": "https://company.com/jobs/123",
  "tone": "professional",
  "additional_context": "Optional context"
}
```

### GET `/memory-stats`
Get memory and tracking statistics

### DELETE `/memory`
Clear all memory data

## Environment Variables

Create a `.env` file with the following variables:

```env
# Required for AI features
OPENAI_API_KEY=your_openai_api_key

# Required for LinkedIn scraping
RAPIDAPI_KEY=your_rapidapi_key

# Optional for email discovery
HUNTER_API_KEY=your_hunter_io_key

# Optional for email delivery
INSTANTLY_API_KEY=your_instantly_ai_key
```

## Railway Deployment

1. **Create Railway Project**
   ```bash
   railway login
   railway init
   railway up
   ```

2. **Set Environment Variables**
   In Railway dashboard, add:
   - `OPENAI_API_KEY`
   - `RAPIDAPI_KEY` 
   - `HUNTER_API_KEY` (optional)
   - `INSTANTLY_API_KEY` (optional)

3. **Deploy**
   The `railway.json` and `Procfile` are already configured.

## Local Development

1. **Install Dependencies**
   ```bash
   pip install -r pyproject.toml
   ```

2. **Set Environment Variables**
   ```bash
   export OPENAI_API_KEY="your_key"
   export RAPIDAPI_KEY="your_key"
   ```

3. **Run Server**
   ```bash
   python api.py
   ```

4. **Access API**
   - API: http://localhost:5000
   - Documentation: http://localhost:5000/docs

## API Keys Setup

### OpenAI API Key
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create account and navigate to API keys
3. Create new API key

### RapidAPI Key (LinkedIn Scraping)
1. Go to [rapidapi.com](https://rapidapi.com)
2. Subscribe to "LinkedIn Company Data" API
3. Copy your API key

### Hunter.io Key (Email Discovery)
1. Go to [hunter.io](https://hunter.io)
2. Create account and get API key
3. Add to environment variables

## Demo Mode

The application runs in demo mode when API keys are missing, using sample data for testing.

## Architecture

- **FastAPI**: Web framework for the API
- **Pydantic**: Data validation and serialization
- **OpenAI**: AI-powered query parsing and message generation
- **RapidAPI**: LinkedIn data scraping
- **Hunter.io**: Email address discovery
- **JobSpy**: Job posting aggregation

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## License

MIT License - see LICENSE file for details.