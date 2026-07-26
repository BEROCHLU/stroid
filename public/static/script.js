/**
 * Stroid - Stock & Forex Tracker
 * Frontend Logic
 */

// DOM Elements
const tickerInput = document.getElementById('text_box');


const liveClock = document.getElementById('live_clock');
const quoteTitle = document.getElementById('quote_title');
const regularPrice = document.getElementById('regular_price');
const regularChange = document.getElementById('regular_change');
const regularTime = document.getElementById('regular_time');
const regularVolume = document.getElementById('regular_volume');

const postPrice = document.getElementById('post_price');
const postChange = document.getElementById('post_change');
const postTime = document.getElementById('post_time');
const afterHoursSection = document.getElementById('after_hours_section');
const loadingSpinner = document.getElementById('loading_spinner');
const toastEl = document.getElementById('toast');

const btnDollar = document.getElementById('btn_dollar');
const btnSave = document.getElementById('btn_save');
const btnUpdate = document.getElementById('btn_update');


/**
 * Set Clock to Last Fetch Time (HH:mm:ss)
 */
function updateClock() {
	const now = new Date();
	const hours = String(now.getHours()).padStart(2, '0');
	const minutes = String(now.getMinutes()).padStart(2, '0');
	liveClock.textContent = `${hours}:${minutes}`;
}



/**
 * Determine API Base URL
 */
function getApiUrl(ticker) {
	const params = new URLSearchParams({ t: ticker });
	let baseUrl;

	switch (location.hostname) {
		case 'aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com':
			// AWS API Gateway endpoint
			baseUrl = 'https://l8u8iob6v1.execute-api.ap-northeast-1.amazonaws.com/new_stage';
			break;
		case '127.0.0.1':
		case 'localhost':
			// Local development endpoint
			baseUrl = '/api/quote';
			break;
		default:
			baseUrl = '/quote';
			break;
	}

	return `${baseUrl}?${params.toString()}`;
}

/**
 * Show Toast Notification
 */
function showToast(message) {
	toastEl.textContent = message;
	toastEl.classList.remove('hidden');
	setTimeout(() => {
		toastEl.classList.add('hidden');
	}, 2000);
}

/**
 * Helper to style positive/negative change elements
 */
function formatChangeElement(el, changeStr, percentStr) {
	if (!changeStr && !percentStr) {
		el.textContent = '';
		return;
	}

	const combined = `${changeStr || ''} ${percentStr || ''}`.trim();
	el.textContent = combined;
	el.className = 'price-change';
}



/**
 * Fetch Quote Data from API / Lambda
 */
async function fetchQuote() {
	const ticker = tickerInput.value.trim().toUpperCase();
	if (!ticker) return;

	loadingSpinner.classList.remove('hidden');

	const url = getApiUrl(ticker);

	try {
		const res = await fetch(url, { method: 'GET', mode: 'cors' });
		if (res.status === 204) {
			// HTTP 204 No Content: Stale timestamp from delayed node. Silently skip update.
			return;
		}
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		const data = await res.json();
		renderQuote(data);
	} catch (err) {

		console.error('API Fetch failed:', err);
		showToast(`Fetch error: Check connection or API server`);
	} finally {
		loadingSpinner.classList.add('hidden');
	}
}

/**
 * Render Quote Data onto DOM
 */
function renderQuote(data) {
	updateClock();
	quoteTitle.textContent = data.title || data.ticker || 'N/A';
	regularPrice.textContent = data.price || '---';

	formatChangeElement(regularChange, data.priceChange, data.priceChangePercent);

	// Display real market time notice from Yahoo Finance (e.g., "As of 4:53:09 AM UTC. Market Open.")
	regularTime.textContent = data.marketTime || '';
	regularVolume.textContent = data.volume || '';


	if (data.postPrice) {
		afterHoursSection.classList.remove('hidden');
		postPrice.textContent = data.postPrice;
		formatChangeElement(postChange, data.postPriceChange, data.postPriceChangePercent);
		postTime.textContent = data.postMarketTime || '';
	} else {
		afterHoursSection.classList.add('hidden');
	}
}



/**
 * Event Listeners
 */
btnUpdate.addEventListener('click', fetchQuote);

btnDollar.addEventListener('click', () => {
	tickerInput.value = 'JPY=X';
});


btnSave.addEventListener('click', () => {

	const currentTicker = tickerInput.value.trim().toUpperCase();
	if (currentTicker) {
		localStorage.setItem('stroid_saved_ticker', currentTicker);
		showToast(`Saved ticker: ${currentTicker}`);
	}
});

tickerInput.addEventListener('keydown', (e) => {

	if (e.key === 'Enter') {
		fetchQuote();
	}
});

/**
 * Initial Load
 */
window.addEventListener('DOMContentLoaded', () => {
	const savedTicker = localStorage.getItem('stroid_saved_ticker');
	if (savedTicker) {
		tickerInput.value = savedTicker;
	}
});


