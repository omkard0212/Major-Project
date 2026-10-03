/**
 * ArthSathi — Main App Logic
 * Handles: language, character, user session storage
 */

// ── App state (saved to localStorage) ────────────────────────
var AppState = {

    get: function(key) {
        return localStorage.getItem('as_' + key);
    },

    set: function(key, value) {
        localStorage.setItem('as_' + key, value);
    },

    clear: function() {
        var keys = Object.keys(localStorage);
        keys.forEach(function(k) {
            if (k.startsWith('as_')) localStorage.removeItem(k);
        });
    }
};

// ── Backend API base URL ──────────────────────────────────────
var API_BASE = 'http://localhost:5000/api';

/**
 * Make an API call to the Flask backend
 * @param {string}   endpoint — e.g. '/auth/login'
 * @param {string}   method   — 'GET' or 'POST'
 * @param {object}   body     — request body (for POST)
 * @param {function} onSuccess — callback with response data
 * @param {function} onError   — callback with error message
 */
function apiCall(endpoint, method, body, onSuccess, onError) {
    var options = {
        method: method,
        headers: { 'Content-Type': 'application/json' }
    };

    if (method === 'POST' && body) {
        options.body = JSON.stringify(body);
    }

    fetch(API_BASE + endpoint, options)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.success) {
                if (onSuccess) onSuccess(data);
            } else {
                if (onError) onError(data.message || 'Something went wrong');
            }
        })
        .catch(function(err) {
            if (onError) onError('Cannot connect to server. Please check your connection.');
        });
}

// ── Language code map ─────────────────────────────────────────
var LANG_CODES = {
    'hindi'     : 'hi-IN',
    'marathi'   : 'mr-IN',
    'gujarati'  : 'gu-IN',
    'bengali'   : 'bn-IN',
    'tamil'     : 'ta-IN',
    'telugu'    : 'te-IN',
    'kannada'   : 'kn-IN',
    'malayalam' : 'ml-IN',
    'punjabi'   : 'pa-IN',
    'odia'      : 'or-IN',
    'assamese'  : 'as-IN',
    'urdu'      : 'ur-IN',
    'english'   : 'en-IN',
};

/**
 * Get the speech language code for the current user's language
 */
function getLangCode() {
    var lang = AppState.get('language') || 'hindi';
    return LANG_CODES[lang] || 'hi-IN';
}

/**
 * Get current user_id from storage
 */
function getUserId() {
    return AppState.get('user_id');
}
