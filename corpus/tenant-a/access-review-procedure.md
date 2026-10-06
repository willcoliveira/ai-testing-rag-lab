---
id: A-REV
title: Access Review Procedure
version: "1.0"
tenant: tenant-a
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-09-01
status: current
format: md
---

# Access Review Procedure

## 1 Purpose and scope

This procedure sets out how Halvenroot confirms, at regular intervals, that every account still
needs the access it holds. Access that nobody can justify widens what an attacker can reach with a
stolen credential.

The procedure applies to every account in the Halvenroot directory and to the access those
accounts hold in Halvenroot systems: standard user accounts, privileged accounts and service
accounts. Granting and removing access for joiners, movers and leavers is covered by the Account
Lifecycle Policy (Joiners, Movers and Leavers); this procedure is the periodic check on top of it.

## 2 Roles

**Resource owner.** Owns a system, application or data set, and confirms that each account with
access to it still needs that access, at the right level.

**Line manager.** Confirms that each member of their team still needs the access listed for them,
given the work they do today.

**IAM team.** Runs the review: builds the lists of accounts and access, sends them to reviewers,
follows up on open reviews, removes access that is not confirmed and keeps the review records.

**Internal Audit.** Checks independently that reviews take place as section 3 requires, that
reviewers act on what they find and that the records in section 5 are complete. Internal Audit
reports its findings to the CISO.

## 3 Review frequency

### 3.1 Standard user accounts

Access for standard user accounts is reviewed every 6 months. The line manager reviews the access
of their team; resource owners review access to the resources they own.

### 3.2 Privileged accounts

Privileged accounts are reviewed every 30 days. Privileged accounts are defined in the Halvenroot
Security Glossary, section 10. The resource owner reviews each privileged account for their
resource.

### 3.3 Service accounts

Service accounts are reviewed every 12 months. The resource owner confirms that the service
account is still in use, still needs its permissions and still has a named owner. A service
account that is also a privileged account is reviewed under section 3.2.

## 4 How a review runs

### 4.1 Review lists

The IAM team sends each reviewer, through the identity portal, the list of accounts and access
they must confirm, showing for each account its type, its groups and roles and the resources it
can reach. The reviewer confirms each item or marks it for removal. A reviewer who is not the
right person for an item tells the IAM team, which reassigns it.

### 4.2 Deadline

Reviewers complete each review within 10 business days. The IAM team reminds reviewers who still
have open items and tells their line manager.

### 4.3 Unconfirmed access

Access that a reviewer does not confirm by the deadline is removed. The IAM team removes it, with
any access marked for removal, and records each removal. Access that is needed again is requested
and approved like any new access.

A reviewer who finds an account they do not recognise, or access that looks misused, reports it to
the Security Operations Centre at once and does not wait for the review to close.

## 5 Evidence

### 5.1 Review records

Review records are kept for 3 years. A review record shows the list sent to each reviewer, each
decision and who made it, the access removed under section 4.3 and the date the review closed.
The IAM team keeps the records and makes them available to Internal Audit on request.

## 6 Exceptions

A resource owner who cannot follow this procedure for a particular account or system requests an
exception through the Policy Exceptions Process. Until an exception is approved, this procedure
applies in full.

## 7 Document control

- Owner: IAM team
- Approver: CISO
- Version: 1.0
- Effective date: 2025-09-01
