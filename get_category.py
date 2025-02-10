import os
import subprocess
import openai
import json
import pandas as pd  # ต้องติดตั้ง pandas: pip install pandas

# โหลด config จากไฟล์ config.txt
def load_config(config_path):
    config = {}
    try:
        with open(config_path, 'r') as file:
            for line in file:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        exit(1)
    return config

# โหลดค่า config
config = load_config("config.txt")
openai.api_key = config.get("OPENAI_API_KEY")
openai_model = config.get("OPENAI_MODEL", "gpt-3.5-turbo")
folder_path = config.get("FOLDER_PATH", "./")  # ค่า default เป็นโฟลเดอร์ปัจจุบัน
output_csv = config.get("OUTPUT_CSV", "output.csv")  # ค่า default เป็น output.csv

# ฟังก์ชันอ่าน metadata จากไฟล์โดยใช้ subprocess
def read_metadata_from_file(file_path):
    try:
        result = subprocess.run(['exiftool', '-j', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
        
        metadata = json.loads(result.stdout)
        if metadata:
            title = metadata[0].get('Title', 'No Title')
            keywords = metadata[0].get('Keywords', ['No Keywords'])
            return title, keywords
        return 'No Title', ['No Keywords']
    except subprocess.CalledProcessError as e:
        print(f"Error executing exiftool: {e.stderr}")
        return 'No Title', ['No Keywords']
    except json.JSONDecodeError:
        print("Error decoding JSON metadata")
        return 'No Title', ['No Keywords']
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 'No Title', ['No Keywords']

# ฟังก์ชันเรียก OpenAI เพื่อจัดหมวดหมู่
def call_openai_to_get_category(title, keywords):
    categories = {
        "Animals": 1, "Buildings and Architecture": 2, "Business": 3, "Drinks": 4,
        "The Environment": 5, "States of Mind": 6, "Food": 7, "Graphic Resources": 8,
        "Hobbies and Leisure": 9, "Industry": 10, "Landscapes": 11, "Lifestyle": 12,
        "People": 13, "Plants and Flowers": 14, "Culture and Religion": 15, "Science": 16,
        "Social Issues": 17, "Sports": 18, "Technology": 19, "Transport": 20, "Travel": 21
    }

    prompt = f"Given the title '{title}' and keywords '{keywords}', select the most appropriate category from the list: {', '.join(categories.keys())}."

    try:
        # เรียก API ด้วยรูปแบบใหม่
        response = openai.ChatCompletion.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that categorizes images."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60
        )

        category_text = response['choices'][0]['message']['content'].strip()
        for category_name, category_id in categories.items():
            if category_name.lower() in category_text.lower():
                return category_name, category_id
        return "Uncategorized", 0
    except openai.OpenAIError as e:  # ใช้ OpenAIError แบบใหม่
        print(f"OpenAI API error: {e}")
        return "Uncategorized", 0

# ฟังก์ชันเพื่อสร้างไฟล์ .csv สำหรับ Adobe Stock
def write_csv_file(data, output_path):
    df = pd.DataFrame(data, columns=["Filename", "Title", "Keywords", "Category", "Releases"])
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f'CSV file saved to: {output_path}')

# ฟังก์ชันประมวลผลไฟล์ทั้งหมดในโฟลเดอร์
def process_folder(folder_path, output_csv):
    data = []
    categories = {
        "Animals": 1, "Buildings and Architecture": 2, "Business": 3, "Drinks": 4,
        "The Environment": 5, "States of Mind": 6, "Food": 7, "Graphic Resources": 8,
        "Hobbies and Leisure": 9, "Industry": 10, "Landscapes": 11, "Lifestyle": 12,
        "People": 13, "Plants and Flowers": 14, "Culture and Religion": 15, "Science": 16,
        "Social Issues": 17, "Sports": 18, "Technology": 19, "Transport": 20, "Travel": 21
    }

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.startswith("._"):
                continue
            if file.lower().endswith(('.jpg', '.png', '.jpeg', '.mp4', '.mov', '.avi')):
                file_path = os.path.join(root, file)
                title, keywords = read_metadata_from_file(file_path)
                if title and keywords:
                    keywords = [str(keyword) for keyword in keywords]
                    category_name, category_id = call_openai_to_get_category(title, keywords)
                    if category_id:
                        data.append([file, title, ', '.join(keywords), category_id, ''])
                        print(f"File: {file}, Category: {category_name}")
                    else:
                        print(f"File: {file}, Category not found")
                else:
                    print(f"File: {file}, No metadata found")
    write_csv_file(data, output_csv)

# เริ่มต้นประมวลผลโฟลเดอร์
process_folder(folder_path, output_csv)
