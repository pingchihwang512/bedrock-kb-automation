import os, glob, yaml, json, boto3

BUCKET_NAME = os.environ['S3_BUCKET_NAME']
KB_ID = os.environ['KNOWLEDGE_BASE_ID']
DS_ID = os.environ['DATA_SOURCE_ID']

s3 = boto3.client('s3')
bedrock_agent = boto3.client('bedrock-agent')

def process_and_upload():
    md_files = glob.glob('tours/*.md')
    for filepath in md_files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                raw_yaml = parts[1]
                markdown_body = parts[2].strip()
                
                # 準備 Metadata JSON
                metadata_dict = yaml.safe_load(raw_yaml)
                bedrock_metadata = {"metadataAttributes": metadata_dict}
                json_filename = f"{filename}.metadata.json"
                
                # 上傳 MD 與 JSON 到 S3
                s3.put_object(Bucket=BUCKET_NAME, Key=filename, Body=markdown_body.encode('utf-8'))
                s3.put_object(Bucket=BUCKET_NAME, Key=json_filename, Body=json.dumps(bedrock_metadata, ensure_ascii=False).encode('utf-8'))
                print(f"上傳成功: {filename} 與 {json_filename}")

    # 觸發知識庫同步
    response = bedrock_agent.start_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=DS_ID)
    print(f"同步已啟動！任務 ID: {response['ingestionJob']['ingestionJobId']}")

if __name__ == "__main__":
    process_and_upload()
