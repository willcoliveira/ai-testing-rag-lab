---
id: A-CLASS
title: Data Classification Policy
version: "1.1"
tenant: tenant-a
kind: company
source: comply:classification.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/classification.md (Apache-2.0, commit aab4849); rewritten for the fictional company Halvenroot, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2025-09-01
status: current
format: md
---

# Data Classification Policy

## 1 Purpose and scope

This policy makes sure information at Halvenroot is protected at an appropriate level. It covers all information in Halvenroot's information security programme, whatever its form, and applies to every employee, contractor and system with access to information held by Halvenroot.

## 2 Background

This policy defines Halvenroot's data classification scheme: the confidentiality levels and how information is classified, labelled and handled. Halvenroot's confidentiality and non-disclosure agreements must reference this policy.

## 3 Classification

### 3.1 Information received from outside

The person who receives classified information from outside Halvenroot must classify it under this policy and becomes its owner.

Customer data handled as part of a Halvenroot service is classified, and given an owner, as the customer agreement and the law require.

### 3.2 Setting the level

The confidentiality level is set by the value of the information to Halvenroot, its sensitivity and criticality, and the legal, regulatory and contractual obligations that apply to it. Information is classified using the levels in Table 1.

Table 1: Information confidentiality levels

| Level | Label | Classification criteria | Access restrictions |
|---|---|---|---|
| Public | For Public Release | Making the information public will not harm Halvenroot in any way. | Available to the public. |
| Internal Use | Internal Use | Unauthorised access may cause minor damage or inconvenience to Halvenroot. | Available to all employees and authorised third parties. |
| Restricted | Restricted | Unauthorised access may cause considerable damage to the business or to Halvenroot's reputation. | Available to a specific group of employees and authorised third parties. |
| Confidential | Confidential | Unauthorised access may cause catastrophic damage to the business or to Halvenroot's reputation. | Available only to named individuals in Halvenroot. |

### 3.3 Lowest adequate level

Information owners use the lowest confidentiality level that still protects the information adequately.

### 3.4 Authorised persons

Restricted and Confidential information must have a list of authorised persons, kept by the information owner, naming the people or job functions allowed to access it. Internal Use information needs such a list only when people outside Halvenroot will access it.

### 3.5 Review

Information owners review the confidentiality level of their information every 2 years. Wherever possible, the level is lowered.

## 4 Labelling

### 4.1 Documents

Electronic documents show their confidentiality level at the top and bottom of each page. Applications and databases show the level on the sign-in screen and on every screen that displays the information. Unlabelled information is treated as Internal Use.

### 4.2 Email

Email shows the confidentiality level in the first line of the message body. The default in section 4.1 applies.

### 4.3 Storage media

Disks, memory cards and other electronic storage media show the confidentiality level on their top surface; the default in section 4.1 applies to media without a label. Removable storage may be used only where the Device Policy allows it (section 6.1 of the Device Policy).

## 5 Handling

Everyone who accesses classified information follows the rules in Appendix A, "Handling of classified information".

## 6 Incidents

Report improper handling of classified information to the Security Operations Centre.

## 7 Document control

- Owner: Chief Information Security Officer (CISO)
- Approver: Chief Executive Officer
- Version: 1.1
- Effective date: 2025-09-01

Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.

## A Handling of classified information

Controls are cumulative: each level's controls also apply to higher levels, unless a higher level sets a stricter one.

### A.1 Electronic documents

Internal Use:

- Only authorised persons may access the document.
- A document shared through an unencrypted file sharing service must be password protected.
- The system where the document is stored follows section A.2.

Restricted:

- Only persons authorised for the document may access the part of the system where it is stored.
- A document shared through any file sharing service must be encrypted.
- Only the document owner may erase the document.

Confidential:

- The document is stored encrypted, only on servers that Halvenroot controls.
- The document is shared only through encrypted services and is itself encrypted when transferred.

### A.2 Information systems

Internal Use:

- Only authorised persons may have access.
- Access to the information system must be protected by a password that meets the Password and Authentication Standard.
- The screen must lock automatically after 10 minutes of inactivity.
- The information system is located only in rooms with controlled physical access.

Restricted:

- Users sign out whenever they leave the workplace.
- Data is erased only with a method that ensures secure deletion.

Confidential:

- Access to the information system must use MFA with a phishing-resistant factor (see the MFA Standard, section 3.1).
- The information system is installed only on servers that Halvenroot controls.
- Rooms that hold the information system also check the identity of everyone who enters.

### A.3 Email

Internal Use:

- Only authorised persons may have access.
- The sender checks every recipient before sending.
- The rules for Internal Use in section A.2 apply.

Restricted:

- Email sent outside Halvenroot must be encrypted.

Confidential:

- All email must be encrypted, inside and outside Halvenroot.
