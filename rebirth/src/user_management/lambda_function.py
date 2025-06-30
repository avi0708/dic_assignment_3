import json
import boto3
import logging
from datetime import datetime
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Initialize AWS clients
        dynamodb = boto3.resource('dynamodb', endpoint_url='http://localstack:4566')
        ssm = boto3.client('ssm', endpoint_url='http://localstack:4566')
        
        # Get parameters from SSM
        reviews_table_name = ssm.get_parameter(Name='/review-app/reviews-table')['Parameter']['Value']
        users_table_name = ssm.get_parameter(Name='/review-app/users-table')['Parameter']['Value']
        
        reviews_table = dynamodb.Table(reviews_table_name)
        users_table = dynamodb.Table(users_table_name)
        
        # Process DynamoDB event
        for record in event['Records']:
            if record['eventName'] in ['INSERT', 'MODIFY']:
                # Extract customer ID from the new review
                dynamodb_record = record['dynamodb']
                customer_id = dynamodb_record['NewImage']['customerId']['S']
                
                logger.info(f"Processing user management for customer: {customer_id}")
                
                # Count unpolite reviews for this customer
                unpolite_count = count_unpolite_reviews(reviews_table, customer_id)
                
                # Update user status
                update_user_status(users_table, customer_id, unpolite_count)
                
                logger.info(f"User management completed for customer: {customer_id}")
                
        return {
            'statusCode': 200,
            'body': json.dumps('User management completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error in user management: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def count_unpolite_reviews(table, customer_id):
    try:
        response = table.query(
            KeyConditionExpression=Key('customerId').eq(customer_id),
            FilterExpression='has_profanity = :true',
            ExpressionAttributeValues={':true': True}
        )
        
        return response['Count']
        
    except Exception as e:
        logger.error(f"Error counting unpolite reviews: {str(e)}")
        return 0

def update_user_status(table, customer_id, unpolite_count):
    # Determine user status
    if unpolite_count > 3:
        status = 'banned'
        ban_reason = f'More than 3 unpolite reviews ({unpolite_count})'
    elif unpolite_count > 0:
        status = 'warned'
        ban_reason = None
    else:
        status = 'active'
        ban_reason = None
    
    # Update or create user record
    item = {
        'customerId': customer_id,
        'unpolite_review_count': unpolite_count,
        'status': status,
        'last_updated': datetime.utcnow().isoformat()
    }
    
    if ban_reason:
        item['ban_reason'] = ban_reason
        item['banned_at'] = datetime.utcnow().isoformat()
    
    table.put_item(Item=item)
    
    logger.info(f"Customer {customer_id} status updated to: {status} (unpolite reviews: {unpolite_count})")