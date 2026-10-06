---
id: A-PWD-V1
title: Password Standard
version: "1.0"
tenant: tenant-a
kind: company
source: comply:password.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/password.md (Apache-2.0, commit aab4849); rewritten for the fictional company Halvenroot, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2024-03-01
status: superseded
format: md
superseded_by: A-PWD-V2
---

# Password Standard

## 1 Purpose and scope

This standard sets out how passwords for Halvenroot accounts are chosen, protected and managed, so that weak or exposed passwords do not give anyone unauthorised access to Halvenroot systems.

It applies to all employees, contractors and anyone else who has a Halvenroot account, on any system at a Halvenroot site or on any system that connects to the Halvenroot network.

The MFA Standard applies to every account.

## 2 Roles

The IAM team owns this standard. It configures the password rules in the identity portal and provides the approved password manager.

The IT Service Desk helps users who cannot sign in and unlocks locked accounts.

The Security Operations Centre receives and investigates reports of suspected password compromise.

Every user is responsible for choosing passwords that meet section 4, protecting them as section 3 describes, and reporting a suspected compromise.

## 3 Protecting passwords

All passwords are confidential information. Do not share your password with anyone, including colleagues, managers or the IT Service Desk. If someone asks you for your password, refuse the request and ask the resource owner to give that person access through their own account.

Do not write passwords down. Do not keep them in emails, electronic notes, documents, chat messages or on mobile devices, and do not read them out over the phone.

Store passwords only in the approved password manager that IT provides.

Use a different password for each Halvenroot account, and never use a Halvenroot password for a personal account or service.

## 4 Password rules

The identity portal enforces the rules in this section wherever a system allows it. Where a system cannot enforce a rule, users must still follow it.

### 4.1 Length

Passwords must be at least 12 characters long. A passphrase made of several unrelated words is an easy way to meet this rule.

### 4.2 Complexity

Passwords must contain at least one upper-case letter, one lower-case letter, one digit and one symbol. Avoid names, dictionary words on their own, and details that others could guess, such as your team, site or product names.

### 4.3 Expiry

User passwords expire every 90 days. The identity portal asks you to choose a new password before the old one expires. Do not reuse a previous password or make only a small change to it.

### 4.4 Lockout

Accounts lock after 5 consecutive failed sign-in attempts and stay locked until the IT Service Desk unlocks them. The IT Service Desk verifies your identity before it unlocks your account.

### 4.5 Suspected compromise

If you suspect a password has been compromised, change it immediately and report it to the Security Operations Centre. Do this even if you are not certain.

## 5 Enforcement

An employee found to have broken this standard may be subject to disciplinary action. A contractor found to have broken it may have their access withdrawn and their engagement reviewed. Where a breach exposes Halvenroot systems or data, the Security Operations Centre may disable the affected account while it investigates.

## 6 Document control

- Owner: Head of Identity and Access Management (IAM team)
- Approver: Chief Information Security Officer (CISO)
- Version: 1.0
- Effective date: 2024-03-01
- Status: superseded by the Password and Authentication Standard

Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.
