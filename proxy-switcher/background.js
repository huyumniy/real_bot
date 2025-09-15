var proxy_auth = {
    host: "gw.dataimpulse.com",
    port: 10009,
    username: "4a8f6e7f6e04ff3d33aa__cr.es",
    password: "712de883887d9108"
}

var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "http",
            host: proxy_auth.host,
            port: proxy_auth.port
            
        },
        bypassList: ["localhost"]
    }
};

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            "username": proxy_auth.username,
            "password": proxy_auth.password
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    { urls: ["<all_urls>"] },
    ['blocking']
);