import pytest
import boto3
import json
import time
from datetime import datetime
import uuid

class TestReviewAnalysisIntegration:
    
    @classmethod
    def setup_class(cls):
        cls.s3 = boto3.client('s3', endpoint_url='http://localhost:4566')
        cls.dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:4566')
        cls.lambda_client = boto3.client('lambda', endpoint_url='http://localhost:4566')
        
        # Table references
        cls.reviews_table = cls.dynamodb.Table('reviews-table')
        cls.users_table = cls.dynamodb.Table('users-table')
        
        # Test data
        cls.test_customer_id = f"test_customer_{uuid.uuid4()}"
        
    def test_01_preprocessing_functionality(self):
        # Create test review
        test_review = {
            "customerId": self.test_customer_id,
            "reviewId": "test_review_1",
            "overall": 5,
            "summary": "Great product! Really love it.",
            "reviewText": "This is an amazing product. I would definitely recommend it to others. The quality is outstanding and the price is reasonable."
        }
        
        # Upload to raw bucket
        key = f"review_{uuid.uuid4()}.json"
        self.s3.put_object(
            Bucket='review-raw-bucket',
            Key=key,
            Body=json.dumps(test_review),
            ContentType='application/json'
        )
        
        # Wait for processing
        time.sleep(5)
        
        # Check if processed file exists
        try:
            processed_key = f"processed/{key}"
            response = self.s3.get_object(Bucket='review-processed-bucket', Key=processed_key)
            processed_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Verify preprocessing results
            assert 'summary_processed' in processed_data
            assert 'reviewText_processed' in processed_data
            assert 'summary_tokens' in processed_data
            assert 'reviewText_tokens' in processed_data
            
            # Check that stop words were removed and lemmatization applied
            assert len(processed_data['summary_tokens']) > 0
            assert len(processed_data['reviewText_tokens']) > 0
            
            print("✓ Preprocessing functionality test passed")
            
        except Exception as e:
            pytest.fail(f"Preprocessing test failed: {e}")
    
    def test_02_profanity_check_clean_review(self):
        test_review = {
            "customerId": self.test_customer_id,
            "reviewId": "test_review_clean",
            "overall": 5,
            "summary": "Excellent service",
            "reviewText": "The service was excellent and the staff was very helpful."
        }
        
        # Process through the pipeline
        key = f"review_clean_{uuid.uuid4()}.json"
        self.s3.put_object(
            Bucket='review-raw-bucket',
            Key=key,
            Body=json.dumps(test_review),
            ContentType='application/json'
        )
        
        # Wait for processing
        time.sleep(10)
        
        # Check DynamoDB for results
        try:
            response = self.reviews_table.get_item(
                Key={
                    'customerId': self.test_customer_id,
                    'reviewId': 'test_review_clean'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                assert item['has_profanity'] == False
                assert item['profanity_count'] == 0
                print("✓ Clean review profanity check test passed")
            else:
                pytest.fail("Review not found in DynamoDB")
                
        except Exception as e:
            pytest.fail(f"Clean review profanity check test failed: {e}")
    
    def test_03_profanity_check_unpolite_review(self):
        test_review = {
            "customerId": self.test_customer_id,
            "reviewId": "test_review_profane",
            "overall": 1,
            "summary": "Terrible damn service",
            "reviewText": "This damn product is shit and the service sucks. What a waste of money!"
        }
        
        # Process through the pipeline
        key = f"review_profane_{uuid.uuid4()}.json"
        self.s3.put_object(
            Bucket='review-raw-bucket',
            Key=key,
            Body=json.dumps(test_review),
            ContentType='application/json'
        )
        
        # Wait for processing
        time.sleep(10)
        
        # Check DynamoDB for results
        try:
            response = self.reviews_table.get_item(
                Key={
                    'customerId': self.test_customer_id,
                    'reviewId': 'test_review_profane'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                assert item['has_profanity'] == True
                assert item['profanity_count'] > 0
                print("✓ Profane review profanity check test passed")
            else:
                pytest.fail("Profane review not found in DynamoDB")
                
        except Exception as e:
            pytest.fail(f"Profane review profanity check test failed: {e}")
    
    def test_04_sentiment_analysis_positive(self):
        test_review = {
            "customerId": self.test_customer_id,
            "reviewId": "test_review_positive",
            "overall": 5,
            "summary": "Amazing product",
            "reviewText": "I absolutely love this product! It's fantastic and exceeded my expectations. Highly recommended!"
        }
        
        # Process through the pipeline
        key = f"review_positive_{uuid.uuid4()}.json"
        self.s3.put_object(
            Bucket='review-raw-bucket',
            Key=key,
            Body=json.dumps(test_review),
            ContentType='application/json'
        )
        
        # Wait for processing
        time.sleep(15)
        
        # Check DynamoDB for sentiment results
        try:
            response = self.reviews_table.get_item(
                Key={
                    'customerId': self.test_customer_id,
                    'reviewId': 'test_review_positive'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                assert 'sentiment_polarity' in item
                assert 'sentiment_label' in item
                assert item['sentiment_label'] == 'positive'
                assert float(item['sentiment_polarity']) > 0
                print("✓ Positive sentiment analysis test passed")
            else:
                pytest.fail("Positive review not found in DynamoDB")
                
        except Exception as e:
            pytest.fail(f"Positive sentiment analysis test failed: {e}")
    
    def test_05_sentiment_analysis_negative(self):
        test_review = {
            "customerId": self.test_customer_id,
            "reviewId": "test_review_negative",
            "overall": 1,
            "summary": "Terrible product",
            "reviewText": "This product is awful and disappointing. I hate it and regret buying it. Complete waste of money!"
        }
        
        # Process through the pipeline
        key = f"review_negative_{uuid.uuid4()}.json"
        self.s3.put_object(
            Bucket='review-raw-bucket',
            Key=key,
            Body=json.dumps(test_review),
            ContentType='application/json'
        )
        
        # Wait for processing
        time.sleep(15)
        
        # Check DynamoDB for sentiment results
        try:
            response = self.reviews_table.get_item(
                Key={
                    'customerId': self.test_customer_id,
                    'reviewId': 'test_review_negative'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                assert 'sentiment_polarity' in item
                assert 'sentiment_label' in item
                assert item['sentiment_label'] == 'negative'
                assert float(item['sentiment_polarity']) < 0
                print("✓ Negative sentiment analysis test passed")
            else:
                pytest.fail("Negative review not found in DynamoDB")
                
        except Exception as e:
            pytest.fail(f"Negative sentiment analysis test failed: {e}")
    
    def test_06_user_management_counting_unpolite_reviews(self):
        # Create multiple unpolite reviews for the same customer
        unpolite_reviews = [
            {
                "customerId": self.test_customer_id,
                "reviewId": "unpolite_1",
                "overall": 1,
                "summary": "Damn terrible",
                "reviewText": "This shit product sucks badly"
            },
            {
                "customerId": self.test_customer_id,
                "reviewId": "unpolite_2",
                "overall": 1,
                "summary": "Fucking awful",
                "reviewText": "What a piece of crap"
            }
        ]
        
        # Process each review
        for i, review in enumerate(unpolite_reviews):
            key = f"unpolite_review_{i}_{uuid.uuid4()}.json"
            self.s3.put_object(
                Bucket='review-raw-bucket',
                Key=key,
                Body=json.dumps(review),
                ContentType='application/json'
            )
            time.sleep(5)  # Wait between uploads
        
        # Wait for all processing to complete
        time.sleep(20)
        
        # Check user status
        try:
            response = self.users_table.get_item(
                Key={'customerId': self.test_customer_id}
            )
            
            if 'Item' in response:
                user_item = response['Item']
                assert 'unpolite_review_count' in user_item
                assert int(user_item['unpolite_review_count']) >= 2
                print(f"✓ User has {user_item['unpolite_review_count']} unpolite reviews")
            else:
                pytest.fail("User not found in users table")
                
        except Exception as e:
            pytest.fail(f"User management counting test failed: {e}")
    
    def test_07_user_banning_functionality(self):
        # Add more unpolite reviews to trigger banning
        additional_reviews = [
            {
                "customerId": self.test_customer_id,
                "reviewId": "unpolite_3",
                "overall": 1,
                "summary": "Bullshit service",
                "reviewText": "This damn company provides shit service"
            },
            {
                "customerId": self.test_customer_id,
                "reviewId": "unpolite_4",
                "overall": 1,
                "summary": "Fucking disaster",
                "reviewText": "What a fucking mess this product is"
            }
        ]
        
        # Process additional reviews
        for i, review in enumerate(additional_reviews):
            key = f"additional_unpolite_{i}_{uuid.uuid4()}.json"
            self.s3.put_object(
                Bucket='review-raw-bucket',
                Key=key,
                Body=json.dumps(review),
                ContentType='application/json'
            )
            time.sleep(5)
        
        # Wait for processing
        time.sleep(25)
        
        # Check if user is banned
        try:
            response = self.users_table.get_item(
                Key={'customerId': self.test_customer_id}
            )
            
            if 'Item' in response:
                user_item = response['Item']
                assert 'status' in user_item
                assert user_item['status'] == 'banned'
                assert 'ban_reason' in user_item
                assert int(user_item['unpolite_review_count']) > 3
                print(f"✓ User banned with {user_item['unpolite_review_count']} unpolite reviews")
            else:
                pytest.fail("User not found for banning test")
                
        except Exception as e:
            pytest.fail(f"User banning test failed: {e}")
    
    def test_08_end_to_end_pipeline(self):
        test_customer = f"e2e_customer_{uuid.uuid4()}"
        test_review = {
            "customerId": test_customer,
            "reviewId": "e2e_review",
            "overall": 3,
            "summary": "Mixed experience with some issues",
            "reviewText": "The product has good features but also some problems. Customer service was okay but could be better."
        }
        
        # Upload review
        key = f"e2e_review_{uuid.uuid4()}.json"
        self.s3.put_object(
            Bucket='review-raw-bucket',
            Key=key,
            Body=json.dumps(test_review),
            ContentType='application/json'
        )
        
        # Wait for complete processing
        time.sleep(20)
        
        # Verify all stages completed
        try:
            # Check review in DynamoDB
            response = self.reviews_table.get_item(
                Key={
                    'customerId': test_customer,
                    'reviewId': 'e2e_review'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                
                # Verify all processing stages
                assert 'has_profanity' in item  # Profanity check completed
                assert 'sentiment_label' in item  # Sentiment analysis completed
                assert 'status' in item
                assert item['status'] == 'sentiment_analyzed'
                
                print("✓ End-to-end pipeline test passed")
                print(f"  - Profanity check: {'Yes' if item['has_profanity'] else 'No'}")
                print(f"  - Sentiment: {item['sentiment_label']}")
                print(f"  - Processing status: {item['status']}")
                
            else:
                pytest.fail("E2E review not found in DynamoDB")
                
        except Exception as e:
            pytest.fail(f"End-to-end pipeline test failed: {e}")
    
    @classmethod
    def teardown_class(cls):
        try:
            # Clean up test reviews
            response = cls.reviews_table.scan(
                FilterExpression='begins_with(customerId, :prefix)',
                ExpressionAttributeValues={':prefix': 'test_customer_'}
            )
            
            for item in response['Items']:
                cls.reviews_table.delete_item(
                    Key={
                        'customerId': item['customerId'],
                        'reviewId': item['reviewId']
                    }
                )
            
            # Clean up test users
            response = cls.users_table.scan(
                FilterExpression='begins_with(customerId, :prefix)',
                ExpressionAttributeValues={':prefix': 'test_customer_'}
            )
            
            for item in response['Items']:
                cls.users_table.delete_item(
                    Key={'customerId': item['customerId']}
                )
            
            print("✓ Test cleanup completed")
            
        except Exception as e:
            print(f"Cleanup failed: {e}")

# Run tests with: pytest tests/integration_tests.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])