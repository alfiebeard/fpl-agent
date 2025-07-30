"""
LLM analyzer for processing FPL expert insights and making team decisions
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

from ..models import Player, FPLTeam, Position, OptimizationResult, Transfer
from ..config import Config

logger = logging.getLogger(__name__)


class FPLLLMAnalyzer:
    """
    LLM-powered analyzer for processing FPL expert insights and making team decisions.
    
    This class uses Large Language Models to:
    - Analyze expert insights and tips
    - Make team selection decisions
    - Suggest transfers based on expert opinions
    - Select captains and vice-captains
    - Determine wildcard usage timing
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.get_llm_config()
        self.provider = self.llm_config.get('provider', 'openai')
        self.model = self.llm_config.get('model', 'gpt-4')
        self.max_tokens = self.llm_config.get('max_tokens', 4000)
        self.temperature = self.llm_config.get('temperature', 0.7)
        
        # Initialize LLM client
        self.client = self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """Initialize the appropriate LLM client"""
        api_key = self.llm_config.get('api_key')
        
        if self.provider == 'openai' and openai:
            if not api_key:
                api_key = self.config.get_env_var('OPENAI_API_KEY')
            return openai.OpenAI(api_key=api_key) if api_key else None
            
        elif self.provider == 'anthropic' and anthropic:
            if not api_key:
                api_key = self.config.get_env_var('ANTHROPIC_API_KEY')
            return anthropic.Anthropic(api_key=api_key) if api_key else None
        
        logger.warning(f"LLM provider '{self.provider}' not available or API key not set")
        return None
    
    def analyze_team_creation(self, insights: List[Dict[str, Any]], 
                            available_players: List[Player],
                            budget: float = 100.0) -> Dict[str, Any]:
        """
        Analyze insights to create a new team from scratch.
        
        Args:
            insights: List of expert insights and tips
            available_players: List of all available players
            budget: Available budget in millions
            
        Returns:
            Analysis with recommended team structure and reasoning
        """
        logger.info("Analyzing insights for team creation...")
        
        if not self.client:
            logger.error("LLM client not available")
            return self._fallback_team_analysis(available_players, budget)
        
        try:
            # Prepare context for LLM
            context = self._prepare_team_creation_context(insights, available_players, budget)
            
            # Generate LLM prompt
            prompt = self._create_team_creation_prompt(context)
            
            # Get LLM response
            response = self._query_llm(prompt)
            
            # Parse and validate response
            analysis = self._parse_team_creation_response(response, available_players)
            
            logger.info("Team creation analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze team creation: {e}")
            return self._fallback_team_analysis(available_players, budget)
    
    def analyze_weekly_transfers(self, insights: List[Dict[str, Any]], 
                               current_team: FPLTeam,
                               available_players: List[Player],
                               free_transfers: int = 1) -> Dict[str, Any]:
        """
        Analyze insights to suggest weekly transfers.
        
        Args:
            insights: List of expert insights and tips
            current_team: Current FPL team
            available_players: List of all available players
            free_transfers: Number of free transfers available
            
        Returns:
            Analysis with transfer recommendations and reasoning
        """
        logger.info("Analyzing insights for weekly transfers...")
        
        if not self.client:
            logger.error("LLM client not available")
            return self._fallback_transfer_analysis(current_team, available_players)
        
        try:
            # Prepare context for LLM
            context = self._prepare_transfer_context(insights, current_team, available_players, free_transfers)
            
            # Generate LLM prompt
            prompt = self._create_transfer_prompt(context)
            
            # Get LLM response
            response = self._query_llm(prompt)
            
            # Parse and validate response
            analysis = self._parse_transfer_response(response, current_team, available_players)
            
            logger.info("Transfer analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze transfers: {e}")
            return self._fallback_transfer_analysis(current_team, available_players)
    
    def analyze_captaincy(self, insights: List[Dict[str, Any]], 
                         team: FPLTeam) -> Dict[str, Any]:
        """
        Analyze insights to select captain and vice-captain.
        
        Args:
            insights: List of expert insights and tips
            team: Current FPL team
            
        Returns:
            Analysis with captain recommendations and reasoning
        """
        logger.info("Analyzing insights for captaincy decisions...")
        
        if not self.client:
            logger.error("LLM client not available")
            return self._fallback_captaincy_analysis(team)
        
        try:
            # Prepare context for LLM
            context = self._prepare_captaincy_context(insights, team)
            
            # Generate LLM prompt
            prompt = self._create_captaincy_prompt(context)
            
            # Get LLM response
            response = self._query_llm(prompt)
            
            # Parse and validate response
            analysis = self._parse_captaincy_response(response, team)
            
            logger.info("Captaincy analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze captaincy: {e}")
            return self._fallback_captaincy_analysis(team)
    
    def analyze_wildcard_usage(self, insights: List[Dict[str, Any]], 
                             current_team: FPLTeam,
                             available_players: List[Player]) -> Dict[str, Any]:
        """
        Analyze insights to determine wildcard usage.
        
        Args:
            insights: List of expert insights and tips
            current_team: Current FPL team
            available_players: List of all available players
            
        Returns:
            Analysis with wildcard recommendation and reasoning
        """
        logger.info("Analyzing insights for wildcard usage...")
        
        if not self.client:
            logger.error("LLM client not available")
            return self._fallback_wildcard_analysis(current_team)
        
        try:
            # Prepare context for LLM
            context = self._prepare_wildcard_context(insights, current_team, available_players)
            
            # Generate LLM prompt
            prompt = self._create_wildcard_prompt(context)
            
            # Get LLM response
            response = self._query_llm(prompt)
            
            # Parse and validate response
            analysis = self._parse_wildcard_response(response)
            
            logger.info("Wildcard analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze wildcard usage: {e}")
            return self._fallback_wildcard_analysis(current_team)
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM with the given prompt"""
        try:
            if self.provider == 'openai' and self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert Fantasy Premier League analyst with deep knowledge of player performance, tactics, and strategy."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                return response.choices[0].message.content
                
            elif self.provider == 'anthropic' and self.client:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system="You are an expert Fantasy Premier League analyst with deep knowledge of player performance, tactics, and strategy.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
            else:
                raise Exception("No valid LLM client available")
                
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            raise
    
    def _prepare_team_creation_context(self, insights: List[Dict[str, Any]], 
                                     players: List[Player], 
                                     budget: float) -> Dict[str, Any]:
        """Prepare context for team creation analysis"""
        # Summarize insights
        insights_summary = self._summarize_insights(insights)
        
        # Prepare player data
        players_by_position = {
            'GK': [p for p in players if p.position == Position.GK],
            'DEF': [p for p in players if p.position == Position.DEF],
            'MID': [p for p in players if p.position == Position.MID],
            'FWD': [p for p in players if p.position == Position.FWD]
        }
        
        # Get top players by position (by form/points)
        top_players = {}
        for pos, pos_players in players_by_position.items():
            sorted_players = sorted(pos_players, key=lambda p: p.form + p.points_per_game, reverse=True)
            top_players[pos] = sorted_players[:10]  # Top 10 per position
        
        return {
            'insights_summary': insights_summary,
            'budget': budget,
            'top_players': top_players,
            'total_players': len(players),
            'formation_constraints': {
                'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3
            }
        }
    
    def _prepare_transfer_context(self, insights: List[Dict[str, Any]], 
                                current_team: FPLTeam,
                                available_players: List[Player],
                                free_transfers: int) -> Dict[str, Any]:
        """Prepare context for transfer analysis"""
        insights_summary = self._summarize_insights(insights)
        
        # Current team analysis
        current_team_data = {
            'players': [self._player_to_dict(p) for p in current_team.players],
            'total_value': current_team.total_value,
            'bank': current_team.bank,
            'free_transfers': free_transfers
        }
        
        # Available alternatives
        current_player_ids = {p.id for p in current_team.players}
        alternatives = [p for p in available_players if p.id not in current_player_ids]
        
        return {
            'insights_summary': insights_summary,
            'current_team': current_team_data,
            'available_alternatives': [self._player_to_dict(p) for p in alternatives[:50]],  # Top 50 alternatives
            'free_transfers': free_transfers
        }
    
    def _prepare_captaincy_context(self, insights: List[Dict[str, Any]], 
                                 team: FPLTeam) -> Dict[str, Any]:
        """Prepare context for captaincy analysis"""
        insights_summary = self._summarize_insights(insights)
        
        team_data = {
            'players': [self._player_to_dict(p) for p in team.players]
        }
        
        return {
            'insights_summary': insights_summary,
            'team': team_data
        }
    
    def _prepare_wildcard_context(self, insights: List[Dict[str, Any]], 
                                current_team: FPLTeam,
                                available_players: List[Player]) -> Dict[str, Any]:
        """Prepare context for wildcard analysis"""
        insights_summary = self._summarize_insights(insights)
        
        current_team_data = {
            'players': [self._player_to_dict(p) for p in current_team.players],
            'total_value': current_team.total_value
        }
        
        return {
            'insights_summary': insights_summary,
            'current_team': current_team_data,
            'total_available_players': len(available_players)
        }
    
    def _summarize_insights(self, insights: List[Dict[str, Any]]) -> str:
        """Create a concise summary of expert insights"""
        if not insights:
            return "No expert insights available."
        
        # Group insights by source and topic
        summary_parts = []
        
        # Add source summary
        sources = list(set(insight.get('source', 'Unknown') for insight in insights))
        summary_parts.append(f"Expert insights from {len(sources)} sources: {', '.join(sources[:5])}")
        
        # Add key topics
        all_content = ' '.join(insight.get('content', '') for insight in insights)
        if all_content:
            summary_parts.append("Key topics discussed:")
            
            # Extract key phrases (simplified)
            important_phrases = []
            for insight in insights[:10]:  # Top 10 insights
                content = insight.get('content', '')
                if len(content) > 100:
                    # Extract first meaningful sentence
                    sentences = content.split('.')
                    for sentence in sentences:
                        if len(sentence.strip()) > 20 and any(word in sentence.lower() for word in ['captain', 'transfer', 'buy', 'sell', 'avoid', 'pick']):
                            important_phrases.append(sentence.strip())
                            break
            
            for phrase in important_phrases[:5]:
                summary_parts.append(f"- {phrase}")
        
        return '\n'.join(summary_parts)
    
    def _player_to_dict(self, player: Player) -> Dict[str, Any]:
        """Convert player object to dictionary for LLM context"""
        return {
            'id': player.id,
            'name': player.name,
            'team': player.team_name,
            'position': player.position.value,
            'price': player.price,
            'form': player.form,
            'total_points': player.total_points,
            'points_per_game': player.points_per_game,
            'selected_by_pct': player.selected_by_pct,
            'is_injured': player.is_injured
        }
    
    def _create_team_creation_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for team creation analysis"""
        return f"""
Based on the following expert insights and player data, create an optimal Fantasy Premier League team from scratch.

EXPERT INSIGHTS:
{context['insights_summary']}

BUDGET: £{context['budget']}m

FORMATION CONSTRAINTS:
- Goalkeepers: {context['formation_constraints']['GK']}
- Defenders: {context['formation_constraints']['DEF']}
- Midfielders: {context['formation_constraints']['MID']}
- Forwards: {context['formation_constraints']['FWD']}

TOP PLAYERS BY POSITION:
{self._format_players_for_prompt(context['top_players'])}

Please provide your analysis in the following JSON format:
{{
    "recommended_team": {{
        "GK": [list of 2 goalkeeper names],
        "DEF": [list of 5 defender names],
        "MID": [list of 5 midfielder names],
        "FWD": [list of 3 forward names]
    }},
    "starting_formation": [defenders, midfielders, forwards],
    "captain": "player name",
    "vice_captain": "player name",
    "reasoning": "detailed explanation of team selection based on expert insights",
    "confidence": 0.85,
    "key_insights_used": [list of key insights that influenced decisions]
}}

Focus on:
1. Value for money based on expert opinions
2. Form and fixture analysis from insights
3. Injury concerns mentioned by experts
4. Popular picks vs differentials
5. Long-term potential based on expert analysis
"""
    
    def _create_transfer_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for transfer analysis"""
        return f"""
Based on expert insights, analyze the current team and suggest optimal transfers.

EXPERT INSIGHTS:
{context['insights_summary']}

CURRENT TEAM:
{self._format_current_team_for_prompt(context['current_team'])}

FREE TRANSFERS AVAILABLE: {context['free_transfers']}

Please provide your analysis in the following JSON format:
{{
    "recommended_transfers": [
        {{
            "player_out": "player name",
            "player_in": "player name",
            "reason": "explanation based on expert insights"
        }}
    ],
    "captain": "player name",
    "vice_captain": "player name", 
    "reasoning": "overall transfer strategy explanation",
    "confidence": 0.75,
    "transfer_priority": "high/medium/low",
    "key_insights_used": [list of key insights that influenced decisions]
}}

Consider:
1. Players mentioned as must-haves by experts
2. Players to avoid based on expert analysis
3. Form and fixture swings highlighted by experts
4. Injury updates from expert sources
5. Price change predictions from experts
"""
    
    def _create_captaincy_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for captaincy analysis"""
        return f"""
Based on expert insights, select the best captain and vice-captain from the current team.

EXPERT INSIGHTS:
{context['insights_summary']}

CURRENT TEAM:
{self._format_team_players_for_prompt(context['team']['players'])}

Please provide your analysis in the following JSON format:
{{
    "captain": "player name",
    "vice_captain": "player name",
    "reasoning": "explanation based on expert captain picks and analysis",
    "confidence": 0.80,
    "alternative_options": [list of other viable captain options],
    "key_insights_used": [list of key insights about captaincy this week]
}}

Focus on:
1. Expert captain recommendations
2. Fixture analysis from expert sources
3. Form and momentum insights
4. Penalty takers and set piece specialists
5. Differential vs template captain choices
"""
    
    def _create_wildcard_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for wildcard analysis"""
        return f"""
Based on expert insights, determine whether to use the wildcard chip this week.

EXPERT INSIGHTS:
{context['insights_summary']}

CURRENT TEAM VALUE: £{context['current_team']['total_value']}m

Please provide your analysis in the following JSON format:
{{
    "use_wildcard": true/false,
    "reasoning": "detailed explanation based on expert wildcard advice",
    "confidence": 0.70,
    "optimal_timing": "this week/next week/later",
    "key_factors": [list of factors from expert analysis that influence decision],
    "template_changes": [list of popular template changes mentioned by experts]
}}

Consider:
1. Expert wildcard timing advice
2. Template team shifts mentioned by experts
3. Fixture swing analysis from expert sources
4. Player price changes and trends
5. Injury crisis or player availability issues
"""
    
    def _format_players_for_prompt(self, players_by_position: Dict[str, List[Player]]) -> str:
        """Format players data for LLM prompt"""
        formatted = []
        for position, players in players_by_position.items():
            formatted.append(f"\n{position}:")
            for i, player in enumerate(players[:5], 1):  # Top 5 per position
                formatted.append(f"  {i}. {player.name} ({player.team_name}) - £{player.price}m, Form: {player.form}, PPG: {player.points_per_game}")
        return '\n'.join(formatted)
    
    def _format_current_team_for_prompt(self, team_data: Dict[str, Any]) -> str:
        """Format current team data for LLM prompt"""
        formatted = []
        formatted.append(f"Team Value: £{team_data['total_value']}m")
        formatted.append(f"Bank: £{team_data['bank']}m")
        formatted.append("Players:")
        
        for player in team_data['players']:
            formatted.append(f"  {player['name']} ({player['position']}) - £{player['price']}m, Form: {player['form']}")
        
        return '\n'.join(formatted)
    
    def _format_team_players_for_prompt(self, players: List[Dict[str, Any]]) -> str:
        """Format team players for LLM prompt"""
        formatted = []
        for player in players:
            formatted.append(f"  {player['name']} ({player['position']}) - £{player['price']}m, Form: {player['form']}, PPG: {player['points_per_game']}")
        return '\n'.join(formatted)
    
    def _parse_team_creation_response(self, response: str, available_players: List[Player]) -> Dict[str, Any]:
        """Parse LLM response for team creation"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate and enhance the response
                return self._validate_team_creation_response(parsed, available_players)
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            logger.error(f"Failed to parse team creation response: {e}")
            return self._fallback_team_analysis(available_players, 100.0)
    
    def _parse_transfer_response(self, response: str, current_team: FPLTeam, available_players: List[Player]) -> Dict[str, Any]:
        """Parse LLM response for transfers"""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                return self._validate_transfer_response(parsed, current_team, available_players)
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            logger.error(f"Failed to parse transfer response: {e}")
            return self._fallback_transfer_analysis(current_team, available_players)
    
    def _parse_captaincy_response(self, response: str, team: FPLTeam) -> Dict[str, Any]:
        """Parse LLM response for captaincy"""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                return self._validate_captaincy_response(parsed, team)
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            logger.error(f"Failed to parse captaincy response: {e}")
            return self._fallback_captaincy_analysis(team)
    
    def _parse_wildcard_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for wildcard analysis"""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                return self._validate_wildcard_response(parsed)
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            logger.error(f"Failed to parse wildcard response: {e}")
            return self._fallback_wildcard_analysis(None)
    
    def _validate_team_creation_response(self, parsed: Dict[str, Any], available_players: List[Player]) -> Dict[str, Any]:
        """Validate and enhance team creation response"""
        # Ensure all required fields exist
        required_fields = ['recommended_team', 'captain', 'vice_captain', 'reasoning', 'confidence']
        for field in required_fields:
            if field not in parsed:
                parsed[field] = self._get_default_value(field)
        
        # Validate team structure
        team = parsed.get('recommended_team', {})
        if not all(pos in team for pos in ['GK', 'DEF', 'MID', 'FWD']):
            parsed['recommended_team'] = self._get_default_team_structure()
        
        return parsed
    
    def _validate_transfer_response(self, parsed: Dict[str, Any], current_team: FPLTeam, available_players: List[Player]) -> Dict[str, Any]:
        """Validate transfer response"""
        required_fields = ['recommended_transfers', 'captain', 'vice_captain', 'reasoning', 'confidence']
        for field in required_fields:
            if field not in parsed:
                parsed[field] = self._get_default_value(field)
        
        return parsed
    
    def _validate_captaincy_response(self, parsed: Dict[str, Any], team: FPLTeam) -> Dict[str, Any]:
        """Validate captaincy response"""
        required_fields = ['captain', 'vice_captain', 'reasoning', 'confidence']
        for field in required_fields:
            if field not in parsed:
                parsed[field] = self._get_default_value(field)
        
        # Ensure captain is from the team
        if team.players:
            if parsed['captain'] not in [p.name for p in team.players]:
                parsed['captain'] = team.players[0].name
            if parsed['vice_captain'] not in [p.name for p in team.players]:
                parsed['vice_captain'] = team.players[1].name if len(team.players) > 1 else team.players[0].name
        
        return parsed
    
    def _validate_wildcard_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Validate wildcard response"""
        required_fields = ['use_wildcard', 'reasoning', 'confidence']
        for field in required_fields:
            if field not in parsed:
                parsed[field] = self._get_default_value(field)
        
        return parsed
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            'recommended_team': {'GK': [], 'DEF': [], 'MID': [], 'FWD': []},
            'captain': 'Unknown',
            'vice_captain': 'Unknown',
            'reasoning': 'Analysis based on available expert insights.',
            'confidence': 0.5,
            'recommended_transfers': [],
            'use_wildcard': False
        }
        return defaults.get(field, '')
    
    def _get_default_team_structure(self) -> Dict[str, List[str]]:
        """Get default team structure"""
        return {
            'GK': ['Goalkeeper 1', 'Goalkeeper 2'],
            'DEF': ['Defender 1', 'Defender 2', 'Defender 3', 'Defender 4', 'Defender 5'],
            'MID': ['Midfielder 1', 'Midfielder 2', 'Midfielder 3', 'Midfielder 4', 'Midfielder 5'],
            'FWD': ['Forward 1', 'Forward 2', 'Forward 3']
        }
    
    # Fallback methods for when LLM is not available
    def _fallback_team_analysis(self, players: List[Player], budget: float) -> Dict[str, Any]:
        """Fallback team analysis when LLM is not available"""
        return {
            'recommended_team': self._get_default_team_structure(),
            'captain': 'Top Player',
            'vice_captain': 'Second Best Player',
            'reasoning': 'LLM analysis not available. Using fallback recommendations.',
            'confidence': 0.3,
            'key_insights_used': ['Fallback analysis due to LLM unavailability']
        }
    
    def _fallback_transfer_analysis(self, current_team: FPLTeam, available_players: List[Player]) -> Dict[str, Any]:
        """Fallback transfer analysis when LLM is not available"""
        return {
            'recommended_transfers': [],
            'captain': current_team.players[0].name if current_team.players else 'Unknown',
            'vice_captain': current_team.players[1].name if len(current_team.players) > 1 else 'Unknown',
            'reasoning': 'LLM analysis not available. No transfers recommended.',
            'confidence': 0.3
        }
    
    def _fallback_captaincy_analysis(self, team: FPLTeam) -> Dict[str, Any]:
        """Fallback captaincy analysis when LLM is not available"""
        return {
            'captain': team.players[0].name if team.players else 'Unknown',
            'vice_captain': team.players[1].name if len(team.players) > 1 else 'Unknown',
            'reasoning': 'LLM analysis not available. Using top players by form.',
            'confidence': 0.3
        }
    
    def _fallback_wildcard_analysis(self, current_team: Optional[FPLTeam]) -> Dict[str, Any]:
        """Fallback wildcard analysis when LLM is not available"""
        return {
            'use_wildcard': False,
            'reasoning': 'LLM analysis not available. Conservative approach - no wildcard recommended.',
            'confidence': 0.3,
            'optimal_timing': 'later'
        }