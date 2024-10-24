from fastapi.middleware.cors import CORSMiddleware
import json
import re
import os
from urllib.parse import urlparse
import time

from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import shutil, tempfile
from typing import List
import argparse

# Check if running in Docker mode
DOCKER_MODE = os.getenv("DOCKERMODE", "false").lower() == "true"


class ProxyExtension:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %d
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        self._dir = os.path.normpath(tempfile.mkdtemp())

        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    def __del__(self):
        shutil.rmtree(self._dir)


# Chromium options arguments
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

browser_path = "/usr/bin/google-chrome"
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Cookie(BaseModel):
    name: str
    value: str
    domain: str


class CookieResponse(BaseModel):
    cookies: List[Cookie]
    user_agent: str
    proxy: str
    url: str


# Function to check if the URL is safe
def is_safe_url(url: str) -> bool:
    parsed_url = urlparse(url)
    ip_pattern = re.compile(
        r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|::1|10\.\d+\.\d+\.\d+|172\.1[6-9]\.\d+\.\d+|172\.2[0-9]\.\d+\.\d+|172\.3[0-1]\.\d+\.\d+|192\.168\.\d+\.\d+)$"
    )
    hostname = parsed_url.hostname
    if (hostname and ip_pattern.match(hostname)) or parsed_url.scheme == "file":
        return False
    return True


# Function to bypass Cloudflare protection
def bypass_cloudflare(url: str, proxy: str, user_agent: str, retries: int, log: bool) -> ChromiumPage:
    from pyvirtualdisplay import Display

    if DOCKER_MODE:
        # Start Xvfb for Docker
        display = Display(visible=0, size=(1920, 1080))
        display.start()

        options = ChromiumOptions()
        options.set_argument("--auto-open-devtools-for-tabs", "true")
        options.set_argument("--remote-debugging-port=9222")
        options.set_argument("--no-sandbox")  # Necessary for Docker
        options.set_argument("--disable-gpu")  # Optional, helps in some cases
        options.set_paths(browser_path=browser_path).headless(False)
        if proxy and proxy != 'vpn':
            proxy = proxy.split(":", 3)
            proxy[1] = int(proxy[1])
            proxy_extension = ProxyExtension(*proxy)
            options.add_extension(proxy_extension.directory)
        if user_agent:
            options.set_argument(f'--user-agent={user_agent}')
    else:
        options = ChromiumOptions()
        options.set_argument("--auto-open-devtools-for-tabs", "true")
        options.set_paths(browser_path=browser_path).headless(False)
        if proxy and proxy != 'vpn':
            proxy = proxy.split(":", 3)
            proxy[1] = int(proxy[1])
            proxy_extension = ProxyExtension(*proxy)
            options.add_extension(proxy_extension.directory)
        if user_agent:
            options.set_argument(f'--user-agent={user_agent}')
    driver = ChromiumPage(addr_or_opts=options)
    try:
        driver.get(url)
        cf_bypasser = CloudflareBypasser(driver, retries, log)
        cf_bypasser.bypass()
        return driver
    except Exception as e:
        driver.quit()
        if DOCKER_MODE:
            display.stop()  # Stop Xvfb
        raise e


# Endpoint to get cookies
@app.get("/cookies", response_model=CookieResponse)
async def get_cookies(url: str, proxy: str, user_agent: str, retries: int = 5):
    print(url, proxy, user_agent, retries)
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        driver = bypass_cloudflare(url, proxy, user_agent, retries, log)
        print(driver.cookies(as_dict=False))
        cookies_list = [
            Cookie(name=cookie["name"], value=cookie["value"], domain=cookie["domain"])
            for cookie in driver.cookies(as_dict=False)
        ]
        user_agent = driver.user_agent
        driver_url = driver.url
        driver.quit()
        return CookieResponse(cookies=cookies_list, user_agent=user_agent, proxy=proxy, url=driver_url)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get HTML content and cookies
@app.get("/html")
async def get_html(url: str, proxy: str, user_agent: str, retries: int = 5):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        driver = bypass_cloudflare(url, proxy, user_agent, retries, log)
        html = driver.html
        cookies_json = json.dumps(driver.cookies(as_dict=False))

        response = Response(content=html, media_type="text/html")
        response.headers["cookies"] = cookies_json
        response.headers["user_agent"] = driver.user_agent
        driver.quit()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cloudflare bypass api")

    parser.add_argument("--nolog", action="store_true", help="Disable logging")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()
    if args.headless and not DOCKER_MODE:
        from pyvirtualdisplay import Display

        display = Display(visible=0, size=(1920, 1080))
        display.start()
    if args.nolog:
        log = False
    else:
        log = True
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
