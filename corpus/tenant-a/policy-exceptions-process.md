---
id: A-EXC
title: Policy Exceptions Process
version: "1.0"
tenant: tenant-a
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-09-01
status: current
format: md
---

# Policy Exceptions Process

## 1 Purpose and scope

This process sets out how an exception to a Halvenroot identity or security rule is requested,
approved, recorded and ended, so that every departure from a rule is deliberate, visible and
limited in time.

It applies to every policy and standard in the Halvenroot identity and security pack, and to
everyone with a Halvenroot account.

An exception is a written, approved permission to depart from a named rule, for named people or
systems, until a stated end date. A rule that is broken without one is a breach, not an exception.

## 2 What cannot be excepted

Requests to depart from the rules below are rejected without review.

### 2.1 Administrator MFA

No exception can remove MFA from an administrator account. Break-glass accounts are governed by the Privileged Access Standard, not by this process.

An administrator who has lost a factor follows section 5 of the Multi-Factor Authentication
Standard instead.

### 2.2 Shared passwords

No exception allows a password to be shared.

Where several people work on the same system, each person is given their own account.

## 3 Requesting an exception

### 3.1 Submitting a request

Submit a Security Exception Request in the IT portal, stating the rule, the reason, the compensating controls and the end date.

The request also names the people or systems it covers and exactly what they will be allowed to
do. Compensating controls reduce the extra risk, for example Halvenroot-managed devices only, or
monitoring by the Security Operations Centre (SOC).

No one may switch off or work around a control themselves; the rule applies while a request is
considered.

### 3.2 Approval

The line manager, the resource owner and the CISO must all approve the request.

The line manager confirms the business need, the resource owner accepts the remaining risk, and
the CISO decides whether the compensating controls are sufficient. One rejection closes the
request.

### 3.3 Recording

The Security Operations Centre records every approved exception in the register in section 5.

An exception that is not in the register gives no permission.

## 4 Duration

### 4.1 Maximum length

An approved exception is valid for at most 12 months from approval. It ends on its end date unless it is renewed through a new request.

A renewal needs the same approvals as a first request, so submit it well before the end date.

### 4.2 Expiry

An expired exception gives no permission; the original rule applies again.

After the end date, the SOC sets the entry's status to Expired and keeps it as a record.

## 5 Exceptions register

### 5.1 Register entries

Table 1 lists the exceptions recorded in the register.

Table 1: Exceptions register

| Id | Rule excepted | Who it covers | What is allowed | Compensating controls | Approved | End date | Status |
|---|---|---|---|---|---|---|---|
| EX-2026-007 | Remote Access Policy, section 4.5 (VPN idle timeout) | Network Operations on-call rota | VPN sessions disconnect after 4 hours of inactivity | Halvenroot-managed on-call laptops only; the SOC monitors these VPN sessions | 2026-02-01 | 2027-01-31 | Approved |
| EX-2025-003 | Device Policy, section 6.1 (USB storage blocked) | Finance team | Encrypted USB drives for the auditor handover | Drives issued and logged by IT | 2025-04-01 | 2026-03-31 | Expired |

The Status column shows Approved while an exception is in force and Expired once its end date has
passed. Only the people and the permission named in an entry are covered by it.

### 5.2 Effect of the register

Exception EX-2026-007 allows the Network Operations on-call rota to keep VPN sessions open for up to 4 hours of inactivity, instead of 60 minutes, until 2027-01-31.

Everyone outside the rota remains subject to section 4.5 of the Remote Access Policy, and the rota
itself may rely on the exception only from Halvenroot-managed on-call laptops.

## 6 Document control

Owner: Security Operations Centre. Approver: CISO. Version: 1.0. Effective date: 2025-09-01.
