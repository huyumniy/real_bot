import os, sys
import nodriver as uc
import time
import random
import requests
from pprint import pprint
from .helpers import save_js_script, read_js_script
import re


async def browser_connect(open_url=None):
    """
    Create and return an undetected-chromedriver driver (with extensions and optional remote Selenium host).
    """
    print("[DEBUG] Creating driver…")
    cwd = os.getcwd()

    nopecha_path = os.path.join(cwd, 'NopeCHA')
    tampermonkey_path = os.path.join(cwd, "tampermonkey")
    bpproxyswitcher_path = os.path.join(cwd, "BP-Proxy-Switcher-Chrome")
    host, port = None, None

    if open_url:
        print(f"[DEBUG] Fetching remote Selenium info from {open_url}")
        resp = requests.get(open_url).json()
        if resp["code"] != 0:
            print(resp["msg"])
            print("please check ads_id")
            sys.exit()
        host, port = resp['data']['ws']['selenium'].split(':')

    # Build nodriver.Config
    if host and port:
        config = uc.Config(
            user_data_dir=None,
            headless=False,
            browser_executable_path=None,
            browser_args=None,
            sandbox=True,
            lang='en-US',
            host=host,
            port=int(port)
        )
        print(f"[DEBUG] Using remote Selenium at {host}:{port}")
    else:
        config = uc.Config(
            user_data_dir=None,
            headless=False,
            browser_executable_path=None,
            browser_args=None,
            sandbox=True,
            lang='en-US'
        )

    # Add extensions
    print(f"[DEBUG] Adding all extension...")
    config.add_extension(extension_path=nopecha_path)
    config.add_extension(extension_path=tampermonkey_path)
    config.add_extension(extension_path=bpproxyswitcher_path)

    driver = await uc.Browser.create(config=config)
    print("[DEBUG] Driver created successfully")

    return driver


async def configure_proxy(tab, proxyList):
    try:
        extensions = await get_all_extension(tab)

        extension_id = get_extension_id_by_name(extensions, 'BP Proxy Switcher')
        
        extension_url = f'chrome-extension://{extension_id}/popup.html'
        await tab.get(extension_url)
        # await tab.get(vpn_url)
        delete_tab = await tab.select('#deleteOptions')
        # driver.evaluate("arguments[0].scrollIntoView();", delete_tab)
        await delete_tab.mouse_click()
        time.sleep(1)
        temp = await tab.select('#privacy > div:first-of-type > input')
        await temp.mouse_click()
        time.sleep(1)
        temp1 = await tab.select('#privacy > div:nth-of-type(2) > input')
        await temp1.mouse_click()
        time.sleep(1)
        temp2 = await tab.select('#privacy > div:nth-of-type(4) > input')
        await temp2.mouse_click()
        time.sleep(1)
        temp3 = await tab.select('#privacy > div:nth-of-type(7) > input')
        await temp3.mouse_click()


        optionsOK = await tab.select('#optionsOK')

        # driver.execute_script("arguments[0].scrollIntoView();", optionsOK)
        await optionsOK.mouse_click()
        time.sleep(1)
        edit = await tab.select('#editProxyList > small > b')
        # driver.execute_script("arguments[0].scrollIntoView();", edit)
        await edit.mouse_click()
        time.sleep(1)
        text_area = await tab.select('#proxiesTextArea')
        for proxy in proxyList:
            js_function = f"""
            (elem) => {{
                elem.value += "{proxy}\\n";
                return elem.value;
            }}
            """
            await text_area.apply(js_function)
        time.sleep(1)
        ok_button = await tab.select('#addProxyOK')
        await ok_button.mouse_click()
        time.sleep(2)
        proxy_auto_reload_checkbox = await check_for_element(tab,'#autoReload', click=True, debug=True)
        time.sleep(2)

        await change_proxy(tab)

        return True
    except Exception as e:
        print('configure_proxy function error:', e)
        return False
    
    
async def change_proxy(tab):
    try:
        extensions = await get_all_extension(tab)
        extension_id = get_extension_id_by_name(extensions, 'BP Proxy Switcher')
        
        extension_url = f'chrome-extension://{extension_id}/popup.html'
        await tab.get(extension_url)
        time.sleep(2)
        select_button = await tab.select('#proxySelectDiv > div > button')
        await select_button.mouse_click()
        time.sleep(2)
        proxy_switch_list = await tab.find_all('#proxySelectDiv > div > div > ul > li')
        if len(proxy_switch_list) == 3:
            await proxy_switch_list[2].scroll_into_view()
            await proxy_switch_list[2].mouse_click()
        else:
            certain_proxy = proxy_switch_list[random.randint(2, len(proxy_switch_list)-1)]
            await certain_proxy.scroll_into_view()
            await certain_proxy.mouse_click()
        time.sleep(5)

        return True
    except Exception as e:
        print('change_proxy function error:', e)
        return False


async def add_tampermonkey_scripts(tab, chrome_profile_name):
    folder_name = "tampermonkey_scripts"
    extensions = await get_all_extension(tab)
    extension_id = get_extension_id_by_name(extensions, "Tampermonkey")

    path_to_script = f'script_settings.js'
    script_settings = read_js_script(folder_name, path_to_script)
    path_to_main_script = f'main_script.js'
    script_main_raw = read_js_script(folder_name, path_to_main_script)


    path_to_main_script = os.path.join(os.getcwd(), folder_name, 'main_script.js')
    path_to_settings_script = os.path.join(os.getcwd(), folder_name, 'script_settings.js')
    save_js_script(path_to_main_script, script_main_raw)
    print(chrome_profile_name)

    # Use regex to replace the chromeProfile value in the JS string
    script_settings = re.sub(
        r'(\bchromeProfile\s*:\s*)(["\'])(.*?)\2',
        rf'\1"\g<3>"'.replace('\g<3>', chrome_profile_name),
        script_settings
    )

    # 2) Replace assignment value (works with " or ')
    script = re.sub(
        r'(\bsettings\.chromeProfile\s*=\s*)(["\'])(.*?)\2',
        rf'\1"\g<3>"'.replace('\g<3>', chrome_profile_name),
        script_settings
    )
    save_js_script(path_to_settings_script, script)
    time.sleep(2)
    await add_script_to_tampermonkey(tab, extension_id, 'main_script.js')
    await add_script_to_tampermonkey(tab, extension_id, 'script_settings.js')


async def add_script_to_tampermonkey(tab, tampermonkey_id, script):
    while True:
        try:
            await tab.get(f'chrome-extension://{tampermonkey_id}/options.html#nav=utils')
           
            current_dir = os.getcwd()
            necessary_path = current_dir + f'/tampermonkey_scripts/{script}'
            await wait_for_element(tab, '#input_ZmlsZV91dGlscw_file', timeout=5)
            input_field = await check_for_element(tab, '#input_ZmlsZV91dGlscw_file', debug=True)
            await input_field.send_file(necessary_path)

            time.sleep(1)
            
            return True
        except Exception as e:
            print(e)


async def get_all_extension(tab):
    while True:
        try:
            await tab.get('chrome://extensions/')
            script = """
                    (async () => {let data = await chrome.management.getAll(); return data;})();
            """

            extensions = await tab.evaluate(expression=script, await_promise=True)
            return extensions
        except Exception as e:
            print(e)
            time.sleep(5)


async def wait_for_element(page, selector, timeout=10):
    for _ in range(0, timeout):
        try:
            element = await page.query_selector(selector)
            if element: return element
            time.sleep(1)
        except Exception as e: 
            time.sleep(1)
            print(selector, e)
    return False


async def wait_for_elements(page, selector, timeout=10):
    for _ in range(0, timeout):
        try:
            element = await page.query_selector_all(selector)
            if element: return element
            time.sleep(1)
        except Exception as e: 
            time.sleep(1)
            print(selector, e)
    return False
    

async def check_for_element(page, selector, click=False, debug=False):
    try:
        element = await page.query_selector(selector)
        if click:
            await element.click()
        return element
    except Exception as e:
        if debug: print("selector", selector, '\n', e)
        return False
    

async def check_for_elements(page, selector, debug=False):
    try:
        element = await page.query_selector_all(selector)
        return element
    except Exception as e:
        if debug: print("selector", selector, '\n', e)
        return False
    

def get_extension_id_by_name(extensions, name):
    for ext in extensions:
        for key, value in ext["value"]:
            if key == "name" and value["value"].lower() == name.lower():
                # Now extract the ID
                for k, v in ext["value"]:
                    if k == "id":
                        return v["value"]
    return None
