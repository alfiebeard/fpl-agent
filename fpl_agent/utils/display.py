"""
Display utilities for FPL team results and data
"""

from typing import Dict, Any
from datetime import datetime


def display_data_status(data_status: Dict[str, Any]) -> None:
    """
    Display comprehensive data status information.
    
    Args:
        data_status: Dictionary containing data status information
    """
    print("📊 FPL Data Status")
    print("=" * 50)
    
    # FPL Data Status
    print(f"\n🔄 FPL Data:")
    if data_status['fpl_data']['available']:
        age = data_status['fpl_data']['age_hours']
        status = "✅ Fresh" if data_status['fpl_data']['fresh'] else "⚠️  Stale"
        print(f"   • Status: {status}")
        print(f"   • Age: {age:.1f} hours")
        print(f"   • Last updated: {datetime.now().timestamp() - (age * 3600):.0f} seconds ago")
    else:
        print("   • Status: ❌ Not available")
        print("   • Action: Run 'fetch' command")
    
    # Enriched Data Status
    print(f"\n🧠 Enriched Data:")
    if data_status['enriched_data']['available']:
        age = data_status['enriched_data']['age_hours']
        status = "✅ Fresh" if data_status['enriched_data']['fresh'] else "⚠️  Stale"
        print(f"   • Status: {status}")
        print(f"   • Age: {age:.1f} hours")
        print(f"   • Last updated: {datetime.now().timestamp() - (age * 3600):.0f} seconds ago")
    else:
        print("   • Status: ❌ Not available")
        print("   • Action: Run 'enrich' command")
    
    # Embeddings Status
    print(f"\n🔍 Embeddings:")
    if data_status['embeddings']['available']:
        age = data_status['embeddings']['age_hours']
        status = "✅ Fresh" if data_status['embeddings']['fresh'] else "⚠️  Stale"
        print(f"   • Status: {status}")
        print(f"   • Age: {age:.1f} hours")
    else:
        print("   • Status: ❌ Not available")
    
    # Overall Status
    print(f"\n📋 Overall Status:")
    overall = data_status['overall_status']
    if overall == 'fresh':
        print("   • Status: ✅ All data is fresh and ready")
        print("   • Action: Ready for team building/updates")
    elif overall == 'stale':
        print("   • Status: ⚠️  Data is available but stale")
        print("   • Action: Consider running 'gw-update' or 'build-team' with --force-all")
    elif overall == 'partial':
        print("   • Status: ⚠️  Partial data available")
        print("   • Action: Run 'enrich' to complete data preparation")
    elif overall == 'fpl_only':
        print("   • Status: ⚠️  Only FPL data available")
        print("   • Action: Run 'enrich' to add LLM insights")
    else:
        print("   • Status: ❌ No data available")
        print("   • Action: Run 'fetch' to get started")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if data_status['overall_status'] == 'fresh':
        print("   • All data is fresh - ready for team operations")
    elif data_status['overall_status'] in ['stale', 'partial']:
        print("   • Run 'gw-update' for complete weekly refresh")
        print("   • Or run 'build-team' with --force-all for fresh team")
    else:
        print("   • Start with 'fetch' to get FPL data")
        print("   • Then 'enrich' to add insights")
        print("   • Finally 'build-team' or 'gw-update'")

def display_fetch_results(result: Dict[str, Any], use_cached: bool = False) -> None:
    """Display fetch operation results to the user"""
    if use_cached:
        print(f"📊 Loaded cached FPL data:")
    else:
        print(f"🔄 Fetched fresh FPL data:")
    
    print(f"   • Players: {result['total_players']}")
    print(f"   • Fixtures: {result['total_fixtures']}")
    print(f"   • Fetched at: {result['fetched_at']}")
    print("✅ Data fetch complete!")


def display_comprehensive_team_result(result: Dict[str, Any]) -> None:
    """Display comprehensive team creation/update results"""
    print("✅ Team building complete!")
    print("\n" + "=" * 80)
    print("FPL COMPREHENSIVE TEAM RESULT")
    print("=" * 80)
    
    # Handle different data structures
    # The result might be wrapped in 'team_data' or directly contain the team info
    if 'team_data' in result:
        team_data_wrapper = result['team_data']
    else:
        team_data_wrapper = result
    
    # Extract team data - handle both nested and flat structures
    if 'team' in team_data_wrapper:
        # Nested structure: team_data_wrapper['team'] contains the actual team
        team_data = team_data_wrapper['team']
        # Captain, vice_captain, etc. are at the same level as 'team'
        captain = team_data_wrapper.get('captain', 'Unknown')
        vice_captain = team_data_wrapper.get('vice_captain', 'Unknown')
        total_cost = team_data_wrapper.get('total_cost', 0.0)
        bank = team_data_wrapper.get('bank', 0.0)
        expected_points = team_data_wrapper.get('expected_points', 0.0)
    else:
        # Flat structure: everything is at the top level
        team_data = team_data_wrapper
        captain = team_data_wrapper.get('captain', 'Unknown')
        vice_captain = team_data_wrapper.get('vice_captain', 'Unknown')
        total_cost = team_data_wrapper.get('total_cost', 0.0)
        bank = team_data_wrapper.get('bank', 0.0)
        expected_points = team_data_wrapper.get('expected_points', 0.0)
    
    # Display basic info
    print("\n" + "=" * 80)
    print("LLM RESPONSE")
    print("=" * 80)
    print(f"Method: Unknown")
    print(f"\nCaptain: {captain}")
    print(f"Vice Captain: {vice_captain}")
    print(f"Total Cost: £{total_cost}m")
    print(f"Bank: £{bank}m")
    print(f"Expected Points: {expected_points}")
    
    # Display team selection reasoning
    print("\n" + "=" * 80)
    print("TEAM SELECTION REASONING")
    print("=" * 80)
    
    # Display raw LLM response
    raw_response = team_data_wrapper.get('raw_llm_response', '')
    if raw_response:
        print("\n" + "=" * 80)
        print("RAW LLM RESPONSE")
        print("=" * 80)
        print(raw_response)
    
    # Display starting 11
    starting = team_data.get('starting', [])
    if starting:
        print("\n" + "=" * 80)
        print("STARTING 11")
        print("=" * 80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6}")
        print("-" * 80)
        
        for player in starting:
            name = player.get('name', 'Unknown')
            team = player.get('team', 'Unknown')
            position = player.get('position', 'UNK')
            price = player.get('price', 0.0)
            reason = player.get('reason', '')
            
            # Add captain/vice-captain indicators
            if name == captain:
                name += " (C)"
            elif name == vice_captain:
                name += " (VC)"
            
            print(f"{name:<25} {team:<15} {position:<4} £{price:<5}")
            if reason:
                print(f"  └─ {reason}")
            print()
    
    # Display substitutes
    substitutes = team_data.get('substitutes', [])
    if substitutes:
        print("=" * 80)
        print("SUBSTITUTES")
        print("=" * 80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Sub Order':<10}")
        print("-" * 80)
        
        for player in substitutes:
            name = player.get('name', 'Unknown')
            team = player.get('team', 'Unknown')
            position = player.get('position', 'UNK')
            price = player.get('price', 0.0)
            sub_order = player.get('sub_order', '')
            reason = player.get('reason', '')
            
            # Format sub order
            if sub_order is None:
                sub_order = 'GK'
            elif sub_order == '':
                sub_order = '-'
            
            print(f"{name:<25} {team:<15} {position:<4} £{price:<5} {sub_order:<10}")
            if reason:
                print(f"  └─ {reason}")
            print()
    
    print("=" * 80)
    print(f"Comprehensive team operation completed at: {datetime.now()}")
    print("=" * 80)
