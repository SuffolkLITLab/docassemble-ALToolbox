# ALToolbox

[![PyPI version](https://badge.fury.io/py/docassemble-ALToolbox.svg)](https://badge.fury.io/py/docassemble-ALToolbox)

This repository is used to host small Python modules, widgets, and JavaScript web components js files that enhance Docassemble interviews. These modules were
built as part of the Suffolk University Law School LIT Lab's [Document Assembly Line project](https://suffolklitlab.org/docassemble-AssemblyLine-documentation/).
They are placed here
rather than in https://github.com/SuffolkLitLab/docassemble-AssemblyLine because we believe these small components can easily be used
by anyone, regardless of whether they use any other code from the Document Assembly Line project.

If you want to add a small function to this project, consider adding it to the existing misc.py to avoid creating too many module files.

## Documentation

Read the [documentation for the functions and components](https://assemblyline.suffolklitlab.org/docs/components/ALToolbox/overview) to learn
how to use these components in your own [Docassemble](https://github.com/jhpyle/docassemble) projects.

## Translating strings inside JavaScript

Docassemble translates anything that reaches Python through `word()`, but JavaScript
running in the browser has no way to reach that catalog, so strings in custom datatypes
and small widgets tend to stay hardcoded in English.

ALToolbox adds an endpoint, `/al_translations.json?lang=es`, that returns the `word()`
catalog for a language, and a script that puts it behind `_()`:

```yaml
include:
  - docassemble.ALToolbox:translation_strings.yml
```

Then, in your JavaScript:

```js
_("Copied!")                                  // "¡Copiado!"
_("You have entered %d characters.", count)   // "Ha escrito 42 caracteres."
_("%1$s of %2$s", done, total)                // positional, so a translation can reorder
_("100%% sure")                               // "%%" is a literal percent sign
```

`alTranslate()` is the same function under a less collision-prone name. `_` is only
assigned if nothing else has claimed it, so an interview that loads lodash or underscore
keeps its own `_`.

### Adding translations

Write a word translation file and list it under `words:` in your server configuration —
the same mechanism docassemble already uses for `word()`:

```yaml
# docassemble/yourpackage/data/sources/yourpackage_words.yml
es:
  Copied!: ¡Copiado!
  You have entered %d characters.: Ha escrito %d caracteres.
```

```yaml
# in the docassemble configuration
words:
  - docassemble.ALToolbox:data/sources/altoolbox_words.yml
  - docassemble.yourpackage:data/sources/yourpackage_words.yml
```

For translations that come from somewhere other than a file, `add_translations()` adds
them to the same catalog at runtime:

```yaml
code: |
  add_translations("es", {"Copied!": "¡Copiado!"})
```

Lookups try an exact match first, then one that ignores surrounding whitespace,
capitalization and trailing punctuation, restoring the source string's capitalization and
punctuation on the way out. So a catalog entry for `copied` will still translate
`_("Copied!")`.

### What to expect

The catalog is fetched once and kept in `localStorage`, keyed by language, so `_()`
resolves synchronously on every page load after the first. On the very first load of a
language the catalog is still in flight and `_()` returns the English source; listen for
the `alTranslationsLoaded` event on `window` if you need to redraw when it arrives.

Docassemble loads every script at the end of the body, so `_` exists from `daPageLoad`
onward — which is where interview JavaScript normally does its work anyway. An inline
`<script>` in a `subquestion` runs *before* that, so wrap it:

```js
document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("greeting").textContent = _("Hello");
});
```

The endpoint is unauthenticated and identical for every user of a language — it exposes
the server's configured `word()` catalog for that language (which may include arbitrary
phrases from installed packages). `translation_strings.translate()` is

Run `translation_strings_demo.yml` to see it working.

## Suffolk LIT Lab Document Assembly Line

<img src="https://user-images.githubusercontent.com/7645641/142245862-c2eb02ab-3090-4e97-9653-bb700bf4c54d.png" alt="drawing of people working together on a website UI" width="300" style="align: center;"/>

The Assembly Line Project is a collection of volunteers, students, and institutions who joined together
during the COVID-19 pandemic to help increase access to the court system. Our vision is mobile-friendly,
easy to use **guided** online forms that help empower litigants to access the court remotely.

Our signature project is [CourtFormsOnline.org](https://courtformsonline.org).

We designed a step-by-step, assembly line style process for automating court forms on top of Docassemble
and built several tools along the way that **you** can use in your home jurisdiction.

This package contains **runtime code** and **pre-written questions** to support authoring robust, 
consistent, and attractive Docassemble interviews that help complete court forms.

Read more on our [documentation page](https://suffolklitlab.org/docassemble-AssemblyLine-documentation/).


## Related repositories

* https://github.com/SuffolkLitLab/docassemble-AssemblyLine
* https://github.com/SuffolkLitLab/docassemble-ALWeaver
* https://github.com/SuffolkLitLab/docassemble-ALMassachusetts
* https://github.com/SuffolkLitLab/docassemble-MassAccess
* https://github.com/SuffolkLitLab/docassemble-ALThemeTemplate
* https://github.com/SuffolkLitLab/EfileProxyServer

## Contributors:
* @plocket  
* @nonprofittechy
* @purplesky2016
* @brycestevenwilley
