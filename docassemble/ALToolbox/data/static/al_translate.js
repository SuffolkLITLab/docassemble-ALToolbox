/* al_translate.js -- translate strings inside JavaScript.
 *
 *   _("Copied!")                               -> "¡Copiado!"
 *   _("You have entered %d characters.", 42)   -> "Has escrito 42 caracteres."
 *   _("%1$s of %2$s", 3, 10)                   -> positional, so a translation
 *                                                 can reorder the arguments
 *
 * Translations come from docassemble's word() catalog, fetched once from
 * /al_translations.json and cached in localStorage so that later page loads
 * translate synchronously -- which matters because custom datatypes call _()
 * while they build their markup.
 *
 * On the very first page load of a language the cache is cold and _() returns
 * the English source. Listen for the "alTranslationsLoaded" event on window if
 * you need to redraw when the catalog arrives.
 */

(function () {
  "use strict";

  var CACHE_PREFIX = "alTranslations/";
  var CACHE_MAX_AGE_MS = 5 * 60 * 1000;

  // Captured now because document.currentScript is null once we are async.
  var scriptSrc = document.currentScript ? document.currentScript.src : "";

  function catalogUrl(language) {
    if (window.alTranslationsUrl) {
      return window.alTranslationsUrl + "?lang=" + encodeURIComponent(language);
    }
    // This file is served from <root>/packagestatic/docassemble.ALToolbox/...,
    // so stripping that suffix gives us the docassemble root, which is not
    // always "/".
    var root = scriptSrc.replace(/packagestatic\/.*$/, "");
    return root + "al_translations.json?lang=" + encodeURIComponent(language);
  }

  function currentLanguage() {
    return (
      window.alTranslationsLang ||
      document.documentElement.getAttribute("lang") ||
      "en"
    );
  }

  /* --- matching ---------------------------------------------------------- */

  var TRAILING_PUNCTUATION = ".:!?";

  // Keep in step with _normalize() in translation_strings.py.
  function normalize(text) {
    var collapsed = text.replace(/\s+/g, " ").trim();
    while (
      collapsed.length &&
      TRAILING_PUNCTUATION.indexOf(collapsed.charAt(collapsed.length - 1)) !== -1
    ) {
      collapsed = collapsed.slice(0, -1);
    }
    return collapsed.toLowerCase();
  }

  // Keep in step with _match_shape() in translation_strings.py.
  function matchShape(source, translated) {
    var strippedSource = source.trim();
    var result = translated.trim();
    if (!result) {
      return source;
    }
    var trailing = strippedSource.match(/[.:!?]+$/);
    if (
      trailing &&
      TRAILING_PUNCTUATION.indexOf(result.charAt(result.length - 1)) === -1
    ) {
      result += trailing[0];
    }
    var firstSource = strippedSource.charAt(0);
    var firstResult = result.charAt(0);
    if (
      firstSource === firstSource.toUpperCase() &&
      firstSource !== firstSource.toLowerCase() &&
      firstResult === firstResult.toLowerCase() &&
      firstResult !== firstResult.toUpperCase()
    ) {
      result = firstResult.toUpperCase() + result.slice(1);
    }
    return result;
  }

  var words = {};
  var normalizedWords = {};

  function setWords(newWords) {
    words = newWords || {};
    normalizedWords = {};
    Object.keys(words).forEach(function (source) {
      // An exact match always wins, so only the first normalized spelling of a
      // source string gets to claim the fuzzy slot.
      var key = normalize(source);
      if (!Object.prototype.hasOwnProperty.call(normalizedWords, key)) {
        normalizedWords[key] = words[source];
      }
    });
  }

  function lookup(text) {
    if (Object.prototype.hasOwnProperty.call(words, text)) {
      return words[text];
    }
    var key = normalize(text);
    if (Object.prototype.hasOwnProperty.call(normalizedWords, key)) {
      return matchShape(text, normalizedWords[key]);
    }
    return text;
  }

  /* --- printf-style substitution ----------------------------------------- */

  /* Supports %s, %d and positional %1$s, plus %% for a literal percent sign.
   * Positional forms exist so a translator can put the arguments in whatever
   * order their language needs. */
  function format(template, args) {
    var nextArg = 0;
    return template.replace(
      /%(?:(\d+)\$)?([sdi%])/g,
      function (whole, position, kind) {
        if (kind === "%") {
          return "%";
        }
        var value = position ? args[parseInt(position, 10) - 1] : args[nextArg++];
        if (value === undefined) {
          return whole;
        }
        if (kind === "d" || kind === "i") {
          var asNumber = parseInt(value, 10);
          return isNaN(asNumber) ? String(value) : String(asNumber);
        }
        return String(value);
      }
    );
  }

  /* --- the public function ----------------------------------------------- */

  function alTranslate(text) {
    if (typeof text !== "string") {
      return text;
    }
    // Always formatted, even with no arguments, so that "%%" reliably means a
    // literal percent sign. A placeholder with no argument to fill it is left
    // as written.
    return format(lookup(text), Array.prototype.slice.call(arguments, 1));
  }

  window.alTranslate = alTranslate;
  // Do not clobber lodash or underscore if an interview loaded one.
  if (typeof window._ === "undefined") {
    window._ = alTranslate;
  }

  /* --- cache and fetch ---------------------------------------------------- */

  function readCache(language) {
    try {
      var raw = window.localStorage.getItem(CACHE_PREFIX + language);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      // Private browsing, a full quota, or hand-edited garbage. Not fatal.
      return null;
    }
  }

  function writeCache(language, catalogWords) {
    try {
      window.localStorage.setItem(
        CACHE_PREFIX + language,
        JSON.stringify({ fetched: Date.now(), words: catalogWords })
      );
    } catch (error) {
      /* Nothing to do: we just refetch next time. */
    }
  }

  function announce(language) {
    window.dispatchEvent(
      new CustomEvent("alTranslationsLoaded", { detail: { language: language } })
    );
  }

  var activeLanguage = null;

  function refresh(language) {
    fetch(catalogUrl(language), { credentials: "same-origin" })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (catalog) {
        if (!catalog || !catalog.words) {
          return;
        }
        writeCache(language, catalog.words);
        // The interview may have moved on to another language while this was
        // in flight; the cache is still worth keeping, the words are not.
        if (language === activeLanguage) {
          setWords(catalog.words);
          announce(language);
        }
      })
      .catch(function () {
        /* Offline or the endpoint is missing: keep the source strings. */
      });
  }

  function load(language) {
    activeLanguage = language;
    var cached = readCache(language);
    if (cached && cached.words) {
      // Use the cache immediately so that _() works on this paint, then
      // revalidate in the background if it is old enough to be worth a request.
      setWords(cached.words);
      if (!cached.fetched || Date.now() - cached.fetched > CACHE_MAX_AGE_MS) {
        refresh(language);
      }
    } else {
      // Better untranslated than translated into the language we just left.
      setWords({});
      refresh(language);
    }
  }

  load(currentLanguage());

  // Docassemble moves between screens over AJAX rather than reloading, and the
  // interview language can change on the way, so re-check on every screen.
  if (window.jQuery) {
    window.jQuery(document).on("daPageLoad", function () {
      var language = currentLanguage();
      if (language !== activeLanguage) {
        load(language);
      }
    });
  }
})();
