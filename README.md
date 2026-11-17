# S-Pay — offline Android proof of concept

**This is a demonstration, not a live financial service.** No card charges, bank payouts, identity verification, real user authentication, or revenue collection are implemented. Never enter actual bank details. Profiles are locally selectable without passwords. The database is unencrypted on the device and is not appropriate for sensitive information.

## Functionality
- Free local poster/supporter demo profiles
- USD bill creation with exact decimal cent arithmetic and 2% fee rounded half-up
- Pending bill feed and right-swipe/tap to record a simulated funding event
- SQLite persisted `users`, `bills`, and `transactions` tables
- Transactional single-funding protection and role checks
- Simulated ledger with zero actual revenue and disbursements

For a $100.00 bill: base $100.00, fee $2.00, total $102.00. The app **does not move this money**.

## Android build
GitHub Actions workflow `.github/workflows/build_apk.yml` uses Buildozer/Kivy, Java 17, and a pinned Android-aware python-for-android revision based on the previously successful S-Calculator CI configuration. This S-Pay workflow must pass its own CI before claiming APK success.

```bash
gh run list --repo shiyamprimetrade-sketch/s-pay --workflow build_apk.yml --limit 3
gh run view RUN_ID --repo shiyamprimetrade-sketch/s-pay
termux-setup-storage
mkdir -p ~/storage/downloads/S-Pay
gh run download RUN_ID --repo shiyamprimetrade-sketch/s-pay --name S-Pay-Android --dir ~/storage/downloads/S-Pay
ls -lh ~/storage/downloads/S-Pay/*.apk
```

## Before production payments
Implement an authenticated HTTPS backend with centralized authorization, PCI-compliant payment provider, verified webhook capture and idempotency, double-entry ledger, KYC/AML and sanctions screening, dispute/refund handling, recipient verification, settlement reconciliation, privacy/security review, and legal licensing assessment for target jurisdictions. Do not trust device-side ledger as source of financial truth. No claims of bank settlement until provider confirms settlement.
