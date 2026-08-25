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
# 必須使用 bedrock-agent 客戶端
bedrock_agent = boto3.client('bedrock-agent')

def process_and_upload():
    md_files = glob.glob(f'{TARGET_FOLDER}/*.md')
    print(f"在 {TARGET_FOLDER}/ 目錄下找到 {len(md_files)} 個 Markdown 檔案。")
    
    uploaded_count = 0

    for filepath in md_files:
        filename = os.path.basename(filepath)
        s3_key = filename 
        json_s3_key = f"{filename}.metadata.json"

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                raw_yaml = parts[1]
                markdown_body = parts[2].strip()

                metadata_dict = yaml.safe_load(raw_yaml)
                bedrock_metadata = {"metadataAttributes": metadata_dict}

                s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=markdown_body.encode('utf-8'))
                s3.put_object(Bucket=BUCKET_NAME, Key=json_s3_key, Body=json.dumps(bedrock_metadata, ensure_ascii=False).encode('utf-8'))
                print(f"✅ 上傳成功 (含 Metadata): {s3_key} 與 {json_s3_key}")
                uploaded_count += 1
        else:
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=content.encode('utf-8'))
            print(f"⚠️ 上傳成功 (純 Markdown): {s3_key}")
            uploaded_count += 1

    # 關鍵：整批上傳完成後，發送 API 呼叫觸發 Bedrock 向量化
    if uploaded_count > 0:
        try:
            response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KB_ID, 
                dataSourceId=DS_ID
            )
            print(f"🚀 同步已啟動！任務 ID: {response['ingestionJob']['ingestionJobId']}")
        except bedrock_agent.exceptions.ConflictException:
            print("⚠️ Bedrock 已有任務執行中，檔案已寫入 S3，忽略此次重複觸發。")
        except Exception as e:
            print(f"❌ 觸發 Bedrock 同步時發生錯誤: {str(e)}")
            raise e
    else:
        print("ℹ️ 沒有發現需要同步的檔案。")

if __name__ == "__main__":
    process_and_upload()
