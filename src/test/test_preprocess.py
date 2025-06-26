import sys
import os
import boto3
from code.pre_process import handler  # your Lambda handler

# === CONFIGURATION ===
LOCAL_FILE_PATH = os.path.join(os.getcwd(), 'data/test.json')
BUCKET_NAME = "reviews-bucket"
OBJECT_KEY = "test.json"

# === STEP 0: Setup DynamoDB connection ===
dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1',
    endpoint_url='http://localhost:4566',  # LocalStack endpoint
    aws_access_key_id='test',
    aws_secret_access_key='test'
)
table = dynamodb.Table('Reviews')

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
        endpoint_url="http://localhost:4566",
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
