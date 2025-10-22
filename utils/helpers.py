import os
import socket
import colorama
from datetime import datetime
from colorama import Fore, Style
from typing import Iterable, List, Optional

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


def is_port_open(host: str, port: int, timeout_sec: float = 1.0) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect((host, port))
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    finally:
        sock.close()


def clean_adspower_ids(adspower_ids: Iterable[str | int] | str | None) -> List[str]:
    """Accept list or multiline string; return cleaned list of strings."""
    if adspower_ids is None:
        return []
    if isinstance(adspower_ids, str):
        return [ln.strip() for ln in adspower_ids.splitlines() if ln.strip()]
    return [str(x).strip() for x in adspower_ids if str(x).strip()]


def build_adspower_profile_url(api: Optional[str], profile_id: Optional[str]) -> Optional[str]:
    if api and profile_id:
        return f"{api}/api/v1/browser/start?serial_number={profile_id}"
    return api 


def generate_profile_name(thread_index: int, adspower_id: Optional[str]) -> str:
    suffix = adspower_id if adspower_id else str(thread_index)
    return f"{os.name}_{suffix}"
