import time
import logging
import sys, os, platform
import re
import requests
from colorama import init, Fore
import threading
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys
import random
import json
import base64
import pytesseract as pyt
import cv2
import eel
import socket
from datetime import datetime, timedelta

# Configure logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloudflare_bypass.log', mode='w')
    ]
)

init(autoreset=True)


def get_chromium_options(browser_path: str, arguments: list, thread_num: int) -> ChromiumOptions:
    """
    Configures and returns Chromium options, including setting unpacked extensions from the profile's extension folder.
    
    :param browser_path: Path to the Chromium browser executable.
    :param arguments: List of arguments for the Chromium browser.
    :param thread_num: Thread number to assign a unique extension and profile.
    :return: Configured ChromiumOptions instance.
    """
    
    options = ChromiumOptions()
    options.set_paths(browser_path=browser_path)
    # print(host, port)
    options.auto_port()
    # options.set_address=host
    # options.set_local_port=port
    options.set_user(user='Profile 10')
    # options.add_extension('NopeCHA')
    nopecha_path = os.getcwd() + '/tampermonkey'
    extension_path = os.getcwd() + '/BP-Proxy-Switcher-Chrome'
    command = f"-load-extension={extension_path},{nopecha_path}"
    
    
    if os.name == 'posix' and platform.system() == 'Darwin': vpn_extension_path = os.getcwd() + "/vpn"
    elif os.name == 'nt': vpn_extension_path = os.getcwd() + "\\vpn"
    command += f',{vpn_extension_path}'

    options.set_argument(command)


    

    # Add arguments to Chromium options
    for argument in arguments:
        options.set_argument(argument)

    # Add all unpacked extensions from the profile's "Extensions" folder
    # if os.path.exists(extensions_folder):
    #     for extension_id in os.listdir(extensions_folder):
    #         extension_path = os.path.join(extensions_folder, extension_id)
    #         if os.path.isdir(extension_path):
    #             # Find the latest version folder
    #             versions = sorted(os.listdir(extension_path), reverse=True)
    #             if versions:
    #                 version_folder = os.path.join(extension_path, versions[0])
    #                 manifest_path = os.path.join(version_folder, 'manifest.json')
    #                 if os.path.exists(manifest_path):
    #                     # Add unpacked extension to options
    #                     options.add_extension(version_folder)
    #                     logging.info(f"Thread {thread_num}: Added extension from {version_folder}")
    #                 else:
    #                     logging.warning(f"Thread {thread_num}: Manifest not found for extension {extension_id}")
    # else:
    #     logging.warning(f"Thread {thread_num}: Extensions folder does not exist at {extensions_folder}")

    # logging.info(f"Thread {thread_num}: Chromium options configured with user data path {user_data_path}.")
    return options

 
 
def add_script(driver, tampermonkey_id, script):
    while True:
        try:
            driver.get(f'chrome-extension://{tampermonkey_id}/options.html#nav=utils')
           
            current_dir = os.getcwd()
            necessary_path = current_dir + f'/tampermonkey_scripts/{script}'
            driver.ele('xpath://*[@id="input_ZmlsZV91dGlscw_file"]').input(necessary_path)
            time.sleep(1)
            tabs = driver.get_tabs()
            
            tabs[0].ele('css:div[class="ask_action_buttons"] > input:nth-child(1)').click()
            return True
        except Exception as e:
            print(e)
            return False


def read_tampermonkey_script(filename):
    # Construct the filename based on the thread number
    file_path = os.path.join('tampermonkey_scripts', filename)

    # Check if the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    
    # Read the contents of the JavaScript file
    with open(file_path, 'r', encoding='cp1251') as file:
        js_content = file.read()
    
    # Use regex to find the variable in the JavaScript content
    # Adjust the regex pattern based on the structure of your JS variable
        return js_content
    

def save_tampermonkey_script(file_path, script):
    with open(file_path, 'w', encoding='cp1251') as file:
        file.write(script)
    print(f"Script saved to {file_path}")


def parse_data_from_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Parse each line into (email, password, proxy)
    data = ''
    for line in lines:
        data += line + '\n'
    
    return data
    

def extract_time_from_text(text):
    # Use regex to extract the time in the format hh:mm:ss
    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', text)
    if time_match:
        time_str = time_match.group(1)
        # Convert the extracted time to a datetime object for today's date
        return datetime.strptime(time_str, '%H:%M:%S').time()
    else:
        return None

def time_difference(time1, time2):
    # Convert time to timedelta from midnight (00:00:00)
    t1 = timedelta(hours=time1.hour, minutes=time1.minute, seconds=time1.second)
    t2 = timedelta(hours=time2.hour, minutes=time2.minute, seconds=time2.second)
    
    # Return the difference as a timedelta object
    return t1 - t2


def connect_vpn(driver):
    blacklist = ['Iran', 'Egypt', 'Italy']
    while True:
        try:
            driver.get('chrome://extensions/')
            script_array = """
            return new Promise((resolve) => {
                chrome.management.getAll((extensions) => {
                    resolve(extensions); // Resolve with the full extensions array
                });
            });
            """

            # Execute the JavaScript and get the result
            extensions = driver.run_js(script_array)
            vpn_id = [extension['id'] for extension in extensions if "Urban VPN Proxy" in extension['name']]
            vpn_url = f'chrome-extension://{vpn_id[0]}/popup/index.html'

            driver.get(vpn_url)
            time.sleep(3)
            try: driver.ele('css:button[class="button button--pink consent-text-controls__action"]').click()
            except: pass
            try: driver.ele('css:#app > div > div.simple-layout > div.simple-layout__body > div > div > button').click()
            except: pass
            is_connected = None
            try: is_connected = driver.ele('css:div[class="play-button play-button--pause"]')
            except: pass
            if is_connected: 
                try: driver.ele('css:div[class="play-button play-button--pause"]').click()
                except: pass
            select_element = driver.ele('css:div[class="select-location"]')
            select_element.click()
            time.sleep(2)
            while True:
                element = random.choice((driver.eles('xpath://ul[@class="locations"][2]/li/p')))
                element_text = element.text
                if element_text not in blacklist: break
            driver.run_js("arguments[0].scrollIntoView();", element)
            
            element.click()
            time.sleep(5)
            break
        except Exception as e: 
            print(e) 
            time.sleep(5)
    return True



def worker(thread_num, initialUrl, serverName, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena, isVpn, adspower_api=None, adspower_id=None):
    print(thread_num, type(thread_num))
    """
    Worker function to run the code in a separate thread.
    
    :param thread_num: Thread number for assigning unique browser profile and extensions.
    """
    if not adspower_api:
        logging.info(f'Thread {thread_num} started.')
    else:
        logging.info(f'Browser {adspower_id} started')
    # Chromium Browser Path
    browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")
    
    # Arguments to make the browser better for automation and less detectable.
    arguments = [
         "-no-first-run",
        "-force-color-profile=srgb",
        "-metrics-recording-only",
        "-password-store=basic",
        "-use-mock-keychain",
        "-export-tagged-pdf",
        "-no-default-browser-check",
        "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
        "-deny-permission-prompts",
        "-disable-gpu",
        "-accept-lang=en-US",
    ]
    host, port = None, None
    if adspower_api:
        adspower_link = f"{adspower_api}/api/v1/browser/start?serial_number={adspower_id}"
        print(adspower_link)

        adspower_link = adspower_link
        if adspower_link:
            resp = requests.get(adspower_link).json()
            if resp["code"] != 0:
                print(resp["msg"])
                print("please check ads_id")
                sys.exit()
            host, port = resp['data']['ws']['selenium'].split(':')
    if not host and not port: options = get_chromium_options(browser_path, arguments, thread_num)
    # Initialize the browser
    if adspower_api: driver = ChromiumPage(addr_or_opts=host+":"+port)
    else: driver = ChromiumPage(addr_or_opts=options)
    time.sleep(5)
    if not adspower_api:
        while True:
            time.sleep(1)
            tabs = driver.get_tabs()
            if len(tabs) > 1:
                driver.close_tabs(tabs_or_ids=tabs[1:], others=True)
            else: break

    try:
        driver.get('chrome://extensions/')
        time.sleep(1)
    
        # Example script to retrieve extensions
        script_array = """
        return new Promise((resolve) => {
            chrome.management.getAll((extensions) => {
                resolve(extensions); // Resolve with the full extensions array
            });
        });
        """

        # Execute the JavaScript and get the result
        extensions = driver.run_js(script_array)
        
        tampermonkey_id = [extension['id'] for extension in extensions if "Tampermonkey" in extension['name']]

        path_to_script = f'script_settings.js'
        script_raw = read_tampermonkey_script(path_to_script)
        path_to_main_script = f'main_script.js'
        script_main_raw = read_tampermonkey_script(path_to_main_script)
        script = re.sub(r'(?<=localhost:)(\d+)?(?=/)', str(serverPort), script_main_raw)


        path_to_main_script = os.path.join(os.getcwd(), 'tampermonkey_scripts', 'main_script.js')
        path_to_settings_script = os.path.join(os.getcwd(), 'tampermonkey_scripts', 'script_settings.js')
        script_dir = os.getcwd() + '\\tampermonkey_scripts'
        save_tampermonkey_script(path_to_main_script, script)
        new_chrome_profile = None
        if not adspower_api: new_chrome_profile = f"{serverName}_{thread_num}"
        else: new_chrome_profile = f"{serverName}"
        print(new_chrome_profile)
        # Use regex to replace the chromeProfile value in the JS string
        script = re.sub(
            r"chromeProfile:\s*'(.*?)'",  # Matches "chromeProfile: 'value'"
            f"chromeProfile: '{new_chrome_profile}'",  # Replace with new profile
            script_raw
        )

        # Replace `chromeProfile` in the assignment
        script = re.sub(
            r"settings\.chromeProfile\s*=\s*'(.*?)'",  # Matches "settings.chromeProfile = 'value'"
            f"settings.chromeProfile = '{new_chrome_profile}'",  # Replace with new profile
            script
        )
        save_tampermonkey_script(path_to_settings_script, script)
        print(tampermonkey_id)
        print('add tampermonkey_script')
        time.sleep(2)
        add_script(driver, tampermonkey_id[0], 'main_script.js')
        add_script(driver, tampermonkey_id[0], 'script_settings.js')

        if proxyList:
            time.sleep(5)
            #proxy configuration
            
            filtered_extensions = [extension for extension in extensions if "BP Proxy Switcher" in extension['name']]
            
            proxy_id = [extension['id'] for extension in filtered_extensions if 'id' in extension][0]
            proxy_url = f'chrome-extension://{proxy_id}/popup.html'
            driver.get(proxy_url)
            # proxies = parse_data_from_file('proxies.txt')
            delete_tab = driver.ele('xpath://*[@id="deleteOptions"]')
            delete_tab.click()
            time.sleep(1)
            driver.ele('xpath://*[@id="privacy"]/div[1]/input').click()
            driver.ele('xpath://*[@id="privacy"]/div[2]/input').click()
            driver.ele('xpath://*[@id="privacy"]/div[4]/input').click()
            driver.ele('xpath://*[@id="privacy"]/div[7]/input').click()
            driver.ele('xpath://*[@id="optionsOK"]').click()
            time.sleep(1)
            edit = driver.ele('xpath://*[@id="editProxyList"]/small/b')
            edit.click()
            time.sleep(1)
            text_area = driver.ele('xpath://*[@id="proxiesTextArea"]')
            text_area.input(proxyList)
            time.sleep(1)
            ok_button = driver.ele('xpath://*[@id="addProxyOK"]')
            ok_button.click()
            time.sleep(1)
            proxy_switch_list = driver.eles('css:#proxySelectDiv > div > div > ul > li')
            proxy_switch_list[random.randint(2, len(proxy_switch_list))].click()
            time.sleep(5)
            proxy_auto_reload_checkbox = driver.ele('xpath://*[@id="autoReload"]')
            proxy_auto_reload_checkbox.click()
            time.sleep(10)
        if isVpn:
            connect_vpn(driver)
        if isNopeCha == 'nopecha':
            captcha_url = 'https://nopecha.com/setup#awscaptcha_auto_open=true|awscaptcha_auto_solve=false|awscaptcha_solve_delay=true|awscaptcha_solve_delay_time=0|disabled_hosts=|enabled=true|funcaptcha_auto_open=true|funcaptcha_auto_solve=false|funcaptcha_solve_delay=true|funcaptcha_solve_delay_time=0|geetest_auto_open=false|geetest_auto_solve=false|geetest_solve_delay=true|geetest_solve_delay_time=1000|hcaptcha_auto_open=true|hcaptcha_auto_solve=false|hcaptcha_solve_delay=true|hcaptcha_solve_delay_time=3000|sub_1QD8apCRwBwvt6pthLg8WQKk|keys=|lemincaptcha_auto_open=false|lemincaptcha_auto_solve=false|lemincaptcha_solve_delay=true|lemincaptcha_solve_delay_time=1000|perimeterx_auto_solve=false|perimeterx_solve_delay=true|perimeterx_solve_delay_time=1000|recaptcha_auto_open=false|recaptcha_auto_solve=false|recaptcha_solve_delay=true|recaptcha_solve_delay_time=1000|recaptcha_solve_method=Image|textcaptcha_auto_solve=true|textcaptcha_image_selector=.captcha-code|textcaptcha_input_selector=#solution|textcaptcha_solve_delay=true|textcaptcha_solve_delay_time=0|turnstile_auto_solve=true|turnstile_solve_delay=true|turnstile_solve_delay_time=30000'
            driver.get("about:blank")
            driver.run_js(f"window.location.href='{captcha_url}'")
            time.sleep(2)
            driver.run_js('window.location.reload()')
            time.sleep(2)
        driver.get(initialUrl)
        #https://tickets.realmadrid.com/realmadrid_futbol/en_US/entradas/evento/39300/session/2225217/select 
        
        print(Fore.GREEN + f"Thread {thread_num}: Successfully started!\n")
        while True:
            try:
                if isMadridista:
                    
                    madridista_modal = driver.ele('css:.reveal-modal-content')
                    if madridista_modal:
                       time.sleep(3)
                       try: driver.ele('css:body > div.cookie-backdrop > div > div > div > div.text-center.cookie-controls > button:nth-child(2)').click()
                       except: pass
                       login = driver.ele('css:#memberUser') 
                       password = driver.ele('css:#memberPwd')
                       login.input(numero)
                       password.input(contrasena)
                       validate = driver.ele('css:#sale-member-submit')
                       validate.click()
                       is_ok = driver.ele('css:#success-member-login > div')
                       if is_ok: driver.refresh()

            except: pass
            try:
                if isNopeCha == 'integrated':
                    while True:
                        captcha_code = driver.run_js('return document.querySelector("img.captcha-code");')
                        #print(captcha_code)
                        if captcha_code:
                            captcha_code_src = captcha_code.attrs['src']
                            #print(captcha_code_src)
                            
                                
                            header, encoded = captcha_code_src.split(',', 1)

                            # Decode the base64 data
                            image_data = base64.b64decode(encoded)

                            output_file = f"output_image{thread_num}.jpg"
                            with open(output_file, "wb") as f:
                                f.write(image_data)
                            
                            img = cv2.imread(f'output_image{thread_num}.jpg')
                            
                            current_dir = os.getcwd()
                            pyt.pytesseract.tesseract_cmd = current_dir + '\\Tesseract-OCR\\tesseract.exe'

                            text = pyt.image_to_string(img)

                            print(text)
                            if not text: 
                                driver.refresh()
                                continue
                            driver.ele('css:input[name="CaptchaCode"]').input(text)
                            try:
                                os.remove(output_file)
                            except: pass
                            break
                        elif not captcha_code: break

            except Exception as e: print(e)
            # print('it goes here')
            # temp_timer = None
            # while True:
            #     try:
            #         # Try to find the elements
            #         mapNavigator, bottomLeftText = None, None
            #         try: bottomLeftText = driver.ele('css:#bottomLeftText')
            #         except: pass
            #         print('found text')
            #         try: mapNavigator = driver.ele('css:div[id="map-navigator"]')
            #         except: pass
            #         print('found map')
            #         # Extract timer if bottomLeftText is found
            #         if bottomLeftText:
            #             print('if bottom')
            #             timer = extract_time_from_text(bottomLeftText.text)
            #             print('timer:', timer)
            #             print('temp_timer', temp_timer)
            #         else:
            #             print('else')
            #             timer = None

            #         # Check for timer difference
            #         if timer is not None and temp_timer is not None:
            #             difference = time_difference(temp_timer, timer)
            #             if abs(difference.total_seconds()) > 1 * 60:
            #                 print("The difference is greater than 1 minute. Initiating page reload")
            #                 driver.refresh()
            #                 temp_timer = timer  # Update temp_timer after refresh
            #                 continue
                    
            #         # Handle the case where bottomLeftText is None but mapNavigator exists
            #         if bottomLeftText is None and mapNavigator is not None:
            #             print('No timer found, initiating page reload')
            #             driver.refresh()
            #             temp_timer = timer
            #             continue
                    
            #         # Update temp_timer if no condition is met
            #         temp_timer = timer if timer is not None else temp_timer
                    
            #     except Exception as e: 
            #         print(e)
            #         break
            try:
                minPrice = driver.ele('css:div[id="settingsFormContainer"] > form > input[id="minPrice"]')
                if minPrice:
                    maxPrice = driver.ele('css:div[id="settingsFormContainer"] > form > input[id="maxPrice"]')
                    ticketsToBuy = driver.ele('css:div[id="settingsFormContainer"] > form > input[id="ticketsToBuy"]')
                    settingsButton = driver.ele('css:#settingsForm > button')
                    
                    if len(minPrice.value) == 0 and len(maxPrice.value) == 0 and len(ticketsToBuy.value) == 0:
                        minPrice.input('0')
                        maxPrice.input('9999')
                        ticketsToBuy.input(str(random.randint(2, 4)))
                        settingsButton.click()
            except:pass
            #try:
            #    bottomLeftText = driver.ele('css:#bottomLeftText')
            #    mapNavigator = driver.ele('css:div[id="map-navigator"]')
            #    
            #    # Extract timer if bottomLeftText is found
            #    timer = extract_time_from_text(bottomLeftText.text) if bottomLeftText else None
            #    
            #    if timer is not None and temp_timer is not None:
            #        difference = time_difference(temp_timer, timer)

                    # Check if the difference is greater than 15 minutes (900 seconds)
            #        if abs(difference.total_seconds()) > 15 * 60:
            #            print("The difference is greater than 15 minutes. Initiating page reload")
            #            driver.refresh()
            #            temp_timer = timer  # Update temp_timer after refresh
            #            continue
            #    
            #    if bottomLeftText is None and mapNavigator is not None:
            #        print('No timer found, initiating page reload')
            #        driver.refresh()
            #        temp_timer = timer
            #        continue
                
            #    # Update temp_timer if no condition is met
            #    temp_timer = timer if timer is not None else temp_timer
                
            #except:pass
            try:
                tabs = driver.get_tabs()
                for tab in tabs:
                    button = None
                    eles = tab.eles("tag:input")
                    for ele in eles:
                        if "name" in ele.attrs.keys() and "type" in ele.attrs.keys():
                            if "turnstile" in ele.attrs["name"] and ele.attrs["type"] == "hidden":
                                button = ele.parent().shadow_root.child()("tag:body").shadow_root("tag:input")
                                continue

                    if button:
                        cf_bypasser = CloudflareBypasser(tab)
                        cf_bypasser.bypass()
                time.sleep(5)
            except Exception as e: 
                print(e)
                time.sleep(5)
                continue

            
    except Exception as e:
        print(f"Thread {thread_num} - An error occurred: {str(e)}")
    finally:
        print(f'Thread {thread_num}: Closing the browser.')
        driver.quit()
        
        
@eel.expose
def main(initialUrl, serverName, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena, isVpn, adspower_api=None, adspower_ids=[]):
    print(initialUrl, serverName, serverPort, isNopeCha, browsersAmount, isMadridista, numero, contrasena, isVpn)
    # eel.spawn(run(initialUrl, isSlack, browserAmount, proxyList))
   
    adspower_ids = [line.strip() for line in adspower_ids.strip().splitlines() if line.strip()]
    
    if not adspower_api and not adspower_ids:
        threads = []
        for i in range(1, int(browsersAmount)+1):  # Example: 3 threads, modify as needed
            # if i!= 1: time.sleep(i*30)
            thread = threading.Thread(target=worker, args=(i, initialUrl, serverName, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena, isVpn))
            threads.append(thread)
            thread.start()
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
    else:
        threads = []
        for i, adspower_id in enumerate(adspower_ids):
            if i+1!=1: time.sleep(i+1*30)
            thread = threading.Thread(target=worker, args=(i+1, initialUrl, adspower_id, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena, isVpn, adspower_api, adspower_id))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


def is_port_open(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((host, port))
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    finally:
        sock.close()


if __name__ == "__main__":
    
    eel.init('web')
    
    port = 8001
    while True:
        try:
            if not is_port_open('localhost', port):
                eel.start('main.html', size=(600, 900), port=port)
                break
            else:
                port += 1
        except OSError as e:
            print(e)