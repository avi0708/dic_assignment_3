import os
import boto3
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

nltk.data.path.append(os.path.join(os.getcwd(), 'nltk_data'))


sia = SentimentIntensityAnalyzer()

endpoint_url = None
if os.getenv("STAGE") == "local":
    endpoint_url = "http://localhost.localstack.cloud:4566"

s3 = boto3.client("s3", endpoint_url=endpoint_url)
ssm = boto3.client("ssm", endpoint_url=endpoint_url)
dynamodb = boto3.client("dynamodb",endpoint_url=endpoint_url)


def get_sentiment(text):
    scores = sia.polarity_scores(text)
    if scores['compound'] >= 0.1:
        return 'POSITIVE'
    elif scores['compound'] <= -0.1:
        return 'NEGATIVE'
    else:
        return 'NEUTRAL'

def handler(event, context):
    reviews_table = ssm.get_parameter(Name='/review-app/tables/reviews')['Parameter']['Value']
    
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            review_id = record['dynamodb']['Keys']['reviewId']['S']
            review = record['dynamodb']['NewImage']
            
            overall_sentiment = get_sentiment(review['processedreviewText']['S'] + " " + review['processedSummary']['S'])
            
            dynamodb.update_item(
                TableName=reviews_table,
                Key={'reviewId': {'S': review_id}},
                UpdateExpression='SET sentiment = :sent',
                ExpressionAttributeValues={':sent': {'S': overall_sentiment}}
            )
    return {'statusCode': 200}