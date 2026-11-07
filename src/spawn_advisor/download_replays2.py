import os
import requests
import time

start_id = 441650
count = 10000
# Обновленный путь к нужной папке
save_dir = r"K:\pet-projects\wotAI\data\raw\web"

# Убедимся, что все вложенные папки существуют (создаст всю цепочку, если ее нет)
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

for i in range(count):
    current_id = start_id - i
    url = f"https://wot-record.com/download/{current_id}"
    
    try:
        response = requests.get(url, stream=True, timeout=10)
        
        if response.status_code == 200:
            # Пытаемся достать оригинальное имя файла из заголовков
            filename = f"replay_{current_id}.wotreplay"
            if 'content-disposition' in response.headers:
                cd = response.headers['content-disposition']
                if 'filename=' in cd:
                    filename = cd.split('filename=')[1].strip('"\'')
            
            file_path = os.path.join(save_dir, filename)
                    
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[{i+1}/{count}] Скачан: {filename} (ID: {current_id})")
        else:
            print(f"[{i+1}/{count}] Ошибка {response.status_code} для ID: {current_id}")
            
    except Exception as e:
        print(f"[{i+1}/{count}] Сбой при скачивании ID {current_id}: {e}")
    
    time.sleep(0.5)