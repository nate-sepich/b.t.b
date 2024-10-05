# dynamodb/btb.py

import boto3
from decimal import Decimal

def convert_floats_to_decimals(obj):
    if isinstance(obj, list):
        return [convert_floats_to_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return round(Decimal(str(obj)))
    else:
        return obj


class BTBDynamoDB():
    def __init__(self):
        self.dynamodb_resource = boto3.resource('dynamodb', region_name='us-west-2', endpoint_url='http://172.17.0.1:9005')
        self.dynamodb_client = boto3.client('dynamodb', region_name='us-west-2', endpoint_url='http://172.17.0.1:9005')
        self.create_bets_table('BetsTable')
        self.create_users_table('UsersTable')
    
    def create_bets_table(self, table_name):
        existing_tables = [table.name for table in self.dynamodb_resource.tables.all()]
        if table_name not in existing_tables:
            table = self.dynamodb_resource.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'bet_id', 'KeyType': 'RANGE'}   # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'bet_id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
            )
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

    def create_users_table(self, table_name):
        existing_tables = [table.name for table in self.dynamodb_resource.tables.all()]
        if table_name not in existing_tables:
            table = self.dynamodb_resource.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
