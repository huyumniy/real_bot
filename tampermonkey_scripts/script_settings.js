// ==UserScript==
// @name         Proticketing Real Madrid Catcher - Settings v3
// @namespace    https://www.realmadrid.com
// @version      3.0
// @description  Settings configuration
// @author       Megazoid
// @match        *://*.realmadrid.com/*
// @match        *://*.tickets.realmadrid.com/*
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==

const storedSettings = JSON.parse(localStorage.getItem('ticketBotSettings'));

let settings = storedSettings || {
  chromeProfile: "nt_2",
  indexUrl: 'https://www.realmadrid.com/en/tickets',
  url: getSessionUrl(),
  allowSeparateTickets: false,
  telegramBotId: '5712671465:AAFqebxudxqEcGp2SZm814vR8RtTKLgEjGs',
  telegramBotChatId: -1001961554005,
  telegramBotChatErrorsId: -4572872479,
  production: true,
  debug: false,
  reload: true,
  secondsToRestartIfNoTicketsFound: 5,
  timesToBrowserTabReload: 200,
  minPrice: null,
  maxPrice: null,
  ticketsToBuy: null,
  selectedViews: [],
  madridista: { login: '222222', password: '2222222' } && null, // To disable this parameter uncomment && null
};

// Пізніше, коли ви отримаєте eventType і eventNumber, ви можете встановити url:

console.log(settings);

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

    form.appendChild(inputElement);
    form.appendChild(document.createElement('br'));
  });

  const selectViewContainer = document.createElement("div");
  selectViewContainer.id = "selectViewContainer";
  selectViewContainer.style.display = "grid";
  selectViewContainer.style.gridTemplateColumns = "1fr 1fr";
  
  const viewLabels = ["Fondo Sur", "Fondo Norte", "Lateral Oeste", "Lateral Este"];

  viewLabels.forEach((viewLabel) => {
    const viewContainer = document.createElement("div");
    viewContainer.style.maxWidth = "120px";
    viewContainer.style.display = "flex";
    viewContainer.style.justifyContent = "space-between";

    const viewCheckbox = document.createElement("input");
    const viewCheckboxLabel = document.createElement("label");
    viewCheckboxLabel.innerHTML = viewLabel;
    viewCheckboxLabel.textContent = viewLabel;
    viewCheckbox.type = "checkbox";
    viewCheckbox.id = viewLabel;
    viewCheckbox.name = viewLabel;
    viewCheckbox.value = viewLabel;
    
    
    viewContainer.appendChild(viewCheckboxLabel);
    viewContainer.appendChild(viewCheckbox);
    selectViewContainer.append(viewContainer);
  });
  
  form.appendChild(selectViewContainer);

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
  const selectedViewsElements = document.querySelectorAll("#selectViewContainer > div > input:checked")
  
  const selectedViews = Array.from(selectedViewsElements).map(selectedView => selectedView.value)
  
  settings.minPrice = minPrice !== '' ? minPrice : null;
  settings.maxPrice = maxPrice !== '' ? maxPrice : null;
  settings.ticketsToBuy = ticketsToBuy !== '' ? ticketsToBuy : null;
  settings.selectedViews = !!selectedViews.length ? selectedViews : [];
  settings.chromeProfile = "nt_2";
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
  settings.secondsToRestartIfNoTicketsFound = 5;
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

  if (sessionNumber) {
    // Determine the event type based on the URL pattern
    let eventType = '';
    if (currentUrl.includes('realmadrid_futbol')) {
      eventType = 'realmadrid_futbol';
    } else if (currentUrl.includes('realmadrid_champions')) {
      eventType = 'realmadrid_champions';
    }

    // Build the URL based on the event type
    if (eventType === 'realmadrid_futbol') {
      return `https://tickets.realmadrid.com/realmadrid_futbol/select/${sessionNumber}?viewCode=V_principal`;
    } else if (eventType === 'realmadrid_champions') {
      return `https://tickets.realmadrid.com/realmadrid_champions/select/${sessionNumber}?viewCode=V_principal`;
    }
  }

  return null;
}

function getSessionNumberFromUrl(url) {
  const futbolPattern =
    'https://tickets.realmadrid.com/realmadrid_futbol/select/';
  const championsPattern =
    'https://tickets.realmadrid.com/realmadrid_champions/select/';

  if (url.startsWith(futbolPattern)) {
    return extractSessionNumber(url, futbolPattern);
  } else if (url.startsWith(championsPattern)) {
    return extractSessionNumber(url, championsPattern);
  }

  return null;
}

function extractSessionNumber(url, urlPattern) {
  const sessionNumber = url.substring(urlPattern.length).split('/')[0];
  return sessionNumber;
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

  const storedViews = storedSettings['selectedViews']
  const viewCheckboxes = document.querySelectorAll("#selectViewContainer > div > input")
  
  viewCheckboxes.forEach((viewCheckbox) => {
    if (storedViews !== null && storedViews.includes(viewCheckbox.value)) 
      viewCheckbox.checked = true;
  });
};

(function () {
  'use strict';
  unsafeWindow.ticketBotSettings = settings;
})();
