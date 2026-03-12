const express = require('express');
const app = express();

app.use(express.json());

const SLACK_WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL;

app.post('/webhook', async (req, res) => {
  const { event, data } = req.body;

  if (event !== 'order.created') {
    return res.sendStatus(200);
  }

  const client = data.client.name;
  const invoice = data.id;
  const item = data.service;
  const amount = `$${data.invoice.total} ${data.invoice.currency}`;

  const message = {
    text: `*New Order*\nClient: ${client}\nOrder #${invoice}\nItem: ${item}\nAmount: ${amount}`
  };

  await fetch(SLACK_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message)
  });

  res.sendStatus(200);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Listening on port ${PORT}`));
