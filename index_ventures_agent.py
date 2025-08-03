"""
Index Ventures Intelligent Agent
A complete working agent that can crawl Index Ventures website and answer questions
about their team members and investment focus.

Usage:
    python index_ventures_agent.py
    
    Then ask questions like:
    - "Which partners invest in early-stage startups?"
    - "Show me team members with AI focus"
    - "Find partners who were previously entrepreneurs"
"""

import asyncio
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
import logging

# Crawl4AI imports
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TeamMember:
    """Data structure for Index Ventures team members"""
    name: str
    title: str
    profile_url: str
    image_url: str = ""
    linkedin_url: str = ""
    biography: str = ""
    investment_focus: List[str] = None
    investment_stage: str = ""
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.investment_focus is None:
            self.investment_focus = []

@dataclass 
class AnalysisResult:
    """Result structure for agent analysis"""
    query: str
    results: List[TeamMember]
    confidence: float
    reasoning: str
    timestamp: str

class IndexVenturesAgent:
    """
    Intelligent agent specifically designed for Index Ventures website
    """
    
    def __init__(self):
        self.base_url = "https://www.indexventures.com"
        self.team_members: List[TeamMember] = []
        self.crawler = None
        
        # Investment stage keywords for analysis
        self.stage_keywords = {
            "early_stage": [
                "seed", "early", "startup", "pre-revenue", "founding", "inception",
                "early-stage", "pre-seed", "angel", "initial", "entrepreneurs"
            ],
            "growth_stage": [
                "series a", "series b", "growth", "scale", "scaling", "expansion",
                "established", "mature"
            ],
            "late_stage": [
                "series c", "late", "pre-ipo", "ipo", "public", "acquisition",
                "exit", "buyout"
            ]
        }
        
        # Sector keywords
        self.sector_keywords = {
            "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "neural"],
            "fintech": ["fintech", "financial", "payments", "banking", "crypto", "blockchain"],
            "saas": ["saas", "software", "enterprise", "b2b", "platform"],
            "consumer": ["consumer", "b2c", "marketplace", "social", "mobile app"],
            "healthcare": ["healthcare", "health", "medical", "biotech", "pharma"],
            "cybersecurity": ["security", "cybersecurity", "cyber", "privacy", "data protection"]
        }

    async def initialize(self):
        """Initialize the crawler and basic configuration"""
        browser_config = BrowserConfig(
            headless=True,
            viewport_width=1280,
            viewport_height=720,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        self.crawler = AsyncWebCrawler(config=browser_config)
        await self.crawler.__aenter__()
        logger.info("Index Ventures Agent initialized successfully")

    async def cleanup(self):
        """Clean up resources"""
        if self.crawler:
            await self.crawler.__aexit__(None, None, None)
        logger.info("Agent cleanup completed")

    async def discover_team_members(self) -> List[TeamMember]:
        """
        Discover all team members from the Index Ventures team page
        """
        logger.info("🔍 Discovering team members from Index Ventures...")
        
        team_url = f"{self.base_url}/team/"
        
        # Schema for extracting team member basic info
        team_extraction_schema = {
            "name": "IndexVenturesTeam",
            "baseSelector": "div[class*='team'], .team-member, [data-component-type*='team']",
            "fields": [
                {
                    "name": "name",
                    "selector": "h3, h2, .name, [class*='name']",
                    "type": "text"
                },
                {
                    "name": "title", 
                    "selector": ".title, .role, .position, p",
                    "type": "text"
                },
                {
                    "name": "profile_url",
                    "selector": "a",
                    "type": "attribute",
                    "attribute": "href"
                },
                {
                    "name": "image_url",
                    "selector": "img",
                    "type": "attribute", 
                    "attribute": "src"
                }
            ]
        }
        
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=JsonCssExtractionStrategy(team_extraction_schema, verbose=True),
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(threshold=0.3)
            ),
            verbose=True
        )
        
        result = await self.crawler.arun(url=team_url, config=crawl_config)
        
        if not result.success:
            logger.error(f"Failed to crawl team page: {result.error_message}")
            return []
        
        # Parse extracted data
        team_data = json.loads(result.extracted_content) if result.extracted_content else []
        logger.info(f"Found {len(team_data)} potential team members")
        
        team_members = []
        for member_data in team_data:
            if not member_data.get('name') or len(member_data.get('name', '').strip()) < 2:
                continue
                
            # Clean and normalize URLs
            profile_url = member_data.get('profile_url', '')
            if profile_url and not profile_url.startswith('http'):
                profile_url = urljoin(self.base_url, profile_url)
            
            image_url = member_data.get('image_url', '')
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(self.base_url, image_url)
            
            member = TeamMember(
                name=member_data.get('name', '').strip(),
                title=member_data.get('title', '').strip(),
                profile_url=profile_url,
                image_url=image_url
            )
            
            team_members.append(member)
        
        # Filter out duplicates and invalid entries
        unique_members = []
        seen_names = set()
        for member in team_members:
            if member.name.lower() not in seen_names and len(member.name) > 2:
                seen_names.add(member.name.lower())
                unique_members.append(member)
        
        self.team_members = unique_members
        logger.info(f"✅ Successfully discovered {len(self.team_members)} unique team members")
        
        return self.team_members

    async def enrich_member_profile(self, member: TeamMember) -> TeamMember:
        """
        Enrich a team member's data by crawling their individual profile
        """
        if not member.profile_url:
            logger.warning(f"No profile URL for {member.name}")
            return member
        
        logger.info(f"🔍 Enriching profile for {member.name}")
        
        try:
            # Configuration for profile crawling
            profile_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight);",  # Scroll to load content
                    "document.querySelector('.show-more, .read-more, .expand')?.click();"  # Expand bio if available
                ],
                wait_for="css:body",
                page_timeout=15000,
                delay_before_return_html=2,
                verbose=True
            )
            
            result = await self.crawler.arun(url=member.profile_url, config=profile_config)
            
            if result.success:
                # Extract biography and other details from the profile page
                profile_text = result.markdown
                
                # Extract LinkedIn URL if present
                linkedin_match = re.search(r'https?://[^/]*linkedin\.com[^\s\)]+', profile_text + result.cleaned_html)
                if linkedin_match:
                    member.linkedin_url = linkedin_match.group(0)
                
                # Clean and store biography (first few paragraphs)
                lines = profile_text.split('\n')
                bio_lines = []
                for line in lines:
                    line = line.strip()
                    if len(line) > 20 and not line.startswith('#') and not line.startswith('!['):
                        bio_lines.append(line)
                        if len(bio_lines) >= 5:  # Limit to first 5 meaningful lines
                            break
                
                member.biography = ' '.join(bio_lines)
                
                # Analyze investment focus and stage preference
                member = await self.analyze_investment_focus(member)
                
                logger.info(f"✅ Successfully enriched {member.name}'s profile")
            else:
                logger.warning(f"Failed to crawl profile for {member.name}: {result.error_message}")
        
        except Exception as e:
            logger.error(f"Error enriching profile for {member.name}: {str(e)}")
        
        return member

    async def analyze_investment_focus(self, member: TeamMember) -> TeamMember:
        """
        Analyze a team member's investment focus and stage preference using text analysis
        """
        text_to_analyze = f"{member.biography} {member.title}".lower()
        
        # Analyze investment stage preference
        stage_scores = {}
        for stage, keywords in self.stage_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_to_analyze)
            stage_scores[stage] = score
        
        # Determine primary stage preference
        if stage_scores:
            primary_stage = max(stage_scores, key=stage_scores.get)
            if stage_scores[primary_stage] > 0:
                member.investment_stage = primary_stage
                member.confidence_score = min(stage_scores[primary_stage] / 3.0, 1.0)
        
        # Analyze sector focus
        sector_interests = []
        for sector, keywords in self.sector_keywords.items():
            if any(keyword in text_to_analyze for keyword in keywords):
                sector_interests.append(sector)
        
        member.investment_focus = sector_interests
        
        return member

    async def crawl_all_profiles(self):
        """
        Crawl and enrich all team member profiles
        """
        if not self.team_members:
            await self.discover_team_members()
        
        logger.info(f"🚀 Starting to enrich {len(self.team_members)} member profiles...")
        
        # Process members in batches to avoid overwhelming the server
        batch_size = 3
        for i in range(0, len(self.team_members), batch_size):
            batch = self.team_members[i:i+batch_size]
            
            # Process batch concurrently but with some delay
            tasks = []
            for member in batch:
                tasks.append(self.enrich_member_profile(member))
            
            enriched_batch = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update the members list with enriched data
            for j, enriched_member in enumerate(enriched_batch):
                if not isinstance(enriched_member, Exception):
                    self.team_members[i + j] = enriched_member
            
            # Small delay between batches
            if i + batch_size < len(self.team_members):
                await asyncio.sleep(2)
        
        logger.info("✅ Completed enriching all member profiles")

    async def query(self, user_query: str) -> AnalysisResult:
        """
        Process a natural language query about Index Ventures team members
        """
        logger.info(f"🤔 Processing query: '{user_query}'")
        
        # Ensure we have team data
        if not self.team_members:
            await self.discover_team_members()
            await self.crawl_all_profiles()
        
        query_lower = user_query.lower()
        matching_members = []
        reasoning_parts = []
        
        # Query analysis patterns
        if any(term in query_lower for term in ["early", "seed", "startup", "early-stage"]):
            # Looking for early-stage investors
            for member in self.team_members:
                if member.investment_stage == "early_stage" and member.confidence_score > 0.3:
                    matching_members.append(member)
                    reasoning_parts.append(f"{member.name}: {member.investment_stage} focus (confidence: {member.confidence_score:.1f})")
        
        elif any(term in query_lower for term in ["ai", "artificial intelligence", "machine learning"]):
            # Looking for AI-focused members
            for member in self.team_members:
                if "ai" in member.investment_focus:
                    matching_members.append(member)
                    reasoning_parts.append(f"{member.name}: AI sector focus")
        
        elif any(term in query_lower for term in ["fintech", "financial", "payments"]):
            # Looking for fintech-focused members
            for member in self.team_members:
                if "fintech" in member.investment_focus:
                    matching_members.append(member)
                    reasoning_parts.append(f"{member.name}: Fintech sector focus")
        
        elif any(term in query_lower for term in ["entrepreneur", "founder", "started", "founded"]):
            # Looking for members with entrepreneurial background
            for member in self.team_members:
                if any(term in member.biography.lower() for term in ["founder", "started", "founded", "entrepreneur"]):
                    matching_members.append(member)
                    reasoning_parts.append(f"{member.name}: Entrepreneurial background mentioned in bio")
        
        elif "partner" in query_lower:
            # Looking for partners specifically
            for member in self.team_members:
                if "partner" in member.title.lower():
                    matching_members.append(member)
                    reasoning_parts.append(f"{member.name}: {member.title}")
        
        else:
            # General search - return all members with basic info
            matching_members = self.team_members[:10]  # Limit to first 10
            reasoning_parts = [f"Showing general team information for {len(matching_members)} members"]
        
        # Calculate overall confidence
        if matching_members:
            avg_confidence = sum(m.confidence_score for m in matching_members) / len(matching_members)
        else:
            avg_confidence = 0.0
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No specific matches found"
        
        return AnalysisResult(
            query=user_query,
            results=matching_members,
            confidence=avg_confidence,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat()
        )

    def format_results(self, analysis: AnalysisResult) -> str:
        """
        Format analysis results into a readable response
        """
        if not analysis.results:
            return f"❌ No results found for: '{analysis.query}'\n\nTry asking about:\n- Early-stage investors\n- AI-focused team members\n- Partners\n- Entrepreneurial backgrounds"
        
        response = f"🎯 **Query**: {analysis.query}\n"
        response += f"📊 **Found {len(analysis.results)} matching team members** (Confidence: {analysis.confidence:.1f})\n\n"
        
        for i, member in enumerate(analysis.results, 1):
            response += f"**{i}. {member.name}** - {member.title}\n"
            
            if member.investment_stage:
                response += f"   💼 Investment Focus: {member.investment_stage.replace('_', ' ').title()}\n"
            
            if member.investment_focus:
                response += f"   🎯 Sectors: {', '.join(member.investment_focus).title()}\n"
            
            if member.biography and len(member.biography) > 50:
                bio_preview = member.biography[:150] + "..." if len(member.biography) > 150 else member.biography
                response += f"   📝 Bio: {bio_preview}\n"
            
            if member.profile_url:
                response += f"   🔗 Profile: {member.profile_url}\n"
            
            if member.linkedin_url:
                response += f"   💼 LinkedIn: {member.linkedin_url}\n"
            
            response += "\n"
        
        response += f"🧠 **Analysis**: {analysis.reasoning}\n"
        response += f"⏰ **Generated**: {analysis.timestamp}\n"
        
        return response

    async def interactive_mode(self):
        """
        Run the agent in interactive mode for testing
        """
        print("🚀 Index Ventures Intelligent Agent")
        print("=" * 50)
        print("Ask me questions about Index Ventures team members!")
        print("\nExample queries:")
        print("- Which partners invest in early-stage startups?")
        print("- Show me team members with AI focus")
        print("- Find partners who were previously entrepreneurs")
        print("- List all partners")
        print("\nType 'quit' to exit\n")
        
        while True:
            try:
                query = input("👤 Your question: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    continue
                
                print("🤖 Analyzing...")
                analysis = await self.query(query)
                response = self.format_results(analysis)
                print(f"\n{response}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}\n")
        
        print("👋 Thanks for using Index Ventures Agent!")

# Main execution
async def main():
    """
    Main function to run the Index Ventures Agent
    """
    agent = IndexVenturesAgent()
    
    try:
        await agent.initialize()
        
        # You can either run specific queries or interactive mode
        
        # Example 1: Specific query
        print("🔍 Running example query...")
        analysis = await agent.query("Which partners invest in early-stage startups?")
        print(agent.format_results(analysis))
        
        # Example 2: Interactive mode (uncomment to use)
        # await agent.interactive_mode()
        
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    # Install required packages first:
    # pip install crawl4ai
    # crawl4ai-setup
    
    asyncio.run(main())