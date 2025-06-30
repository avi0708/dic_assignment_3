# # LocalStack-compatible dummy AWS credentials
# os.environ["AWS_ACCESS_KEY_ID"] = "test"
# os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
# os.environ["AWS_REGION"] = "us-east-1"
# os.environ["LOCALSTACK_ENDPOINT"] = "http://localhost:4566"

# s3 = boto3.client(
#     "s3",
#     region_name=os.environ["AWS_REGION"],
#     endpoint_url=os.environ["LOCALSTACK_ENDPOINT"],
#     aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
#     aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
# )

# dynamodb = boto3.client(
#     "dynamodb",
#     region_name=os.environ["AWS_REGION"],
#     endpoint_url=os.environ["LOCALSTACK_ENDPOINT"],
#     aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
#     aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
# )

# ssm = boto3.client(
#     "ssm",
#     region_name=os.environ["AWS_REGION"],
#     endpoint_url=os.environ["LOCALSTACK_ENDPOINT"],
#     aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
#     aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
# )