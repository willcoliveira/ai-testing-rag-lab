---
id: A-MFA
title: Multi-Factor Authentication Standard
version: "1.0"
tenant: tenant-a
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-09-01
status: current
format: html
---

# Multi-Factor Authentication Standard

## 1 Purpose and scope

A stolen password gives an attacker everything they need unless a second proof of identity is
required. Multi-factor authentication (MFA) closes that gap: a sign-in succeeds only when the person
proves both what they know and what they have.

This standard sets out where Halvenroot requires MFA, which factors are approved, the stricter rule
for administrators, what to do when a factor is lost, when factors are revoked and how often MFA is
asked for again. It applies to every person who holds a Halvenroot account and to every system that
signs people in through Halvenroot single sign-on. Password rules are set in the Password and
Authentication Standard; administrator accounts, break-glass accounts and service accounts are
governed by the Privileged Access Standard. The IAM team enforces this standard through the
identity portal.

## 2 Where MFA is required

### 2.1 Systems that require MFA

MFA is required for every sign-in to Halvenroot single sign-on (SSO), the VPN, email and every administrative console. Section 4.1 sets the only standing exception; any other departure needs an approved exception under section 8.

Systems that sign people in through SSO inherit this requirement, so a new application is covered
once it is connected to SSO. A system that cannot enforce MFA must not hold Halvenroot data unless
an exception has been approved under section 8.

## 3 Factors

### 3.1 Approved factors

The approved factors are FIDO2 security keys, passkeys, authenticator app push notifications with number matching, and authenticator app one-time codes.

FIDO2 security keys and passkeys are the phishing-resistant factors.

A phishing-resistant factor is bound to the real Halvenroot sign-in page, so it will not complete a
sign-in on a look-alike site. Number matching asks the user to type the number shown on the sign-in
screen into the app, which stops a user from approving a request they did not start.

Use a phishing-resistant factor wherever you can. Information systems that hold Confidential data
require one; see the Data Classification Policy, section A.2.

### 3.2 Factors that are not approved

SMS and voice-call codes are not approved factors at Halvenroot.

Codes sent by text message or phone call can be intercepted or redirected to an attacker's SIM
card. The identity portal does not offer these methods, and the IT Service Desk will not enable
them.

### 3.3 Registering factors

Every user registers at least two factors.

Register your factors in the identity portal, on separate devices where you can, so that losing a
single device does not lock you out. Never share a factor with a colleague.

## 4 Administrators

### 4.1 MFA for administrator accounts

Administrators must always use MFA, with a FIDO2 security key, for every sign-in to an administrative console.

The only exception is the break-glass accounts described in section 6 of the Privileged Access Standard: they sign in without MFA, and only while an outage of the MFA or SSO service has been declared.

## 5 Lost, stolen or replaced factors

### 5.1 Getting a temporary access pass

If you lose a phone or security key, contact the IT Service Desk at +1-202-555-0142. After verifying your identity on a video call, the Service Desk issues a temporary access pass that is valid for 8 hours and can be used once to register a new factor.

The Service Desk never asks for your password. If you replace a device and can still sign in with
another registered factor, register the new one yourself in the identity portal; you do not need a
pass.

### 5.2 After registering a new factor

Remove the lost factor from your account once the new one is registered.

If the lost security key belonged to an administrator account, also report it to the Security Operations Centre.

If you think a lost or stolen device has been used to sign in to your account, treat it as a
suspected account compromise and follow the Account-Compromise Incident Runbook.

### 5.3 No other way in

There is no other way to sign in without MFA. If you cannot use any approved factor for a longer period, request an exception through the Policy Exceptions Process.

Colleagues, line managers and the Service Desk cannot switch MFA off for you, and you must not ask
them to.

## 6 Revocation

### 6.1 Disabled accounts

All MFA factors registered to an account are revoked within 1 hour of the account being disabled.

Revocation is carried out by the identity portal. A revoked factor cannot be used again, even if the
account is later re-enabled; the account holder registers new factors instead.

### 6.2 Compromised accounts

Factors are also revoked when the Security Operations Centre contains a compromised account; see the Account-Compromise Incident Runbook, section 5.

## 7 Sessions

### 7.1 Asking for MFA again

Halvenroot SSO asks for MFA again after 12 hours.

SSO also asks for MFA again after you sign out and when you sign in from a new device or browser.

## 8 Exceptions

Exceptions to this standard are requested and approved through the Policy Exceptions Process. No
exception can remove MFA from an administrator account; see the Policy Exceptions Process,
section 2.

## 9 Document control

- Owner: IT Operations Manager
- Approver: CISO
- Version: 1.0
- Effective date: 2025-09-01
