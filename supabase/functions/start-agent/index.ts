import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const API_BASE = 'https://coogi-2-production.up.railway.app'

interface AgentRequest {
  query: string
  hours_old: number
  enforce_salary: boolean
  auto_generate_messages: boolean
  create_campaigns: boolean
  campaign_name: string | null
  min_score: number
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    })
  }

  try {
    const { query, hours_old, enforce_salary, auto_generate_messages, create_campaigns, campaign_name, min_score }: AgentRequest = await req.json()

    // Validate required fields
    if (!query) {
      return new Response(
        JSON.stringify({ error: 'Query is required' }),
        { 
          status: 400,
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          }
        }
      )
    }

    // Start agent creation asynchronously using the city-by-city flow
    const agentPromise = fetch(`${API_BASE}/search-jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        hours_old: hours_old || 24,
        enforce_salary: enforce_salary ?? true,
        auto_generate_messages: auto_generate_messages ?? false,
        create_campaigns: create_campaigns ?? true,
        campaign_name: campaign_name || null,
        min_score: min_score || 0.5
      })
    })

    // Return immediately with a "processing" status
    return new Response(
      JSON.stringify({
        status: 'processing',
        message: 'Agent creation started',
        query,
        timestamp: new Date().toISOString()
      }),
      {
        status: 202,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      }
    )

  } catch (error) {
    console.error('Error in start-agent function:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to start agent',
        details: error.message 
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      }
    )
  }
}) 