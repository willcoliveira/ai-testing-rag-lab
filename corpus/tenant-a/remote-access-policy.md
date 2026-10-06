---
id: A-REMOTE
title: Remote Access Policy
version: "1.1"
tenant: tenant-a
kind: company
source: comply:remote.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/remote.md (Apache-2.0, commit aab4849); rewritten for the fictional company Halvenroot, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2025-09-01
status: current
format: md
---

# Remote Access Policy

## 1 Purpose and scope

This policy sets the requirements for connecting to Halvenroot systems and networks from remote hosts, including personally owned devices, so that the loss or exposure of Halvenroot data is kept to a minimum.

It applies to every user of Halvenroot information systems. This includes employees and contractors, and any external party that comes into contact with systems and information controlled by Halvenroot (together, "users"). The policy is published on the Halvenroot intranet so that every user can read it.

## 2 Background and definitions

Unauthorised remote use of Halvenroot resources can lead to the loss of confidential company data and intellectual property, including the software and robotics designs that Halvenroot builds for warehouse customers. It can also damage Halvenroot's public image and internal systems, and lead to fines or other financial liabilities. This policy is intended to reduce that exposure.

In this policy:

- **Mobile computing equipment** means portable computers, mobile phones, smartphones, memory cards and other mobile equipment used to store, process or transfer data.
- **Remote host** means an information system, node or network that is not under the direct control of Halvenroot.
- **Telework** means using mobile computing equipment and remote hosts to do work outside Halvenroot premises. Telework does not include the use of mobile phones.

## 3 General care in uncontrolled spaces

Users must take care when they place or use mobile computing equipment in uncontrolled spaces, such as vehicles, public spaces, hotel rooms, meeting places, conference centres and other unprotected areas outside Halvenroot premises. Equipment should not be left unattended in these places.

When a user connects to Halvenroot systems or works with Halvenroot data on a remote host or on mobile computing equipment, the user must make sure that information on the device, such as what is displayed on the screen, cannot be read by unauthorised people. In public spaces, users should sit where the screen cannot be overlooked, or move to a more private place before opening confidential material.

## 4 Security requirements for remote hosts

### 4.1 Security updates

Remote hosts must install security updates within 14 days of their release.

### 4.2 Endpoint protection

Remote hosts must have endpoint protection software, such as a malware scanner, installed and kept up to date at all times. Users must not disable or uninstall it.

### 4.3 VPN and MFA

Access to Halvenroot systems from outside the office network must go through the Halvenroot VPN, with MFA as set out in the MFA Standard.

The VPN connection is encrypted and authenticated. Every user who needs remote access is given VPN credentials by the Halvenroot IT team; users must not share them or set up other routes into Halvenroot systems.

### 4.4 VPN client certificates

VPN client certificates are valid for 12 months and are revoked when the account is disabled.

The IT team issues a replacement certificate before the current one expires, so that users can keep working without interruption.

### 4.5 VPN session timeout

VPN sessions disconnect after 60 minutes of inactivity.

After a disconnection the user signs in to the VPN again, with MFA.

### 4.6 Full-disk encryption

Information stored on mobile computing equipment must be protected with full-disk encryption. Devices that cannot be encrypted must not hold Halvenroot data.

### 4.7 Backups

Users of mobile computing equipment outside Halvenroot premises are responsible for regular backups of the Halvenroot data held on the device. Backups go to Halvenroot-approved storage, never to personal storage.

## 5 Telework

Employees may telework only when their line manager has authorised it in writing.

Only the user to whom a device is assigned may use it for telework. Other people, such as those living or working where the telework takes place, must not use Halvenroot remote hosts or mobile computing equipment.

Devices used for telework must be authorised with certificates before they can connect to Halvenroot systems.

Users who telework are responsible for configuring the home or local network they use to connect to the internet, including its Wi-Fi security and keeping the router software up to date.

Users who telework must protect Halvenroot intellectual property, whether software or other material, that is present on remote hosts and mobile computing equipment.

## 6 Document control

- Owner: IT Operations Manager
- Approver: CISO
- Version: 1.1
- Effective date: 2025-09-01

Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.
