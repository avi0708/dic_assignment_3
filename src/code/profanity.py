import os
import boto3
from profanityfilter import ProfanityFilter

pf = ProfanityFilter()

s3 = boto3.client('s3', endpoint_url=os.getenv('LOCALSTACK_ENDPOINT'))
dynamodb = boto3.client('dynamodb', endpoint_url=os.getenv('LOCALSTACK_ENDPOINT'))
ssm = boto3.client('ssm', endpoint_url=os.getenv('LOCALSTACK_ENDPOINT'))

def handler(event, context):
    reviews_table = ssm.get_parameter(Name='/review-app/tables/reviews')['Parameter']['Value']
    users_table = ssm.get_parameter(Name='/review-app/tables/users')['Parameter']['Value']
    
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            review_id = record['dynamodb']['Keys']['reviewId']['S']
            review = record['dynamodb']['NewImage']
            
            # Check for profanity
            has_profanity = (
                pf.is_profane(review['processedSummary']['S']) or 
                pf.is_profane(review['processedText']['S'])
            )
            
            # Update review with profanity check result
            dynamodb.update_item(
                TableName=reviews_table,
                Key={'reviewId': {'S': review_id}},
                UpdateExpression='SET profanityCheck = :val',
                ExpressionAttributeValues={':val': {'BOOL': has_profanity}}
            )
            
            # Get the reviewerID
            reviewer_ID = review['reviewerID']['N']
            
            # Update or Insert default values for new users
            response = dynamodb.update_item(
                TableName=users_table,
                Key={'reviewerID': {'N': reviewer_ID}},
                UpdateExpression='''
                    SET unpoliteCount = if_not_exists(unpoliteCount, :default_count),
                        banned = if_not_exists(banned, :default_banned)
                    ADD unpoliteCount :inc
                ''',
                ExpressionAttributeValues={
                    ':default_count': {'N': '0'},
                    ':default_banned': {'BOOL': False},
                    ':inc': {'N': '1' if has_profanity else '0'}  # Only increment unpoliteCount if profanity is found
                },
                ReturnValues='ALL_NEW'
            )
            
            # Get the updated unpolite count
            unpolite_count = int(response['Attributes'].get('unpoliteCount', {'N': '0'})['N'])
            
            # Check if user should be banned
            if unpolite_count > 3:
                dynamodb.update_item(
                    TableName=users_table,
                    Key={'reviewerID': {'N': reviewer_ID}},
                    UpdateExpression='SET banned = :true',
                    ExpressionAttributeValues={':true': {'BOOL': True}}
                )
            return {'statusCode': 200}
        continue
