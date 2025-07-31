import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const API_BASE = 'https://coogi-2-production.up.railway.app'

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    })
  }

  try {
    const url = new URL(req.url)
    const batchId = url.searchParams.get('batch_id')
    const limit = url.searchParams.get('limit') || '100'

    if (!batchId) {
      return new Response(
        JSON.stringify({ error: 'batch_id is required' }),
        { 
          status: 400,
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          }
        }
      )
    }

    // Get agent logs from Railway backend
    const response = await fetch(`${API_BASE}/logs/${batchId}?limit=${limit}`)
    
    if (!response.ok) {
      return new Response(
        JSON.stringify({ error: 'Failed to get agent logs' }),
        { 
          status: response.status,
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          }
        }
      )
    }

    const logs = await response.json()

    return new Response(
      JSON.stringify(logs),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      }
    )

  } catch (error) {
    console.error('Error in get-agent-logs function:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to get agent logs',
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