import os
import logging
import oss2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bucket():
    """Create OSS bucket for storing images"""
    try:
        # OSS configuration
        access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        endpoint = 'https://oss-cn-hangzhou.aliyuncs.com'
        bucket_name = 'pricing-agent-ocr'

        # Create bucket object
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

        try:
            # Try to create the bucket
            bucket.create_bucket()
            logger.info(f"Successfully created bucket: {bucket_name}")
            
            # Set bucket ACL to public-read for image access
            bucket.put_bucket_acl('public-read')
            logger.info(f"Set bucket ACL to public-read")
            
        except oss2.exceptions.ServerError as e:
            if 'BucketAlreadyExists' in str(e):
                logger.info(f"Bucket {bucket_name} already exists")
            else:
                raise

        return True

    except Exception as e:
        logger.error(f"Failed to create bucket: {str(e)}")
        raise

if __name__ == '__main__':
    create_bucket()
