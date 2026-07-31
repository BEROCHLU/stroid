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

const btnClear = document.getElementById('btn_clear');
const btnBtc = document.getElementById('btn_btc');
const btnEth = document.getElementById('btn_eth');
const btnUsdJpy = document.getElementById('btn_usdjpy');
const btnSave = document.getElementById('btn_save');
const btnLoad = document.getElementById('btn_load');
const btnUpdate = document.getElementById('btn_update');


/**
 * Update Live Clock (HH:mm)
 */
function updateClock() {
	const now = new Date();
	const hours = String(now.getHours()).padStart(2, '0');
	const minutes = String(now.getMinutes()).padStart(2, '0');
	liveClock.textContent = `${hours}:${minutes}`;
}

// 画面読み込み時に即時表示 ＋ 1秒(1000ms)ごとに自動更新
updateClock();
setInterval(updateClock, 1000);

/**
 * Determine API Base URL
 */
function getApiUrl(ticker) {
	const params = new URLSearchParams({ t: ticker });
	let baseUrl;

	switch (location.hostname) {
		case 'aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com':
			// AWS Lambda Function URL endpoint
			baseUrl = 'https://2q4qxczvx3y347l5uegv6zyxgy0xfduo.lambda-url.ap-northeast-1.on.aws/';
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
	}, 1800);
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
		if (!res.ok) {
			const errData = await res.json();
			throw new Error(errData.error || `HTTP ${res.status}`);
		}
		const data = await res.json();
		renderQuote(data);
	} catch (err) {

		console.error('API Fetch failed:', err);
		showToast(err.message);
	} finally {
		loadingSpinner.classList.add('hidden');
	}
}

/**
 * Render Quote Data onto DOM
 */
function renderQuote(data) {
	quoteTitle.textContent = data.title || data.ticker || 'N/A';
	regularPrice.textContent = data.price || '---';

	formatChangeElement(regularChange, data.priceChange, data.priceChangePercent);

	// Display real market time notice from Yahoo Finance
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

btnBtc.addEventListener('click', () => {
	tickerInput.value = 'BTC-USD';
});

btnEth.addEventListener('click', () => {
	tickerInput.value = 'ETH-USD';
});

btnUsdJpy.addEventListener('click', () => {
	tickerInput.value = 'JPY=X';
});


btnSave.addEventListener('click', () => {
	const currentTicker = tickerInput.value.trim().toUpperCase();
	if (currentTicker) {
		localStorage.setItem('stroid_saved_ticker', currentTicker);
		showToast(`Saved ticker: ${currentTicker}`);
	}
});

btnLoad.addEventListener('click', () => {
	const savedTicker = localStorage.getItem('stroid_saved_ticker');
	if (savedTicker) {
		tickerInput.value = savedTicker;
	}
});

btnClear.addEventListener('click', () => {
	tickerInput.value = '';
	tickerInput.focus();
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
