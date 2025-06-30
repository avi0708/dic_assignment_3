#!/bin/bash

# Create S3 bucket
awslocal s3 mb s3://reviews-bucket

# Create DynamoDB tables
awslocal dynamodb create-table \
  --table-name Reviews \
  --attribute-definitions \
      AttributeName=reviewerID,AttributeType=S \
      AttributeName=reviewId,AttributeType=S \
  --key-schema \
      AttributeName=reviewerID,KeyType=HASH \
      AttributeName=reviewId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

awslocal dynamodb create-table \
  --table-name Users \
  --attribute-definitions \
  AttributeName=reviewerID,AttributeType=S \
  --key-schema \
    AttributeName=reviewerID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Store configuration in SSM
awslocal ssm put-parameter --name /review-app/buckets/reviews --type "String" --value "reviews-bucket"
awslocal ssm put-parameter --name /review-app/tables/reviews --type "String" --value "Reviews"
awslocal ssm put-parameter --name /review-app/tables/users --type "String" --value "Users"

awslocal dynamodb update-table \
  --table-name Reviews \
  --stream-specification '{
    "StreamEnabled": true,
    "StreamViewType": "NEW_IMAGE"
  }'

awslocal lambda create-function \
   --function-name pre-process \
   --runtime python3.13 \
   --handler pre_process.handler \
   --zip-file fileb://package.zip \
   --role arn:aws:iam::000000000000:role/lambda-role \
   --environment Variables="{STAGE=local}"

awslocal lambda create-function \
    --function-name profanity \
    --runtime python3.13 \
    --handler profanity.handler \
    --zip-file fileb://package.zip \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment Variables="{STAGE=local}"

awslocal lambda create-function \
    --function-name sentiment \
    --runtime python3.13 \
    --handler sentiment.handler \
    --zip-file fileb://package.zip \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment Variables="{STAGE=local}"

awslocal s3api put-bucket-notification-configuration \
  --bucket reviews-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "arn:aws:lambda:us-east-1:000000000000:function:pre-process",
        "Events": ["s3:ObjectCreated:*"]
      }
    ]
  }'

LATEST_STREAM_ARN=$(awslocal dynamodb describe-table --table-name Reviews --query "Table.LatestStreamArn" --output text)
awslocal lambda create-event-source-mapping \
  --function-name profanity \
  --event-source-arn "$LATEST_STREAM_ARN" \
  --starting-position LATEST

awslocal lambda create-event-source-mapping \
  --function-name sentiment \
  --event-source-arn "$LATEST_STREAM_ARN" \
  --starting-position LATEST