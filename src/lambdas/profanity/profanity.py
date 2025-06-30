import os
import boto3
from profanityfilter import ProfanityFilter

pf = ProfanityFilter()

endpoint_url = None
if os.getenv("STAGE") == "local":
    endpoint_url = "http://localhost.localstack.cloud:4566"

s3 = boto3.client("s3", endpoint_url=endpoint_url)
ssm = boto3.client("ssm", endpoint_url=endpoint_url)
dynamodb = boto3.client("dynamodb",endpoint_url=endpoint_url)


def handler(event, context):
    reviews_table = ssm.get_parameter(Name='/review-app/tables/reviews')['Parameter']['Value']
    users_table = ssm.get_parameter(Name='/review-app/tables/users')['Parameter']['Value']
    
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            review_id = record['dynamodb']['Keys']['reviewId']['S']
            reviewer_id = record['dynamodb']['Keys']['reviewerID']['S']
            review = record['dynamodb']['NewImage']
            
            # Check for profanity
            has_profanity = (
                pf.is_profane(review['processedreviewText']['S']) or 
                pf.is_profane(review['processedSummary']['S'])
            )
            
            # Update review with profanity check result
            dynamodb.update_item(
                TableName=reviews_table,
                Key={
                    'reviewerID': {'S': reviewer_id},
                    'reviewId': {'S': review_id}
                    },
                UpdateExpression='SET profanityCheck = :val',
                ExpressionAttributeValues={':val': {'BOOL': has_profanity}}
            )
            update_expression = '''
                SET unpoliteCount = if_not_exists(unpoliteCount, :default_count),
                    banned = if_not_exists(banned, :default_banned)
            '''
            expression_values = {
                ':default_count': {'N': '0'},
                ':default_banned': {'BOOL': False}
            }

            # Increment unpoliteCount only if profanity is found
            if has_profanity:
                update_expression += ' ADD unpoliteCount :inc'
                expression_values[':inc'] = {'N': '1'}

            # Update or Insert default values for new users
            response = dynamodb.update_item(
                TableName=users_table,
                Key={'reviewerID': {'S': reviewer_id}},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            # Get the updated unpolite count
            unpolite_count = int(response['Attributes'].get('unpoliteCount', {'N': '0'})['N'])

            # Ban user if unpoliteCount exceeds threshold (e.g., 3)
            if unpolite_count > 3:
                dynamodb.update_item(
                    TableName=users_table,
                    Key={'reviewerID': {'S': reviewer_id}},
                    UpdateExpression='SET banned = :true',
                    ExpressionAttributeValues={':true': {'BOOL': True}}
                )
    return {'statusCode': 200}
