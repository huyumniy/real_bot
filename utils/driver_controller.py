import os
import re
import random
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional, Sequence
import nodriver as uc
import requests
from nodriver import Tab, Element, Browser
from nodriver.core import element
from nodriver.cdp.dom import Node
from .helpers import log_line, save_js_script, read_js_script

BLOCKED_TEXT_XPATH = "//*[contains(text(), 'Sorry, you have been blocked')]"
NOT_FOUND_TEXT_XPATH = "//*[contains(text(), '404 Not Found')]"
CF_1015_SELECTOR = (
    'a[href="https://developers.cloudflare.com/support/troubleshooting/'
    'http-status-codes/cloudflare-1xxx-errors/error-1015/"]'
)
REAL_MADRID_HOME = "https://www.realmadrid.com/es-ES"
NEW_TAB_URLS = ["chrome://newtab/", "about:blank"]


STARTUP_TAB_ACTIVATION_DELAY_SEC = 5.0
POST_CONNECT_PAUSE_SEC = 10.0
POST_PROXY_CONFIG_PAUSE_SEC = 5.0

CWD = Path.cwd()

class DriverController:
    """
    High-level browser and tabs controller built on top of `nodriver`.

    Responsibilities:
    - Create and configure a Chromium session (optionally via AdsPower remote endpoint).
    - Load required extensions (NopeCHA, Tampermonkey etc.).
    - Perform one-time post-connect setup (proxy configuration, userscript install).
    - Provide convenience operations used by higher-level loops (recover, reload, click verify).
    
    note:
    - This controller assumes a Chromium-based browser with specific extensions installed.
    - If you run in Adspower mode, ensure the AdsPower profile has the required extensions pre-installed.
    """
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


    async def navigate_to_initial_url(self) -> None:
        if not self.main_tab:
            raise RuntimeError("Driver not initialized; call setup() first.")
        await self.main_tab.get(self.initial_url)


    async def post_connect_setup(self) -> None:
        """
        Prepare driver & tab for automation.
        
        steps:
        1) Brief stabilization and tab activation.
        2) Proxy configuration
        3) Install/refresh Tampermonkey scripts (main + settings) for this profile.
        4) Close extra tabs created during setup.

        note:
        - This setup assumes a stable network connection.
        - You do not have to make any actions in the browser during this setup.
        """
        await self.driver.sleep(POST_CONNECT_PAUSE_SEC)
        await self.main_tab.activate()
        await self.driver.sleep(STARTUP_TAB_ACTIVATION_DELAY_SEC)
        if self.proxy_list:
            await self.configure_proxy(self.main_tab)
            await self.change_proxy(self.main_tab)
            await self.driver.sleep(POST_PROXY_CONFIG_PAUSE_SEC)
        await self.setup_tampermonkey_scripts(self.main_tab, self.profile_name)    
        await self.main_tab.activate()
        await self.driver.sleep(STARTUP_TAB_ACTIVATION_DELAY_SEC)
        await self._click_install_tampermonkey_script_button()
        await self.driver.sleep(STARTUP_TAB_ACTIVATION_DELAY_SEC)
        await self._close_extra_tabs()


    async def setup_driver(self):
        """
        Create a `nodriver` Browser with required extensions and optional AdsPower connection.

        - If `adspower_link` is provided, fetch the Selenium WebSocket endpoint from 
        AdsPower API and connect to it.
        - Otherwise, create a local browser instance.
        - Always loads NopeCHA, Tampermonkey and BP Proxy Switcher extensions.
        """
        log_line("INFO", "Creating driver…")
        global CWD

        nopecha_path = CWD / 'NopeCHA'
        tampermonkey_path = CWD / 'tampermonkey'
        bpproxyswitcher_path = CWD / "BP-Proxy-Switcher-Chrome"
        host, port = None, None

        if self.adspower_link:
            log_line("INFO", f"Fetching remote Selenium info from {self.adspower_link}")
            resp = requests.get(self.adspower_link).json()
            if resp["code"] != 0:
                log_line("ERROR", f"AdsPower error: {resp['msg']}. Check ads_id.")
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
        config.add_extension(extension_path=nopecha_path)
        config.add_extension(extension_path=tampermonkey_path)
        config.add_extension(extension_path=bpproxyswitcher_path)

        driver = await uc.Browser.create(config=config)
        log_line("INFO", "Driver created successfully")

        self.driver = driver
    

    async def configure_proxy(self, tab: Tab) -> bool:
        """
        Configure BP Proxy Switcher with `self.proxy_list` on the given tab.

        Opens the extension UI, unselect default privacy options e.g.
        Delete cache, cookies, localstorage etc. on proxy change, then
        populates the proxy list from `self.proxy_list`.

        Returns True if successful, False otherwise.
        """
        try:
            extensions = await self._get_all_extensions(tab)
            extension_id = self._get_extension_id_by_name(extensions, 'BP Proxy Switcher')
            extension_url = f'chrome-extension://{extension_id}/popup.html'

            await tab.get(extension_url)
            delete_tab = await tab.select('#deleteOptions')
            await delete_tab.mouse_click()
            await self.driver.sleep(1)
            temp = await tab.select('#privacy > div:first-of-type > input')
            await temp.mouse_click()
            await self.driver.sleep(1)
            temp1 = await tab.select('#privacy > div:nth-of-type(2) > input')
            await temp1.mouse_click()
            await self.driver.sleep(1)
            temp2 = await tab.select('#privacy > div:nth-of-type(4) > input')
            await temp2.mouse_click()
            await self.driver.sleep(1)
            temp3 = await tab.select('#privacy > div:nth-of-type(7) > input')
            await temp3.mouse_click()

            optionsOK = await tab.select('#optionsOK')
            await optionsOK.mouse_click()
            await self.driver.sleep(1)
            edit = await tab.select('#editProxyList > small > b')
            
            await edit.mouse_click()
            await self.driver.sleep(1)
            text_area = await tab.select('#proxiesTextArea')
            for proxy in self.proxy_list:
                js_function = f"""
                (elem) => {{
                    elem.value += "{proxy}\\n";
                    return elem.value;
                }}
                """
                await text_area.apply(js_function)
            await self.driver.sleep(1)
            ok_button = await tab.select('#addProxyOK')
            await ok_button.mouse_click()
            await self.driver.sleep(2)
            await self.check_for_element(tab,'#autoReload', click=True)
            await self.driver.sleep(2)

            return True
        except Exception as e:
            log_line("ERROR", f'configure_proxy function error: {e}')
            return False
        

    async def change_proxy(self, tab: Tab) -> bool:
        """
        Select a random proxy in BP Proxy Switcher.

        Returns True if successful, False otherwise.
        """
        try:
            extensions = await self._get_all_extensions(tab)
            extension_id = self._get_extension_id_by_name(extensions, 'BP Proxy Switcher')
            
            extension_url = f'chrome-extension://{extension_id}/popup.html'
            await tab.get(extension_url)
            await self.driver.sleep(2)
            select_button = await tab.select('#proxySelectDiv > div > button')
            await select_button.mouse_click()
            await self.driver.sleep(2)
            proxy_switch_list = await tab.find_all('#proxySelectDiv > div > div > ul > li')
            if len(proxy_switch_list) == 3:
                await proxy_switch_list[2].scroll_into_view()
                await proxy_switch_list[2].mouse_click()
            else:
                choices = proxy_switch_list[2:] or proxy_switch_list
                choice = random.choice(choices)
                await choice.scroll_into_view()
                await choice.mouse_click()
            await self.driver.sleep(5)

            return True
        except Exception as e:
            log_line("ERROR", f'change_proxy function error: {e}')
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
            iframe_node: Node = shadow_roots.children[0]
            iframe_el: Element = element.create(iframe_node, tab, iframe_node.content_document)
            
            await browser.sleep(1)

            async with self._use_iframe_tab(browser, tab, iframe_el) as iframe:
                
                body: Element = await iframe.select("body")
                if not body or not getattr(body, "shadow_roots", None):
                    return
                
                await self.driver.sleep(1.3)
                inner_shadow: Node = body.shadow_roots[0]
                host_node: Node = inner_shadow.children[1]
                wrapper: Element = element.create(host_node, iframe, host_node.content_document)

                # Query once (the second line was duplicate in your code)
                cf_input = await wrapper.query_selector("div label.cb-lb > input")
                if cf_input:
                    await cf_input.mouse_click()
                    await self.driver.sleep(3)
            
        except Exception as e:
            await self.driver.sleep(5)
            pass
    

    @asynccontextmanager
    async def _use_iframe_tab(self, browser: Browser, page_tab: Tab, iframe_el: Element):
        """Context manager to switch to an iframe's tab, then restore the original tab."""
        iframe_tab: Tab = self._switch_frame(browser, iframe_el)
        try:
            yield iframe_tab
        finally:
            # Best-effort: ensure the original page tab is the active target again
            try:
                await page_tab.activate()
            except Exception:
                pass


    def _switch_frame(self, browser: Browser, iframe: Element) -> Tab:
        """Shorthand for switching between tabs and their corresponding iframes."""
        iframe_tab: Tab = next(
            filter(
                lambda x: str(x.target.target_id) == str(iframe.frame_id), browser.targets
            )
        )
        iframe_tab.websocket_url = iframe_tab.websocket_url.replace("iframe", "page")
        return iframe_tab


    async def recover_if_blocked(self, tab: Tab) -> None:
        """
        Check if the current tab is blocked (Cloudflare block or 404) and recover by changing proxy."""
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


    async def setup_tampermonkey_scripts(self, tab: Tab, chrome_profile_name: str) -> None:
        """
        Install/refresh Tampermonkey scripts and inject the current profile name into settings.
        
        Side effects:
        - Saves modified settings script to disk before uploading to Tampermonkey.
        - Opens new Tampermonkey tab for each script added. 
        """
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
        await self.driver.sleep(2)
        await self._add_script_to_tampermonkey(tab, extension_id, 'main_script.js')
        await self._add_script_to_tampermonkey(tab, extension_id, 'script_settings.js')


    async def _add_script_to_tampermonkey(self, tab: Tab, tampermonkey_id: str, script: str) -> bool:
        """Upload a local script file to Tampermonkey 'Utilities' page."""
        try:
            await tab.get(f'chrome-extension://{tampermonkey_id}/options.html#nav=utils')
        
            current_dir = os.getcwd()
            necessary_path = current_dir + f'/tampermonkey_scripts/{script}'
            await self.wait_for_element(tab, '#input_ZmlsZV91dGlscw_file', timeout=5)
            input_field = await self.check_for_element(tab, '#input_ZmlsZV91dGlscw_file')
            await input_field.send_file(necessary_path)

            await self.driver.sleep(1)
            
            return True
        except Exception as e:
            log_line("ERROR", f"_add_script_to_tampermonkey function:\n{e}")
            return False
    

    async def _click_install_tampermonkey_script_button(self):
        """Click the 'Install' button on every Tampermonkey confirmation tab."""
        for t in list(self.driver.tabs):
            await self.check_for_element(t,\
                'div[class="ask_action_buttons"] > input:nth-child(1)',
                click=True
            )
            await self.driver.sleep(2)
    

    async def _get_all_extensions(self, tab: Tab) -> list:
        """Return the `chrome.management.getAll()` extension list via an extensions page."""
        while True:
            try:
                await tab.get('chrome://extensions/')
                script = """
                        (async () => {let data = await chrome.management.getAll(); return data;})();
                """

                extensions = await tab.evaluate(expression=script, await_promise=True)
                return extensions
            except Exception as e:
                log_line("ERROR", f"_get_all_extension function:\n{e}")
                await self.driver.sleep(5)


    async def check_for_element(
        self,
        page,
        selector,
        xpath=False,
        click=False,
        debug=False
    ) -> Element | bool:
        """
        Query a single element by CSS Selector (default) or XPath.

        side effects:
        - If `xpath` is True result could be a List[nodriver.Element] or [] type.
        """
        try:
            if xpath:
                element = await page.xpath(selector)
            else:
                element = await page.query_selector(selector)
            if click:
                await element.click()
            return element
        except Exception as e:
            if debug: log_line("ERROR", f"selector {selector}\n{e}")
            return False
        

    async def check_for_elements(
        self,
        page,
        selector,
        debug=False
    ) -> List[Element] | bool:
        """Query multiple elements by CSS selector. Returns list or False."""
        try:
            element = await page.query_selector_all(selector)
            return element
        except Exception as e:
            if debug: log_line("ERROR", f"selector {selector}\n{e}")
            return False


    async def wait_for_element(
        self,
        page,
        selector,
        timeout=10,
        debug=False
    ) -> Element | bool:
        """Poll for a single element by CSS selector until found or `timeout` expires (seconds)."""
        for _ in range(0, timeout):
            try:
                element = await page.query_selector(selector)
                if element: return element
                await self.driver.sleep(1)
            except Exception as e: 
                await self.driver.sleep(1)
                if debug: log_line("ERROR", f"selector {selector}\n{e}")
        return False
    

    async def wait_for_elements(
        self,
        page,
        selector,
        timeout=10,
        debug=False
    ) -> List[Element] | bool:
        """Poll for multiple elements by CSS selector until found or `timeout` expires (seconds)."""
        for _ in range(0, timeout):
            try:
                element = await page.query_selector_all(selector)
                if element: return element
                await self.driver.sleep(1)
            except Exception as e: 
                await self.driver.sleep(1)
                if debug: log_line("ERROR", f"selector {selector}\n{e}")
        return False

    
    @property
    def main_tab(self) -> Tab:
        if not self.driver:
            raise RuntimeError("Driver not initialized; call setup() first.")
        return self.driver.main_tab


    @staticmethod
    def _get_extension_id_by_name(extensions, name):
        """Return the extension ID for the given extension name from the extensions list."""
        for ext in extensions:
            for key, value in ext["value"]:
                if key == "name" and value["value"].lower() == name.lower():
                    for k, v in ext["value"]:
                        if k == "id":
                            return v["value"]
        return None


    async def _close_extra_tabs(self) -> None:
        """Close all tabs except the main tab and known new tab URLs."""
        keep = self.main_tab
        for t in list(self.driver.tabs):
            if t is keep: continue
            try:
                if t.url not in NEW_TAB_URLS: await t.close()
            except Exception as exc: 
                log_line("ERROR", f"Ignoring tab close error: {exc}")
