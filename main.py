import time
import logging
import sys, os, platform
import re
import requests
from colorama import init, Fore
from nodriver import Tab, cdp, Element, Browser, start
from nodriver.core import element
from nodriver.cdp.dom import Node
import threading
import random
import json
import base64
import pytesseract as pyt
import nodriver as uc
import cv2
import asyncio
import eel
import socket
from datetime import datetime, timedelta
from utils.nodriverUtil import configure_proxy, browser_connect, change_proxy, \
    wait_for_element, check_for_element, check_for_elements, wait_for_elements, get_all_extension,\
    get_extension_id_by_name, add_tampermonkey_scripts
from utils.helpers import read_js_script, save_js_script

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloudflare_bypass.log', mode='w')
    ]
)

init(autoreset=True)


async def worker(thread_num, initial_url, is_nopeCha, browsers_amount, proxy_list, is_madridista, numero, contrasena, is_vpn, adspower_api=None, adspower_id=None):
    print(thread_num, type(thread_num))
    """
    Worker function to run the code in a separate thread.
    
    :param thread_num: Thread number for assigning unique browser profile and extensions.
    """
    if not adspower_api:
        logging.info(f'Thread {thread_num} started.')
    else:
        logging.info(f'Browser {adspower_id} started')
    
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

    adspower_link = f"{adspower_api}/api/v1/browser/start?serial_number={adspower_id}" if adspower_api else adspower_api
    chrome_profile_name = f"{os.name}_{adspower_id}" if adspower_id and adspower_api else f"{os.name}_{thread_num}"
    # Initialize the browser
    driver = await browser_connect(adspower_link)

    tab = driver.main_tab
    time.sleep(10)
    await tab.activate()
    time.sleep(1)

    await close_extra_tabs(driver)
    await configure_proxy(tab, proxy_list)
    time.sleep(5)
    await add_tampermonkey_scripts(tab, chrome_profile_name)

   
    await driver.get(initial_url)
    for driver_tab in driver.tabs:
        install_button = await check_for_element(driver_tab, 'div[class="ask_action_buttons"] > input:nth-child(1)')
        if install_button:
            await install_button.click()
    time.sleep(5)

    

    await tab.send(cdp.page.add_script_to_evaluate_on_new_document(
        source="""
            Element.prototype._as = Element.prototype.attachShadow;
            Element.prototype.attachShadow = function (params) {
                return this._as({mode: "open"})
            };
        """
    ))
    
    while True:
        try:
            for driver_tab in driver.tabs:
                await click_verify(driver, driver_tab)
        except Exception as e: 
            print(e)
            time.sleep(5)
            continue

def switch_frame(browser, iframe) -> Tab:
    iframe: Tab = next(
        filter(
            lambda x: str(x.target.target_id) == str(iframe.frame_id), browser.targets
        )
    )
    iframe.websocket_url = iframe.websocket_url.replace("iframe", "page")
    return iframe

async def click_verify(browser: Browser, tab: Tab):
    try:

        div_host: Element = await check_for_element(tab, 'div[style="display: grid;"] > div > div')
        shadow_roots: Node = div_host.shadow_roots[0]
        iframe: Node = shadow_roots.children[0]
        iframe: Element = element.create(iframe, tab, iframe.content_document)
        await tab.sleep(1)

        iframe: Tab = switch_frame(browser, iframe)
        # await iframe_tab.get_content()
        await tab.sleep(1.3)
        div_host: Element = await iframe.select("body")
        shadow_roots: Node = div_host.shadow_roots[0]
        # div => main-wrapper
        div_: Node = shadow_roots.children[1]
        wrapper: Element = element.create(div_, iframe, div_.content_document)
        
        cf_input = await wrapper.query_selector("div label.cb-lb > input")
        cf_input = await wrapper.query_selector("div label.cb-lb > input")

        await cf_input.mouse_click()
        await tab.sleep(3)
        
    except Exception as e:
        # logging.error("couldn't click button: %s", e)
        time.sleep(5)
        pass


async def close_extra_tabs(driver):
    for driver_tab in driver.tabs:
        print(driver_tab)
        if driver_tab.url not in ["chrome://newtab/", "about:blank"] : await driver_tab.close()

@eel.expose
def main(initialUrl, isNopeCha, browsersAmount, proxyList, isMadridista,
         numero, contrasena, isVpn, adspower_api=None, adspower_ids=[]):

    print(initialUrl, isNopeCha, browsersAmount, isMadridista, numero, contrasena, isVpn)

    adspower_ids = _normalize_adspower_ids(adspower_ids)
    threads = []

    if not adspower_api and not adspower_ids:
        # No AdsPower: launch N workers
        for i in range(1, int(browsersAmount) + 1):
            if i != 1:
                time.sleep(i * 15)
            t = threading.Thread(
                target=_run_coro_in_thread,
                args=(worker(
                    i, initialUrl, isNopeCha, browsersAmount, proxyList,
                    isMadridista, numero, contrasena, isVpn,  # core args
                    None,  # adspower_api
                    None   # adspower_id
                ),),
                daemon=True
            )
            threads.append(t)
            t.start()
    else:
        # With AdsPower: one worker per id
        for i, adspower_id in enumerate(adspower_ids, 1):
            if i != 1:
                time.sleep(i * 15)
            t = threading.Thread(
                target=_run_coro_in_thread,
                args=(worker(
                    i, initialUrl, isNopeCha, browsersAmount, proxyList,
                    isMadridista, numero, contrasena, isVpn,
                    adspower_api, adspower_id
                ),),
                daemon=True
            )
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

def _run_coro_in_thread(coro):
    """Run an async coroutine in a fresh event loop inside a thread."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
    finally:
        loop.close()

def _normalize_adspower_ids(adspower_ids):
    """Accepts list or multiline string, returns list[str]."""
    if isinstance(adspower_ids, str):
        return [line.strip() for line in adspower_ids.splitlines() if line.strip()]
    elif isinstance(adspower_ids, (list, tuple)):
        return [str(x).strip() for x in adspower_ids if str(x).strip()]
    return []


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
