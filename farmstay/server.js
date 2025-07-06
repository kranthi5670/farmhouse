const express = require('express');
const bodyParser = require('body-parser');
const Razorpay = require('razorpay');
const dotenv = require('dotenv');
const axios = require('axios');
const path = require('path');

dotenv.config();
const app = express();
app.use(bodyParser.json());
app.use(express.static('public'));

const razorpay = new Razorpay({
  key_id: process.env.RAZORPAY_KEY_ID,
  key_secret: process.env.RAZORPAY_KEY_SECRET,
});

app.post('/book', async (req, res) => {
  try {
    const {
      name,
      email,
      mobile,
      checkin,
      checkout,
      guests,
      promoCode,
    } = req.body;

    const checkinDate = new Date(checkin);
    const checkoutDate = new Date(checkout);
    const days = Math.ceil((checkoutDate - checkinDate) / (1000 * 60 * 60 * 24));

    let ratePerDay = ['Friday', 'Saturday', 'Sunday'].includes(
      checkinDate.toLocaleString('en-US', { weekday: 'long' })
    ) ? 12000 : 10000;

    let extraGuests = Math.max(guests - 10, 0);
    let total = (ratePerDay + extraGuests * 500) * days;

    let discount = 0;
    if (promoCode) {
      const response = await axios.post('http://localhost:5000/validate-promo', { code: promoCode });
      if (response.data.valid) {
        discount = Math.floor((response.data.discount / 100) * total);
      }
    }

    const finalAmount = total - discount;
    const amountToPay = Math.floor(finalAmount * 0.5); // 50%

    const razorpayOrder = await razorpay.orders.create({
      amount: amountToPay * 100,
      currency: 'INR',
      receipt: `order_rcptid_${Date.now()}`,
    });

    res.json({
      orderId: razorpayOrder.id,
      amount: amountToPay,
      total,
      discount,
    });
  } catch (err) {
    console.error(err);
    res.status(500).send('Something went wrong');
  }
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
