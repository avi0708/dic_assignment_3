import json
import boto3
import nltk
import re
from textblob import TextBlob
import logging

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Initialize AWS clients
        s3 = boto3.client('s3', endpoint_url='http://localstack:4566')
        ssm = boto3.client('ssm', endpoint_url='http://localstack:4566')
        
        # Get parameters from SSM
        processed_bucket = ssm.get_parameter(Name='/review-app/processed-bucket')['Parameter']['Value']
        
        # Process S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            logger.info(f"Processing file: {key} from bucket: {bucket}")
            
            # Download and parse the review
            response = s3.get_object(Bucket=bucket, Key=key)
            review_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Preprocess the review
            processed_review = preprocess_review(review_data)
            
            # Store processed review
            processed_key = f"processed/{key}"
            s3.put_object(
                Bucket=processed_bucket,
                Key=processed_key,
                Body=json.dumps(processed_review),
                ContentType='application/json'
            )
            
            logger.info(f"Processed review stored at: {processed_key}")
            
        return {
            'statusCode': 200,
            'body': json.dumps('Preprocessing completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error in preprocessing: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def preprocess_review(review_data):
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))
    
    processed_review = review_data.copy()
    
    # Fields to process
    text_fields = ['summary', 'reviewText']
    
    for field in text_fields:
        if field in review_data and review_data[field]:
            # Clean text
            text = clean_text(review_data[field])
            
            # Tokenize
            tokens = word_tokenize(text.lower())
            
            # Remove stop words and lemmatize
            processed_tokens = [
                lemmatizer.lemmatize(token) 
                for token in tokens 
                if token.isalpha() and token not in stop_words
            ]
            
            # Store both original and processed
            processed_review[f'{field}_original'] = review_data[field]
            processed_review[f'{field}_processed'] = ' '.join(processed_tokens)
            processed_review[f'{field}_tokens'] = processed_tokens
    
    return processed_review

def clean_text(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text