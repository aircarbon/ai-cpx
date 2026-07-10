import io
import os
from typing import Any
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3-compatible object storage configuration (SeaweedFS / MinIO / AWS S3)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:8333")
S3_PUBLIC_ENDPOINT = os.getenv("S3_PUBLIC_ENDPOINT", "http://localhost:8333")
S3_ACCESS_KEY = os.getenv("S3_ROOT_USER", "aicpx_s3_access")
S3_SECRET_KEY = os.getenv("S3_ROOT_PASSWORD", "change-me-strong-secret")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "aicpx-documents")


def get_s3_client(
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    region_name: str = "us-east-1",
) -> boto3.client | None:
    try:
        endpoint = endpoint_url or S3_ENDPOINT
        access = access_key or S3_ACCESS_KEY
        secret = secret_key or S3_SECRET_KEY

        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            region_name=region_name,
            use_ssl=False,
            config=Config(
                s3={"addressing_style": "path"},
                signature_version="s3v4",
                connect_timeout=10,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
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


def _list_all_objects(s3_client: boto3.client, bucket_name: str, prefix: str = "") -> list[dict[str, Any]]:
    """Paginate through list_objects_v2 to return all objects."""
    all_contents: list[dict[str, Any]] = []
    continuation_token: str | None = None

    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket_name}
        if prefix:
            kwargs["Prefix"] = prefix
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**kwargs)
        if "Contents" in response:
            all_contents.extend(response["Contents"])

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return all_contents


def list_pdf_files_by_folder(
    s3_client: boto3.client | None = None, bucket_name: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    if not s3_client:
        s3_client = get_s3_client()
        if not s3_client:
            return {}

    if not bucket_name:
        bucket_name = get_bucket_name()

    try:
        contents = _list_all_objects(s3_client, bucket_name)

        if not contents:
            return {}

        folder_files: dict[str, list[dict[str, Any]]] = {}

        for obj in contents:
            key = obj["Key"]

            # Skip directories and non-PDF files
            if key.endswith("/") or not key.lower().endswith(".pdf"):
                continue

            # Get the first-level folder
            parts = key.split("/")
            if len(parts) >= 2:
                folder = parts[0]
                filename = parts[-1]

                if folder not in folder_files:
                    folder_files[folder] = []

                folder_files[folder].append({"key": key, "filename": filename, "size": obj["Size"]})

        return folder_files

    except Exception as e:
        print(f"Error listing PDF files: {e}")
        return {}


def download_file_to_buffer(
    file_key: str, s3_client: boto3.client | None = None, bucket_name: str | None = None
) -> io.BytesIO | None:
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


def file_exists(file_key: str, s3_client: boto3.client | None = None, bucket_name: str | None = None) -> bool:
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
        if e.response["Error"]["Code"] == "404":
            return False
        # For other errors, log and return False
        print(f"Error checking if file {file_key} exists: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking file {file_key}: {e}")
        return False


def generate_document_url(project_name: str, file_name: str, bucket_name: str | None = None) -> str:
    if not bucket_name:
        bucket_name = get_bucket_name()

    # URL encode the project name and file name to handle spaces and special characters
    encoded_project_name = quote(project_name, safe="")
    encoded_file_name = quote(file_name, safe="")

    document_url = f"{S3_PUBLIC_ENDPOINT}/{bucket_name}/{encoded_project_name}/{encoded_file_name}"

    return document_url
