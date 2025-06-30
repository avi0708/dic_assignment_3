import boto3
import json
import time
import zipfile
import os
from pathlib import Path

def setup_infrastructure():
    # Initialize clients
    s3 = boto3.client('s3', endpoint_url='http://localhost:4566')
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:4566')
    lambda_client = boto3.client('lambda', endpoint_url='http://localhost:4566')
    ssm = boto3.client('ssm', endpoint_url='http://localhost:4566')
    iam = boto3.client('iam', endpoint_url='http://localhost:4566')
    
    # Create IAM role for Lambda functions
    create_lambda_role(iam)
    
    # Set up SSM parameters
    setup_ssm_parameters(ssm)
    
    # Create S3 buckets
    create_s3_buckets(s3)
    
    # Create DynamoDB tables
    create_dynamodb_tables(dynamodb)
    
    # Create Lambda functions
    create_lambda_functions(lambda_client)
    
    # Set up S3 event notifications
    setup_s3_events(s3, lambda_client)
    
    # Set up DynamoDB streams
    setup_dynamodb_streams(dynamodb, lambda_client)
    
    print("Infrastructure setup completed!")

def create_lambda_role(iam):
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "s3:GetObject",
                    "s3:PutObject",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "ssm:GetParameter"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam.create_role(
            RoleName='review-analysis-lambda-role',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Path='/'
        )
        
        iam.put_role_policy(
            RoleName='review-analysis-lambda-role',
            PolicyName='review-analysis-lambda-policy',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print("IAM role created successfully")
        
    except Exception as e:
        print(f"IAM role creation failed: {e}")

def setup_ssm_parameters(ssm):
    parameters = {
        '/review-app/raw-bucket': 'review-raw-bucket',
        '/review-app/processed-bucket': 'review-processed-bucket',
        '/review-app/sentiment-bucket': 'review-sentiment-bucket',
        '/review-app/reviews-table': 'reviews-table',
        '/review-app/users-table': 'users-table'
    }
    
    for param_name, param_value in parameters.items():
        ssm.put_parameter(
            Name=param_name,
            Value=param_value,
            Type='String',
            Overwrite=True
        )
    
    print("SSM parameters created successfully")

def create_s3_buckets(s3):
    buckets = [
        'review-raw-bucket',
        'review-processed-bucket',
        'review-sentiment-bucket'
    ]
    
    for bucket_name in buckets:
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Bucket {bucket_name} created successfully")
        except Exception as e:
            print(f"Bucket creation failed for {bucket_name}: {e}")

def create_dynamodb_tables(dynamodb):
    # Reviews table
    try:
        reviews_table = dynamodb.create_table(
            TableName='reviews-table',
            KeySchema=[
                {'AttributeName': 'customerId', 'KeyType': 'HASH'},
                {'AttributeName': 'reviewId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'customerId', 'AttributeType': 'S'},
                {'AttributeName': 'reviewId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            }
        )
        print("Reviews table created successfully")
        
    except Exception as e:
        print(f"Reviews table creation failed: {e}")
    
    # Users table
    try:
        users_table = dynamodb.create_table(
            TableName='users-table',
            KeySchema=[
                {'AttributeName': 'customerId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'customerId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Users table created successfully")
        
    except Exception as e:
        print(f"Users table creation failed: {e}")

def create_lambda_functions(lambda_client):
    functions = [
        {
            'name': 'preprocessing-function',
            'handler': 'lambda_function.lambda_handler',
            'code_path': '../src/preprocessing'
        },
        {
            'name': 'profanity-check-function',
            'handler': 'lambda_function.lambda_handler',
            'code_path': '../src/profanity_check'
        },
        {
            'name': 'sentiment-analysis-function',
            'handler': 'lambda_function.lambda_handler',
            'code_path': '../src/sentiment_analysis'
        },
        {
            'name': 'user-management-function',
            'handler': 'lambda_function.lambda_handler',
            'code_path': '../src/user_management'
        }
    ]
    
    for func in functions:
        try:
            # Create deployment package
            zip_path = f"{func['name']}.zip"
            create_deployment_package(func['code_path'], zip_path)
            
            with open(zip_path, 'rb') as zip_file:
                lambda_client.create_function(
                    FunctionName=func['name'],
                    Runtime='python3.9',
                    Role='arn:aws:iam::000000000000:role/review-analysis-lambda-role',
                    Handler=func['handler'],
                    Code={'ZipFile': zip_file.read()},
                    Timeout=300,
                    MemorySize=256
                )
            
            print(f"Lambda function {func['name']} created successfully")
            
        except Exception as e:
            print(f"Lambda function creation failed for {func['name']}: {e}")

def create_deployment_package(code_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for root, dirs, files in os.walk(code_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, code_path)
                zip_file.write(file_path, arcname)

def setup_s3_events(s3, lambda_client):
    # Raw bucket -> Preprocessing function
    try:
        s3.put_bucket_notification_configuration(
            Bucket='review-raw-bucket',
            NotificationConfiguration={
                'LambdaConfigurations': [
                    {
                        'Id': 'preprocessing-trigger',
                        # 'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:preprocessing-function',
                        'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:preprocessing-function',
                        'Events': ['s3:ObjectCreated:*']
                    }
                ]
            }
        )
        print("S3 event notification configured for raw bucket")
        
    except Exception as e:
        print(f"S3 event configuration failed: {e}")
    
    # Processed bucket -> Profanity check function
    try:
        s3.put_bucket_notification_configuration(
            Bucket='review-processed-bucket',
            NotificationConfiguration={
                'LambdaConfigurations': [
                    {
                        'Id': 'profanity-check-trigger',
                        # 'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:profanity-check-function',
                        'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:profanity-check-function',
                        'Events': ['s3:ObjectCreated:*']
                    }
                ]
            }
        )
        print("S3 event notification configured for processed bucket")
        
    except Exception as e:
        print(f"S3 event configuration failed: {e}")
    
    # Sentiment bucket -> Sentiment analysis function
    try:
        s3.put_bucket_notification_configuration(
            Bucket='review-sentiment-bucket',
            NotificationConfiguration={
                'LambdaConfigurations': [
                    {
                        'Id': 'sentiment-analysis-trigger',
                        # 'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:sentiment-analysis-function',
                        'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:sentiment-analysis-function',
                        'Events': ['s3:ObjectCreated:*']
                    }
                ]
            }
        )
        print("S3 event notification configured for sentiment bucket")
        
    except Exception as e:
        print(f"S3 event configuration failed: {e}")

def setup_dynamodb_streams(dynamodb, lambda_client):
    try:
        # Get the stream ARN
        table = dynamodb.Table('reviews-table')
        stream_arn = table.latest_stream_arn
        
        # Create event source mapping
        lambda_client.create_event_source_mapping(
            EventSourceArn=stream_arn,
            FunctionName='user-management-function',
            StartingPosition='LATEST'
        )
        
        print("DynamoDB stream configured successfully")
        
    except Exception as e:
        print(f"DynamoDB stream configuration failed: {e}")

if __name__ == "__main__":
    setup_infrastructure()