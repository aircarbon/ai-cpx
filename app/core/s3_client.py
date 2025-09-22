import os
import boto3
import io
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from urllib.parse import quote

# Load environment variables
load_dotenv()

# MinIO/S3 Configuration
S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
S3_PUBLIC_ENDPOINT = os.getenv('S3_PUBLIC_ENDPOINT', 'http://localhost:9100')
S3_ACCESS_KEY = os.getenv('S3_ROOT_USER', 'minioadmin')
S3_SECRET_KEY = os.getenv('S3_ROOT_PASSWORD', 'minioadmin')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'documents')


def get_s3_client(endpoint_url: Optional[str] = None, 
                  access_key: Optional[str] = None,
                  secret_key: Optional[str] = None,
                  region_name: str = 'us-east-1') -> Optional[boto3.client]:

    try:
        endpoint = endpoint_url or S3_ENDPOINT
        access = access_key or S3_ACCESS_KEY
        secret = secret_key or S3_SECRET_KEY
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            region_name=region_name
        )
        return s3_client
    except (ClientError, NoCredentialsError) as e:
        print(f"Error creating S3 client: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error creating S3 client: {e}")
        return None


def get_bucket_name() -> str:
    return S3_BUCKET_NAME


def list_pdf_files_by_folder(s3_client: Optional[boto3.client] = None, 
                            bucket_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    if not s3_client:
        s3_client = get_s3_client()
        if not s3_client:
            return {}
    
    if not bucket_name:
        bucket_name = get_bucket_name()
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in response:
            return {}
        
        folder_files = {}
        
        for obj in response['Contents']:
            key = obj['Key']
            
            # Skip directories and non-PDF files
            if key.endswith('/') or not key.lower().endswith('.pdf'):
                continue
            
            # Get the first-level folder
            parts = key.split('/')
            if len(parts) >= 2:
                folder = parts[0]
                filename = parts[-1]
                
                if folder not in folder_files:
                    folder_files[folder] = []
                
                folder_files[folder].append({
                    'key': key,
                    'filename': filename,
                    'size': obj['Size']
                })
        
        return folder_files
        
    except Exception as e:
        print(f"Error listing PDF files: {e}")
        return {}


def download_file_to_buffer(file_key: str, 
                           s3_client: Optional[boto3.client] = None, 
                           bucket_name: Optional[str] = None) -> Optional[io.BytesIO]:
    if not s3_client:
        s3_client = get_s3_client()
        if not s3_client:
            print("Failed to create S3 client")
            return None
    
    if not bucket_name:
        bucket_name = get_bucket_name()
    
    try:
        file_buffer = io.BytesIO()
        s3_client.download_fileobj(bucket_name, file_key, file_buffer)
        file_buffer.seek(0)  # Reset buffer position to beginning
        return file_buffer
        
    except ClientError as e:
        print(f"Error downloading file {file_key}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading file {file_key}: {e}")
        return None


def file_exists(file_key: str, 
                s3_client: Optional[boto3.client] = None, 
                bucket_name: Optional[str] = None) -> bool:
    if not s3_client:
        s3_client = get_s3_client()
        if not s3_client:
            return False
    
    if not bucket_name:
        bucket_name = get_bucket_name()
    
    try:
        s3_client.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except ClientError as e:
        # If error code is 404, file doesn't exist
        if e.response['Error']['Code'] == '404':
            return False
        # For other errors, log and return False
        print(f"Error checking if file {file_key} exists: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking file {file_key}: {e}")
        return False


def generate_document_url(project_name: str, file_name: str, bucket_name: Optional[str] = None) -> str:
    if not bucket_name:
        bucket_name = get_bucket_name()

    # URL encode the project name and file name to handle spaces and special characters
    encoded_project_name = quote(project_name, safe='')
    encoded_file_name = quote(file_name, safe='')
    
    document_url = f"{S3_PUBLIC_ENDPOINT}/{bucket_name}/{encoded_project_name}/{encoded_file_name}"

    return document_url
