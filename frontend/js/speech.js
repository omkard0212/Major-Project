/**
 * ArthSathi — Speech Engine
 * Handles Text-to-Speech (voice output) using Web Speech API
 * No external API needed — built into Chrome/Android browser
 */

var currentUtterance = null;

// Cache available voices
var availableVoices = [];

// Load voices — Chrome loads them asynchronously
function loadVoices() {
    availableVoices = window.speechSynthesis.getVoices();
}

if (window.speechSynthesis) {
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
}

/**
 * Find best matching voice for a language code
 * Falls back to Hindi, then English if exact match not found
 */
function getBestVoice(langCode) {
    if (!availableVoices.length) {
        availableVoices = window.speechSynthesis.getVoices();
    }

    // Try exact match first (e.g. 'mr-IN')
    var exact = availableVoices.find(function(v) {
        return v.lang === langCode;
    });
    if (exact) return exact;

    // Try language prefix match (e.g. 'mr' matches 'mr-IN')
    var prefix = langCode.split('-')[0];
    var partial = availableVoices.find(function(v) {
        return v.lang.startsWith(prefix);
    });
    if (partial) return partial;

    // Fallback 1: Hindi (also works for Urdu — similar language)
    var hindi = availableVoices.find(function(v) {
        return v.lang === 'hi-IN' || v.lang.startsWith('hi');
    });
    if (hindi) return hindi;

    // Fallback 2: any English
    var english = availableVoices.find(function(v) {
        return v.lang.startsWith('en');
    });
    if (english) return english;

    return null;
}

/**
 * Speak a text in a given language
 * @param {string} text     — text to speak
 * @param {string} langCode — BCP-47 language code e.g. 'hi-IN', 'mr-IN'
 * @param {function} onDone — optional callback when speech ends
 */
function speak(text, langCode, onDone) {
    stopSpeaking();

    if (!('speechSynthesis' in window)) {
        console.warn('Text-to-Speech not supported in this browser.');
        if (onDone) onDone();
        return;
    }

    var utterance        = new SpeechSynthesisUtterance(text);
    var voice            = getBestVoice(langCode);
    utterance.lang       = langCode || 'hi-IN';
    utterance.rate       = 0.85;
    utterance.pitch      = 1.0;
    utterance.volume     = 1.0;

    if (voice) {
        utterance.voice = voice;
    }

    utterance.onend = function() {
        currentUtterance = null;
        if (onDone) onDone();
    };

    utterance.onerror = function(e) {
        console.warn('Speech error:', e.error);
        if (onDone) onDone();
    };

    currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
}

/**
 * Stop any currently playing speech
 */
function stopSpeaking() {
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
    currentUtterance = null;
}

/**
 * Check if speech is currently playing
 */
function isSpeaking() {
    return window.speechSynthesis && window.speechSynthesis.speaking;
}
