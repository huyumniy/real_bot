import time
import asyncio
import logging
import sys, os, platform
import re
import requests
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
import eel
import socket
from datetime import datetime, timedelta
from utils.nodriverUtil import configure_proxy, browser_connect, change_proxy, \
    wait_for_element, check_for_element, check_for_elements, wait_for_elements, get_all_extension,\
    get_extension_id_by_name, add_tampermonkey_scripts, switch_frame, click_verify
from utils.helpers import read_js_script, save_js_script, log_line


async def cdp_health_check(tab, timeout=5):
    try:
        await asyncio.wait_for(
            tab.send(cdp.runtime.evaluate(expression="1")),
            timeout=timeout
        )
        return True
    except Exception:
        return False


async def dom_health_check(tab, timeout=5):
    try:
        await asyncio.wait_for(
            tab.send(cdp.runtime.evaluate(
                expression="document.readyState"
            )),
            timeout=timeout
        )
        return True
    except Exception:
        return False


async def worker(
    thread_num,
    initial_url,
    is_nopeCha,
    browsers_amount,
    proxy_list,
    is_madridista,
    numero,
    contrasena,
    is_vpn, 
    adspower_api=None, 
    adspower_id=None
):
    """
    Worker function to run the code in a separate thread.
    
    :param thread_num: Thread number for assigning unique browser profile and extensions.
    """
    if not adspower_api:
        log_line("info", f'Thread {thread_num} started.')
    else:
        log_line("info", f'Browser {adspower_id} started')
    
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

    start_time = time.time()
    last_health_check = time.time()
    last_activity = time.time()

    adspower_link = f"{adspower_api}/api/v1/browser/start?serial_number={adspower_id}" if adspower_api else adspower_api
    chrome_profile_name = f"{os.name}_{adspower_id}" if adspower_id and adspower_api else f"{os.name}_{thread_num}"
    # Initialize the browser
    driver = await browser_connect(adspower_link)

    tab = driver.main_tab
    await asyncio.sleep(10)
    await tab.activate()
    await asyncio.sleep(1)

    await close_extra_tabs(driver)
    await configure_proxy(tab, proxy_list)
    await asyncio.sleep(5)
    await add_tampermonkey_scripts(tab, chrome_profile_name)
    if is_nopeCha:
        await driver.get("https://nopecha.com/setup#sub_1SohHKCRwBwvt6pt8VQkMtCT|keys=|enabled=true|disabled_hosts=|base_api=https://api.nopecha.com|awscaptcha_auto_open=false|awscaptcha_auto_solve=false|awscaptcha_solve_delay_time=1000|awscaptcha_solve_delay=true|geetest_auto_open=false|geetest_auto_solve=false|geetest_solve_delay_time=1000|geetest_solve_delay=true|funcaptcha_auto_open=true|funcaptcha_auto_solve=true|funcaptcha_solve_delay_time=1000|funcaptcha_solve_delay=true|hcaptcha_auto_open=true|hcaptcha_auto_solve=true|hcaptcha_solve_delay_time=3000|hcaptcha_solve_delay=true|lemincaptcha_auto_open=false|lemincaptcha_auto_solve=false|lemincaptcha_solve_delay_time=1000|lemincaptcha_solve_delay=true|perimeterx_auto_solve=false|perimeterx_solve_delay_time=1000|perimeterx_solve_delay=true|recaptcha_auto_open=true|recaptcha_auto_solve=true|recaptcha_solve_delay_time=2000|recaptcha_solve_delay=true|textcaptcha_auto_solve=false|textcaptcha_image_selector=|textcaptcha_input_selector=|textcaptcha_solve_delay_time=100|textcaptcha_solve_delay=true|turnstile_auto_solve=true|turnstile_solve_delay_time=30000|turnstile_solve_delay=true")
    await driver.get(initial_url)
    tabs = list(driver.tabs)
    for driver_tab in tabs:
        install_button = await check_for_element(driver_tab, 'div[class="ask_action_buttons"] > input:nth-child(1)')
        if install_button:
            await install_button.click()
    await asyncio.sleep(5)

    
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
            tabs = list(driver.tabs)
            for driver_tab in tabs:
                if (
                    await check_for_element(driver_tab, "//*[contains(text(), 'Sorry, you have been blocked')]", xpath=True)
                    or await check_for_element(driver_tab, "//*[contains(text(), '404 Not Found')]", xpath=True)
                    or await check_for_element(
                        driver_tab,
                        'a[href="https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1015/"]'
                    )
                ):
                    await change_proxy(driver_tab)
                    await driver_tab.get(initial_url)
                if "realmadrid.com/" in driver_tab.url and "/select/" not in driver_tab.url:
                    await driver_tab.get(initial_url)
                if 'oneboxtm.queue-it.net/error' in driver_tab.url or 'oneboxtm.queue-it.net/error403' in driver_tab.url:
                    await change_proxy(driver_tab)
                    await driver_tab.get(initial_url)
                await check_for_element(driver_tab, '#buttonConfirmRedirect', click=True)
                    
                await click_verify(driver, driver_tab)

        except Exception as e: 
            log_line('error', e)
            await asyncio.sleep(5)
            continue
        await asyncio.sleep(1) 


async def close_extra_tabs(driver):
    for driver_tab in list(driver.tabs):
        if driver_tab.url not in ["chrome://newtab/", "about:blank"] : await driver_tab.close()


@eel.expose
def main(initialUrl, isNopeCha, browsersAmount, proxyList, isMadridista,
         numero, contrasena, isVpn, adspower_api=None, adspower_ids=[]):

    adspower_ids = _normalize_adspower_ids(adspower_ids)

    asyncio.run(
        async_main(
            initialUrl, isNopeCha, browsersAmount, proxyList,
            isMadridista, numero, contrasena, isVpn,
            adspower_api, adspower_ids
        )
    )


async def async_main(initialUrl, isNopeCha, browsersAmount, proxyList,
                     isMadridista, numero, contrasena, isVpn,
                     adspower_api, adspower_ids):

    tasks = []

    if not adspower_api and not adspower_ids:
        for i in range(1, int(browsersAmount) + 1):
            if i != 1:
                await asyncio.sleep(i * 15)

            tasks.append(
                asyncio.create_task(
                    worker(
                        i, initialUrl, isNopeCha, browsersAmount,
                        proxyList, isMadridista,
                        numero, contrasena, isVpn,
                        None, None
                    )
                )
            )
    else:
        for i, adspower_id in enumerate(adspower_ids, 1):
            if i != 1:
                await asyncio.sleep(i * 15)

            tasks.append(
                asyncio.create_task(
                    worker(
                        i, initialUrl, isNopeCha, browsersAmount,
                        proxyList, isMadridista,
                        numero, contrasena, isVpn,
                        adspower_api, adspower_id
                    )
                )
            )

    await asyncio.gather(*tasks)



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
