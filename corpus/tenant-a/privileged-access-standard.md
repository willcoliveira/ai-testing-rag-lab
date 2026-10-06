---
id: A-PRIV
title: Privileged Access Standard
version: "1.0"
tenant: tenant-a
kind: company
source: ours
licence: CC-BY-4.0
effective: 2025-09-01
status: current
format: md
---

# Privileged Access Standard

## 1 Purpose and scope

This standard sets out how Halvenroot grants, protects, uses and reviews privileged access to its systems, networks and data. Privileged access is a prime target for attackers, so the controls below keep it separate, short-lived, strongly authenticated and visible to the Security Operations Centre.

This standard applies to every privileged account, as defined in the Halvenroot Security Glossary.

It covers employees, contractors and automated workloads in every Halvenroot environment, including the warehouse robotics platforms.

## 2 Administrator accounts

### 2.1 Separate administrator accounts

Privileged work is done from a separate administrator account whose name starts with adm-, never from a person's everyday account.

The administrator account is used only for privileged work: it has no mailbox and is not used to browse the internet. Each administrator account belongs to a named account holder, who is accountable for everything done with it, and administrator accounts are never shared. The IAM team creates an administrator account only on a request approved by the requester's line manager and the resource owner of the systems concerned.

## 3 Just-in-time elevation

### 3.1 Time-limited roles

Privileged roles are activated on request and expire after at most 4 hours.

An administrator account holds no standing privileged role. To do privileged work, the account holder requests the role they need in the identity portal and states the reason, such as a change ticket or an incident reference. The role is removed automatically when it expires; if the work is not finished, the account holder makes a new request. Every activation is logged and sent to the Security Operations Centre.

## 4 Authentication

### 4.1 MFA and lockout

Administrator accounts use MFA as set out in section 4 of the MFA Standard. Lockout values for privileged accounts are in Table 1 of the Password and Authentication Standard.

This standard does not repeat those values.

## 5 Administrator devices

### 5.1 Managed devices only

Privileged access is allowed only from Halvenroot-managed devices.

A personal device may not be used for privileged work, even where it is otherwise allowed to reach Halvenroot services. Administrative consoles reject sign-ins from devices that Halvenroot device management does not recognise as Halvenroot-managed.

## 6 Break-glass accounts

Break-glass accounts are emergency administrator accounts that keep the identity platform manageable when the normal sign-in route is unavailable. Because they sign in without MFA, they are protected by the controls in this section instead.

### 6.1 Number of accounts

Halvenroot keeps exactly 2 break-glass accounts.

Break-glass accounts are not assigned to any person and are never used for day-to-day administration.

### 6.2 Storing the passwords

Each break-glass password is 30 characters long and is kept in two sealed envelopes, each holding one half, in the safe in the CISO's office.

Each password is generated at random and is not stored anywhere else, including the approved password manager and the secrets vault. Every opening of an envelope is recorded in the safe log.

### 6.3 When a break-glass account may be used

A break-glass account may be used only while an outage of the MFA or SSO service has been declared. Every use raises an alert to the Security Operations Centre, and the password is changed within 24 hours after each use.

The person who uses the account records the reason, the time and the actions taken, and the Security Operations Centre reviews that record once the outage is over. After the password is changed, new sealed envelopes are placed in the safe.

### 6.4 Testing

Break-glass accounts are tested every 3 months.

The IAM team runs each test with the Security Operations Centre. The test checks that the envelopes are sealed and complete, that each account still exists and holds its expected role, and that alerting to the Security Operations Centre is in place.

## 7 Service accounts

Service accounts are used by applications, scripts and robotics controllers to call other systems.

### 7.1 No interactive sign-in

Service accounts cannot sign in interactively.

Each service account has a named owner, who is accountable for it, and holds only the permissions its workload needs.

### 7.2 Secrets

Service account secrets are kept in the secrets vault and rotated every 180 days.

Secrets are never written into source code, configuration files, tickets or chat messages. A secret is also rotated whenever it may have been exposed.

## 8 Reviews

### 8.1 Review frequency

Privileged accounts are reviewed at the frequency set in section 3.2 of the Access Review Procedure.

In each review, the resource owner confirms that every administrator account holder still needs each role they can activate. Roles that are not confirmed are removed, as the Access Review Procedure describes.

## 9 Exceptions

No exception can remove MFA from an administrator account; see the Policy Exceptions Process, section 2.

Other exceptions to this standard are requested, approved and recorded through the Policy Exceptions Process. The use of break-glass accounts is not an exception; it is governed by section 6 of this standard.

## 10 Document control

- Owner: IT Operations Manager
- Approver: CISO
- Version: 1.0
- Effective date: 2025-09-01
