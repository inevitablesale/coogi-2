# MindGlimpse - Intelligent Job Search & Lead Generation Platform

An advanced automated recruiting platform that intelligently searches for jobs, analyzes companies, and generates targeted leads for outreach campaigns.

## 🚀 Features

### Core Capabilities
- **Multi-City Job Search**: Searches across 55 major US cities simultaneously
- **Intelligent Company Analysis**: Web search for real-time company data and employee counts
- **Smart Blacklisting**: Automatically skips companies with internal TA teams or >100 employees
- **Lead Generation**: Finds decision-makers and their contact information via LinkedIn
- **Email Campaign Integration**: Seamless integration with Instantly.ai for automated outreach
- **Rate Limiting**: Optimized API calls with intelligent delays and batch processing
- **Memory Management**: Prevents duplicate processing and API calls

### Technical Features
- **FastAPI Backend**: High-performance async API with automatic documentation
- **Railway Deployment**: Production-ready deployment configuration
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Error Handling**: Robust error handling with retry logic
- **Environment Management**: Secure API key management

## 📋 Prerequisites

- Python 3.11+
- Railway account (for deployment)
- API keys for external services

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/inevitablesale/coogi-2.git
cd coogi-2
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file with your API keys:
```env
# Required API Keys
OPENAI_API_KEY=your_openai_api_key
RAPIDAPI_KEY=your_rapidapi_key
HUNTER_API_KEY=your_hunter_api_key
INSTANTLY_API_KEY=your_instantly_api_key
CLEAROUT_API_KEY=your_clearout_api_key

# Optional (for database features)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

### 4. Local Development
```bash
python api.py
```
The API will be available at `http://localhost:8000`

## 🚀 Deployment

### Railway Deployment (Recommended)

1. **Connect to Railway**:
   ```bash
   railway login
   railway link
   ```

2. **Set Environment Variables**:
   - Go to Railway dashboard
   - Add all required environment variables
   - Deploy the application

3. **Deploy**:
   ```bash
   railway up
   ```

The application will be automatically deployed and available at your Railway URL.

### Manual Deployment
The project includes all necessary deployment files:
- `railway.json` - Railway configuration
- `Procfile` - Process definition
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification

## 📚 API Documentation

### Production API
**Live API**: [https://coogi-2-production.up.railway.app](https://coogi-2-production.up.railway.app)

**Status**: ✅ All services operational
- OpenAI: ✅ Connected
- RapidAPI: ✅ Connected  
- Hunter.io: ✅ Connected
- Instantly.ai: ✅ Connected
- JobSpy_API: ✅ Connected

### Base URLs
```
Production: https://coogi-2-production.up.railway.app
Local: http://localhost:8000
```

### Core Endpoints

#### Health Check
```http
GET /
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-31T10:22:55.918362",
  "api_status": {
    "OpenAI": true,
    "RapidAPI": true,
    "Hunter.io": true,
    "Instantly.ai": true,
    "JobSpy_API": true
  },
  "demo_mode": false
}
```

#### Job Search
```http
POST /search-jobs
```
**Request Body:**
```json
{
  "query": "software engineer",
  "hours_old": 24,
  "create_campaigns": false
}
```
**Response:**
```json
{
  "status": "success",
  "message": "Job search completed",
  "data": {
    "total_jobs": 15,
    "jobs": [
      {
        "title": "Senior Software Engineer",
        "company": "Tech Corp",
        "location": "San Francisco, CA",
        "job_url": "https://example.com/job",
        "company_website": "techcorp.com",
        "description": "Job description...",
        "salary": "$120k-$150k",
        "job_type": "fulltime",
        "is_remote": true
      }
    ]
  }
}
```

#### Company Analysis
```http
POST /analyze-companies
```
**Request Body:**
```json
{
  "companies": [
    {
      "name": "Tech Corp",
      "website": "techcorp.com"
    }
  ]
}
```

#### Message Generation
```http
POST /generate-message
```
**Request Body:**
```json
{
  "company_name": "Tech Corp",
  "contact_name": "John Doe",
  "job_title": "Senior Software Engineer",
  "template_type": "outreach"
}
```

#### Debug Environment Variables
```http
GET /debug/env
```
Returns current environment variable status for debugging.

### Additional Endpoints
- `POST /analyze-contract-opportunities` - Contract analysis
- `POST /create-instantly-campaign` - Campaign creation
- `POST /blacklist/add` - Add companies to blacklist
- `GET /blacklist` - View blacklisted companies

## 🔧 Configuration

### Rate Limiting
The system implements intelligent rate limiting:
- **JobSpy API**: 5-second delays between calls
- **RapidAPI**: Batch processing to stay within 20 requests/minute limit
- **OpenAI**: Optimized batch analysis for multiple companies

### Search Parameters
- `query`: Job search term (e.g., "software engineer", "nurse")
- `hours_old`: How far back to search (1, 24, 168, 720 hours)
- `location`: Specific city or "United States" for nationwide search
- `create_campaigns`: Whether to create Instantly.ai campaigns

### Blacklisting Rules
Companies are automatically blacklisted if:
- They have >100 employees (configurable)
- They have dedicated Talent Acquisition teams
- They're already processed in current session

## 🏗️ Architecture

### Core Components

#### 1. Job Scraper (`utils/job_scraper.py`)
- Handles JobSpy API integration
- Multi-city search across 55 US cities
- Rate limiting and error handling
- Domain finding via Clearout API

#### 2. Contact Finder (`utils/contact_finder.py`)
- LinkedIn company and people scraping
- Hunter.io email discovery
- OpenAI-powered company analysis
- Web search for real-time data

#### 3. Memory Manager (`utils/memory_manager.py`)
- Prevents duplicate processing
- Session-based caching
- Blacklist management

#### 4. Instantly Manager (`utils/instantly_manager.py`)
- Campaign creation and management
- Lead list management
- Email campaign automation

### Data Flow
1. **Job Search**: Query parsed → Multi-city search → Job collection
2. **Company Analysis**: Unique companies → Batch OpenAI analysis → Size/TA team detection
3. **Lead Generation**: Non-blacklisted companies → LinkedIn scraping → Contact discovery
4. **Campaign Creation**: Qualified leads → Instantly.ai integration → Email campaigns

## 🎨 Frontend Integration with Supabase

### Quick Start for Frontend Developers

This section provides complete instructions for connecting your frontend application (React/Next.js) with Supabase to the production MindGlimpse API.

#### 1. Environment Setup

Create a `.env.local` file in your frontend project:

```env
# Production Backend API (Recommended)
NEXT_PUBLIC_API_BASE_URL=https://coogi-2-production.up.railway.app

# Local development (optional)
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

#### 2. API Client Setup

Create `lib/api-client.js`:

```javascript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Health check
  async checkHealth() {
    return this.request('/');
  }

  // Job search
  async searchJobs(params) {
    return this.request('/search-jobs', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Company analysis
  async analyzeCompanies(companies) {
    return this.request('/analyze-companies', {
      method: 'POST',
      body: JSON.stringify({ companies }),
    });
  }

  // Generate messages
  async generateMessage(params) {
    return this.request('/generate-message', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }
}

export const apiClient = new ApiClient();
```

#### 3. Supabase Database Schema

Run this SQL in your Supabase SQL editor:

```sql
-- Job searches table
CREATE TABLE IF NOT EXISTS job_searches (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id),
  query TEXT NOT NULL,
  hours_old INTEGER DEFAULT 24,
  total_jobs INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  results JSONB
);

-- Job results table
CREATE TABLE IF NOT EXISTS job_results (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  search_id UUID REFERENCES job_searches(id),
  title TEXT,
  company TEXT,
  location TEXT,
  job_url TEXT,
  company_website TEXT,
  description TEXT,
  salary TEXT,
  job_type TEXT,
  is_remote BOOLEAN,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE job_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_results ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own searches" ON job_searches
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own searches" ON job_searches
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own job results" ON job_results
  FOR SELECT USING (
    auth.uid() = (
      SELECT user_id FROM job_searches WHERE id = job_results.search_id
    )
  );

CREATE POLICY "Users can insert their own job results" ON job_results
  FOR INSERT WITH CHECK (
    auth.uid() = (
      SELECT user_id FROM job_searches WHERE id = job_results.search_id
    )
  );
```

#### 4. React Component Example

```jsx
// components/JobSearch.jsx
import { useState } from 'react';
import { apiClient } from '../lib/api-client';
import { supabase } from '../lib/supabase';

export default function JobSearch() {
  const [query, setQuery] = useState('');
  const [hoursOld, setHoursOld] = useState(24);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    setIsSearching(true);
    setError(null);

    try {
      // Check API health first
      const health = await apiClient.checkHealth();
      console.log('API Health:', health);

      // Perform job search using production API
      const searchResults = await apiClient.searchJobs({
        query,
        hours_old: hoursOld,
        create_campaigns: false,
      });

      // Store in Supabase
      const { data: user } = await supabase.auth.getUser();
      if (user?.user) {
        const { data: searchRecord } = await supabase
          .from('job_searches')
          .insert({
            user_id: user.user.id,
            query,
            hours_old: hoursOld,
            total_jobs: searchResults.data?.total_jobs || 0,
            status: 'completed',
            completed_at: new Date().toISOString(),
            results: searchResults.data,
          })
          .select()
          .single();

        // Store individual job results
        if (searchResults.data?.jobs) {
          const jobRecords = searchResults.data.jobs.map(job => ({
            search_id: searchRecord.id,
            title: job.title,
            company: job.company,
            location: job.location,
            job_url: job.job_url,
            company_website: job.company_website,
            description: job.description,
            salary: job.salary,
            job_type: job.job_type,
            is_remote: job.is_remote,
          }));

          await supabase.from('job_results').insert(jobRecords);
        }
      }

      setResults(searchResults);
    } catch (err) {
      setError(err.message);
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Job Search</h1>
      
      <form onSubmit={handleSearch} className="mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Job Query
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., software engineer, nurse, marketing manager"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">
              Hours Old
            </label>
            <select
              value={hoursOld}
              onChange={(e) => setHoursOld(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value={1}>Last Hour</option>
              <option value={24}>Last 24 Hours</option>
              <option value={168}>Last Week</option>
              <option value={720}>Last Month</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <button
              type="submit"
              disabled={isSearching}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSearching ? 'Searching...' : 'Search Jobs'}
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {results && (
        <div>
          <h2 className="text-2xl font-semibold mb-4">
            Results ({results.data?.total_jobs || 0} jobs found)
          </h2>
          
          <div className="grid gap-4">
            {results.data?.jobs?.map((job, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold">{job.title}</h3>
                <p className="text-gray-600">{job.company}</p>
                <p className="text-gray-500">{job.location}</p>
                {job.salary && (
                  <p className="text-green-600 font-medium">{job.salary}</p>
                )}
                <div className="flex gap-2 mt-2">
                  {job.is_remote && (
                    <span className="px-2 py-1 bg-green-100 text-green-800 text-sm rounded">
                      Remote
                    </span>
                  )}
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                    {job.job_type}
                  </span>
                </div>
                {job.job_url && (
                  <a
                    href={job.job_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block text-blue-600 hover:underline"
                  >
                    View Job →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

#### 5. Testing the Integration

```javascript
// Test API connectivity
const health = await apiClient.checkHealth();
console.log('Production API Status:', health.api_status);

// Test job search (note: this may take 2-5 minutes for comprehensive search)
const results = await apiClient.searchJobs({
  query: 'software engineer',
  hours_old: 24,
  create_campaigns: false,
});
console.log('Search Results:', results);
```

#### 6. Important Notes

- **Search Duration**: Job searches across 55 US cities may take 2-5 minutes to complete
- **Rate Limiting**: The API includes intelligent rate limiting to respect external service limits
- **Error Handling**: Implement proper error handling and loading states in your frontend
- **CORS**: The production API supports CORS for frontend applications

## 🔍 Usage Examples

### Basic Job Search
```bash
curl -X POST "https://coogi-2-production.up.railway.app/search-jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "software engineer",
    "hours_old": 24,
    "create_campaigns": false
  }'
```

### Search for Recent Nursing Jobs
   ```bash
curl -X POST "https://coogi-2-production.up.railway.app/search-jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "nurse",
    "hours_old": 1,
    "create_campaigns": false
  }'
```

### Company Analysis
   ```bash
curl -X POST "https://coogi-2-production.up.railway.app/analyze-companies" \
  -H "Content-Type: application/json" \
  -d '{
    "companies": [
      {
        "name": "Google",
        "website": "google.com"
      }
    ]
  }'
```

## 🧪 Testing

### Local Testing
   ```bash
# Start the API
   python api.py
   
# Test health endpoint
curl http://localhost:8000/

# Test job search
curl -X POST "http://localhost:8000/search-jobs" \
  -H "Content-Type: application/json" \
  -d '{"query": "nurse", "hours_old": 1}'
```

### Test Scripts
- `test_api.py` - API endpoint testing
- `test_jobspy.py` - JobSpy integration testing
- `test_startup.py` - Basic import and startup testing

## 🔧 Troubleshooting

### Common Issues

#### 1. API Keys Not Recognized
- Check environment variables in Railway dashboard
- Verify `.env` file for local development
- Use `/debug/env` endpoint to verify

#### 2. JobSpy API Timeouts
- System includes automatic retry logic
- Check network connectivity
- Verify JobSpy API status

#### 3. Rate Limiting Issues
- System automatically handles rate limits
- Check logs for rate limit messages
- Increase delays if needed

#### 4. Deployment Issues
- Verify all environment variables are set
- Check Railway logs for errors
- Ensure `requirements.txt` is up to date

### Debug Endpoints
- `GET /` - Health check with API status
- `GET /debug/env` - Environment variable status
- Check application logs for detailed error information

## 📊 Monitoring

### Health Checks
The system provides comprehensive health monitoring:
- API connectivity status
- External service availability
- Environment variable validation

### Logging
Detailed logging includes:
- Job search progress
- API call status
- Error tracking
- Performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Test with the debug endpoints
4. Create an issue on GitHub

## 🔄 Recent Updates

### Latest Changes
- ✅ Removed proxy system for improved reliability
- ✅ Simplified JobSpy API calls with direct connections
- ✅ Enhanced error handling and logging
- ✅ Optimized rate limiting and batch processing
- ✅ Improved domain finding and company analysis

### Performance Improvements
- Reduced API call complexity
- Improved error recovery
- Enhanced logging for debugging
- Streamlined deployment process

---

**MindGlimpse** - Intelligent job search and lead generation for modern recruiting. 