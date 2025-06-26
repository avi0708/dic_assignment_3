import json
import os
import boto3
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import uuid, math
from spellchecker import SpellChecker

nltk.data.path.append(os.path.join(os.getcwd(), 'nltk_data'))

import os

# LocalStack-compatible dummy AWS credentials
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["LOCALSTACK_ENDPOINT"] = "http://localhost:4566"
import boto3

s3 = boto3.client(
    "s3",
    region_name=os.environ["AWS_REGION"],
    endpoint_url=os.environ["LOCALSTACK_ENDPOINT"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
)

dynamodb = boto3.client(
    "dynamodb",
    region_name=os.environ["AWS_REGION"],
    endpoint_url=os.environ["LOCALSTACK_ENDPOINT"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
)

ssm = boto3.client(
    "ssm",
    region_name=os.environ["AWS_REGION"],
    endpoint_url=os.environ["LOCALSTACK_ENDPOINT"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
)


def preprocess_text(text):
    spell = SpellChecker()
    tokens = word_tokenize(text.lower())
    
    # Remove stopwords and non-alpha tokens
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word.isalpha() and word not in stop_words]
    
    # Correct spelling
    # tokens = [spell.correction(word) if spell.correction(word) else word for word in tokens]
    
    # Lemmatize
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    
    return ' '.join(tokens)

def handler(event, context):
    bucket_name = ssm.get_parameter(Name='/review-app/buckets/reviews')['Parameter']['Value']
    reviews_table = ssm.get_parameter(Name='/review-app/tables/reviews')['Parameter']['Value']

    for record in event['Records']:
        key = record['s3']['object']['key']
        obj = s3.get_object(Bucket=bucket_name, Key=key)

        # Process each line as a separate JSON object
        for line in obj['Body'].read().decode('utf-8').splitlines():
            if not line.strip():
                continue  # Skip empty lines

            try:
                review_data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON line: {e}")
                continue

            processed_review = {
                'reviewId' : {'S': f"{review_data['reviewerID']}-{uuid.uuid4()}"},
                'reviewerID': {'S': review_data['reviewerID']},
                'processedreviewText': {'S': preprocess_text(review_data['reviewText'])},
                'processedSummary': {'S': preprocess_text(review_data['summary'])},
                'overall': {'N': str(review_data['overall'])},
                'profanityCheck': {'BOOL': False},
                'sentiment': {'S': 'PENDING'}
            }
            value = review_data.get('overall')
            if value is not None and not (isinstance(value, float) and math.isnan(value)):
                processed_review['overall'] = {'N': str(value)}

            dynamodb.put_item(TableName=reviews_table, Item=processed_review)

    return {'statusCode': 200}