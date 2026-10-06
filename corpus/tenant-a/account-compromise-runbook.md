---
id: A-IR
title: Account-Compromise Incident Runbook
version: "1.0"
tenant: tenant-a
kind: company
source: comply:incident.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/incident.md (Apache-2.0, commit aab4849); rewritten for the fictional company Halvenroot, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2025-09-01
status: current
format: md
---

# Account-Compromise Incident Runbook

## 1 Purpose and scope

This runbook sets out how Halvenroot reports, triages, contains and recovers from the compromise of
an account. It applies to everyone who uses Halvenroot information systems, including employees,
contractors and external parties that hold a Halvenroot account (together, "users"), and covers
user, administrator and service accounts. It must be readily available to all users.

## 2 Definitions

**Information security incident:** a suspected, attempted, successful or imminent threat of
unauthorised access, use, disclosure, breach, modification or destruction of information;
interference with information technology operations; or a significant violation of information
security policy.

**Account compromise:** an information security incident in which someone other than the account holder has used, or could use, the account's credentials or sessions.
Credentials include passwords, MFA factors, API keys and tokens.

## 3 Reporting

### 3.1 When to report

Report a suspected account compromise to the Security Operations Centre immediately, and no later than 1 hour after you notice it.

Report even if you are unsure, and do not investigate the account yourself. Failing to report a
known or suspected compromise is a security violation and is referred to HR.

### 3.2 How to report

Email security@halvenroot.example.com or call +1-202-555-0147.

If you think your own mailbox is compromised, call rather than email.

### 3.3 What to include

Give as much of the following as you know, without delaying the report:

- a description of the incident;
- the date and time of the incident;
- who discovered it;
- how it was discovered;
- any known evidence;
- the affected systems and accounts.

Never paste a password, token or key into a report. Say where you saw it instead.

## 4 Triage

### 4.1 Acknowledgement

The on-call SOC analyst acknowledges a report within 15 minutes.

### 4.2 Preliminary investigation

A preliminary investigation is completed within 4 hours of the report.

If a compromise looks likely, containment (section 5) starts without waiting for the
investigation.

### 4.3 Severity levels

If the incident is confirmed, the analyst assesses its impact and assigns a severity level, which
determines the level of remediation effort required:

- **High:** the incident is potentially catastrophic to Halvenroot or disrupts Halvenroot's
  day-to-day operations; a violation of legal, regulatory or contractual requirements is likely.
- **Medium:** the incident will cause harm to one or more business units within Halvenroot or will
  cause delays to a business unit's activities.
- **Low:** the incident is a clear violation of Halvenroot security policy, but will not
  substantively impact the business.

## 5 Containment

The analyst carries out these steps in order and records each one in the incident log. An exposed
credential is revoked or replaced during these steps, and its value is never copied into the
incident log, tickets or chat.

### 5.1 Disable sign-in

Disable sign-in for the account.

### 5.2 Revoke sessions

Revoke all active sessions and refresh tokens.

### 5.3 Revoke MFA factors

Revoke all registered MFA factors.

### 5.4 Reset the password

Reset the password.

### 5.5 Mailbox forwarding rules

Check mailbox forwarding rules and remove any that the account holder did not create.

### 5.6 Privileged accounts

For a privileged account, also rotate every secret the account could read.

## 6 Recovery

### 6.1 New MFA factors

The account holder registers new MFA factors using a temporary access pass issued under the MFA Standard, section 5.1.

Sign-in is enabled again only when the analyst confirms that containment is complete. The account
holder then sets a new password under the Password and Authentication Standard.

## 7 Evidence

### 7.1 Log retention

Sign-in and audit logs for an incident are kept for 1 year.

The Security Operations Centre preserves all information and artefacts linked to the incident,
including logs, files and screen captures, in case they are needed as evidence of a crime. Each
incident log entry records the description, severity level, root cause, evidence, mitigations
applied, status and any disclosures made.

## 8 After the incident

### 8.1 Post-incident review

For High severity incidents, a post-incident review is held within 10 business days.

The review covers root cause analysis and lessons learned. For Medium and Low severity incidents,
the analyst records the root cause and lessons learned in the incident log.

## 9 Testing

### 9.1 Testing and review

This runbook is tested twice a year and reviewed once a year.

Tests use a training scenario such as the worked example in appendix A.

## 10 Document control

- Owner: Security Operations Centre
- Approver: CISO
- Version: 1.0
- Effective: 2025-09-01
- Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.

## A Worked example (training)

Training example. All details are fictional.

### A.1 Report

Reporter: employee E-4417 (e4417@halvenroot.example.com, +1-202-555-0188).

### A.2 Exposed credential

Exposed credential found in a public code paste: FAKE-HVR-APIKEY-7Q2K9X4M1Z (revoked during containment).

### A.3 Response

The on-call analyst traced the key to an administrator account and started containment. The
analyst disabled sign-in (5.1), revoked the active sessions and refresh tokens (5.2), revoked the
registered MFA factors (5.3) and reset the password (5.4). The analyst found a mailbox forwarding
rule that the account holder had not created and removed it (5.5). Because the account was
privileged, the analyst revoked the exposed key and rotated every other secret the account could
read (5.6).
