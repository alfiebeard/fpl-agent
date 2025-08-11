"""
Embedding-based player filtering for FPL Optimizer
"""

import logging
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ..core.config import Config
from ..core.models import Position

logger = logging.getLogger(__name__)


class EmbeddingFilter:
    """
    Embedding-based player filtering using BAAI/bge-base-en-v1.5 model.
    
    This class handles:
    - Loading and caching player embeddings
    - Position-specific query encoding
    - Cosine similarity scoring
    - Top player selection per position
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.embeddings_cache = {}
        self.position_queries = {
            'GK': "Must-have OR recommended, fit, high points, clean sheet, saves, consistent starter, good fixtures. NOT out of form, injured, suspended.",
            'DEF': "Must-have OR recommended, fit, high points, clean sheet, attacking potential, consistent starter, good fixtures. NOT out of form, injured, suspended.",  
            'MID': "Must-have OR recommended, fit, high points, goals, assists, consistent starter, set pieces, penalties, good fixtures. NOT out of form, injured, suspended.",
            'FWD': "Must-have OR recommended, fit, high points, goals, assists, consistent starter, set pieces, penalties, good fixtures. NOT out of form, injured, suspended."
        }
        self.selection_counts = {
            'GK': 15,
            'DEF': 60,  # Increased from 45
            'MID': 70,  # Increased from 45
            'FWD': 30
        }
    
    def _get_embeddings_cache_path(self) -> Path:
        """Get the path to the embeddings cache file"""
        cache_dir = Path("team_data")
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / "player_embeddings.json"
    
    def _load_embeddings_model(self):
        """Load the sentence-transformers model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading BAAI/bge-base-en-v1.5 embedding model...")
            self.model = SentenceTransformer('BAAI/bge-base-en-v1.5')
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed. Please install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _load_cached_embeddings(self) -> Optional[Dict[str, Any]]:
        """Load cached embeddings from file"""
        cache_path = self._get_embeddings_cache_path()
        
        if not cache_path.exists():
            logger.info("No cached embeddings found")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check cache age
            cache_timestamp = cached_data.get('cache_timestamp')
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                if age_hours > 24:
                    logger.warning(f"Using cached embeddings that are {age_hours:.1f} hours old")
                else:
                    logger.info(f"Using cached embeddings ({age_hours:.1f} hours old)")
            
            return cached_data
            
        except Exception as e:
            logger.error(f"Failed to load cached embeddings: {e}")
            return None
    
    def _save_embeddings_cache(self, embeddings_data: Dict[str, Any]) -> None:
        """Save embeddings to cache file"""
        cache_path = self._get_embeddings_cache_path()
        
        try:
            cache_data = {
                'cache_timestamp': datetime.now().isoformat(),
                'embeddings': embeddings_data,
                'total_players': len(embeddings_data)
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved embeddings cache with {len(embeddings_data)} players to {cache_path}")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")
    
    def _encode_players(self, enriched_data: Dict[str, str]) -> Dict[str, np.ndarray]:
        """Encode all players' enriched data into embeddings"""
        if self.model is None:
            self._load_embeddings_model()
        
        logger.info(f"Encoding {len(enriched_data)} players...")
        
        try:
            # Prepare texts for encoding
            player_names = list(enriched_data.keys())
            player_texts = list(enriched_data.values())
            
            # Encode all texts at once (more efficient)
            embeddings = self.model.encode(player_texts, show_progress_bar=True)
            
            # Create dictionary mapping player names to embeddings
            player_embeddings = {}
            for i, player_name in enumerate(player_names):
                player_embeddings[player_name] = embeddings[i]
            
            logger.info(f"Successfully encoded {len(player_embeddings)} players")
            return player_embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode players: {e}")
            raise
    
    def _encode_queries(self) -> Dict[str, np.ndarray]:
        """Encode position-specific queries"""
        if self.model is None:
            self._load_embeddings_model()
        
        logger.info("Encoding position-specific queries...")
        
        try:
            query_texts = list(self.position_queries.values())
            query_embeddings = self.model.encode(query_texts)
            
            # Create dictionary mapping positions to query embeddings
            position_embeddings = {}
            for i, position in enumerate(self.position_queries.keys()):
                position_embeddings[position] = query_embeddings[i]
            
            logger.info("Successfully encoded position queries")
            return position_embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode queries: {e}")
            raise
    
    def _get_player_positions(self, enriched_data: Dict[str, str]) -> Dict[str, str]:
        """Extract player positions from enriched data"""
        player_positions = {}
        
        # Get structured data for position extraction
        from .llm_strategy import LLMStrategy
        from ..core.config import Config
        
        # Create a minimal config and strategy to access cached data
        config = Config()
        strategy = LLMStrategy(config)
        structured_data = strategy.get_enriched_player_data(force_refresh=False)
        
        # Use structured data for position extraction
        for player_name in enriched_data.keys():
            position = structured_data[player_name]["data"]["position"]
            player_positions[player_name] = position
        
        return player_positions
    
    def _get_structured_data_for_hybrid_scoring(self, enriched_data: Dict[str, str]) -> Dict[str, Any]:
        """Get structured data needed for hybrid scoring"""
        try:
            # Get structured data for keyword extraction
            from .llm_strategy import LLMStrategy
            from ..core.config import Config
            
            config = Config()
            strategy = LLMStrategy(config)
            structured_data = strategy.get_enriched_player_data(force_refresh=False)
            
            return structured_data
            
        except Exception as e:
            logger.warning(f"Failed to get structured data for hybrid scoring: {e}")
            return {}
    
    def _calculate_similarities(self, player_embeddings: Dict[str, np.ndarray], 
                              query_embeddings: Dict[str, np.ndarray],
                              player_positions: Dict[str, str]) -> Dict[str, List[Tuple[str, float]]]:
        """Calculate cosine similarities between queries and players by position"""
        similarities = {position: [] for position in self.position_queries.keys()}
        
        logger.info("Calculating cosine similarities...")
        
        for position, query_embedding in query_embeddings.items():
            position_players = []
            position_player_embeddings = []
            
            # Get all players for this position
            for player_name, player_embedding in player_embeddings.items():
                if player_positions.get(player_name) == position:
                    position_players.append(player_name)
                    position_player_embeddings.append(player_embedding)
            
            if not position_players:
                logger.warning(f"No players found for position {position}")
                continue
            
            # Calculate similarities for this position
            position_embeddings_array = np.array(position_player_embeddings)
            query_embedding_array = query_embedding.reshape(1, -1)
            
            similarities_array = cosine_similarity(query_embedding_array, position_embeddings_array)[0]
            
            # Create list of (player_name, similarity_score) tuples
            position_similarities = list(zip(position_players, similarities_array))
            
            # Sort by similarity score (highest first)
            position_similarities.sort(key=lambda x: x[1], reverse=True)
            
            similarities[position] = position_similarities
            
            logger.info(f"Calculated similarities for {position}: {len(position_similarities)} players")
        
        return similarities
    
    def _extract_keyword_bonus(self, player_name: str, structured_data: Dict) -> float:
        """Extract keyword bonus from player's hints_tips_news"""
        try:
            if player_name in structured_data:
                hints_tips = structured_data[player_name].get('hints_tips_news', '')
                if hints_tips:
                    hints_lower = hints_tips.lower()
                    
                    # Look for keywords at the start of the text
                    if hints_lower.startswith('must-have'):
                        return 0.5  # Increased from 0.3
                    elif hints_lower.startswith('recommended'):
                        return 0.3  # Increased from 0.15
                    elif hints_lower.startswith('rotation risk'):
                        return -0.2  # Increased penalty from -0.1
                    elif hints_lower.startswith('avoid'):
                        return -0.5  # Increased penalty from -0.3
                    
            return 0.0  # Default if no keyword found
            
        except Exception as e:
            logger.warning(f"Failed to extract keyword bonus for {player_name}: {e}")
            return 0.0
    
    def _calculate_hybrid_scores(self, similarities: Dict[str, List[Tuple[str, float]]], 
                               structured_data: Dict) -> Dict[str, List[Tuple[str, float, float, float]]]:
        """Calculate hybrid scores combining embeddings with keyword bonuses"""
        hybrid_scores = {}
        
        for position, player_scores in similarities.items():
            hybrid_position_scores = []
            
            for player_name, embedding_score in player_scores:
                # Get keyword bonus from hints_tips_news
                keyword_bonus = self._extract_keyword_bonus(player_name, structured_data)
                
                # Calculate final hybrid score - giving more weight to keywords
                final_score = 0.6 * embedding_score + 0.4 * keyword_bonus
                
                hybrid_position_scores.append((player_name, final_score, embedding_score, keyword_bonus))
            
            # Sort by hybrid score (descending)
            hybrid_position_scores.sort(key=lambda x: x[1], reverse=True)
            hybrid_scores[position] = hybrid_position_scores
            
            logger.info(f"Calculated hybrid scores for {position}: {len(hybrid_position_scores)} players")
        
        return hybrid_scores
    
    def _select_top_players(self, similarities: Dict[str, List[Tuple[str, float]]], 
                          structured_data: Dict = None) -> List[str]:
        """Select top players per position based on hybrid scores or embedding scores"""
        selected_players = []
        
        if structured_data:
            # Use hybrid scoring
            hybrid_scores = self._calculate_hybrid_scores(similarities, structured_data)
            
            for position, player_scores in hybrid_scores.items():
                count = self.selection_counts.get(position, 0)
                top_players = player_scores[:count]
                
                selected_players.extend([player_name for player_name, _, _, _ in top_players])
                
                logger.info(f"Selected top {len(top_players)} players for {position} using hybrid scoring")
        else:
            # Fallback to original embedding-only scoring
            for position, position_similarities in similarities.items():
                count = self.selection_counts.get(position, 0)
                top_players = position_similarities[:count]
                
                selected_players.extend([player_name for player_name, _ in top_players])
                
                logger.info(f"Selected top {len(top_players)} players for {position} using embedding-only scoring")
        
        logger.info(f"Total selected players: {len(selected_players)}")
        return selected_players
    
    def filter_players_by_position(self, enriched_data: Dict[str, str], 
                                 force_refresh: bool = False) -> Dict[str, str]:
        """
        Filter players using embedding-based similarity scoring.
        
        Args:
            enriched_data: Dictionary of enriched player data
            force_refresh: If True, ignore cache and recompute embeddings
            
        Returns:
            Filtered dictionary of enriched player data
        """
        logger.info("Starting embedding-based player filtering...")
        
        # Try to load cached embeddings first
        if not force_refresh:
            cached_data = self._load_cached_embeddings()
            if cached_data:
                player_embeddings = cached_data.get('embeddings', {})
                if player_embeddings:
                    # Convert string representations back to numpy arrays
                    converted_embeddings = {}
                    for player_name, embedding_str in player_embeddings.items():
                        try:
                            embedding_array = np.array(json.loads(embedding_str))
                            converted_embeddings[player_name] = embedding_array
                        except Exception as e:
                            logger.warning(f"Failed to convert embedding for {player_name}: {e}")
                    
                    if len(converted_embeddings) == len(enriched_data):
                        logger.info("Using cached embeddings for filtering")
                        player_embeddings = converted_embeddings
                    else:
                        logger.info("Cached embeddings don't match current data, recomputing...")
                        player_embeddings = None
                else:
                    player_embeddings = None
            else:
                player_embeddings = None
        else:
            player_embeddings = None
        
        # Encode players if needed
        if player_embeddings is None:
            player_embeddings = self._encode_players(enriched_data)
            
            # Cache the embeddings
            cacheable_embeddings = {}
            for player_name, embedding in player_embeddings.items():
                cacheable_embeddings[player_name] = json.dumps(embedding.tolist())
            
            self._save_embeddings_cache(cacheable_embeddings)
        
        # Encode queries
        query_embeddings = self._encode_queries()
        
        # Get player positions
        player_positions = self._get_player_positions(enriched_data)
        
        # Calculate similarities
        similarities = self._calculate_similarities(player_embeddings, query_embeddings, player_positions)
        
        # Get structured data for hybrid scoring
        structured_data = self._get_structured_data_for_hybrid_scoring(enriched_data)
        
        # Select top players using hybrid scoring
        selected_player_names = self._select_top_players(similarities, structured_data)
        
        # Filter enriched data to only include selected players
        filtered_data = {
            player_name: enriched_data[player_name]
            for player_name in selected_player_names
            if player_name in enriched_data
        }
        
        logger.info(f"Filtering complete: {len(filtered_data)} players selected from {len(enriched_data)} total")
        
        return filtered_data 