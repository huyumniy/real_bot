import os

def read_js_script(folder_name, filename):
    file_path = os.path.join(folder_name, filename)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} not found.")

    with open(file_path, 'r', encoding='cp1251') as file:
        js_content = file.read()
        return js_content
    

def save_js_script(file_path, script):
    with open(file_path, 'w', encoding='cp1251') as file:
        file.write(script)
    print(f"Script saved to {file_path}")

