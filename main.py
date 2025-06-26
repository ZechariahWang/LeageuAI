import requests
import json
import time
import random
import os
import sys
from riotwatcher import RiotWatcher
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('RIOT_API_KEY')
if not api_key:
    print("Error: RIOT_API_KEY not found in .env file")
    sys.exit(1)

class Match:
    def __init__(self, match_id, region, player_puuid):
        self.match_id = match_id
        self.region = region
        self.player_puuid = player_puuid
        self.match_data = None

    def fetch_match_data(self):
        url = f"https://{self.region}.api.riotgames.com/lol/match/v5/matches/{self.match_id}"
        headers = {
            'X-Riot-Token': api_key
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            self.match_data = response.json()
        except requests.RequestException as e:
            print(f"Error fetching match data for {self.match_id}: {e}")
            self.match_data = None

def get_puuid(game_name, tag_line, region):
    watcher = RiotWatcher(api_key)
    
    try:
        account = watcher.account.by_riot_id(region, game_name, tag_line)
        if hasattr(account, 'json'):
            puuid = account.json()['puuid']
        else:
            puuid = account['puuid']
        return puuid
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_match_history(puuid, region, count=20):
    try:
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            'start': 0,
            'count': count
        }
        headers = {
            'X-Riot-Token': api_key
        }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error getting match history: {e}")
        return None

def get_match_details(match_id, region):
    try:
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        headers = {
            'X-Riot-Token': api_key
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error getting match details for {match_id}: {e}")
        return None

def get_summoner_id_from_puuid(puuid, region):
    try:
        region_map = {
            'americas': 'na1',
            'asia': 'kr',
            'europe': 'euw1',
            'sea': 'oc1'
        }
        
        platform = region_map.get(region, 'na1')
        url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        headers = {
            'X-Riot-Token': api_key
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()['id']
    except Exception as e:
        print(f"Error getting summoner ID: {e}")
        return None

def get_rank_info(summoner_id, region):
    try:
        region_map = {
            'americas': 'na1',
            'asia': 'kr',
            'europe': 'euw1',
            'sea': 'oc1'
        }
        
        platform = region_map.get(region, 'na1')
        url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        headers = {
            'X-Riot-Token': api_key
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        rank_data = response.json()
        
        ranks = {}
        for entry in rank_data:
            queue_type = entry['queueType']
            if queue_type == 'RANKED_SOLO_5x5':
                ranks['solo'] = {
                    'tier': entry['tier'],
                    'rank': entry['rank'],
                    'lp': entry['leaguePoints'],
                    'wins': entry['wins'],
                    'losses': entry['losses']
                }
            elif queue_type == 'RANKED_FLEX_SR':
                ranks['flex'] = {
                    'tier': entry['tier'],
                    'rank': entry['rank'],
                    'lp': entry['leaguePoints'],
                    'wins': entry['wins'],
                    'losses': entry['losses']
                }
        
        return ranks
    except Exception as e:
        print(f"Error getting rank info: {e}")
        return {}

def analyze_match_history(puuid, region, count=5):
    print(f"Analyzing last {count} matches...")
    
    match_list = get_match_history(puuid, region, count)
    if not match_list:
        print("No match history found")
        return
    
    print(f"Found {len(match_list)} matches")
    
    for i, match_id in enumerate(match_list[:count], 1):
        print(f"\n--- Match {i}: {match_id} ---")
        match_data = get_match_details(match_id, region)
        
        if match_data:
            info = match_data['info']
            print(f"Game Mode: {info['gameMode']}")
            print(f"Game Duration: {info['gameDuration']} seconds")
            print(f"Game Creation: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info['gameCreation']/1000))}")
            
            for participant in info['participants']:
                if participant['puuid'] == puuid:
                    print(f"Champion: {participant['championName']}")
                    print(f"KDA: {participant['kills']}/{participant['deaths']}/{participant['assists']}")
                    print(f"Win: {'Yes' if participant['win'] else 'No'}")
                    break
        
        time.sleep(1)
        

def get_player_info(player_number):
    print(f"\n--- Player {player_number} Information ---")
    print("Valid regions: americas, asia, europe, sea")
    print("Region examples:")
    print("  - americas: North America, Brazil, Latin America")
    print("  - asia: Korea, Japan")
    print("  - europe: EUW, EUNE, Turkey, Russia")
    print("  - sea: Southeast Asia, Oceania")
    
    game_name = input(f"Enter the game name for Player {player_number}: ")
    tag_line = input(f"Enter the tag line for Player {player_number} (e.g., NA1): ")
    
    valid_regions = ['americas', 'asia', 'europe', 'sea']
    while True:
        region = input(f"Enter the region for Player {player_number} (americas/asia/europe/sea): ").lower()
        if region in valid_regions:
            break
        print(f"Invalid region '{region}'. Please choose from: {', '.join(valid_regions)}")
    
    return game_name, tag_line, region

def format_rank(rank_data, queue_type):
    if queue_type not in rank_data:
        return "Unranked"
    
    rank = rank_data[queue_type]
    tier = rank['tier'].capitalize()
    division = rank['rank']
    lp = rank['lp']
    wins = rank['wins']
    losses = rank['losses']
    total_games = wins + losses
    winrate = (wins / total_games * 100) if total_games > 0 else 0
    
    return f"{tier} {division} ({lp} LP) - {wins}W/{losses}L ({winrate:.1f}%)"

def compare_matches(player1_matches, player2_matches, player1_name, player2_name, player1_ranks=None, player2_ranks=None):
    print(f"\n{'='*60}")
    print(f"PLAYER COMPARISON: {player1_name} vs {player2_name}")
    print(f"{'='*60}")
    
    if player1_ranks or player2_ranks:
        print(f"\nRank Comparison:")
        if player1_ranks:
            solo_rank = format_rank(player1_ranks, 'solo')
            flex_rank = format_rank(player1_ranks, 'flex')
            print(f"{player1_name}:")
            print(f"  Solo/Duo: {solo_rank}")
            print(f"  Flex: {flex_rank}")
        else:
            print(f"{player1_name}: Rank data unavailable")
            
        if player2_ranks:
            solo_rank = format_rank(player2_ranks, 'solo')
            flex_rank = format_rank(player2_ranks, 'flex')
            print(f"{player2_name}:")
            print(f"  Solo/Duo: {solo_rank}")
            print(f"  Flex: {flex_rank}")
        else:
            print(f"{player2_name}: Rank data unavailable")
    
    player1_wins = sum(1 for match in player1_matches if match.get('win', False))
    player2_wins = sum(1 for match in player2_matches if match.get('win', False))
    
    print(f"\nRecent Performance (Last 3 matches):")
    print(f"{player1_name}: {player1_wins}/3 wins ({player1_wins/3*100:.1f}%)")
    print(f"{player2_name}: {player2_wins}/3 wins ({player2_wins/3*100:.1f}%)")
    
    player1_total_kda = sum(match.get('kills', 0) + match.get('assists', 0) for match in player1_matches)
    player1_total_deaths = sum(match.get('deaths', 0) for match in player1_matches)
    player2_total_kda = sum(match.get('kills', 0) + match.get('assists', 0) for match in player2_matches)
    player2_total_deaths = sum(match.get('deaths', 0) for match in player2_matches)
    
    player1_avg_kda = player1_total_kda / max(player1_total_deaths, 1)
    player2_avg_kda = player2_total_kda / max(player2_total_deaths, 1)
    
    print(f"\nAverage KDA Ratio:")
    print(f"{player1_name}: {player1_avg_kda:.2f}")
    print(f"{player2_name}: {player2_avg_kda:.2f}")
    
    print(f"\nDetailed Match Breakdown:")
    for i, (match1, match2) in enumerate(zip(player1_matches, player2_matches), 1):
        print(f"\nMatch {i}:")
        print(f"  {player1_name}: {match1.get('championName', 'Unknown')} | "
              f"{match1.get('kills', 0)}/{match1.get('deaths', 0)}/{match1.get('assists', 0)} | "
              f"{'WIN' if match1.get('win', False) else 'LOSS'}")
        print(f"  {player2_name}: {match2.get('championName', 'Unknown')} | "
              f"{match2.get('kills', 0)}/{match2.get('deaths', 0)}/{match2.get('assists', 0)} | "
              f"{'WIN' if match2.get('win', False) else 'LOSS'}")

def get_player_match_data(puuid, region, game_name, count=3):
    match_list = get_match_history(puuid, region, count)
    if not match_list:
        print(f"No match history found for {game_name}")
        return []
    
    player_matches = []
    for match_id in match_list[:count]:
        match_data = get_match_details(match_id, region)
        if match_data:
            for participant in match_data['info']['participants']:
                if participant['puuid'] == puuid:
                    player_matches.append(participant)
                    break
        time.sleep(0.5)
    
    return player_matches

def main():
    print("Riot API Player Comparison Tool")
    print("This tool compares the last 3 matches and ranks of two players")
    
    try:
        player1_name, player1_tag, player1_region = get_player_info(1)
        player2_name, player2_tag, player2_region = get_player_info(2)
        
        print(f"\nGetting PUUID for {player1_name}#{player1_tag}...")
        player1_puuid = get_puuid(player1_name, player1_tag, player1_region)
        if not player1_puuid:
            print(f"Could not retrieve PUUID for Player 1. Please check the name and tag.")
            return
        
        print(f"Getting PUUID for {player2_name}#{player2_tag}...")
        player2_puuid = get_puuid(player2_name, player2_tag, player2_region)
        if not player2_puuid:
            print(f"Could not retrieve PUUID for Player 2. Please check the name and tag.")
            return
        
        print(f"\nGetting rank information for {player1_name}...")
        player1_summoner_id = get_summoner_id_from_puuid(player1_puuid, player1_region)
        player1_ranks = get_rank_info(player1_summoner_id, player1_region) if player1_summoner_id else None
        
        print(f"Getting rank information for {player2_name}...")
        player2_summoner_id = get_summoner_id_from_puuid(player2_puuid, player2_region)
        player2_ranks = get_rank_info(player2_summoner_id, player2_region) if player2_summoner_id else None
        
        print(f"\nFetching last 3 matches for {player1_name}...")
        player1_matches = get_player_match_data(player1_puuid, player1_region, player1_name)
        
        print(f"Fetching last 3 matches for {player2_name}...")
        player2_matches = get_player_match_data(player2_puuid, player2_region, player2_name)
        
        if len(player1_matches) < 3 or len(player2_matches) < 3:
            print("Warning: One or both players don't have 3 recent matches available.")
        
        compare_matches(player1_matches, player2_matches, f"{player1_name}#{player1_tag}", f"{player2_name}#{player2_tag}", player1_ranks, player2_ranks)
        
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

