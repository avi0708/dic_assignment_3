import json
import boto3
from better_profanity import profanity
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Initialize AWS clients
        s3 = boto3.client('s3', endpoint_url='http://localstack:4566')
        dynamodb = boto3.resource('dynamodb', endpoint_url='http://localstack:4566')
        ssm = boto3.client('ssm', endpoint_url='http://localstack:4566')
        
        # Get parameters from SSM
        sentiment_bucket = ssm.get_parameter(Name='/review-app/sentiment-bucket')['Parameter']['Value']
        reviews_table_name = ssm.get_parameter(Name='/review-app/reviews-table')['Parameter']['Value']
        
        reviews_table = dynamodb.Table(reviews_table_name)
        
        # Process S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            logger.info(f"Profanity checking file: {key} from bucket: {bucket}")
            
            # Download and parse the processed review
            response = s3.get_object(Bucket=bucket, Key=key)
            review_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Perform profanity check
            profanity_result = check_profanity(review_data)
            
            # Store profanity check results in DynamoDB
            store_review_result(reviews_table, review_data, profanity_result)
            
            # Forward to sentiment analysis
            review_data.update(profanity_result)
            
            sentiment_key = key.replace('processed/', 'profanity_checked/')
            s3.put_object(
                Bucket=sentiment_bucket,
                Key=sentiment_key,
                Body=json.dumps(review_data),
                ContentType='application/json'
            )
            
            logger.info(f"Profanity check completed for: {key}")
            
        return {
            'statusCode': 200,
            'body': json.dumps('Profanity check completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error in profanity check: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def check_profanity(review_data):
    profanity_result = {
        'has_profanity': False,
        'profanity_fields': [],
        'profanity_count': 0,
        'check_timestamp': datetime.utcnow().isoformat()
    }
    
    # Fields to check for profanity
    text_fields = ['summary_processed', 'reviewText_processed']
    
    for field in text_fields:
        if field in review_data and review_data[field]:
            text = review_data[field]
            
            if profanity.contains_profanity(text):
                profanity_result['has_profanity'] = True
                profanity_result['profanity_fields'].append(field)
                
                # Count profane words
                words = text.split()
                profane_words = [word for word in words if profanity.contains_profanity(word)]
                profanity_result['profanity_count'] += len(profane_words)
    
    return profanity_result

def store_review_result(table, review_data, profanity_result):
    # Extract customer ID (assuming it's in the review data)
    customer_id = review_data.get('customerId', 'unknown')
    review_id = review_data.get('reviewId', f"review_{datetime.utcnow().timestamp()}")
    
    item = {
        'customerId': customer_id,
        'reviewId': review_id,
        'overall': review_data.get('overall', 0),
        'summary': review_data.get('summary_original', ''),
        'reviewText': review_data.get('reviewText_original', ''),
        'has_profanity': profanity_result['has_profanity'],
        'profanity_count': profanity_result['profanity_count'],
        'profanity_fields': profanity_result['profanity_fields'],
        'created_at': datetime.utcnow().isoformat(),
        'status': 'profanity_checked'
    }
    
    table.put_item(Item=item)