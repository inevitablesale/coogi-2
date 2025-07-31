# Lead Lists Design - Company Type Based Organization

## Overview
We organize leads into persistent lists by company type for better campaign targeting and management.

## Lead List Categories

### 1. **Tech_Startups_Leads**
- **Target Companies**: Startups, tech companies, AI/ML, SaaS, digital platforms
- **Keywords**: startup, tech, ai, software, digital, app, platform, saas, api, cloud, data, analytics, machine learning, ml, artificial intelligence
- **Campaign Focus**: Innovation, growth, technical roles, remote work
- **Example Companies**: Stripe, OpenAI, Notion, Figma, Zoom

### 2. **Established_Companies_Leads**
- **Target Companies**: Large corporations, enterprises, established businesses
- **Keywords**: inc, corp, llc, ltd, company, enterprise, corporation, industries, group, holdings, partners
- **Campaign Focus**: Stability, benefits, career growth, established processes
- **Example Companies**: Microsoft, Apple, Google, Amazon, Salesforce

### 3. **Agencies_Consulting_Leads**
- **Target Companies**: Consulting firms, agencies, service providers
- **Keywords**: agency, consulting, services, advisory, partners, solutions, strategies, management
- **Campaign Focus**: Project-based work, client variety, consulting expertise
- **Example Companies**: McKinsey, Deloitte, Accenture, BCG

### 4. **Healthcare_Leads**
- **Target Companies**: Healthcare, medical, biotech, wellness companies
- **Keywords**: health, medical, pharma, biotech, healthcare, hospital, clinic, therapy, wellness, fitness, dental, veterinary
- **Campaign Focus**: Healthcare innovation, patient care, medical technology
- **Example Companies**: Moderna, Pfizer, Mayo Clinic, CVS Health

### 5. **Financial_Services_Leads**
- **Target Companies**: Banks, insurance, investment, fintech companies
- **Keywords**: finance, bank, insurance, wealth, investment, capital, credit, lending, mortgage, trading, asset, fund
- **Campaign Focus**: Financial stability, regulatory compliance, fintech innovation
- **Example Companies**: Goldman Sachs, JPMorgan, State Farm, Robinhood

### 6. **Education_Leads**
- **Target Companies**: Schools, universities, edtech, training companies
- **Keywords**: education, learning, school, university, college, academy, training, edtech, tutoring, curriculum
- **Campaign Focus**: Education technology, student impact, learning innovation
- **Example Companies**: Coursera, Udemy, Khan Academy, Harvard

### 7. **Retail_Consumer_Leads**
- **Target Companies**: Retail, ecommerce, consumer brands, hospitality
- **Keywords**: retail, ecommerce, store, shop, marketplace, consumer, brand, fashion, food, restaurant, hospitality
- **Campaign Focus**: Customer experience, retail innovation, consumer trends
- **Example Companies**: Amazon, Walmart, Nike, Starbucks

### 8. **Manufacturing_Industrial_Leads**
- **Target Companies**: Manufacturing, industrial, logistics companies
- **Keywords**: manufacturing, industrial, factory, production, supply chain, logistics, warehouse, distribution, automotive, construction
- **Campaign Focus**: Industrial innovation, supply chain optimization, manufacturing efficiency
- **Example Companies**: Tesla, Boeing, Caterpillar, FedEx

### 9. **Media_Entertainment_Leads**
- **Target Companies**: Media, entertainment, gaming, creative companies
- **Keywords**: media, entertainment, gaming, publishing, broadcasting, streaming, content, creative, design, advertising, marketing
- **Campaign Focus**: Creative work, content creation, entertainment innovation
- **Example Companies**: Netflix, Disney, Spotify, EA Games

### 10. **Real_Estate_Construction_Leads**
- **Target Companies**: Real estate, construction, infrastructure companies
- **Keywords**: real estate, property, development, construction, architecture, engineering, infrastructure, utilities, energy
- **Campaign Focus**: Real estate technology, construction innovation, infrastructure development
- **Example Companies**: Zillow, WeWork, Bechtel, CBRE

### 11. **Nonprofit_Government_Leads**
- **Target Companies**: Nonprofits, government, social impact organizations
- **Keywords**: nonprofit, foundation, charity, ngo, government, public, social, community, advocacy
- **Campaign Focus**: Social impact, public service, mission-driven work
- **Example Companies**: Red Cross, UNICEF, World Bank, local governments

### 12. **Other_Companies_Leads**
- **Target Companies**: Companies that don't fit other categories
- **Keywords**: None specific (catch-all)
- **Campaign Focus**: General recruiting, diverse opportunities
- **Example Companies**: Various companies not fitting other categories

## Benefits of This Design

### ✅ **Targeted Campaigns**
- Each list gets campaigns tailored to that industry
- Email templates can be industry-specific
- Subject lines can reference industry trends

### ✅ **Better Organization**
- Easy to see which industries have the most leads
- Can prioritize campaigns by industry
- Clear separation of different company types

### ✅ **Scalable Management**
- Lists grow over time with more leads
- Can create industry-specific campaigns
- Easy to track performance by industry

### ✅ **Flexible Targeting**
- Can run campaigns for specific industries
- Can exclude certain industries if needed
- Can prioritize high-value industries

## Implementation

### Lead List Creation
- Lists are created automatically when first lead of that type is found
- Lists persist across multiple searches
- New leads are added to existing lists

### Campaign Strategy
- Each company type gets its own campaign
- Campaigns can be customized by industry
- Email templates can be industry-specific

### Management
- API endpoints to view all lists
- Cleanup functionality for old lists
- Easy to see which industries are most active

## Example Flow

1. **Search 1**: "Python developers in San Francisco"
   - Creates `Tech_Startups_Leads` with 3 leads
   - Creates `Established_Companies_Leads` with 2 leads

2. **Search 2**: "Marketing managers in New York"
   - Adds 2 leads to `Agencies_Consulting_Leads`
   - Adds 1 lead to `Media_Entertainment_Leads`

3. **Search 3**: "Data scientists in Boston"
   - Adds 4 leads to `Tech_Startups_Leads` (now has 7 total)
   - Adds 1 lead to `Healthcare_Leads`

This creates a growing, organized database of leads by industry! 🎯 