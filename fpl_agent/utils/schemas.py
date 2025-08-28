from google.genai import types

def create_player_schema(player_list : list[str]) -> dict:
    """
    Generate a ResponseSchema object based on a dynamic list of player names.
    This should ensure enforcement to the player names in the JSON response.

    Args:
        player_list (list[str]): List of player names.

    Returns:
        dict: Schema object for LLM.
    """
    # Construct the JSON schema properties
    properties = {player: {"type": "string"} for player in player_list}
    
    schema = {
        "type": "object",
        "properties": properties,
        "required": player_list
    }
    
    return schema