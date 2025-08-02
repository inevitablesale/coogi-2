import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

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
  tags?: string[]
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
  tags?: string[]
  job_title?: string
  linkedin_url?: string
  custom_variables?: Record<string, any>
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
    const { batch_id, campaign_id, list_id, action, hunter_emails, company, job_title, domain } = await req.json()

    // Validate required fields
    if (!batch_id) {
      return new Response(
        JSON.stringify({ error: 'batch_id is required' }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      )
    }

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

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

    // Use hunter_emails from payload if provided, otherwise query database
    let hunterEmailsData = []
    console.log(`🔍 Debug: hunter_emails from payload:`, hunter_emails)
    console.log(`🔍 Debug: hunter_emails length:`, hunter_emails ? hunter_emails.length : 'undefined')
    console.log(`🔍 Debug: hunter_emails type:`, typeof hunter_emails)
    
    if (hunter_emails && hunter_emails.length > 0) {
      // Use emails from payload
      hunterEmailsData = [{
        company: company || 'Unknown',
        email_list: hunter_emails,
        domain: domain || null
      }]
      console.log(`📧 Using ${hunter_emails.length} emails from payload for ${company}`)
    } else {
      // Fallback to database query
      const { data: dbHunterEmailsData, error: supabaseError } = await supabase
        .from('hunter_emails')
        .select('*')
        .eq('batch_id', batch_id)

      if (supabaseError) {
        return new Response(
          JSON.stringify({ error: `Supabase error: ${supabaseError.message}` }),
          {
            status: 500,
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            },
          }
        )
      }

      if (!dbHunterEmailsData || dbHunterEmailsData.length === 0) {
        return new Response(
          JSON.stringify({ error: 'No hunter_emails data found for this batch' }),
          {
            status: 404,
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            },
          }
        )
      }
      
      hunterEmailsData = dbHunterEmailsData
      console.log(`📧 Using ${dbHunterEmailsData.length} records from database`)
    }

    // Extract contacts from hunter_emails data
    const contacts: Contact[] = []
    
    for (const record of hunterEmailsData) {
      const emailList = record.email_list || []
      
      for (const contact of emailList) {
        // Extract or generate first and last names
        let firstName = contact.first_name || ''
        let lastName = contact.last_name || ''
        
        // If names are null/empty, try to extract from full name
        if (!firstName && !lastName && contact.name) {
          const nameParts = contact.name.split(' ')
          if (nameParts.length >= 2) {
            firstName = nameParts[0]
            lastName = nameParts.slice(1).join(' ')
          } else if (nameParts.length === 1) {
            firstName = nameParts[0]
          }
        }
        
        // If still no names, try to extract from email
        if (!firstName && !lastName && contact.email) {
          const emailParts = contact.email.split('@')[0].split('.')
          if (emailParts.length >= 2) {
            firstName = emailParts[0].charAt(0).toUpperCase() + emailParts[0].slice(1)
            lastName = emailParts[1].charAt(0).toUpperCase() + emailParts[1].slice(1)
          } else {
            firstName = emailParts[0].charAt(0).toUpperCase() + emailParts[0].slice(1)
          }
        }
        
        // Final fallback: use "Unknown" names
        if (!firstName) firstName = 'Unknown'
        if (!lastName) lastName = 'Contact'
        
        // Use domain from Supabase record if available, otherwise generate from email
        let website = ''
        if (record.domain) {
          website = `https://${record.domain}`
        } else if (contact.email) {
          website = `https://${contact.email.split('@')[1]}`
        }
        
        contacts.push({
          email: contact.email || '',
          first_name: firstName,
          last_name: lastName,
          company_name: contact.company || record.company || '',
          website: website,
          title: contact.title || 'Hiring Manager',
          linkedin_url: contact.linkedin_url || '',
          tags: [
            `company:${contact.company || record.company || 'unknown'}`,
            `source:hunter_io`,
            `coogi_generated`
          ]
        })
      }
    }

    console.log(`📧 Found ${contacts.length} contacts from email_list data`)

    let result

    if (action === 'create_leads') {
      // Create leads in Instantly
      result = await createLeads(contacts, batch_id, campaign_id, list_id, headers)
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

async function createLeads(contacts: Contact[], batch_id: string, campaign_id?: string, list_id?: string, headers?: Record<string, string>) {
  const createdLeads: any[] = []
  const errors: any[] = []

  // First, we need to create or find a campaign for this agent
  let agentCampaignId = campaign_id
  if (!agentCampaignId) {
    // Get agent information from the batch_id
    const agentName = await getAgentName(batch_id)
    console.log(`🔍 Looking for campaign for agent: ${agentName}`)
    
    // Try to find existing campaign for this agent
    const existingCampaign = await findAgentCampaign(agentName, headers)
    
    if (existingCampaign) {
      agentCampaignId = existingCampaign.id
      console.log(`✅ Found existing campaign for agent: ${existingCampaign.name} (ID: ${agentCampaignId})`)
    } else {
      // Create a new campaign for this agent
      const campaignName = `Coogi Agent - ${agentName}`
      
      // Available email accounts to rotate through
      const emailAccounts = [
        "chuck@liacgroupagency.com",
        "chuck@liacgroupworkforce.com", 
        "chuck@liacworkforce.com",
        "cole@liacgroupagency.com",
        "cole@liacgroupworkforce.com",
        "cole@liacworkforce.com",
        "contact@liacgroupagency.com",
        "contact@liacgroupworkforce.com",
        "contact@liacworkforce.com"
      ]
      
      // Pick a random email account for this campaign
      const selectedEmail = emailAccounts[Math.floor(Math.random() * emailAccounts.length)]
      
      console.log(`🚀 Creating new campaign for agent: ${campaignName} with email: ${selectedEmail}`)
      
      const campaignResponse = await fetch(`${INSTANTLY_API_BASE}/campaigns`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: campaignName,
          campaign_schedule: {
            schedules: [
              {
                name: "Coogi Schedule",
                timing: {
                  from: "09:00",
                  to: "17:00"
                },
                days: {
                  0: true, // Monday
                  1: true, // Tuesday
                  2: true, // Wednesday
                  3: true, // Thursday
                  4: true, // Friday
                  5: false, // Saturday
                  6: false  // Sunday
                },
                timezone: "America/Chicago"
              }
            ],
            start_date: new Date().toISOString(),
            end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString() // 30 days from now
          },
          sequences: [
            {
              steps: [
                {
                  type: "email",
                  subject: "Opportunity at {{company_name}}",
                  body: `Hi {{first_name}},

I noticed your role as {{job_title}} at {{company_name}} and thought you might be interested in a new opportunity.

Would you be open to a brief conversation about potential roles that could be a great fit for your background?

Best regards,
{{sender_name}}`,
                  delay: 0,
                  variants: [
                    {
                      subject: "Opportunity at {{company_name}}",
                      body: `Hi {{first_name}},

I noticed your role as {{job_title}} at {{company_name}} and thought you might be interested in a new opportunity.

Would you be open to a brief conversation about potential roles that could be a great fit for your background?

Best regards,
{{sender_name}}`
                    }
                  ]
                }
              ]
            }
          ],
          email_list: [selectedEmail],
          daily_limit: 50,
          stop_on_reply: true,
          link_tracking: true,
          open_tracking: true
        })
      })
      
      if (campaignResponse.ok) {
        const campaignData = await campaignResponse.json()
        agentCampaignId = campaignData.id
        console.log(`✅ Created new campaign for agent: ${campaignName} (ID: ${agentCampaignId})`)
      } else {
        console.error(`❌ Failed to create campaign: ${campaignResponse.status}`)
        return {
          success: false,
          error: 'Failed to create campaign',
          created_leads: [],
          errors: []
        }
      }
    }
  }

  // Create leads first (without campaign assignment)
  const leadIds: string[] = []
  
  for (const contact of contacts) {
    try {
      // Check if lead already exists by email
      const existingLead = await findLeadByEmail(contact.email, headers)
      
      if (existingLead) {
        // Skip existing lead (Instantly.ai doesn't have a PUT endpoint)
        console.log(`⏭️ Skipping existing lead: ${contact.email} (ID: ${existingLead.id})`)
        leadIds.push(existingLead.id)
      } else {
        // Create new lead directly in the campaign
        console.log(`📝 Creating new lead: ${contact.email}`)

        // Generate better names if they're null or empty
        let firstName = contact.first_name || ''
        let lastName = contact.last_name || ''
        
        // If names are null/empty, try to extract from email
        if (!firstName && !lastName) {
          const email = contact.email || ''
          const username = email.split('@')[0] || ''
          
          if (username && username.length > 3) {
            // Try to extract name from email patterns like firstname.lastname@domain.com
            const nameParts = username.replace(/[._-]/g, ' ').split(' ')
              .filter(part => part.length > 1)
              .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
            
            if (nameParts.length >= 2) {
              firstName = nameParts[0]
              lastName = nameParts.slice(1).join(' ')
            } else if (nameParts.length === 1) {
              firstName = nameParts[0]
              lastName = ''
            }
          }
        }
        
        // Final fallback if still no names
        if (!firstName && !lastName) {
          firstName = 'Hiring'
          lastName = 'Manager'
        }

        // Format lead data with official Instantly.ai API fields
        const formattedLead: any = {
          email: contact.email,
          first_name: firstName,
          last_name: lastName,
          company_name: contact.company_name || '',
          phone: contact.phone || '',
          website: contact.website || '',
          personalization: contact.personalization || '',
          campaign: agentCampaignId // Assign directly to campaign
        }

        // Add custom fields for additional data
        const customFields: Record<string, any> = {}
        
        // Add LinkedIn URL as custom field
        if (contact.linkedin_url) {
          customFields.linkedin_url = contact.linkedin_url
        }
        
        // Add job title as custom field
        if (contact.title) {
          customFields.job_title = contact.title
        }
        
        // Add custom fields if we have any
        if (Object.keys(customFields).length > 0) {
          formattedLead.custom_variables = customFields
        }

        // Add tags if supported by the API
        if (contact.tags && contact.tags.length > 0) {
          formattedLead.tags = [
            `agent:coogi`,
            `batch:${new Date().toISOString().split('T')[0]}`,
            `company:${contact.company_name || 'unknown'}`,
            `source:hunter_io`,
            `coogi_generated`
          ]
        }

        // Create lead using Instantly API
        const response = await fetch(`${INSTANTLY_API_BASE}/leads`, {
          method: 'POST',
          headers,
          body: JSON.stringify(formattedLead),
        })

        if (response.ok) {
          const lead = await response.json()
          createdLeads.push({
            contact,
            lead_id: lead.id,
            status: 'created',
            lead_data: lead,
          })
          leadIds.push(lead.id)
          console.log(`✅ Created lead: ${contact.email} (ID: ${lead.id})`)
        } else {
          const errorData = await response.json()
          errors.push({
            contact,
            error: errorData,
            status: 'failed',
          })
          console.error(`❌ Failed to create lead ${contact.email}: ${response.status} - ${JSON.stringify(errorData)}`)
        }
      }

      // Rate limiting - wait 100ms between requests
      await new Promise(resolve => setTimeout(resolve, 100))

    } catch (error: any) {
      errors.push({
        contact,
        error: error.message,
        status: 'failed',
      })
      console.error(`❌ Error processing lead ${contact.email}: ${error.message}`)
    }
  }

  // Leads are now created directly in the campaign, no need to move them
  console.log(`✅ Created ${createdLeads.length} leads directly in campaign ${agentCampaignId}`)

  return {
    success: true,
    created_leads: createdLeads,
    errors,
    summary: {
      total_contacts: contacts.length,
      created: createdLeads.length,
      skipped: contacts.length - createdLeads.length - errors.length,
      failed: errors.length,
      campaign_id: agentCampaignId
    },
  }
}

async function findLeadByEmail(email: string, headers?: Record<string, string>): Promise<any | null> {
  try {
    // Search for lead by email using the list endpoint
    const response = await fetch(`${INSTANTLY_API_BASE}/leads/list`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        search: email,
        limit: 10
      })
    })

    if (response.ok) {
      const data = await response.json()
      const leads = data.items || []
      
      // Find exact email match
      const exactMatch = leads.find((lead: any) => 
        lead.email && lead.email.toLowerCase() === email.toLowerCase()
      )
      
      return exactMatch || null
    }
    
    return null
  } catch (error) {
    console.error(`❌ Error finding lead by email ${email}: ${error}`)
    return null
  }
}

async function getAgentName(batch_id: string): Promise<string> {
  try {
    // Get agent information from Supabase
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )
    
    // First try to get agent from agents table
    const agentResponse = await supabase
      .from('agents')
      .select('prompt, name')
      .eq('batch_id', batch_id)
      .single()
    
    if (agentResponse.data) {
      // First try to use the agent name if it exists
      const agentName = agentResponse.data.name
      if (agentName && agentName.trim()) {
        // Extract the actual name from "Agent: {name}..."
        const nameMatch = agentName.match(/Agent:\s*(.+?)(?:\.\.\.)?$/)
        if (nameMatch && nameMatch[1]) {
          const extractedName = nameMatch[1].trim()
          console.log(`📝 Using agent name: ${extractedName}`)
          return extractedName
        } else {
          console.log(`📝 Using full agent name: ${agentName}`)
          return agentName.trim()
        }
      }
      
      // Fallback to extracting from prompt
      const prompt = agentResponse.data.prompt || ''
      if (prompt) {
        // Extract the first meaningful word from the prompt
        const words = prompt.split(' ')
          .filter(word => word.length > 2) // Filter out short words
          .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()) // Capitalize first letter
        
        if (words.length > 0) {
          const agentName = words[0] // Use the first meaningful word
          console.log(`📝 Using prompt-based name: ${agentName} (from prompt: "${prompt}")`)
          return agentName
        }
      }
    }
    
    // If no agent found, try to get query from hunter_emails table
    console.log(`🔍 Agent not found in agents table, checking hunter_emails...`)
    const hunterResponse = await supabase
      .from('hunter_emails')
      .select('query')
      .eq('batch_id', batch_id)
      .limit(1)
      .single()
    
    if (hunterResponse.data && hunterResponse.data.query) {
      const query = hunterResponse.data.query
      // Extract the first meaningful word from the query
      const words = query.split(' ')
        .filter(word => word.length > 2) // Filter out short words
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()) // Capitalize first letter
      
      if (words.length > 0) {
        const agentName = words[0] // Use the first meaningful word
        console.log(`📝 Using hunter_emails query-based name: ${agentName} (from query: "${query}")`)
        return agentName
      }
    }
    
    // Final fallback: use last 8 characters of batch_id
    const fallbackName = `Agent-${batch_id.slice(-8)}`
    console.log(`📝 Using fallback name: ${fallbackName}`)
    return fallbackName
  } catch (error) {
    console.error(`❌ Error getting agent name: ${error}`)
    // Fallback: use last 8 characters of batch_id
    const fallbackName = `Agent-${batch_id.slice(-8)}`
    console.log(`📝 Using fallback name: ${fallbackName}`)
    return fallbackName
  }
}

async function findAgentCampaign(agentName: string, headers?: Record<string, string>): Promise<any | null> {
  try {
    // Get all campaigns and look for one with this agent name
    const response = await fetch(`${INSTANTLY_API_BASE}/campaigns`, {
      method: 'GET',
      headers
    })

    if (response.ok) {
      const data = await response.json()
      const campaigns = data.campaigns || []
      
      // Look for a campaign with this agent name
      const agentCampaign = campaigns.find((campaign: any) => 
        campaign.name && 
        campaign.name.includes('Coogi Agent') &&
        campaign.name.includes(agentName)
      )
      
      if (agentCampaign) {
        console.log(`🔍 Found existing agent campaign: ${agentCampaign.name} (created: ${agentCampaign.created_at})`)
      } else {
        console.log(`🔍 No existing agent campaign found for: ${agentName}`)
      }
      
      return agentCampaign || null
    }
    
    return null
  } catch (error) {
    console.error(`❌ Error finding agent campaign: ${error}`)
    return null
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