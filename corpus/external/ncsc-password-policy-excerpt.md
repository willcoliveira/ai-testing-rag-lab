---
id: X-NCSC
title: "NCSC excerpt: Password policy, updating your approach"
version: "1.0"
tenant: shared
kind: external
source: ncsc:password-policy-updating-your-approach
licence: OGL-UK-3.0
effective: 2018-11-19
status: current
format: md
source_url: https://www.ncsc.gov.uk/collection/passwords/updating-your-approach
retrieved: 2026-10-06
attribution: "Contains public sector information licensed under the Open Government Licence v3.0 (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Source: National Cyber Security Centre, 'Password policy: updating your approach', https://www.ncsc.gov.uk/collection/passwords/updating-your-approach (page shown as version 1.0, reviewed 19 November 2018; retrieved 2026-10-06). Selected text; omissions marked [...]."
---

# NCSC excerpt: Password policy, updating your approach

Contains public sector information licensed under the Open Government Licence v3.0 (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Source: National Cyber Security Centre, 'Password policy: updating your approach', https://www.ncsc.gov.uk/collection/passwords/updating-your-approach (page shown as version 1.0, reviewed 19 November 2018; retrieved 2026-10-06). Selected text; omissions marked [...].

The section numbers in this excerpt are added for citation and are not part of the NCSC page.

## 1 Use throttling or account lockout

Password systems can be configured so that there is a progressively increasing time delay between successive login attempts - a technique known as 'throttling'. This restricts the number of guesses an attacker can attempt while giving users multiple opportunities to remember their password. An alternative is account lockout, where a user only has a fixed number of attempts to enter their password before their account is locked.

Throttling is preferred, because account lockout can leave legitimate users unable to access their accounts, and requires access to an account recovery method.

[...]

If using account lockout, we recommend you allow between 5 and 10 login attempts before the account is frozen, to avoid accidental lockout.

[...]

## 2 Do not use complexity requirements

Using complexity requirements (that is, where staff can only use passwords that are suitably complex) is a poor defence against guessing attacks. [...]

[...]

Complexity requirements provide no defence against common attacks and should not be used.

[...]

## 3 Don't enforce regular password expiry

Regular password changing harms rather than improves security. Many systems will force users to change their password at regular intervals, typically every 30, 60 or 90 days. This imposes burdens on the user and there are costs associated with recovering accounts.

Forcing password expiry carries no real benefits because:

- the user is likely to choose new passwords that are only minor variations of the old
- stolen passwords are generally exploited immediately
- resetting the password gives you no information about whether a compromise has occurred
- an attacker with access to the account will probably also receive the request to reset the password
- if compromised via insecure storage, the attacker will be able to find the new password in the same place

[...]

Note: Users must change their passwords when you know (or suspect) it has been compromised.
