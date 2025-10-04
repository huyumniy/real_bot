import os
import colorama
from datetime import datetime
from colorama import Fore, Style

colorama.init(autoreset=True)

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


def log_line(info: str, data: str):
    """
    Prints one line with:
      • timestamp in green
      • info label in cyan
      • data payload in white
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"{Fore.GREEN}{ts}"
        f"{Fore.CYAN} [{info.upper()}]"
        f"{Style.RESET_ALL} {data}"
    )


def write_to_txt(path, e):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(path, 'a') as file: file.write(ts + str(e) + "\n")
    except Exception as exc:
        print("function write_to_txt exception: ", exc)