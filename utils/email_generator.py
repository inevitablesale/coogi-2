import os
import json
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class EmailGenerator:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
        if not self.openai_client:
            logger.warning("🚫 OpenAI API key not found - message generation unavailable")
    
    def generate_outreach(self, job_title: str, company: str, contact_title: str, job_url: str, 
                         tone: str = "professional", additional_context: str = "") -> str:
        """Generate personalized outreach message using OpenAI only"""
        if not self.openai_client:
            logger.error(f"🚫 MESSAGE GENERATION UNAVAILABLE: OpenAI API key required for {job_title} at {company}")
            return ""
        
        try:
            return self._generate_ai_message(job_title, company, contact_title, job_url, tone, additional_context)
        except Exception as e:
            logger.error(f"Error generating AI message: {e}")
            return ""
    

    
    def _generate_ai_message(self, job_title: str, company: str, contact_title: str, 
                            job_url: str, tone: str, additional_context: str) -> str:
        """Generate personalized outreach message using advanced prompt engineering"""
        system_prompt = f"""
        You are an expert recruiter with 10+ years of experience in executive outreach and talent acquisition. You specialize in crafting high-conversion cold emails that decision makers actually respond to.
        
        ROLE: Generate a {tone} outreach message targeting a {contact_title} at {company}.
        
        CONTEXT: You've identified this company doesn't have an internal talent acquisition team, making them a high-conversion opportunity for external recruiting services.
        
        PROVEN EMAIL STRUCTURE:
        1. Personalized opening (mention their role/company specifically)
        2. Brief credibility statement (why you're reaching out)
        3. Value proposition (what's in it for them)
        4. Specific call to action
        5. Professional closing
        
        EXAMPLES OF HIGH-CONVERTING OPENERS:
        - "I noticed {company} recently posted for a {job_title} position..."
        - "As {contact_title} at {company}, you're likely focused on..."
        - "I came across the {job_title} role at {company} and thought..."
        
        TONE GUIDELINES:
        - Professional: Formal, respectful, business-focused
        - Friendly: Warm but professional, conversational
        - Direct: Brief, to-the-point, action-oriented
        
        REQUIREMENTS:
        - 120-150 words maximum
        - Mention specific job title and company name
        - Include clear value proposition
        - End with specific call to action
        - Reference job URL naturally
        - Sign as [Your Name]
        - NO generic phrases like "hope this finds you well"
        - Focus on THEIR benefit, not yours
        
        Additional context: {additional_context}"""
        
        user_prompt = f"""
        Write an outreach message for:
        - Job Title: {job_title}
        - Company: {company}
        - Contact Title: {contact_title}
        - Job URL: {job_url}
        - Tone: {tone}
        """
        
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise e
    
    def generate_subject_line(self, job_title: str, company: str) -> str:
        """Generate email subject line"""
        templates = [
            f"Regarding the {job_title} position at {company}",
            f"Qualified candidates for your {job_title} opening",
            f"{job_title} opportunity at {company}",
            f"Great candidates for your {job_title} role"
        ]
        
        # Use first template as default
        return templates[0]
    
    def generate_follow_up(self, original_message: str, job_title: str, company: str) -> str:
        """Generate a follow-up message"""
        if self.ai_demo_mode or not self.openai_client:
            return f"""Hi again,

I wanted to follow up on my previous message about the {job_title} position at {company}. 

I understand you're likely busy, but I have some excellent candidates who could be great fits for this role. Would it be worth a quick 5-minute call to discuss?

Thanks for your time!

Best regards,
[Your Name]"""
        
        try:
            system_prompt = """
            Write a polite follow-up message for a recruiter who previously reached out about a job opening.
            Keep it brief, friendly, and include a soft call to action.
            Sign as [Your Name].
            """
            
            user_prompt = f"""
            Original message: {original_message[:200]}...
            Job: {job_title} at {company}
            
            Write a follow-up message.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6,
                max_tokens=200
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as e:
            logger.error(f"Error generating follow-up: {e}")
            return self.generate_follow_up("", job_title, company)  # Fallback to demo
