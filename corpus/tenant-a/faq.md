---
id: A-FAQ
title: Identity and Access FAQ
version: "1.0"
tenant: tenant-a
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-10-01
status: current
format: md
---

# Identity and Access FAQ

## 1 Questions

This page answers the questions that Halvenroot staff and contractors most often ask the IT Service
Desk about passwords, MFA, remote working and devices. Each answer is a short summary and names the
document and section that set the rule. If a summary here and the named document ever seem to
differ, the named document applies.

### Q1 How long must my password be?

Passwords must be at least 15 characters long (Password and Authentication Standard, section 4.1).

You do not need to mix in particular types of character, but the identity portal will reject a
password that appears on its blocklist of common and breached passwords.

### Q2 Do I have to change my password regularly?

Yes. User passwords expire every 60 days (Password and Authentication Standard, section 4.4).

The identity portal prompts you when your password is due. Choose a new password each time rather
than adding a number or a letter to the old one.

### Q3 Which MFA methods can I use?

Halvenroot accepts the four approved factors: FIDO2 security keys, passkeys, authenticator app push
notifications with number matching, and authenticator app one-time codes. FIDO2 security keys and
passkeys are phishing-resistant, so use one of them wherever you can. SMS and voice-call codes are
not approved, and the Service Desk cannot turn them on for you (MFA Standard, section 3).

### Q4 I lost my phone. How do I sign in?

Contact the IT Service Desk on +1-202-555-0142. After checking your identity on a video call, the
Service Desk issues you a temporary access pass, which you use to register a new factor (MFA
Standard, section 5.1).

If you still have another registered factor, such as a security key, sign in with it and register
the replacement yourself in the identity portal. Once the new factor works, remove the lost one
from your account.

### Q5 Can I skip MFA if it gets in the way?

No. There is no other way to sign in without MFA, and colleagues, line managers and the Service
Desk cannot switch it off for you. If you cannot use any approved factor for a longer period,
request an exception through the Policy Exceptions Process (MFA Standard, section 5.3).

### Q6 Can I work from a café or a hotel?

Yes. Connect to Halvenroot systems through the Halvenroot VPN, with MFA, as you would from home
(Remote Access Policy, section 4.3). Sit where your screen cannot be overlooked, keep it out of view
of other people, and do not leave your laptop or phone unattended (Remote Access Policy, section 3).
Working away from Halvenroot premises needs your line manager's written authorisation (Remote
Access Policy, section 5).

### Q7 Can I copy files to a USB stick?

No. USB storage devices are blocked on Halvenroot devices, and device management enforces the block
(Device Policy, section 6.1). If your work genuinely needs removable media, exceptions follow the
Policy Exceptions Process (Device Policy, section 6.2).

### Q8 I typed my password into a suspicious page. What now?

Change it now and report it to the Security Operations Centre within 1 hour: security@halvenroot.example.com, +1-202-555-0147 (Account-Compromise Incident Runbook, section 3).

Report it even if you are not sure the page was malicious. Tell the Security Operations Centre
what happened, when, which page you saw and which systems you use with that account.

### Q9 What is a break-glass account?

A break-glass account is an emergency administrator account. It is used only while an outage of
the MFA or SSO service has been declared, so that administrators can still reach critical systems
(Halvenroot Security Glossary, section 3; Privileged Access Standard, section 6).

Break-glass accounts are not for everyday administration, and every use is alerted to the Security
Operations Centre.

### Q10 Can a colleague use my login while I'm on leave?

No. Never share your password with anyone, including a colleague who is covering for you. If a
colleague needs access to your work while you are away, the resource owner grants them their own
access (Password and Authentication Standard, section 4.6).

### Q11 Who approves an exception?

The line manager, the resource owner and the CISO must all approve the request (Policy Exceptions
Process, section 3.2).

You submit a Security Exception Request in the IT portal, stating the rule, the reason, the
compensating controls and the end date. Some rules cannot be excepted at all: no exception allows a
password to be shared, and no exception can remove MFA from an administrator account.

### Q12 Where do I get help?

Contact the IT Service Desk: servicedesk@halvenroot.example.com, +1-202-555-0142.

To report a suspected account compromise, contact the Security Operations Centre as described in
Q8.

## 2 Document control

- Owner: IT Operations Manager
- Approver: CISO
- Version: 1.0
- Effective date: 2025-10-01
