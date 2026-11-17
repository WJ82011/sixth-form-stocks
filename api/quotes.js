/**
 * GET /api/quotes?symbols=AAPL,NVDA
 * Thin Vercel serverless proxy — Finnhub key from server env only.
 */
'use strict';

const { createVercelHandler } = require('../lib/quotes-api');

module.exports = createVercelHandler('quotes');
