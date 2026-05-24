# Security

## Supported versions

The project is pre-1.0. Security fixes are made on the latest main branch.

## Reporting a vulnerability

Please open a private security advisory on GitHub if available, or contact the
maintainers through the repository issue tracker with minimal reproduction
details. Do not include secrets in issues or test fixtures.

## Data handling

readme-first-screen runs locally. It does not call external AI services or upload
README contents. Network access only happens when the user passes a GitHub or raw
HTTP(S) URL as the input source.
