---
id: A-GLOSS
title: Halvenroot Security Glossary
version: "1.0"
tenant: tenant-a
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-09-01
status: current
format: md
---

# Halvenroot Security Glossary

This glossary defines the terms used across the Halvenroot identity and security policies, so that
each term has one meaning wherever it appears.

## 1 Account holder

The person to whom a Halvenroot account is issued. The account holder is responsible for
everything done with the account and keeps its password and MFA factors to themselves.

## 2 Administrator account

A separate account, named with the prefix adm-, used only for privileged work; see the Privileged
Access Standard, section 2.

## 3 Break-glass account

An emergency administrator account that works without MFA and is used only while an outage of the
MFA or SSO service has been declared.

## 4 Business day

A business day is Monday to Friday, excluding Halvenroot public holidays.

Compare working day (section 15).

## 5 Contractor

A person who works for Halvenroot under a contract for services rather than as an employee.
Every contractor has a sponsoring manager, and every contractor account has an end date; see the
Account Lifecycle Policy, section 7.

## 6 Exception

A written, approved permission to depart from a named rule, for named people, teams or systems,
until a stated end date. Exceptions are requested and approved through the Policy Exceptions
Process.

## 7 IAM team

The identity and access management team. It runs the identity portal and single sign-on,
creates, changes and disables accounts, and sends reviewers the lists they confirm under the Access
Review Procedure.

## 8 Joiner, mover, leaver

A joiner is a person starting work at Halvenroot. A mover is a person changing role or team. A
leaver is a person whose work for Halvenroot is ending. The Account Lifecycle Policy sets out how
accounts are created, changed and disabled at each of these events.

## 9 Phishing-resistant factor

FIDO2 security keys and passkeys.

The full list of approved factors is in the MFA Standard, section 3.1.

## 10 Privileged account

A privileged account is any account that can do at least one of the following: (a) change another account's access or credentials; (b) administer a production system, a network device or the identity platform; (c) read Confidential data in bulk. A service account with any of these rights is also a privileged account.

Every privileged account is governed by the Privileged Access Standard.

## 11 Resource owner

The person accountable for a system or a set of data. The resource owner approves who may have
access to it, confirms that access during access reviews, and accepts the remaining risk when an
exception is approved for it.

## 12 Security Operations Centre (SOC)

The team that monitors Halvenroot systems for security events, receives reports of suspected
compromise, leads the response under the Account-Compromise Incident Runbook, and keeps the
register of approved exceptions.

## 13 Service account

An account used by an application, script or automated process rather than by a person. Service
accounts cannot sign in interactively, and their secrets are kept in the secrets vault; see the
Privileged Access Standard, section 7.

## 14 Temporary access pass

A time-limited pass issued by the IT Service Desk after an identity check, used once to register a
new MFA factor; see the MFA Standard, section 5.1.

## 15 Working day

A day on which the person is scheduled to work.

It follows the person's own work pattern, so it can differ from a business day.

## 16 Document control

- Owner: IT Operations Manager
- Approver: CISO
- Version: 1.0
- Effective date: 2025-09-01
