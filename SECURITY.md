# Security policy

## Supported versions

Security fixes are applied to the latest version on the `main` branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature under the repository's **Security** tab. Do not include secrets, personal files, or credentials in a public issue.

Mochi runs locally after dependency installation and does not make runtime network requests. Its persistent preferences, processed custom appearance, and allowlisted daily aggregate activity data are documented in the README. It never stores raw input events or captures input content.

Custom images are re-encoded as a bounded RGBA PNG without EXIF metadata and saved only in Mochi's per-user data folder. The original path is not retained. Import rejects unreadable, fully transparent, oversized, and decompression-bomb images; a failed replacement does not overwrite the previous valid copy.
