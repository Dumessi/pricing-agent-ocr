import os
import oss2
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_oss_bucket():
    """设置OSS存储桶"""
    try:
        # 创建认证对象
        auth = oss2.Auth(
            os.getenv('ALIYUN_ACCESS_KEY_ID'),
            os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        )
        
        # 创建Bucket对象
        bucket = oss2.Bucket(
            auth,
            'http://oss-cn-hangzhou.aliyuncs.com',
            'pricing-agent-ocr'
        )
        
        # 尝试创建存储桶
        try:
            bucket.create_bucket(
                oss2.models.BUCKET_ACL_PUBLIC_READ,
                oss2.models.BucketCreateConfig(oss2.BUCKET_STORAGE_CLASS_STANDARD)
            )
            logger.info("存储桶创建成功")
        except oss2.exceptions.ServerError as e:
            if 'BucketAlreadyExists' in str(e):
                logger.info("存储桶已存在")
            else:
                raise
        
        return True
    
    except Exception as e:
        logger.error(f"设置OSS存储桶失败: {str(e)}")
        return False

if __name__ == '__main__':
    setup_oss_bucket()
