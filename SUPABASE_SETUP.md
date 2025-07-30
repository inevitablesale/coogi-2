# Supabase Setup Guide

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and anon key

## 2. Environment Variables

Add these to your `.env` file:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

## 3. Database Tables

Create these tables in your Supabase SQL editor:

### Batches Table
```sql
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_id TEXT UNIQUE NOT NULL,
    summary JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'processing'
);
```

### Company Analysis Table
```sql
CREATE TABLE company_analysis (
    id SERIAL PRIMARY KEY,
    batch_id TEXT REFERENCES batches(batch_id),
    company TEXT NOT NULL,
    job_title TEXT,
    job_url TEXT,
    has_ta_team BOOLEAN DEFAULT FALSE,
    contacts_found INTEGER DEFAULT 0,
    top_contacts JSONB,
    recommendation TEXT,
    hunter_emails JSONB DEFAULT '[]',
    instantly_campaign_id TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 4. Install Dependencies

```bash
pip install supabase httpx
```

## 5. Test Integration

The API will automatically:
- ✅ Store batch results in Supabase
- ✅ Store individual company analysis
- ✅ Provide endpoints to query results
- ✅ Work without Supabase (graceful fallback)

## 6. Available Endpoints

- `GET /batch/{batch_id}` - Get specific batch results
- `GET /batches` - Get all batches with pagination
- `GET /companies/target` - Get target companies (no TA team)
- `POST /webhook/results` - Receive webhook results
- `POST /process-jobs-background` - Start background processing

## 7. Production Deployment

For production, update the webhook URL in `send_webhook()`:

```python
webhook_url = "https://your-domain.com/webhook/results"
```

The app is now ready for Supabase integration! 🚀 