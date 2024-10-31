const express = require('express');
const app = express();
const http = require('http');
const bodyParser = require('body-parser');

// Додамо парсер для обробки JSON-даних в POST-запитах
app.use(bodyParser.json());

// Додамо заголовки CORS
app.use((req, res, next) => {
  res.setHeader(
    'Access-Control-Allow-Origin',
    'https://tickets.realmadrid.com'
  );
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Credentials', true);
  next();
});

// Обробник POST-запитів на шлях '/sendTelegramMessage'
app.post('/sendTelegramMessage', (req, res) => {
  // Розпаковуємо дані з тіла запиту
  const { message, telegramBotToken, chatId, botName, chromeProfile } =
    req.body;

  // Виконуємо GET-запит до Telegram API для відправки повідомлення
  const telegramApiUrl = `https://api.telegram.org/bot${telegramBotToken}/sendMessage?chat_id=${chatId}&text=${encodeURIComponent(
    botName + ' ' + chromeProfile + ': ' + message
  )}`;

  fetch(telegramApiUrl) // Виконуємо GET-запит
    .then((response) => response.json()) // Парсимо JSON-відповідь
    .then((data) => {
      console.log('Telegram API response:', data);
      res.json({
        success: true,
        message: 'Telegram message sent successfully',
      }); // Відправляємо відповідь клієнту
    })
    .catch((error) => {
      console.error('Error sending message to Telegram:', error);
      res
        .status(500)
        .json({ success: false, error: 'Error sending message to Telegram' }); // Відправляємо відповідь про помилку клієнту
    });
});

// Прослуховування порту 3307
const PORT = 3340;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
