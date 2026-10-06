---
id: B-MFA
title: Mirrowfen MFA Standard
version: "1.0"
tenant: tenant-b
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-06-01
status: current
format: md
---

# Mirrowfen MFA Standard

## 1 Purpose and scope

Mirrowfen is a business unit that runs its own directory and its own security standards. This
standard sets out how multi-factor authentication (MFA) protects accounts in the Mirrowfen
directory: where it is required, which factors may be used, the rule for administrators, what to do
when a factor is lost, when factors are revoked and when MFA is asked for again.

It applies to every person who holds an account in the Mirrowfen directory and to every system that
signs people in through that directory. Password rules are set in the Mirrowfen Password Standard.
Mirrowfen IT Support runs the identity portal and enforces this standard.

## 2 Where MFA is required

MFA is required for every sign-in to Mirrowfen systems.

A system that cannot ask for MFA must not hold Mirrowfen data until the Mirrowfen security lead has
confirmed that it meets this standard.

## 3 Factors

### 3.1 Approved factors

The approved factors are authenticator app push notifications with number matching, authenticator app one-time codes and FIDO2 security keys.

Number matching asks you to type the number shown on the sign-in screen into the app, so you cannot
approve a request you did not start. A FIDO2 security key only works with the genuine Mirrowfen
sign-in page, which makes it the strongest choice. Register your factors in the identity portal and
never share them with anyone.

### 3.2 Fallback factor

SMS codes are allowed only as a fallback factor, when no other approved factor is available.

Text messages can be intercepted or redirected, so register an approved factor as soon as you can.

## 4 Administrators

Mirrowfen administrators use a FIDO2 security key.

This applies to every sign-in with an administrator account.

## 5 Lost factors

### 5.1 Recovery code

Call Mirrowfen IT Support on +1-202-555-0175. After checking your identity, IT Support issues a one-time recovery code that is valid for 2 hours.

Use the recovery code to sign in once and register a new factor, then remove the lost one in the
identity portal. IT Support never asks for your password. If you can still sign in with another
registered factor, register the replacement yourself; you do not need a recovery code.

## 6 Revocation

### 6.1 Disabled accounts

MFA factors are revoked within 24 hours of the account being disabled.

A revoked factor cannot be used again. If the account is later re-enabled, the holder registers new
factors.

## 7 Sessions

### 7.1 Asking for MFA again

Mirrowfen sign-ins ask for MFA again after 24 hours.

You are also asked for MFA again after you sign out and when you sign in from a new device or
browser.

## 8 Document control

- Owner: Mirrowfen IT Support
- Approver: Mirrowfen security lead
- Version: 1.0
- Effective date: 2025-06-01
