import boto3

# Or, for a Boto3 service resource
dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

table_name = 'BetsTable'

try:
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'user_id',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'bet_id',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'user_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'bet_id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
except dynamodb.meta.client.exceptions.ResourceInUseException:
    print(f"Table {table_name} already exists.")
