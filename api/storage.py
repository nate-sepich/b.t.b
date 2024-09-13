import pandas as pd
import gspread
# from oauth2client.service_account import ServiceAccountCredentials

# # Google Sheets setup
# def initialize_google_sheets(sheet_name: str):
#     scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#     creds = ServiceAccountCredentials.from_json_keyfile_name('path_to_credentials.json', scope)
#     client = gspread.authorize(creds)
#     sheet = client.open(sheet_name).sheet1
#     return sheet

# Function to add a bet to Google Sheets
def add_bet_to_google_sheets(sheet, bet_details: dict):
    bet_data = [
        bet_details['user_id'], bet_details['bet_type'], bet_details['league'], 
        bet_details['date'], bet_details['away_team'], bet_details['home_team'], 
        bet_details['wager_team'], bet_details['odds'], bet_details['bet'], 
        bet_details['risk'], bet_details['payout'], bet_details['outcome'], 
        bet_details['bankroll_before'], bet_details['bankroll_after']
    ]
    sheet.append_row(bet_data)

# Function to get all bets for a user from Google Sheets
def get_user_bets_google_sheets(sheet, user_id: str):
    all_bets = sheet.get_all_records()
    user_bets = [bet for bet in all_bets if bet['user_id'] == user_id]
    return user_bets

# CSV Storage Functions
CSV_FILE_PATH = 'bets.csv'

# Function to add a new bet to a CSV file
def add_bet_to_csv(bet_details: dict):
    df = pd.DataFrame([bet_details])
    df.to_csv(CSV_FILE_PATH, mode='a', header=False, index=False)

# Function to get all bets for a user from a CSV file
def get_user_bets_csv(user_id: str):
    df = pd.read_csv(CSV_FILE_PATH)
    user_bets = df[df['user_id'] == user_id]
    return user_bets.to_dict(orient='records')

# Function to calculate metrics (e.g., win rate, profit/loss)
def calculate_metrics(user_bets):
    total_bets = len(user_bets)
    wins = len([bet for bet in user_bets if bet['outcome'] == 'win'])
    win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
    profit_loss = sum(bet['payout'] - bet['risk'] for bet in user_bets)
    
    return {
        "total_bets": total_bets,
        "win_rate": win_rate,
        "profit_loss": profit_loss
    }
