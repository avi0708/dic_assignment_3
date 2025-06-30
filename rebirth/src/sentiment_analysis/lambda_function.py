import json
import boto3
from textblob import TextBlob
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
        reviews_table_name = ssm.get_parameter(Name='/review-app/reviews-table')['Parameter']['Value']
        
        reviews_table = dynamodb.Table(reviews_table_name)
        
        # Process S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            logger.info(f"Sentiment analysis for file: {key} from bucket: {bucket}")
            
            # Download and parse the review
            response = s3.get_object(Bucket=bucket, Key=key)
            review_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Perform sentiment analysis
            sentiment_result = analyze_sentiment(review_data)
            
            # Update review in DynamoDB
            update_review_sentiment(reviews_table, review_data, sentiment_result)
            
            logger.info(f"Sentiment analysis completed for: {key}")
            
        return {
            'statusCode': 200,
            'body': json.dumps('Sentiment analysis completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def analyze_sentiment(review_data):
    sentiment_result = {
        'sentiment_polarity': 0.0,
        'sentiment_subjectivity': 0.0,
        'sentiment_label': 'neutral',
        'field_sentiments': {},
        'analysis_timestamp': datetime.utcnow().isoformat()
    }
    
    # Fields to analyze
    text_fields = ['summary_processed', 'reviewText_processed']
    polarities = []
    subjectivities = []
    
    for field in text_fields:
        if field in review_data and review_data[field]:
            text = review_data[field]
            blob = TextBlob(text)
            
            field_sentiment = {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
            
            sentiment_result['field_sentiments'][field] = field_sentiment
            polarities.append(blob.sentiment.polarity)
            subjectivities.append(blob.sentiment.subjectivity)
    
    # Calculate overall sentiment
    if polarities:
        sentiment_result['sentiment_polarity'] = sum(polarities) / len(polarities)
        sentiment_result['sentiment_subjectivity'] = sum(subjectivities) / len(subjectivities)
        
        # Determine sentiment label
        if sentiment_result['sentiment_polarity'] > 0.1:
            sentiment_result['sentiment_label'] = 'positive'
        elif sentiment_result['sentiment_polarity'] < -0.1:
            sentiment_result['sentiment_label'] = 'negative'
        else:
            sentiment_result['sentiment_label'] = 'neutral'
    
    return sentiment_result

def update_review_sentiment(table, review_data, sentiment_result):
    customer_id = review_data.get('customerId', 'unknown')
    review_id = review_data.get('reviewId', f"review_{datetime.utcnow().timestamp()}")
    
    # Update the review item
    table.update_item(
        Key={
            'customerId': customer_id,
            'reviewId': review_id
        },
        UpdateExpression='SET sentiment_polarity = :pol, sentiment_subjectivity = :sub, sentiment_label = :label, field_sentiments = :fields, analysis_timestamp = :ts, #status = :status',
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues={
            ':pol': sentiment_result['sentiment_polarity'],
            ':sub': sentiment_result['sentiment_subjectivity'],
            ':label': sentiment_result['sentiment_label'],
            ':fields': sentiment_result['field_sentiments'],
            ':ts': sentiment_result['analysis_timestamp'],
            ':status': 'sentiment_analyzed'
        }
    )