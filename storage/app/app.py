# External Python Dependencies
from decimal import Decimal
import boto3
from boto3.dynamodb.types import TypeSerializer
from fastapi import FastAPI, HTTPException
import uuid
# Internal Python Dependencies
from dynamodb.btb import BTBDynamoDB, convert_floats_to_decimals
from service_models.models import BetDetails, UserDetails

# Serialize bet_details to DynamoDB format
serializer = TypeSerializer()

app = FastAPI()
dynamodb_resource = BTBDynamoDB().dynamodb_resource

table_name = 'BetsTable'

bets_table = dynamodb_resource.Table('BetsTable')
users_table = dynamodb_resource.Table('UsersTable')

# Helper Functions
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

@app.post("/bets")
def add_bet(bet_details: BetDetails):
    # Calculate profit/loss
    profit_loss = calculate_profit_loss(bet_details)
    bet_details.profit_loss = profit_loss

    # Update user's bankroll
    update_user_bankroll(bet_details.user_id, profit_loss)

    bet_details = convert_floats_to_decimals(bet_details.dict())
    bets_table.put_item(Item=bet_details)
    return {"message": "Bet added successfully", "bet_id": bet_details['bet_id']}

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