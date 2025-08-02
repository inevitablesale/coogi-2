import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const INSTANTLY_API_BASE = "https://api.instantly.ai/api/v2"

interface Contact {
  email: string
  first_name?: string
  last_name?: string
  company_name?: string
  website?: string
  phone?: string
  title?: string
  linkedin_url?: string
  personalization?: string
}

interface InstantlyLead {
  email: string
  first_name?: string
  last_name?: string
  company_name?: string
  website?: string
  phone?: string
  personalization?: string
  campaign?: string
  list_id?: string
}

interface MoveLeadsRequest {
  lead_ids: string[]
  campaign_id?: string
  list_id?: string
  search?: string
  filter?: string
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    })
  }

  try {
    const { contacts, campaign_id, list_id, action } = await req.json()

    // Validate required fields
    if (!contacts || !Array.isArray(contacts)) {
      return new Response(
        JSON.stringify({ error: 'Contacts array is required' }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      )
    }

    // Get Instantly API key from environment
    const instantlyApiKey = Deno.env.get('INSTANTLY_API_KEY')
    if (!instantlyApiKey) {
      return new Response(
        JSON.stringify({ error: 'INSTANTLY_API_KEY not configured' }),
        {
          status: 500,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      )
    }

    const headers = {
      'Authorization': `Bearer ${instantlyApiKey}`,
      'Content-Type': 'application/json',
    }

    let result

    if (action === 'create_leads') {
      // Create leads in Instantly
      result = await createLeads(contacts, campaign_id, list_id, headers)
    } else if (action === 'move_leads') {
      // Move existing leads to a campaign
      result = await moveLeads(contacts, campaign_id, list_id, headers)
    } else {
      return new Response(
        JSON.stringify({ error: 'Invalid action. Use "create_leads" or "move_leads"' }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      )
    }

    return new Response(
      JSON.stringify(result),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    )

  } catch (error) {
    console.error('Error in send-to-instantly edge function:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    )
  }
})

async function createLeads(contacts: Contact[], campaign_id?: string, list_id?: string, headers?: Record<string, string>) {
  const createdLeads = []
  const errors = []

  for (const contact of contacts) {
    try {
      // Prepare lead data for Instantly API
      const leadData: InstantlyLead = {
        email: contact.email,
        first_name: contact.first_name,
        last_name: contact.last_name,
        company_name: contact.company_name,
        website: contact.website,
        phone: contact.phone,
        personalization: contact.personalization,
      }

      // Add campaign or list ID if provided
      if (campaign_id) {
        leadData.campaign = campaign_id
      } else if (list_id) {
        leadData.list_id = list_id
      }

      // Create lead using Instantly API
      const response = await fetch(`${INSTANTLY_API_BASE}/leads`, {
        method: 'POST',
        headers,
        body: JSON.stringify(leadData),
      })

      if (response.ok) {
        const lead = await response.json()
        createdLeads.push({
          contact,
          lead_id: lead.id,
          status: 'created',
          lead_data: lead,
        })
      } else {
        const errorData = await response.json()
        errors.push({
          contact,
          error: errorData,
          status: 'failed',
        })
      }

      // Rate limiting - wait 100ms between requests
      await new Promise(resolve => setTimeout(resolve, 100))

    } catch (error) {
      errors.push({
        contact,
        error: error.message,
        status: 'failed',
      })
    }
  }

  return {
    success: true,
    created_leads: createdLeads,
    errors,
    summary: {
      total_contacts: contacts.length,
      created: createdLeads.length,
      failed: errors.length,
    },
  }
}

async function moveLeads(contacts: Contact[], campaign_id?: string, list_id?: string, headers?: Record<string, string>) {
  // For moving leads, we need lead IDs
  // This function assumes contacts have lead_id property or we need to find them by email
  const leadIds = []
  const errors = []

  for (const contact of contacts) {
    try {
      // If contact has a lead_id, use it directly
      if (contact.lead_id) {
        leadIds.push(contact.lead_id)
        continue
      }

      // Otherwise, try to find lead by email
      const searchResponse = await fetch(`${INSTANTLY_API_BASE}/leads?email=${encodeURIComponent(contact.email)}`, {
        method: 'GET',
        headers,
      })

      if (searchResponse.ok) {
        const searchResult = await searchResponse.json()
        if (searchResult.data && searchResult.data.length > 0) {
          leadIds.push(searchResult.data[0].id)
        } else {
          errors.push({
            contact,
            error: 'Lead not found by email',
            status: 'not_found',
          })
        }
      } else {
        errors.push({
          contact,
          error: 'Failed to search for lead',
          status: 'search_failed',
        })
      }

    } catch (error) {
      errors.push({
        contact,
        error: error.message,
        status: 'failed',
      })
    }
  }

  if (leadIds.length === 0) {
    return {
      success: false,
      error: 'No valid lead IDs found',
      errors,
    }
  }

  // Move leads to campaign or list
  try {
    const moveData: MoveLeadsRequest = {
      lead_ids: leadIds,
    }

    if (campaign_id) {
      moveData.campaign_id = campaign_id
    } else if (list_id) {
      moveData.list_id = list_id
    }

    const moveResponse = await fetch(`${INSTANTLY_API_BASE}/leads/move`, {
      method: 'POST',
      headers,
      body: JSON.stringify(moveData),
    })

    if (moveResponse.ok) {
      const moveResult = await moveResponse.json()
      return {
        success: true,
        moved_leads: leadIds.length,
        move_result: moveResult,
        errors,
        summary: {
          total_contacts: contacts.length,
          moved: leadIds.length,
          failed: errors.length,
        },
      }
    } else {
      const errorData = await moveResponse.json()
      return {
        success: false,
        error: errorData,
        errors,
      }
    }

  } catch (error) {
    return {
      success: false,
      error: error.message,
      errors,
    }
  }
} 