import os
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
import boto3
from botocore.exceptions import ClientError

class S3StorageManager:
    """Manage S3 file uploads and downloads"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def generate_s3_key(self, project_id, file_type, filename):
        """Generate S3 key for file"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        return f"projects/{project_id}/{file_type}/{timestamp}_{filename}"
    
    def get_upload_url(self, s3_key, content_type='application/octet-stream'):
        """Generate presigned POST URL for client-side upload"""
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields={
                    'Content-Type': content_type,
                    'x-amz-server-side-encryption': 'AES256',
                },
                Conditions=[
                    ['content-length-range', 0, settings.MAX_FILE_UPLOAD_SIZE],
                    {'x-amz-server-side-encryption': 'AES256'},
                ],
                ExpiresIn=3600,  # 1 hour
            )
            return response
        except ClientError as e:
            print(f"Error generating upload URL: {e}")
            return None
    
    def get_download_url(self, s3_key, expires_in=3600):
        """Generate presigned download URL"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            print(f"Error generating download URL: {e}")
            return None
    
    def delete_file(self, s3_key):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            print(f"Error deleting file: {e}")
            return False
    
    def scan_file_for_virus(self, s3_key):
        """Placeholder for virus scanning integration"""
        # In production, integrate with ClamAV or similar service
        # For MVP, just return True
        return True
    
    def get_file_metadata(self, s3_key):
        """Get file metadata from S3"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
            }
        except ClientError as e:
            print(f"Error getting file metadata: {e}")
            return None
