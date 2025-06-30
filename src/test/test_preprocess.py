import os
import sys
# === STEP 0: Setup DynamoDB connection ===
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["STAGE"] = "local"
import boto3
from lambdas.pre_process.pre_process import handler  # your Lambda handler

# === CONFIGURATION ===
LOCAL_FILE_PATH = os.path.join(os.getcwd(), 'data/test.json')
BUCKET_NAME = "reviews-bucket"
OBJECT_KEY = "test.json"


s3 = boto3.client(
    "s3", endpoint_url="http://localhost.localstack.cloud:4566"
)
ssm = boto3.client(
    "ssm", endpoint_url="http://localhost.localstack.cloud:4566"
)
awslambda = boto3.client(
    "lambda", endpoint_url="http://localhost.localstack.cloud:4566"
)
dynamodb = boto3.client(
    "dynamodb", endpoint_url="http://localhost.localstack.cloud:4566"
)
dynamodbRes = boto3.resource(
    "dynamodb", endpoint_url="http://localhost.localstack.cloud:4566"
)
table = dynamodbRes.Table('Reviews')

def overview_reviews_table():
    print("\n=== Overview of Reviews DB ===")
    # Get total count
    response = table.scan(Select='COUNT')
    print(f"Total reviews: {response['Count']}")

    # Get sample items
    response = table.scan(Limit=3)
    print("Sample reviews:")
    for item in response['Items']:
        print(item)

def clean_reviews_table():
    print("\n=== Cleaning Reviews DB ===")
    scan = table.scan(ProjectionExpression='reviewerID, reviewId')
    items = scan.get('Items', [])
    if not items:
        print("No items to delete.")
        return
    with table.batch_writer() as batch:
        for each in items:
            batch.delete_item(Key={'reviewerID': each['reviewerID'], 'reviewId': each['reviewId']})
    print(f"Deleted {len(items)} items.")

def main():
    # === STEP 1: Overview before cleaning ===
    overview_reviews_table()

    # === STEP 2: Clean the Reviews DB ===
    clean_reviews_table()

    # === STEP 3: Overview after cleaning ===
    overview_reviews_table()

    # === STEP 4: Check if local test file exists ===
    if not os.path.exists(LOCAL_FILE_PATH):
        raise FileNotFoundError(f"{LOCAL_FILE_PATH} not found")

    # === STEP 5: Upload test file to S3 (LocalStack) ===
    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        endpoint_url="http://localhost.localstack.cloud:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

    s3.upload_file(LOCAL_FILE_PATH, BUCKET_NAME, OBJECT_KEY)
    print(f"\nUploaded {LOCAL_FILE_PATH} to s3://{BUCKET_NAME}/{OBJECT_KEY}")

    # === STEP 6: Simulate Lambda event ===
    fake_event = {
        "Records": [
            {
                "s3": {
                    "object": {
                        "key": OBJECT_KEY
                    }
                }
            }
        ]
    }

    # === STEP 7: Invoke Lambda handler ===
    print("\n=== Invoking Lambda handler ===")
    result = handler(fake_event, None)
    print("\nLambda handler result:")
    print(result)

    # === STEP 8: Overview after Lambda processing ===
    overview_reviews_table()

if __name__ == "__main__":
    main()
