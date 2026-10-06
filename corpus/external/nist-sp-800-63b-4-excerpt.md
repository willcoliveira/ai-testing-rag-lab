---
id: X-NIST
title: "NIST SP 800-63B-4 excerpt: password verifiers and rate limiting"
version: "SP 800-63B-4"
tenant: shared
kind: external
source: nist:sp800-63b-4
licence: NIST-public
effective: 2025-07-31
status: current
format: md
source_url: https://pages.nist.gov/800-63-4/sp800-63b.html
retrieved: 2026-10-06
attribution: "Excerpt from NIST Special Publication 800-63B-4, Digital Identity Guidelines: Authentication and Authenticator Management (National Institute of Standards and Technology, 2025), https://doi.org/10.6028/NIST.SP.800-63B-4. Courtesy of NIST; selected text, omissions marked [...]."
---

# NIST SP 800-63B-4 excerpt: password verifiers and rate limiting

Excerpt from NIST Special Publication 800-63B-4, Digital Identity Guidelines: Authentication and Authenticator Management (National Institute of Standards and Technology, 2025), https://doi.org/10.6028/NIST.SP.800-63B-4. Courtesy of NIST; selected text, omissions marked [...].

## 3.1.1.2 Password Verifiers

- Verifiers and CSPs SHALL require passwords that are used as a single-factor authentication mechanism to be a minimum of 15 characters in length. Verifiers and CSPs MAY allow passwords that are only used as part of multi-factor authentication processes to be shorter but SHALL require them to be a minimum of eight characters in length.
- Verifiers and CSPs SHOULD permit a maximum password length of at least 64 characters.

[...]

- Verifiers and CSPs SHALL NOT impose other composition rules (e.g., requiring mixtures of different character types) for passwords.
- Verifiers and CSPs SHALL NOT require subscribers to change passwords periodically. However, verifiers SHALL force a change if there is evidence that the authenticator has been compromised.

[...]

- When processing a request to establish or change a password, verifiers SHALL compare the prospective secret against a blocklist that contains known commonly used, expected, or compromised passwords.

[...]

- Verifiers SHALL implement a rate-limiting mechanism that effectively limits the number of failed authentication attempts that can be made on the subscriber account, as described in Sec. 3.2.2.
- Verifiers SHALL allow the use of password managers and autofill functionality.

## 3.2.2 Rate Limiting (Throttling)

When required by the authenticator type descriptions in Sec. 3.1, the verifier SHALL implement controls to protect against online guessing attacks. Unless otherwise specified in the description of a given authenticator, the verifier SHALL limit consecutive failed authentication attempts using a specific authenticator on a single subscriber account to no more than 100 by disabling that authenticator.

[...]

The limit of 100 attempts is an upper bound, and agencies MAY impose lower limits.

[...]

Requiring the claimant to wait after a failed attempt for a period of time that increases as the subscriber account approaches its maximum allowance for consecutive failed attempts (e.g., 30 seconds up to an hour)

[...]

Following successful authentication at a given AAL, the verifier SHOULD reset the retry count of the authenticators that were used.
