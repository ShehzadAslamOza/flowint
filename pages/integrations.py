import streamlit as st
import boto3
from pymongo import MongoClient
import uuid
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# AWS + MongoDB config (replace with your actual keys)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
MONGODB_URI = os.getenv("MONGODB_URI")

# MongoDB Setup
client = MongoClient(MONGODB_URI)
db = client["ita-rag-db"]
integrations_collection = db["integrations"]

# S3 Client
s3 = boto3.client("s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

st.title("🔌 Integrations")
st.write("Name your integration, upload OpenAPI YAML, and add an optional description.")

# Form for integration details
with st.form("upload_form"):
    name = st.text_input("Integration Name")
    description = st.text_area("Description", height=100)
    uploaded_file = st.file_uploader("Upload OpenAPI file", type=["yaml", "yml"])
    submit = st.form_submit_button("Upload")

    if submit:
        if not (name and uploaded_file):
            st.warning("Please provide a name and upload a file.")
        else:
            try:
                # Generate a unique filename
                file_id = str(uuid.uuid4())
                s3_key = f"openapi-specs/{file_id}_{uploaded_file.name}"

                # Upload to S3
                s3.upload_fileobj(
                    uploaded_file,
                    BUCKET_NAME,
                    s3_key,
                    ExtraArgs={"ContentType": "text/yaml", "ACL": "public-read"}
                )

                # Generate public URL
                s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

                # Save metadata to MongoDB
                integrations_collection.insert_one({
                    "name": name,
                    "description": description,
                    "s3_url": s3_url,
                    "filename": uploaded_file.name,
                    "isVectorized": False
                })

                st.success("Integration uploaded and saved successfully!")
                st.markdown(f"**File URL:** [View File]({s3_url})")

            except Exception as e:
                st.error(f"Upload failed: {e}")

st.divider()
st.subheader("📋 Existing Integrations")

# Fetch all integrations from MongoDB
integrations = list(integrations_collection.find())

if not integrations:
    st.info("No integrations uploaded yet.")
else:
    for integration in integrations:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**🔗 {integration['name']}**")
            st.markdown(f"- Description: {integration.get('description', '')}")
            st.markdown(f"- [View OpenAPI File]({integration['s3_url']})")
        with col2:
            # Toggle "Add to RAG" or "Remove from RAG"
            if integration.get("isRagged", False):
                if st.button(f"❌ Remove from RAG", key=f"remove_{integration['_id']}"):
                    integrations_collection.update_one(
                        {"_id": integration["_id"]},
                        {"$set": {"isRagged": False}}
                    )
                    st.rerun()

            else:
                if st.button(f"✅ Add to RAG", key=f"add_{integration['_id']}"):
                    integrations_collection.update_one(
                        {"_id": integration["_id"]},
                        {"$set": {"isRagged": True}}
                    )
                    st.rerun()
        with col3:
            # Delete integration
            if st.button("🗑️ Delete", key=f"delete_{integration['_id']}"):
                # Delete file from S3 too
                try:
                    s3_key = integration["s3_url"].split(".amazonaws.com/")[1]
                    s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
                except:
                    pass  # if file doesn't exist, skip
                integrations_collection.delete_one({"_id": integration["_id"]})
                st.rerun()
