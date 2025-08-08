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
            'GK': "Must-have and recommended players that are fit are highly desirable. Expected to score high fantasy points, consistent starter, with strong clean sheet potential. Avoid players that are out of form, injured or suspended.",
            'DEF': "Must-have and recommended players that are fit are highly desirable. Expected to score high fantasy points, with clean sheet and attacking potential, good fixtures. Avoid players that are out of form, injured or suspended.",  
            'MID': "Must-have and recommended players that are fit are highly desirable. Expected to score high fantasy points from goals or assists, consistent starter, on set pieces or penalties is a plus. Avoid players that are out of form, injured or suspended.",
            'FWD': "Must-have and recommended players that are fit are highly desirable. Expected to score high fantasy points from goals, consistent starter, good form and fixtures. Avoid players that are out of form, injured or suspended."
        }
        self.selection_counts = {
            'GK': 15,
            'DEF': 45,
            'MID': 45,
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
        
        # Try to get structured data for position extraction
        try:
            from .llm_strategy import LLMStrategy
            from ..core.config import Config
            
            # Create a minimal config and strategy to access cached data
            config = Config()
            strategy = LLMStrategy(config)
            structured_data = strategy.get_enriched_player_data(force_refresh=False)
            
            # Use structured data for position extraction when available
            for player_name in enriched_data.keys():
                if player_name in structured_data and isinstance(structured_data[player_name], dict) and "data" in structured_data[player_name]:
                    position = structured_data[player_name]["data"]["position"]
                    player_positions[player_name] = position
                else:
                    # Fallback to string parsing for legacy data
                    enriched_text = enriched_data[player_name]
                    try:
                        # Use regex to extract position (second group after opening parenthesis)
                        import re
                        match = re.search(r'\(([^,]+),\s*([^,]+),', enriched_text)
                        if match:
                            position = match.group(2).strip()
                            player_positions[player_name] = position
                        else:
                            logger.warning(f"Could not extract position for {player_name}")
                            player_positions[player_name] = 'MID'  # Default fallback
                    except Exception as e:
                        logger.warning(f"Failed to extract position for {player_name}: {e}")
                        player_positions[player_name] = 'MID'  # Default fallback
            
        except Exception as e:
            logger.warning(f"Failed to access structured data for position extraction: {e}")
            # Fallback to original string parsing method
            for player_name, enriched_text in enriched_data.items():
                try:
                    # Use regex to extract position (second group after opening parenthesis)
                    import re
                    match = re.search(r'\(([^,]+),\s*([^,]+),', enriched_text)
                    if match:
                        position = match.group(2).strip()
                        player_positions[player_name] = position
                    else:
                        logger.warning(f"Could not extract position for {player_name}")
                        player_positions[player_name] = 'MID'  # Default fallback
                except Exception as e:
                    logger.warning(f"Failed to extract position for {player_name}: {e}")
                    player_positions[player_name] = 'MID'  # Default fallback
        
        return player_positions
    
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
    
    def _select_top_players(self, similarities: Dict[str, List[Tuple[str, float]]]) -> List[str]:
        """Select top players per position based on similarity scores"""
        selected_players = []
        
        for position, position_similarities in similarities.items():
            count = self.selection_counts.get(position, 0)
            top_players = position_similarities[:count]
            
            selected_players.extend([player_name for player_name, _ in top_players])
            
            logger.info(f"Selected top {len(top_players)} players for {position}")
        
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
        
        # Select top players
        selected_player_names = self._select_top_players(similarities)
        
        # Filter enriched data to only include selected players
        filtered_data = {
            player_name: enriched_data[player_name]
            for player_name in selected_player_names
            if player_name in enriched_data
        }
        
        logger.info(f"Filtering complete: {len(filtered_data)} players selected from {len(enriched_data)} total")
        
        return filtered_data 