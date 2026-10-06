---
id: B-PWD
title: Mirrowfen Password Standard
version: "1.0"
tenant: tenant-b
kind: company
source: comply:password.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/password.md (Apache-2.0, commit aab4849); rewritten for the fictional business unit Mirrowfen, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2025-06-01
status: current
format: md
---

# Mirrowfen Password Standard

## 1 Purpose and scope

This standard describes how passwords for Mirrowfen accounts are chosen, protected and managed, so
that weak or exposed passwords do not give anyone unauthorised access to Mirrowfen systems.

This standard applies to every account in the Mirrowfen directory. Mirrowfen is a business unit that runs its own directory and its own security standards.

It covers user passwords for employees, contractors and any other personnel who sign in with a
Mirrowfen account. Multi-factor authentication is set by the Mirrowfen MFA Standard.

## 2 Roles

- **Every user** follows this standard, protects their own passwords and reports any password they
  believe has been exposed.
- **Mirrowfen IT Support** configures the Mirrowfen directory so that it enforces sections 3 and 4,
  maintains the password blocklist and helps users who cannot sign in. It never asks a user for
  their password.
- **The Mirrowfen security lead** owns this standard, receives reports of exposed or compromised
  passwords and decides what further action is needed.

## 3 Password rules

### 3.1 Minimum length

Passwords must be at least 16 characters long. A passphrase made of several unrelated words is an
easy way to meet this rule and is encouraged.

### 3.2 Composition and blocklist

Mirrowfen does not impose composition rules. New passwords are checked against a blocklist of
common and breached passwords. A password that appears on the blocklist is rejected, and the
directory asks the user to choose another one.

### 3.3 Expiry

Mirrowfen passwords do not expire on a schedule. A password is changed only when compromise is known or suspected.

If you know or suspect that a password has been compromised, change it straight away and tell the
Mirrowfen security lead. Report it even if you have already changed the password, and even if you
are not sure.

## 4 Sign-in protection

### 4.1 Account lockout

An account locks for 15 minutes after 8 failed sign-in attempts. The account unlocks by itself
when the lockout ends.

## 5 Protecting passwords

All passwords are confidential information. Never share your password with anyone, including
Mirrowfen IT Support. If someone asks you for your password, refuse and tell the Mirrowfen security
lead. If a colleague needs access to a system, they ask for their own account; they never use
yours.

Do not write passwords down, and do not keep them in email, chat messages or notes. Store work
passwords only in the approved password manager. Do not reuse a Mirrowfen password for any other
account, work or personal.

## 6 Help

For help with passwords or sign-in problems, contact Mirrowfen IT Support.

Mirrowfen IT Support: itsupport@mirrowfen.example.org, +1-202-555-0175.

## 7 Document control

- **Owner:** Mirrowfen security lead
- **Approver:** Head of Mirrowfen
- **Version:** 1.0
- **Effective date:** 2025-06-01

Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.
