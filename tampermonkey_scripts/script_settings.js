// ==UserScript==
// @name         Proticketing Real Madrid Catcher - Settings v3
// @namespace    https://www.realmadrid.com
// @version      3.0
// @run-at       document-idle
// @description  Settings configuration
// @author       Megazoid
// @match        *://*.realmadrid.com/*
// @match        *://*.tickets.realmadrid.com/*
// @grant        unsafeWindow
// ==/UserScript==

const storedSettings = JSON.parse(localStorage.getItem('ticketBotSettings'));


let settings = storedSettings || {
  chromeProfile: 'S3U1_1',
  indexUrl: 'https://www.realmadrid.com/en/tickets',
  url: getSessionUrl(),
  allowSeparateTickets: false,
  telegramBotId: '5712671465:AAFqebxudxqEcGp2SZm814vR8RtTKLgEjGs',
  telegramBotChatId: -1001961554005,
  telegramBotChatErrorsId: -4572872479,
  production: true,
  debug: false,
  reload: true,
  secondsToRestartIfNoTicketsFound: 10,
  timesToBrowserTabReload: 200,
  minPrice: null,
  maxPrice: null,
  ticketsToBuy: null,
  madridista: { login: '222222', password: '2222222' } && null, // To disable this parameter uncomment && null
};


// Пізніше, коли ви отримаєте eventType і eventNumber, ви можете встановити url:

function createForm() {
  const body = document.body;

  const settingsFormContainer = document.createElement('div');
  settingsFormContainer.id = 'settingsFormContainer';
  body.appendChild(settingsFormContainer);

  const form = document.createElement('form');
  form.id = 'settingsForm';

  const labels = ['minPrice', 'maxPrice', 'ticketsToBuy'];
  labels.forEach((label, index) => {
    const labelElement = document.createElement('label');
    labelElement.for = label;
    labelElement.textContent = `${label}:`;

    if (index === 0) {
      labelElement.style.marginRight = '27px';
    } else if (index === 1) {
      labelElement.style.marginRight = '24px';
    }

    form.appendChild(labelElement);

    const inputElement = document.createElement('input');
    inputElement.type = 'text';
    inputElement.id = label;
    inputElement.name = label;
    const storedValue = localStorage.getItem(label);
    inputElement.value = storedValue !== null ? storedValue : '';

    form.appendChild(inputElement);
    form.appendChild(document.createElement('br'));
  });

  const updateButton = document.createElement('button');
  updateButton.type = 'button';
  updateButton.textContent = 'Update Settings and Reload';
  updateButton.addEventListener('click', updateSettings);
  updateButton.style.width = '100%';
  form.appendChild(updateButton);
  settingsFormContainer.appendChild(form);

  settingsFormContainer.style.position = 'fixed';
  settingsFormContainer.style.bottom = '10px';
  settingsFormContainer.style.right = '10px';
  settingsFormContainer.style.padding = '10px';
  settingsFormContainer.style.backgroundColor = '#f0f0f0';
  settingsFormContainer.style.border = '1px solid #ccc';
}
function updateSettings() {
  const minPrice = document.getElementById('minPrice').value;
  const maxPrice = document.getElementById('maxPrice').value;
  const ticketsToBuy = parseInt(document.getElementById('ticketsToBuy').value);

  settings.minPrice = minPrice !== '' ? minPrice : null;
  settings.maxPrice = maxPrice !== '' ? maxPrice : null;
  settings.ticketsToBuy = ticketsToBuy !== '' ? ticketsToBuy : null;
  settings.chromeProfile = 'S3U1_1';
  settings.indexUrl = 'https://www.realmadrid.com/en/tickets';

  // Dynamically get the session URL when the button is clicked
  settings.url = getSessionUrl();

  settings.allowSeparateTickets = false;
  settings.telegramBotId = '5712671465:AAFqebxudxqEcGp2SZm814vR8RtTKLgEjGs';
  settings.telegramBotChatId = -1001961554005;
  settings.telegramBotChatErrorsId = -4572872479;
  settings.production = true;
  settings.debug = false;
  settings.reload = true;
  settings.secondsToRestartIfNoTicketsFound = 10;
  settings.timesToBrowserTabReload = 200;
  settings.madridista = { login: '222222', password: '2222222' } && null; // To disable this parameter uncomment && null
  console.log('Updated settings:', settings);
  localStorage.setItem('ticketBotSettings', JSON.stringify(settings));

  setTimeout(() => {
    window.location.reload();
  }, 1000);
}

function getSessionUrl() {
  const currentUrl = window.location.href;
  const sessionNumber = getSessionNumberFromUrl(currentUrl);


  // Check if the URL contains /es_ES/ or /en_US/ and set the language code accordingly
  const languageCode = currentUrl.includes('/es_ES/') ? 'es_ES' : 'en_US';

  // Determine the event type based on the URL pattern
  let eventType = '';
  if (currentUrl.includes('realmadrid_futbol')) {
    eventType = 'realmadrid_futbol';
  } else if (currentUrl.includes('realmadrid_champions')) {
    eventType = 'realmadrid_champions';
  } else if (currentUrl.includes('realmadrid_ligavipsilver')) {
    eventType = 'realmadrid_ligavipsilver'
  } else if (currentUrl.includes('realmadrid_ligavipgold')) {
    eventType = 'realmadrid_ligavipgold'
  }

  // Build the URL based on the event type
  if (eventType === 'realmadrid_futbol') {
    const eventNumber = extractEventNumber(currentUrl, `https://tickets.realmadrid.com/realmadrid_futbol/${languageCode}/entradas/evento/`)
    return `https://tickets.realmadrid.com/realmadrid_futbol/${languageCode}/entradas/evento/${eventNumber}/session/${sessionNumber}/select?viewCode=V_blockmap_view`;
  } else if (eventType === 'realmadrid_champions') {
    const eventNumber = extractEventNumber(currentUrl, `https://tickets.realmadrid.com/realmadrid_champions/${languageCode}/entradas/evento/`)
    return `https://tickets.realmadrid.com/realmadrid_champions/${languageCode}/entradas/evento/${eventNumber}/session/${sessionNumber}/select?viewCode=V_blockmap_view`;
  } else if (eventType === 'realmadrid_ligavipsilver') {
    const eventNumber = extractEventNumber(currentUrl, `https://tickets.realmadrid.com/realmadrid_ligavipsilver/${languageCode}/entradas/evento/`)
    return `https://tickets.realmadrid.com/realmadrid_ligavipsilver/${languageCode}/entradas/evento/${eventNumber}/session/${sessionNumber}/select?viewCode=V_blockmap_view`;
  } else if (eventType === 'realmadrid_ligavipgold') {
    const eventNumber = extractEventNumber(currentUrl, `https://tickets.realmadrid.com/realmadrid_ligavipgold/${languageCode}/entradas/evento/`)
    return `https://tickets.realmadrid.com/realmadrid_ligavipgold/${languageCode}/entradas/evento/${eventNumber}/session/${sessionNumber}/select?viewCode=V_blockmap_view`;
  }
  return null;
}

function getSessionNumberFromUrl(url) {
  if (url.includes('session')) return url.split('/session/')[1].split('/')[0]

  return null;
}

function extractSessionNumber(url, urlPattern) {
  const sessionNumber = url.substring(urlPattern.length).split('/')[0];
  return sessionNumber;
}

function extractEventNumber(url, urlPattern) {
  return url.substring(urlPattern.length).split('/')[0];
}

window.onload = () => {
  createForm();

  const labels = ['minPrice', 'maxPrice', 'ticketsToBuy'];
  labels.forEach((label) => {
    const inputElement = document.getElementById(label);
    if (inputElement && storedSettings && storedSettings[label] !== undefined) {
      inputElement.value = storedSettings[label];
    }
  });
};

(function () {
  'use strict';
  unsafeWindow.ticketBotSettings = settings;
})();
