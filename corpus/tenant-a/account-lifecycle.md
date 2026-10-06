---
id: A-LIFE
title: Account Lifecycle Policy (Joiners, Movers and Leavers)
version: "1.1"
tenant: tenant-a
kind: company
source: comply:access.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/access.md (Apache-2.0, commit aab4849); rewritten for the fictional company Halvenroot, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2025-09-01
status: current
format: md
---

# Account Lifecycle Policy (Joiners, Movers and Leavers)

## 1 Purpose and scope

This policy sets out how Halvenroot creates, changes, disables and deletes user accounts when
people join, move to a new role and leave, in a way that keeps the risk of information loss or
exposure low.

It applies to every Halvenroot system that holds a user account, and to all full-time and
part-time employees and contractors. Administrator accounts must also meet the Privileged Access
Standard. Business day, joiner, mover and leaver are defined in the Halvenroot Security Glossary.

## 2 Background (least privilege)

To limit the risk of information loss or exposure, from inside or outside the company, Halvenroot
relies on the principle of least privilege. Accounts and permissions are granted only for the
resources a person needs to perform their job duties. When someone's role changes, their access
is changed or removed to fit the new role; when they leave, their accounts are disabled and later
deleted.

The IAM team runs the processes in this policy. HR, line managers and resource owners provide the
information and approvals it acts on.

## 3 Joiners

### 3.1 Notification

The line manager tells HR about a new joiner, and HR notifies the IAM team at least 5 business days before the start date.

HR's notification gives the joiner's role, team, line manager and start date, and says whether
the joiner is an employee or a contractor. The IAM team prepares a checklist of the accounts and
permission levels the role needs.

### 3.2 Account creation

Accounts are created no earlier than 3 business days before the start date.

If a start date moves, HR tells the IAM team, which adjusts the creation date to match.

### 3.3 MFA registration

New joiners must register at least two MFA factors before the end of their first working day.

The approved factors are set out in the Multi-Factor Authentication Standard.

### 3.4 Resource owner approval

The owner of each resource reviews and approves every new account on that resource and the
permissions that come with it. No account is created and no permission is granted without that
approval. The IAM team then works with each resource owner to set up the joiner.

## 4 Movers

When someone changes role, team or line manager within Halvenroot, the line manager or HR tells
the IAM team about the move and gives the move date.

### 4.1 Removing access the new role does not need

Access that the new role does not need is removed within 5 business days of the move date.

People do not keep access from an earlier role "just in case". Old access needed for a handover
is requested again and approved as set out in section 3.4.

### 4.2 Confirming the access the new role needs

The new line manager confirms to the IAM team which accounts and permissions the new role needs.
The IAM team grants new access only after this confirmation and the approval of each resource
owner, following the same steps as for a joiner.

## 5 Leavers

HR tells the IAM team about every leaver as soon as the leaving date is known, and again
straight away if the leaver's last working day changes.

### 5.1 Employees

Employee accounts are disabled at the end of the employee's last working day. If an employee leaves with immediate effect, the account is disabled within 2 hours of HR's leaver notification.

### 5.2 Contractors

Contractor accounts are disabled at 17:00 local time on the contractor's last working day.

The sponsoring manager tells HR when a contract ends early, so that the IAM team can bring the
date forward.

### 5.3 Deletion

Disabled accounts are deleted 30 days after they are disabled.

Before deletion, the line manager arranges with the IAM team the transfer of any business data
that Halvenroot needs to keep.

### 5.4 Factors and certificates

For the revocation of MFA factors, see the MFA Standard, section 6. For VPN certificates, see the Remote Access Policy, section 4.4.

Leavers return Halvenroot devices and security keys to their line manager or the IT Service Desk
on or before their last working day.

## 6 Inactive accounts

This section applies to the user accounts of employees and contractors. Service accounts and
break-glass accounts follow the Privileged Access Standard.

### 6.1 Automatic disabling

Accounts with no sign-in for 45 days are disabled automatically.

To have an account enabled again, the line manager asks the IAM team, which confirms that the
person still needs it before re-enabling it.

## 7 Contractors

### 7.1 End dates

Every contractor account has an end date no more than 6 months after it is created. Extending it needs the sponsoring manager's approval.

The sponsoring manager sends any extension request to the IAM team before the end date.

## 8 Access reviews

Access is reviewed under the Access Review Procedure.

## 9 Document control

- Owner: IAM team lead
- Approver: Chief Information Security Officer (CISO)
- Version: 1.1
- Effective date: 2025-09-01

Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.
