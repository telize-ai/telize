# Telize website

Static landing page for [telize.ro](https://telize.ro).

## Local preview

```bash
cd website
python -m http.server 8080
```

Open [http://localhost:8080](http://localhost:8080).

Or with any static file server:

```bash
npx serve website
```

## Deploy

Upload the contents of this directory to your web host. No build step required.

Suggested structure on the server:

```
/
  index.html
  css/styles.css
  js/main.js
```

## Contents

Single-page site covering:

- Hero and project positioning
- Features overview
- Architecture / how it works
- Installation and quick start
- Workflow reference and CLI
- Examples, requirements, contributing
- Footer with GitHub, PyPI, license, and contact links
