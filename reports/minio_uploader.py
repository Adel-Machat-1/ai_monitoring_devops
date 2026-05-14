from config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY, MINIO_BUCKET,
    MINIO_SECURE, MINIO_BUCKET_REMEDIATION
)

import io
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

import logging
logger = logging.getLogger(__name__)


def get_minio_client():
    """Retourne un client MinIO"""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )

def upload_to_minio(pdf_bytes, filename):
    """Upload PDF incident dans bucket incident-reports"""
    logger.info(f"\n[MINIO] Upload de {filename}...")
    try:
        client = get_minio_client()

        # Créer bucket si absent
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info(f"[MINIO] Bucket '{MINIO_BUCKET}' créé")

        pdf_stream = io.BytesIO(pdf_bytes)
        client.put_object(
            MINIO_BUCKET, filename,
            pdf_stream, length=len(pdf_bytes),
            content_type="application/pdf"
        )

        # URL pré-signée valide 24h (accessible sans authentification)
        presigned_url = client.presigned_get_object(
            MINIO_BUCKET, filename, expires=timedelta(hours=24)
        )
        logger.info(f"[MINIO] ✅ Upload réussi — URL pré-signée générée")
        return presigned_url

    except S3Error as e:
        logger.info(f"[MINIO] ❌ Erreur : {str(e)}")
        return None

def upload_remediation_to_minio(pdf_bytes, filename):
    """Upload PDF remédiation dans bucket self-healing-reports"""
    logger.info(f"\n[MINIO] Upload remédiation : {filename}...")
    try:
        client = get_minio_client()

        # Créer bucket self-healing-reports si absent
        if not client.bucket_exists(MINIO_BUCKET_REMEDIATION):
            client.make_bucket(MINIO_BUCKET_REMEDIATION)
            logger.info(f"[MINIO] Bucket '{MINIO_BUCKET_REMEDIATION}' créé")

        pdf_stream = io.BytesIO(pdf_bytes)
        client.put_object(
            MINIO_BUCKET_REMEDIATION, filename,
            pdf_stream, length=len(pdf_bytes),
            content_type="application/pdf"
        )

        minio_url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET_REMEDIATION}/{filename}"
        logger.info(f"[MINIO] ✅ Upload remédiation réussi : {minio_url}")
        return minio_url

    except S3Error as e:
        logger.info(f"[MINIO] ❌ Erreur remédiation : {str(e)}")
        return None