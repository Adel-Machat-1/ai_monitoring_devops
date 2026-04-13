
from config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE

import io
from minio import Minio
from minio.error import S3Error

def upload_to_minio(pdf_bytes, filename):
    print(f"\n[MINIO] Upload de {filename}...")
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )

        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            print(f"[MINIO] Bucket '{MINIO_BUCKET}' créé")

        pdf_stream = io.BytesIO(pdf_bytes)
        client.put_object(
            MINIO_BUCKET, filename,
            pdf_stream, length=len(pdf_bytes),
            content_type="application/pdf"
        )

        minio_url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}"
        print(f"[MINIO] ✅ Upload réussi : {minio_url}")
        return minio_url

    except S3Error as e:
        print(f"[MINIO] ❌ Erreur : {str(e)}")
        return None
