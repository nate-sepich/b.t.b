from decimal import Decimal
import decimal
import logging
import boto3
from boto3.dynamodb.types import TypeSerializer
from fastapi import FastAPI, HTTPException
from dynamodb.btb import BTBDynamoDB, convert_floats_to_decimals
from service_models.models import BetDetails, UserDetails
from typing import List

# Serialize bet_details to DynamoDB format
serializer = TypeSerializer()

app = FastAPI()
dynamodb_resource = BTBDynamoDB().dynamodb_resource

bets_table = dynamodb_resource.Table('BetsTable')
users_table = dynamodb_resource.Table('UsersTable')

# Configure logging to output to standard output
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# Helper Functions
def convert_floats_to_decimals(item):
    """
    Recursively convert all floats in a dictionary to Decimals.
    """
    if isinstance(item, list):
        return [convert_floats_to_decimals(i) for i in item]
    elif isinstance(item, dict):
        return {k: convert_floats_to_decimals(v) for k, v in item.items()}
    elif isinstance(item, float):
        return Decimal(str(item))
    return item

def calculate_user_profit_loss(bets: list) -> Decimal:
    """
    Calculate the total profit or loss for a user based on a list of bets.
    """
    total_profit_loss = sum(Decimal(str(bet.get("profit_loss", 0))) for bet in bets)
    return total_profit_loss

def league_breakdown(bets: list) -> dict:
    """
    Calculate the profit/loss breakdown by league.
    """
    league_summary = {}
    for bet in bets:
        league = bet.get("league", "Unknown")
        profit_loss = Decimal(str(bet.get("profit_loss", 0)))
        if league not in league_summary:
            league_summary[league] = Decimal('0.0')
        league_summary[league] += profit_loss
    # Round each league's profit/loss value to 4 decimal places
    league_summary = {league: round(profit, 4) for league, profit in league_summary.items()}
    return league_summary

def bet_type_breakdown(bets: list) -> dict:
    """
    Calculate the profit/loss breakdown by bet type.
    """
    bet_type_summary = {}
    for bet in bets:
        bet_type = bet.get("bet_type", "Unknown")
        profit_loss = Decimal(str(bet.get("profit_loss", 0)))
        if bet_type not in bet_type_summary:
            bet_type_summary[bet_type] = Decimal('0.0')
        bet_type_summary[bet_type] += profit_loss
    # Round each bet type's profit/loss value to 4 decimal places
    bet_type_summary = {bet_type: round(profit, 4) for bet_type, profit in bet_type_summary.items()}
    return bet_type_summary

def get_bets_summary(bets: list) -> dict:
    """
    Generate a summary of various metrics for a user's bets.
    """
    summary = {
        "total_profit_loss": calculate_user_profit_loss(bets),
        "league_breakdown": league_breakdown(bets),
        "bet_type_breakdown": bet_type_breakdown(bets)
    }
    return summary

def calculate_profit_loss(bet_details: BetDetails) -> Decimal:
    """
    Calculate the profit or loss for a bet based on American odds.
    
    Parameters:
    - bet_details (BetDetails): Details of the bet including odds, stake, and outcome.
    
    Returns:
    - Decimal: The profit or loss calculated based on the bet details.
    """
    def parse_decimal(value):
        """
        Parse a value into a Decimal, removing any currency symbols or commas.
        """
        try:
            return Decimal(str(value).replace('$', '').replace(',', ''))
        except (ValueError, decimal.InvalidOperation):
            logging.error(f"Invalid decimal value: {value}")
            return Decimal('0.0')

    # Extract the stake and odds from the bet details
    stake = parse_decimal(bet_details.stake)
    odds = bet_details.odds
    outcome = bet_details.outcome.upper()

    # Calculate profit based on American odds
    if outcome == 'WON':
        try:
            # For negative American odds (e.g., -120), the formula is stake * (100 / |odds|)
            if odds.startswith('-'):
                profit = stake * (Decimal('100') / Decimal(odds.replace('-', '')))
            # For positive American odds (e.g., +120), the formula is stake * (odds / 100)
            elif odds.startswith('+'):
                profit = stake * (Decimal(odds.replace('+', '')) / Decimal('100'))
            else:
                profit = Decimal('0.0')
        except (ValueError, decimal.InvalidOperation):
            logging.error(f"Invalid odds: {odds}")
            profit = Decimal('0.0')
    elif outcome == 'LOST':
        # If the bet is lost, the profit is negative the stake (loss)
        profit = -stake
    else:
        # For other outcomes like 'PUSH', no profit or loss
        profit = Decimal('0.0')

    logging.info(f"Calculated profit/loss for bet {bet_details.bet_id}: {profit}")
    return profit

def update_user_bankroll(user_id, profit_loss):
    # Fetch current bankroll
    response = users_table.get_item(Key={'user_id': user_id})
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Ensure bankroll is a Decimal
    current_bankroll = Decimal(str(response['Item'].get('bankroll', 0.0)))
    
    # Ensure profit_loss is a Decimal
    profit_loss = Decimal(str(profit_loss))
    
    # Update bankroll
    new_bankroll = current_bankroll + profit_loss
    users_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression="SET bankroll = :val",
        ExpressionAttributeValues={':val': new_bankroll}
    )

# Bets Endpoints
@app.post("/bets")
def add_bets(bet_details_list: List[BetDetails]):
    succeeded_bets = []
    failed_bets = []
    bet_ids = set()
    with bets_table.batch_writer() as batch:
        for bet_details in bet_details_list:
            try:
                # Calculate profit/loss
                profit_loss = calculate_profit_loss(bet_details)
                bet_details.profit_loss = profit_loss

                # Update user's bankroll
                update_user_bankroll(bet_details.user_id, profit_loss)

                bet_details_dict = convert_floats_to_decimals(bet_details.dict())
                batch.put_item(Item=bet_details_dict)
                bet_ids.add(bet_details.bet_id)
                succeeded_bets.append(bet_details.bet_id)
                logging.info(f"Bet {bet_details.bet_id} Processed: {bet_details.selection} - {bet_details.bet_type} - {bet_details.outcome} - {bet_details.profit_loss}")
            except Exception as e:
                logging.error(f"Error processing bet {bet_details.bet_id}: {e}")
                failed_bets.append(bet_details.bet_id)
    
    return {
        "message": "Bets uploaded to DynamoDB - BetsTable",
        "succeeded_bets": succeeded_bets,
        "failed_bets": failed_bets
    }

@app.get("/bets/{user_id}/summary")
def get_user_bets_summary(user_id: str):
    response = bets_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
    )
    if not response.get('Items'):
        raise HTTPException(status_code=404, detail="No bets found for user")
    
    bets = response['Items']
    summary = get_bets_summary(bets)
    return summary

# Users Endpoints
@app.get("/users/{user_id}")
def get_user(user_id: str):
    response = users_table.get_item(
        Key={'user_id': user_id}
    )
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="User not found")
    return response['Item']

@app.post("/users")
def create_user(user_details: UserDetails):
    # Check if user already exists
    response = users_table.get_item(Key={'user_id': user_details.user_id})
    if 'Item' in response:
        raise HTTPException(status_code=400, detail="User already exists")
    users_table.put_item(Item=convert_floats_to_decimals(user_details.dict()))
    return {"message": "User created successfully", "user_id": user_details.user_id}

try:
    user_details = UserDetails(user_id="X", bankroll=Decimal('100.00'))
    create_user(user_details)
except HTTPException as e:
    if e.status_code == 400 and "User already exists" in e.detail:
        # print("User already exists, continuing with application startup.")
        pass
    else:
        raise e

@app.put("/users/{user_id}/bankroll")
def update_bankroll(user_details: UserDetails):
    # Update the bankroll
    response = users_table.update_item(
        Key={'user_id': user_details.user_id},
        UpdateExpression="SET bankroll = :val",
        ExpressionAttributeValues={':val': Decimal(str(user_details.bankroll))},
        ReturnValues="UPDATED_NEW"
    )
    return response['Attributes']
