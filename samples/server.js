const express = require('express');
const app = express();
const http = require('http')
const bodyParser = require('body-parser');

app.use(bodyParser.json());

const allowedOrigins = [
    "https://tickets.realmadrid.com",
    "https://entradas.atleticodemadrid.com",
    "https://en.atleticodemadrid.com"
];
  
app.use((req, res, next) => {
    const origin = req.headers.origin;
    if (allowedOrigins.includes(origin)) {
        res.setHeader("Access-Control-Allow-Origin", origin);
    }
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Access-Control-Allow-Credentials", "true");
    next();
});


app.post('/sendTelegramMessage', (req, res) => {
    console.log(req.body)
    const { message, chatId, botName, chromeProfile } = req.body;
    let telegramToken = ''
    if (botName === '<RealBot>') telegramToken = 'token'
    else if (botName === '<AtleticoBot>') telegramToken = 'token'

    const telegramApiUrl = `https://api.telegram.org/bot${telegramToken}/sendMessage?chat_id=${chatId}&text=${encodeURIComponent(
        botName + ' ' + chromeProfile + ': ' + message
    )}`;

    fetch(telegramApiUrl)
        .then((response) => response.json())
        .then((data) => {
            console.log('Telegram API response:', data);
            res.json({
                success: true,
                message: 'Telegram message sent successfully',
            })
        })
        .catch((error) => {
            console.error('Error sending message to Telegram:', error);
            res
                .status(500)
                .json({ success: false, error: 'Error sending message to Telegram' });
        });
});

const PORT = 3309;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
