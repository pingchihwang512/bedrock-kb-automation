import os
import glob
import yaml
import json
import boto3

BUCKET_NAME = os.environ['S3_BUCKET_NAME']
KB_ID = os.environ['KNOWLEDGE_BASE_ID']
DS_ID = os.environ['DATA_SOURCE_ID']
TARGET_FOLDER = os.environ.get('TARGET_FOLDER', 'peony-tours').strip()

s3 = boto3.client('s3')
bedrock_agent = boto3.client('bedrock-agent')

def process_and_upload():
    md_files = glob.glob(f'{TARGET_FOLDER}/*.md')
    print(f"在 {TARGET_FOLDER}/ 目錄下找到 {len(md_files)} 個 Markdown 檔案。")
    
    uploaded_count = 0

    for filepath in md_files:
        filename = os.path.basename(filepath)
        
        # 💡 若你的 Bedrock Data Source 設在 S3 根目錄，維持用 filename 即可
        # 💡 若設在子目錄，可改為：s3_key = f"{TARGET_FOLDER}/{filename}"
        s3_key = filename 
        json_s3_key = f"{filename}.metadata.json"

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 判斷是否有 Frontmatter (---)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                raw_yaml = parts[1]
                markdown_body = parts[2].strip()

                # 準備 Metadata JSON
                metadata_dict = yaml.safe_load(raw_yaml)
                bedrock_metadata = {"metadataAttributes": metadata_dict}

                # 上傳 MD 主體與 JSON 至 S3
                s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=markdown_body.encode('utf-8'))
                s3.put_object(Bucket=BUCKET_NAME, Key=json_s3_key, Body=json.dumps(bedrock_metadata, ensure_ascii=False).encode('utf-8'))
                print(f"✅ 上傳成功 (含 Metadata): {s3_key} 與 {json_s3_key}")
                uploaded_count += 1
        else:
            # 💡 備案：若檔案沒有 Frontmatter，依然上傳純 MD 檔，避免檔案被遺漏
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=content.encode('utf-8'))
            print(f"⚠️ 上傳成功 (純 Markdown 無 Metadata): {s3_key}")
            uploaded_count += 1

    # 有成功上傳檔案才觸發知識庫同步
    if uploaded_count > 0:
        response = bedrock_agent.start_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=DS_ID)
        print(f"🚀 同步已啟動！任務 ID: {response['ingestionJob']['ingestionJobId']}")
    else:
        print("ℹ️ 沒有發現需要同步的檔案。")

if __name__ == "__main__":
    process_and_upload()
