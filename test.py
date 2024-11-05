import time
import logging
import sys, os
import re
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

    options.auto_port()
    options.set_user(user='Profile 10')
    options.add_extension('tampermonkey')
    options.add_extension('NopeCHA')

    options.add_extension('BP-Proxy-Switcher-Chrome')


    

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


def add_tampermonkey_script(driver, script_text):
    while True:
        try:
            driver.get('chrome-extension://dhdgffkkebhmkfjojejmpbldmpobfkfo/options.html#nav=new-user-script+editor')
           
            selection = driver.ele('css:#label_bmV3LXVzZXItc2NyaXB0X3NlbGVjdGlvbg_editormenulabel_id')
            selection.click()
            time.sleep(1)
            tr = driver.ele('css:table>#tr_bmV3LXVzZXItc2NyaXB0X3NlbGVjdGlvbl9zZWxlY3RTY29wZQ_editorsubmenuentry_tr')
            tr.click()
            text_input = driver.ele('xpath://*[@id="div_bmV3LXVzZXItc2NyaXB0X2VkaXQ"]/div/div/div[6]/div[1]/div')
            driver.actions.key_down(Keys.DEL)
            text_input.input(script_text)
            time.sleep(1)
            file_selection = driver.ele('css:#label_bmV3LXVzZXItc2NyaXB0X2ZpbGU_editormenulabel_id')
            file_selection.click()
            time.sleep(1)
            save_button = driver.ele('css:#td_bmV3LXVzZXItc2NyaXB0X2VkaXRvcnN1Ym1lbnVlbnRyeV90ZF9sZmlsZV9zYXZl')
            save_button.click()
            return True
        except Exception as e:
            print(e)
            return False
 
 
def add_main_script(driver):
    while True:
        try:
            driver.get('chrome-extension://dhdgffkkebhmkfjojejmpbldmpobfkfo/options.html#nav=utils')
           
            current_dir = os.getcwd()
            necessary_path = current_dir + '/tampermonkey_scripts/main_script.js'
            driver.ele('xpath://*[@id="input_ZmlsZV91dGlscw_file"]').input(necessary_path)
            time.sleep(1)
            tabs = driver.get_tabs()
            
            tabs[0].ele('xpath://*[@id="input_SW5zdGFsbF91bmRlZmluZWQ_bu"] | //*[@id="input_I0FCMD0MjhCTF91bmRlZmluZWQ_bu"] | //*[@id="input_EkFCMD0MjhCOF91bmRlZmluZWQ_bu"]').click()
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


def worker(thread_num, initialUrl, serverName, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena):
    """
    Worker function to run the code in a separate thread.
    
    :param thread_num: Thread number for assigning unique browser profile and extensions.
    """
    logging.info(f'Thread {thread_num} started.')
    time.sleep(thread_num)
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

    options = get_chromium_options(browser_path, arguments, thread_num)

    # Initialize the browser
    driver = ChromiumPage(addr_or_opts=options)
    try:
        time.sleep(5)
        tabs = driver.get_tabs()
        if len(tabs) > 1:
            driver.close_tabs(tabs_or_ids=tabs[1:], others=True)
        path_to_script = f'script_settings.js'
        script_raw = read_tampermonkey_script(path_to_script)
        path_to_main_script = f'main_script.js'
        script_main_raw = read_tampermonkey_script(path_to_main_script)
        script = re.sub(r'(?<=localhost:)(\d+)?(?=/)', str(serverPort), script_main_raw)


        path_to_main_script = os.path.join(os.getcwd(), 'tampermonkey_scripts', 'main_script.js')
        script_dir = os.getcwd() + '\\tampermonkey_scripts'
        save_tampermonkey_script(path_to_main_script, script)

        new_chrome_profile = f"{serverName}_{thread_num}"
        # Use regex to replace the chromeProfile value in the JS string
        script = re.sub(
           r"(chromeProfile:\s*')[^']*(')",
           rf"\1{new_chrome_profile}\2",
           script_raw
        )
        script = re.sub(
           r"(settings.chromeProfile =\s*')[^']*(')",
           rf"\1{new_chrome_profile}\2",
           script_raw
        )
        
        add_tampermonkey_script(driver, script)
        time.sleep(2)
        add_main_script(driver)

        if proxyList:
            time.sleep(5)
            #proxy configuration
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
def main(initialUrl, serverName, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena):
    print(initialUrl, serverName, serverPort, isNopeCha, browsersAmount, isMadridista, numero, contrasena)
    # eel.spawn(run(initialUrl, isSlack, browserAmount, proxyList))
    threads = []
    for i in range(1, int(browsersAmount)+1):  # Example: 3 threads, modify as needed
        if i!= 1: time.sleep(i*30)
        thread = threading.Thread(target=worker, args=(i, initialUrl, serverName, serverPort, isNopeCha, browsersAmount, proxyList, isMadridista, numero, contrasena))
        threads.append(thread)
        thread.start()
    # Wait for all threads to complete
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
                eel.start('main.html', size=(600, 800), port=port)
                break
            else:
                port += 1
        except OSError as e:
            print(e)
