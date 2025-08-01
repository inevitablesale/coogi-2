import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const API_BASE = 'https://coogi-2-production.up.railway.app'

interface AgentRequest {
  query: string
  hours_old: number
  enforce_salary: boolean
  auto_generate_messages: boolean
  create_campaigns: boolean
  campaign_name?: string
  min_score?: number
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400',
      },
    })
  }

  try {
    // Parse request body
    const { query, hours_old, enforce_salary, auto_generate_messages, create_campaigns, campaign_name, min_score }: AgentRequest = await req.json()

    // Validate required fields
    if (!query) {
      return new Response(JSON.stringify({ error: 'Query is required' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        },
      })
    }

    // Forward request to Railway API
    const response = await fetch(`${API_BASE}/process-jobs-background`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        hours_old: hours_old || 24,
        enforce_salary: enforce_salary || false,
        auto_generate_messages: auto_generate_messages || false,
        create_campaigns: create_campaigns || true,
        campaign_name: campaign_name || `${query} Campaign`,
        min_score: min_score || 0.7
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      return new Response(JSON.stringify({ error: `Railway API error: ${response.status} - ${errorText}` }), {
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        },
      })
    }

    const result = await response.json()

    // Return the Railway API response
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    })

  } catch (error) {
    console.error('Edge Function error:', error)
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    })
  }
}) 