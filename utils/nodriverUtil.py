import re
import time
import random
import asyncio
import os, sys
from typing import List, Optional, Sequence

import nodriver as uc
import requests
from nodriver import Tab, Element, Browser
from nodriver.core import element
from nodriver.cdp.dom import Node
from utils.helpers import log_line
from .helpers import save_js_script, read_js_script

BLOCKED_TEXT_XPATH = "//*[contains(text(), 'Sorry, you have been blocked')]"
NOT_FOUND_TEXT_XPATH = "//*[contains(text(), '404 Not Found')]"
CF_1015_SELECTOR = (
    'a[href="https://developers.cloudflare.com/support/troubleshooting/'
    'http-status-codes/cloudflare-1xxx-errors/error-1015/"]'
)
REAL_MADRID_HOME = "https://www.realmadrid.com/es-ES"
NEW_TAB_URLS = {"chrome://newtab/", "about:blank"}


STARTUP_TAB_ACTIVATION_DELAY_SEC = 1.0
POST_CONNECT_PAUSE_SEC = 10.0
POST_PROXY_CONFIG_PAUSE_SEC = 5.0

class DriverController:
    """Wrapper around Nodriver Browser operations"""

    def __init__(self,
            initial_url: str,
            proxy_list: Sequence[str],
            profile_name: str,
            adspower_link: Optional[str] = None,
        ) -> None:
        self.driver = None
        self.initial_url = initial_url
        self.proxy_list = proxy_list
        self.profile_name = profile_name
        self.adspower_link = adspower_link
    
    async def navigate_initial(self) -> None:
        if not self.driver:
            raise RuntimeError("Driver not initialized; call setup() first.")
        await self.driver.get(self.initial_url)

    async def post_connect_setup(self) -> None:
        """Prepare driver & tab for automation."""
        await asyncio.sleep(POST_CONNECT_PAUSE_SEC)
        await self.main_tab.activate()
        await asyncio.sleep(STARTUP_TAB_ACTIVATION_DELAY_SEC)
        await self.configure_proxy(self.main_tab, self.proxy_list)
        await self.change_proxy(self.main_tab)
        await asyncio.sleep(POST_PROXY_CONFIG_PAUSE_SEC)
        await self.setup_tampermonkey_scripts(self.main_tab, self.profile_name)    
        await self._close_extra_tabs()

    async def setup_driver(self):
        """
        Create and return an undetected-chromedriver driver 
        (with extensions and optional remote Selenium host).
        """
        log_line("INFO", "Creating driver…")
        cwd = os.getcwd()

        nopecha_path = os.path.join(cwd, 'NopeCHA')
        tampermonkey_path = os.path.join(cwd, "tampermonkey")
        bpproxyswitcher_path = os.path.join(cwd, "BP-Proxy-Switcher-Chrome")
        host, port = None, None

        if self.adspower_link:
            log_line("INFO", f"Fetching remote Selenium info from {self.adspower_link}")
            resp = requests.get(self.adspower_link).json()
            if resp["code"] != 0:
                log_line("WARN", resp["msg"])
                log_line("WARN", "please check ads_id")
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
            log_line(f"[DEBUG] Using remote Selenium at {host}:{port}")
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
        log_line(f"[DEBUG] Adding all extension...")
        config.add_extension(extension_path=nopecha_path)
        config.add_extension(extension_path=tampermonkey_path)
        config.add_extension(extension_path=bpproxyswitcher_path)

        driver = await uc.Browser.create(config=config)
        log_line("[DEBUG] Driver created successfully")

        self.driver = driver
    

    async def configure_proxy(self, tab: Tab) -> bool:
        """
        Enter BP Proxy Switcher
        """
        try:
            extensions = await self._get_all_extensions(tab)
            extension_id = self._get_extension_id_by_name(extensions, 'BP Proxy Switcher')
            extension_url = f'chrome-extension://{extension_id}/popup.html'

            await tab.get(extension_url)
            delete_tab = await tab.select('#deleteOptions')
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
            await optionsOK.mouse_click()
            time.sleep(1)
            edit = await tab.select('#editProxyList > small > b')
            
            await edit.mouse_click()
            time.sleep(1)
            text_area = await tab.select('#proxiesTextArea')
            for proxy in self.proxy_list:
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
            await self.check_for_element(tab,'#autoReload', click=True, debug=True)
            time.sleep(2)

            return True
        except Exception as e:
            log_line('configure_proxy function error:', e)
            return False
        

    async def change_proxy(self, tab: Tab) -> bool:
        try:
            extensions = await self._get_all_extensions(tab)
            extension_id = self._get_extension_id_by_name(extensions, 'BP Proxy Switcher')
            
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
            log_line('change_proxy function error:', e)
            return False


    async def click_verify(self, browser: Browser, tab: Tab) -> None:
        """
        Locate and click the Cloudflare verification checkbox within a shadow DOM and iframe structure.

        This method is used to automatically bypass the Cloudflare "I'm not a robot" verification step by
        programmatically finding and clicking the verification checkbox. It works by traversing nested shadow
        roots and switching into the iframe that contains the Cloudflare challenge widget.

        This function assumes the Cloudflare challenge has been loaded and is visible.
        """
        try:

            div_host: Element = await self.check_for_element(tab, \
                'div[style="display: grid;"] > div > div')
            shadow_roots: Node = div_host.shadow_roots[0]
            iframe: Node = shadow_roots.children[0]
            iframe: Element = element.create(iframe, tab, iframe.content_document)
            await tab.sleep(1)

            iframe: Tab = self.switch_frame(browser, iframe)
            
            await tab.sleep(1.3)
            div_host: Element = await iframe.select("body")
            shadow_roots: Node = div_host.shadow_roots[0]
            
            div_: Node = shadow_roots.children[1]
            wrapper: Element = element.create(div_, iframe, div_.content_document)
            
            cf_input = await wrapper.query_selector("div label.cb-lb > input")
            cf_input = await wrapper.query_selector("div label.cb-lb > input")

            await cf_input.mouse_click()
            await tab.sleep(3)
            
        except Exception as e:
            time.sleep(5)
            pass
    

    def switch_frame(browser, iframe) -> Tab:
        """
        Shorthand for switching between tabs and their corresponding iframes.
        """
        iframe: Tab = next(
            filter(
                lambda x: str(x.target.target_id) == str(iframe.frame_id), browser.targets
            )
        )
        iframe.websocket_url = iframe.websocket_url.replace("iframe", "page")
        return iframe


    async def recover_if_blocked(self, tab: Tab) -> None:
        is_blocked = (
            await self.check_for_element(tab, BLOCKED_TEXT_XPATH, xpath=True)
            or await self.check_for_element(tab, NOT_FOUND_TEXT_XPATH, xpath=True)
            or await self.check_for_element(tab, CF_1015_SELECTOR)
        )
        if is_blocked:
            await self.change_proxy(tab)
            await tab.get(self.initial_url)
    

    async def reload_initial_if_home_redirect(self, tab: Tab) -> None:
        if tab.url == REAL_MADRID_HOME:
            await tab.get(self.initial_url)
    

    async def check_for_element(
        self,
        page,
        selector,
        xpath=False,
        click=False,
        debug=False
    ) -> Element | bool:
        try:
            if xpath:
                element = await page.xpath(selector)
            else:
                element = await page.query_selector(selector)
            if click:
                await element.click()
            return element
        except Exception as e:
            if debug: log_line("selector", selector, '\n', e)
            return False
        

    async def check_for_elements(
        self,
        page,
        selector,
        debug=False
    ) -> List[Element] | bool:
        try:
            element = await page.query_selector_all(selector)
            return element
        except Exception as e:
            if debug: log_line("selector", selector, '\n', e)
            return False


    async def wait_for_element(
        self,
        page,
        selector,
        timeout=10
    ) -> Element | bool:
        for _ in range(0, timeout):
            try:
                element = await page.query_selector(selector)
                if element: return element
                time.sleep(1)
            except Exception as e: 
                time.sleep(1)
                log_line(selector, e)
        return False
    

    async def wait_for_elements(
        self,
        page,
        selector,
        timeout=10
    ) -> List[Element] | bool:
        for _ in range(0, timeout):
            try:
                element = await page.query_selector_all(selector)
                if element: return element
                time.sleep(1)
            except Exception as e: 
                time.sleep(1)
                log_line(selector, e)
        return False


    async def setup_tampermonkey_scripts(self, tab: Tab, chrome_profile_name: str) -> None:
        folder_name = "tampermonkey_scripts"
        extensions = await self._get_all_extensions(tab)
        extension_id = self._get_extension_id_by_name(extensions, "Tampermonkey")

        path_to_script = f'script_settings.js'
        script_settings = read_js_script(folder_name, path_to_script)
        path_to_main_script = f'main_script.js'
        script_main_raw = read_js_script(folder_name, path_to_main_script)


        path_to_main_script = os.path.join(os.getcwd(), folder_name, 'main_script.js')
        path_to_settings_script = os.path.join(os.getcwd(), folder_name, 'script_settings.js')
        save_js_script(path_to_main_script, script_main_raw)
        log_line(chrome_profile_name)

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
        await self.add_script_to_tampermonkey(tab, extension_id, 'main_script.js')
        await self.add_script_to_tampermonkey(tab, extension_id, 'script_settings.js')


    async def _add_script_to_tampermonkey(self, tab: Tab, tampermonkey_id: str, script: str) -> bool:
        while True:
            try:
                await tab.get(f'chrome-extension://{tampermonkey_id}/options.html#nav=utils')
            
                current_dir = os.getcwd()
                necessary_path = current_dir + f'/tampermonkey_scripts/{script}'
                await self.wait_for_element(tab, '#input_ZmlsZV91dGlscw_file', timeout=5)
                input_field = await self.check_for_element(tab, '#input_ZmlsZV91dGlscw_file', debug=True)
                await input_field.send_file(necessary_path)

                time.sleep(1)
                
                return True
            except Exception as e:
                log_line(e)
                return False


    async def _get_all_extensions(tab: Tab) -> list:
        while True:
            try:
                await tab.get('chrome://extensions/')
                script = """
                        (async () => {let data = await chrome.management.getAll(); return data;})();
                """

                extensions = await tab.evaluate(expression=script, await_promise=True)
                return extensions
            except Exception as e:
                log_line(e)
                time.sleep(5)
    
    @property
    def main_tab(self) -> Tab:
        if not self.driver:
            raise RuntimeError("Driver not initialized; call setup() first.")
        return self.driver.main_tab
    
    
    @staticmethod
    def _get_extension_id_by_name(extensions, name):
        for ext in extensions:
            for key, value in ext["value"]:
                if key == "name" and value["value"].lower() == name.lower():
                    for k, v in ext["value"]:
                        if k == "id":
                            return v["value"]
        return None

    async def _close_extra_tabs(self) -> None:
        for t in list(self.driver.tabs):
            try:
                if t.url not in NEW_TAB_URLS:
                    await t.close()
            except Exception as exc: 
                log_line("ERROR", f"Ignoring tab close error: {exc}")
