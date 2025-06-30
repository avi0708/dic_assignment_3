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
  --attribute-definitions AttributeName=reviewerID,AttributeType=S \
  --key-schema AttributeName=reviewerID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Store configuration in SSM
awslocal ssm put-parameter --name /review-app/buckets/reviews --type String --value reviews-bucket
awslocal ssm put-parameter --name /review-app/tables/reviews --type String --value Reviews
awslocal ssm put-parameter --name /review-app/tables/users --type String --value Users

# Create Lambda functions
for func in pre_process profanity sentiment
do
  awslocal lambda create-function \
    --function-name $func \
    --runtime python3.13 \
    --handler ${func}.handler \
    --zip-file fileb://package.zip \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment Variables="{STAGE=local}"
done

# Create Step Functions state machine definition
cat <<EOF > /tmp/statemachine-definition.json
{
  "Comment": "Sequential Review Processing Workflow",
  "StartAt": "ProfanityCheck",
  "States": {
    "ProfanityCheck": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:000000000000:function:profanity",
      "Next": "SentimentAnalysis",
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 1,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ]
    },
    "SentimentAnalysis": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:000000000000:function:sentiment",
      "End": true,
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 1,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ]
    }
  }
}
EOF

# Create Step Functions state machine
awslocal stepfunctions create-state-machine \
  --name review-state-machine \
  --definition file:///tmp/statemachine-definition.json \
  --role-arn arn:aws:iam::000000000000:role/step-functions-role

# Get the state machine ARN
STATE_MACHINE_ARN=$(awslocal stepfunctions list-state-machines --query "stateMachines[?name=='review-state-machine'].stateMachineArn" --output text)

# Update Lambda environments with the state machine ARN
awslocal lambda update-function-configuration \
  --function-name pre_process \
  --environment Variables="{STAGE=local,STATE_MACHINE_ARN=$STATE_MACHINE_ARN}"

# Set up S3 trigger to start the workflow
PREPROCESS_ARN=$(awslocal lambda get-function --function-name pre_process --query 'Configuration.FunctionArn' --output text)

# Configure S3 to trigger the pre_process Lambda
awslocal s3api put-bucket-notification-configuration \
  --bucket reviews-bucket \
  --notification-configuration "{
    \"LambdaFunctionConfigurations\": [
      {
        \"LambdaFunctionArn\": \"$PREPROCESS_ARN\",
        \"Events\": [\"s3:ObjectCreated:*\"]
      }
    ]
  }"

echo "Deployment complete. Sequential workflow setup:"
echo "1. S3 Upload → triggers pre_process Lambda"
echo "2. pre_process → stores review and starts Step Functions execution"
echo "3. Step Functions executes: profanity → sentiment sequentially"