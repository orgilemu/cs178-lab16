"""
CS 178 - Lab 16: Lambda Function — Image Flipper
lambda_function.py

This function is triggered automatically when an image is uploaded
to the SOURCE S3 bucket. It flips the image vertically (upside down)
and saves the result to the PROCESSED S3 bucket.

Students receive this file pre-written. The goal is to understand
WHAT it does and WHY, not to write it from scratch.

Deploy this as a .zip (bundled with Pillow) — see lab instructions.
"""

import boto3
import os
from io import BytesIO
from PIL import Image, ImageOps

# The processed bucket name — must match what you set in app.py
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "mt-image-source-processed")


def lambda_handler(event, context):
    """
    Entry point for the Lambda function.

    AWS calls this automatically when an S3 object-created event fires.
    The 'event' dict contains details about what was uploaded.
    """

    # ── Step 1: Extract the bucket name and filename from the trigger event ───
    # When S3 triggers Lambda, the event contains a 'Records' list.
    # Each record describes one file that was uploaded.
    record = event["Records"][0]
    source_bucket = record["s3"]["bucket"]["name"]
    filename = record["s3"]["object"]["key"]

    print(f"Triggered by upload: s3://{source_bucket}/{filename}")

    # ── Step 2: Download the uploaded image from S3 into memory ──────────────
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=source_bucket, Key=filename)
    image_data = response["Body"].read()

    # ── Step 3: Open the image with Pillow and flip it vertically ─────────────
    image = Image.open(BytesIO(image_data))

    # Normalize EXIF orientation first — phone photos store raw pixels rotated
    # with an EXIF tag telling apps how to display them upright. Without this,
    # flipping operates on the raw (rotated) pixels and produces unexpected results.
    image = ImageOps.exif_transpose(image)

    flipped = image.transpose(Image.FLIP_TOP_BOTTOM)  # upside down!

    # ── Step 4: Save the flipped image back into a BytesIO buffer ─────────────
    buffer = BytesIO()
    # Preserve the original format (JPEG or PNG)
    image_format = image.format if image.format else "JPEG"
    flipped.save(buffer, format=image_format)
    buffer.seek(0)  # rewind so boto3 can read from the start

    # ── Step 5: Upload the result to the processed bucket ─────────────────────
    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=filename,           # same filename, different bucket
        Body=buffer,
        ContentType=f"image/{image_format.lower()}",
    )

    print(f"Processed image saved to: s3://{PROCESSED_BUCKET}/{filename}")

    return {
        "statusCode": 200,
        "body": f"Flipped {filename} and saved to {PROCESSED_BUCKET}"
    }