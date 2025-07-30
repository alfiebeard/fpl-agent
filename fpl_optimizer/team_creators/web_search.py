"""
Web search functionality for gathering FPL expert insights and tips
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import re
from urllib.parse import urljoin, urlparse

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from ..config import Config

logger = logging.getLogger(__name__)


class FPLWebSearcher:
    """
    Web searcher for gathering FPL expert insights and tips from various sources.
    
    This class searches for and extracts FPL-related content from:
    - Fantasy Football Scout
    - FPL Analytics
    - Reddit r/FantasyPL
    - Twitter/X FPL community
    - Planet FPL
    - Other expert sources
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.search_config = config.get_llm_config().get('web_search', {})
        self.max_results = self.search_config.get('max_results', 20)
        self.expert_sources = self.search_config.get('expert_sources', [])
        self.search_terms = self.search_config.get('search_terms', [])
        self.max_age_days = config.get_llm_config().get('analysis', {}).get('max_age_days', 7)
        
        # Request session for efficiency
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_fpl_insights(self, specific_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for FPL insights and expert tips across multiple sources.
        
        Args:
            specific_query: Optional specific query to search for
            
        Returns:
            List of insights with content, source, date, and relevance
        """
        logger.info("Starting comprehensive FPL insights search...")
        
        all_insights = []
        
        try:
            # Use specific query or default search terms
            queries = [specific_query] if specific_query else self.search_terms
            
            for query in queries:
                logger.info(f"Searching for: {query}")
                
                # Search using DuckDuckGo
                if DDGS:
                    ddg_results = self._search_with_duckduckgo(query)
                    all_insights.extend(ddg_results)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
            
            # Filter and rank insights
            filtered_insights = self._filter_and_rank_insights(all_insights)
            
            logger.info(f"Found {len(filtered_insights)} relevant FPL insights")
            return filtered_insights
            
        except Exception as e:
            logger.error(f"Failed to search for FPL insights: {e}")
            return []
    
    def search_gameweek_specific(self, gameweek: int) -> List[Dict[str, Any]]:
        """
        Search for gameweek-specific insights and tips.
        
        Args:
            gameweek: Current gameweek number
            
        Returns:
            List of gameweek-specific insights
        """
        logger.info(f"Searching for gameweek {gameweek} specific insights...")
        
        gameweek_queries = [
            f"FPL gameweek {gameweek} tips",
            f"fantasy premier league GW{gameweek} captain picks",
            f"FPL GW{gameweek} transfer suggestions",
            f"fantasy football gameweek {gameweek} best picks"
        ]
        
        all_insights = []
        
        for query in gameweek_queries:
            insights = self.search_fpl_insights(query)
            all_insights.extend(insights)
        
        # Remove duplicates and return top insights
        unique_insights = self._remove_duplicate_insights(all_insights)
        return unique_insights[:15]  # Return top 15 gameweek-specific insights
    
    def search_transfer_insights(self) -> List[Dict[str, Any]]:
        """
        Search for transfer-specific insights and recommendations.
        
        Returns:
            List of transfer-related insights
        """
        logger.info("Searching for transfer-specific insights...")
        
        transfer_queries = [
            "FPL transfer tips this week",
            "fantasy premier league best transfers",
            "FPL players to buy and sell",
            "fantasy football transfer recommendations"
        ]
        
        all_insights = []
        
        for query in transfer_queries:
            insights = self.search_fpl_insights(query)
            all_insights.extend(insights)
        
        return self._remove_duplicate_insights(all_insights)[:10]
    
    def search_captain_insights(self) -> List[Dict[str, Any]]:
        """
        Search for captain selection insights and recommendations.
        
        Returns:
            List of captain-related insights
        """
        logger.info("Searching for captain selection insights...")
        
        captain_queries = [
            "FPL captain picks this week",
            "fantasy premier league captaincy tips",
            "FPL best captain options",
            "fantasy football captain recommendations"
        ]
        
        all_insights = []
        
        for query in captain_queries:
            insights = self.search_fpl_insights(query)
            all_insights.extend(insights)
        
        return self._remove_duplicate_insights(all_insights)[:8]
    
    def search_wildcard_insights(self) -> List[Dict[str, Any]]:
        """
        Search for wildcard usage insights and team templates.
        
        Returns:
            List of wildcard-related insights
        """
        logger.info("Searching for wildcard insights...")
        
        wildcard_queries = [
            "FPL wildcard team template",
            "fantasy premier league wildcard tips",
            "FPL best wildcard players",
            "fantasy football wildcard strategy"
        ]
        
        all_insights = []
        
        for query in wildcard_queries:
            insights = self.search_fpl_insights(query)
            all_insights.extend(insights)
        
        return self._remove_duplicate_insights(all_insights)[:10]
    
    def _search_with_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo API"""
        if not DDGS:
            logger.warning("DuckDuckGo search not available - install duckduckgo-search package")
            return []
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query, 
                    max_results=self.max_results // len(self.search_terms),
                    timelimit='w'  # Last week
                ))
            
            insights = []
            for result in results:
                # Extract content from the result
                content = self._extract_content_from_url(result.get('href', ''))
                
                if content:
                    insight = {
                        'title': result.get('title', ''),
                        'content': content,
                        'url': result.get('href', ''),
                        'source': self._extract_source_name(result.get('href', '')),
                        'snippet': result.get('body', ''),
                        'date': datetime.now(),  # Approximate date
                        'relevance_score': self._calculate_relevance_score(result, query),
                        'search_query': query
                    }
                    insights.append(insight)
            
            return insights
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed for query '{query}': {e}")
            return []
    
    def _extract_content_from_url(self, url: str) -> str:
        """Extract readable content from a URL"""
        if not BeautifulSoup or not url:
            return ""
        
        try:
            # Check if it's from a trusted source
            if not self._is_trusted_source(url):
                return ""
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text from common content containers
            content_selectors = [
                'article', '.article-content', '.post-content', 
                '.entry-content', '.content', 'main', '.main-content'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0].get_text(strip=True, separator=' ')
                    break
            
            if not content:
                # Fallback to body text
                content = soup.get_text(strip=True, separator=' ')
            
            # Clean and truncate content
            content = self._clean_content(content)
            return content[:2000]  # Limit content length
            
        except Exception as e:
            logger.debug(f"Failed to extract content from {url}: {e}")
            return ""
    
    def _is_trusted_source(self, url: str) -> bool:
        """Check if URL is from a trusted FPL source"""
        if not url:
            return False
        
        domain = urlparse(url).netloc.lower()
        
        trusted_domains = [
            'fantasyfootballscout.co.uk',
            'fantasyfootballpundit.com',
            'planetfpl.com',
            'fplanalytics.com',
            'reddit.com',
            'twitter.com',
            'x.com',
            'premierleague.com',
            'fantasy.premierleague.com'
        ]
        
        return any(trusted in domain for trusted in trusted_domains)
    
    def _clean_content(self, content: str) -> str:
        """Clean extracted content"""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common navigation elements
        navigation_patterns = [
            r'Home\s+About\s+Contact',
            r'Menu\s+Search',
            r'Subscribe\s+Newsletter',
            r'Follow\s+us\s+on',
            r'Cookie\s+Policy',
            r'Privacy\s+Policy'
        ]
        
        for pattern in navigation_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _extract_source_name(self, url: str) -> str:
        """Extract a readable source name from URL"""
        if not url:
            return "Unknown"
        
        domain = urlparse(url).netloc.lower()
        
        source_mapping = {
            'fantasyfootballscout.co.uk': 'Fantasy Football Scout',
            'fantasyfootballpundit.com': 'Fantasy Football Pundit',
            'planetfpl.com': 'Planet FPL',
            'fplanalytics.com': 'FPL Analytics',
            'reddit.com': 'Reddit r/FantasyPL',
            'twitter.com': 'Twitter/X',
            'x.com': 'Twitter/X',
            'premierleague.com': 'Premier League Official',
            'fantasy.premierleague.com': 'FPL Official'
        }
        
        for domain_key, source_name in source_mapping.items():
            if domain_key in domain:
                return source_name
        
        # Fallback to domain name
        return domain.replace('www.', '').replace('.com', '').replace('.co.uk', '').title()
    
    def _calculate_relevance_score(self, result: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for a search result"""
        score = 0.0
        
        title = result.get('title', '').lower()
        snippet = result.get('body', '').lower()
        url = result.get('href', '').lower()
        
        # Query term matching
        query_terms = query.lower().split()
        for term in query_terms:
            if term in title:
                score += 2.0
            if term in snippet:
                score += 1.0
            if term in url:
                score += 0.5
        
        # Source credibility bonus
        if self._is_trusted_source(result.get('href', '')):
            score += 3.0
        
        # FPL-specific term bonuses
        fpl_terms = ['fpl', 'fantasy', 'premier', 'league', 'gameweek', 'captain', 'transfer']
        for term in fpl_terms:
            if term in title or term in snippet:
                score += 0.5
        
        return score
    
    def _filter_and_rank_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and rank insights by relevance and recency"""
        if not insights:
            return []
        
        # Filter out low-quality insights
        filtered = []
        for insight in insights:
            if (len(insight.get('content', '')) > 100 and  # Minimum content length
                insight.get('relevance_score', 0) > 1.0):   # Minimum relevance
                filtered.append(insight)
        
        # Sort by relevance score
        filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Remove duplicates based on content similarity
        unique_insights = self._remove_duplicate_insights(filtered)
        
        return unique_insights
    
    def _remove_duplicate_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate insights based on content similarity"""
        if not insights:
            return []
        
        unique_insights = []
        seen_content = set()
        
        for insight in insights:
            content = insight.get('content', '')
            
            # Create a simple hash of the content for duplicate detection
            content_hash = hash(content[:200])  # Use first 200 chars for comparison
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_insights.append(insight)
        
        return unique_insights
    
    def get_insights_summary(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of gathered insights"""
        if not insights:
            return {
                'total_insights': 0,
                'sources': [],
                'topics': [],
                'average_relevance': 0.0
            }
        
        sources = list(set(insight.get('source', 'Unknown') for insight in insights))
        
        # Extract common topics/themes
        all_content = ' '.join(insight.get('content', '') for insight in insights)
        topics = self._extract_topics(all_content)
        
        average_relevance = sum(insight.get('relevance_score', 0) for insight in insights) / len(insights)
        
        return {
            'total_insights': len(insights),
            'sources': sources,
            'topics': topics,
            'average_relevance': average_relevance,
            'date_range': self._get_date_range(insights)
        }
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract common FPL topics from content"""
        if not content:
            return []
        
        content_lower = content.lower()
        
        fpl_topics = [
            'captain', 'transfer', 'wildcard', 'bench boost', 'triple captain',
            'differential', 'template', 'rotation', 'fixtures', 'form',
            'injury', 'suspension', 'price rise', 'price fall', 'ownership'
        ]
        
        found_topics = []
        for topic in fpl_topics:
            if topic in content_lower:
                found_topics.append(topic.title())
        
        return found_topics[:10]  # Return top 10 topics
    
    def _get_date_range(self, insights: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get date range of insights"""
        if not insights:
            return {'earliest': '', 'latest': ''}
        
        dates = [insight.get('date') for insight in insights if insight.get('date')]
        
        if not dates:
            return {'earliest': '', 'latest': ''}
        
        earliest = min(dates)
        latest = max(dates)
        
        return {
            'earliest': earliest.strftime('%Y-%m-%d') if earliest else '',
            'latest': latest.strftime('%Y-%m-%d') if latest else ''
        }