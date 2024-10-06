# External Python Dependencies
from decimal import Decimal
import boto3
from boto3.dynamodb.types import TypeSerializer
from fastapi import FastAPI, HTTPException
# Internal Python Dependencies
from dynamodb.btb import BTBDynamoDB, convert_floats_to_decimals
from service_models.models import BetDetails, UserDetails
from typing import List

# Serialize bet_details to DynamoDB format
serializer = TypeSerializer()

app = FastAPI()
dynamodb_resource = BTBDynamoDB().dynamodb_resource

table_name = 'BetsTable'

bets_table = dynamodb_resource.Table('BetsTable')
users_table = dynamodb_resource.Table('UsersTable')

# Helper Functions
# New Helper Functions for Additional Visibility

def calculate_user_profit_loss(bets: list) -> float:
    """
    Calculate the total profit or loss for a user based on a list of bets.
    """
    total_profit_loss = sum(bet.get("profit_loss", 0) for bet in bets)
    return round(total_profit_loss, 2)

def league_breakdown(bets: list) -> dict:
    """
    Calculate the profit/loss breakdown by league.
    """
    league_summary = {}
    for bet in bets:
        league = bet.get("league", "Unknown")
        profit_loss = bet.get("profit_loss", 0)
        if league not in league_summary:
            league_summary[league] = 0.0
        league_summary[league] += float(profit_loss)
    # Round each league's profit/loss value to 2 decimal places
    league_summary = {league: round(profit, 2) for league, profit in league_summary.items()}
    return league_summary

def bet_type_breakdown(bets: list) -> dict:
    """
    Calculate the profit/loss breakdown by bet type.
    """
    bet_type_summary = {}
    for bet in bets:
        bet_type = bet.get("bet_type", "Unknown")
        profit_loss = bet.get("profit_loss", 0)
        if bet_type not in bet_type_summary:
            bet_type_summary[bet_type] = 0.0
        bet_type_summary[bet_type] += float(profit_loss)
    # Round each bet type's profit/loss value to 2 decimal places
    bet_type_summary = {bet_type: round(profit, 2) for bet_type, profit in bet_type_summary.items()}
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

def calculate_profit_loss(bet_details: BetDetails):
    bet_amount = bet_details.risk
    odds = bet_details.odds
    outcome = bet_details.outcome

    if outcome.upper() == 'WON':
        if odds.startswith('-'):
            print(bet_amount, odds), float(bet_amount) * (100 / float(odds.replace('-','')))
            profit = float(bet_amount) * (100 / float(odds.replace('-','')))
        elif odds.startswith('+'):
            profit = float(bet_amount) * (float(odds.replace('+','')) / 100)
        else:
            profit = profit = Decimal('0.0')
    elif outcome.upper() == 'LOST':
        profit = -float(bet_amount.replace('+','').replace('-',''))
    else:
        profit = 0.0  # For 'PUSH' or other outcomes

    return round(profit, 2)

def update_user_bankroll(user_id, profit_loss):
    # Fetch current bankroll
    response = users_table.get_item(Key={'user_id': user_id})
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="User not found")
    current_bankroll = response['Item'].get('bankroll', 0.0)

    # Update bankroll
    new_bankroll = float(current_bankroll) + profit_loss
    users_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression="SET bankroll = :val",
        ExpressionAttributeValues={':val': round(Decimal(new_bankroll))}
    )

# Bets Endpoints
@app.get("/bets/{user_id}")
def get_user_bets(user_id: str):
    response = bets_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
    )
    if not response.get('Items'):
        raise HTTPException(status_code=404, detail="No bets found for user")
    return response['Items']

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

@app.post("/bets")
def add_bets(bet_details_list: List[BetDetails]):
    bet_ids = []
    with bets_table.batch_writer() as batch:
        for bet_details in bet_details_list:
            # Calculate profit/loss
            profit_loss = calculate_profit_loss(bet_details)
            bet_details.profit_loss = profit_loss

            # Update user's bankroll
            update_user_bankroll(bet_details.user_id, profit_loss)

            bet_details_dict = convert_floats_to_decimals(bet_details.dict())
            batch.put_item(Item=bet_details_dict)
            bet_ids.append(bet_details.bet_id)
    
    return {"message": "Bets added successfully", "bet_ids": bet_ids}

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
    users_table.put_item(Item=user_details.dict())
    return {"message": "User created successfully", "user_id": user_details.user_id}

try:
    user_details = UserDetails(user_id="Nate", bankroll=Decimal('170.00'))
    create_user(user_details)
except HTTPException as e:
    if e.status_code == 400 and "User already exists" in e.detail:
        print("User already exists, continuing with application startup.")
    else:
        raise e

@app.put("/users/{user_id}/bankroll")
def update_bankroll(user_details: UserDetails, amount: float):
    # Update the bankroll
    response = users_table.update_item(
        Key={'user_id': user_details.user_id},
        UpdateExpression="SET bankroll = :val",
        ExpressionAttributeValues={':val': amount},
        ReturnValues="UPDATED_NEW"
    )
    return response['Attributes']