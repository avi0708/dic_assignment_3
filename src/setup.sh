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