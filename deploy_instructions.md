# Railway Deployment Instructions

## Quick Deploy to Railway

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Deploy from GitHub**
   - Push this code to GitHub repository
   - In Railway dashboard, click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Set Environment Variables**
   In Railway project settings, add these variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   RAPIDAPI_KEY=9fc749430dmsh203a8a9d7a08955p1eec7djsnb30f69ff59c7
   HUNTER_API_KEY=your_hunter_io_key (optional)
   INSTANTLY_API_KEY=your_instantly_ai_key (optional)
   ```

4. **Deploy**
   - Railway will automatically detect the configuration
   - Build and deployment will start automatically
   - Your API will be available at `https://your-app-name.railway.app`

## API Endpoints Available

- **GET /** - Health check and API status
- **POST /search-jobs** - Search for jobs and generate leads
- **POST /generate-message** - Generate personalized outreach messages
- **GET /memory-stats** - View system statistics
- **DELETE /memory** - Clear system memory

## API Keys Still Needed

To get full functionality, obtain these API keys:

### 1. OpenAI API Key (Required for AI features)
- Go to [platform.openai.com](https://platform.openai.com)
- Create account → API keys → Create new key
- Add as `OPENAI_API_KEY` environment variable

### 2. Hunter.io API Key (Optional - for email discovery)
- Go to [hunter.io](https://hunter.io)
- Sign up → API → Get API key
- Add as `HUNTER_API_KEY` environment variable

### 3. Instantly.ai API Key (Optional - for email delivery)
- Go to [instantly.ai](https://instantly.ai)
- Sign up → API settings → Get API key
- Add as `INSTANTLY_API_KEY` environment variable

## Current Status

✅ **RapidAPI Key**: Already configured for LinkedIn scraping
✅ **JobSpy Integration**: Using external API for real job data
✅ **FastAPI Setup**: Complete REST API with documentation
✅ **Railway Config**: Deployment files ready

The platform will work in demo mode without optional API keys, but full functionality requires OpenAI API key.

## Testing the Deployment

Once deployed, test your API:

```bash
# Health check
curl https://your-app.railway.app/

# Search for jobs
curl -X POST "https://your-app.railway.app/search-jobs" \
  -H "Content-Type: application/json" \
  -d '{"query": "software engineer", "max_leads": 5}'
```

## Next Steps

1. Deploy to Railway
2. Add OpenAI API key for full AI functionality
3. Test all endpoints
4. Set up monitoring and analytics
5. Scale based on usage