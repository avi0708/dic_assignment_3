# Deploy Review Analysis Serverless Application
echo "Deploying Review Analysis Application to LocalStack..."

# Check if LocalStack is running
if ! curl -s http://localhost:4566/health > /dev/null; then
    echo "LocalStack is not running. Please start LocalStack first:"
    echo "   docker-compose up -d"
    exit 1
fi

echo "LocalStack is running"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set up infrastructure
echo "Setting up infrastructure..."
cd infrastructure
python setup.py
cd ..

# Wait for infrastructure to be ready
echo "Waiting for infrastructure to be ready..."
sleep 10

# Run integration tests
echo "Running integration tests..."
cd tests
python -m pytest integration_tests.py -v
cd ..

echo "Deployment completed successfully!"
echo ""
echo "Resources created:"
echo "   - S3 Buckets: review-raw-bucket, review-processed-bucket, review-sentiment-bucket"
echo "   - DynamoDB Tables: reviews-table, users-table"
echo "   - Lambda Functions: preprocessing, profanity-check, sentiment-analysis, user-management"
echo "   - SSM Parameters: /review-app/*"
echo ""
echo "To test the application:"
echo "   1. Upload a review JSON file to the raw bucket:"
echo "      aws --endpoint-url=http://localhost:4566 s3 cp review.json s3://review-raw-bucket/"
echo ""
echo "   2. Monitor the processing:"
echo "      aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name reviews-table"
echo "      aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name users-table"