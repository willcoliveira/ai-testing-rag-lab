---
id: A-DEVICE
title: Device Policy
version: "1.2"
tenant: tenant-a
kind: company
source: comply:workstation.md
licence: Apache-2.0
changed: "Adapted from strongdm/comply themes/comply-soc2/policies/workstation.md (Apache-2.0, commit aab4849); rewritten for the fictional company Halvenroot, values replaced with planted values, sections renumbered. Changed by the ai-testing-rag-lab authors, 2026-10-06."
effective: 2025-11-03
status: current
format: md
---

# Device Policy

## 1 Purpose and scope

This policy sets the controls that reduce the risk of Halvenroot data being lost or exposed through
the devices people use to do their work.

The policy applies to all Halvenroot employees and contractors, and to every device that holds or
accesses Halvenroot data, wherever it is used.

## 2 Definitions

A workstation is any company-owned or personal device that holds company data, taken together as
the collection of all such devices. In this policy, "device" means a workstation of any kind:
laptops, desktops, mobile phones and tablets. Shared kiosk devices are covered in section 7.

Halvenroot device management is the service IT uses to enrol devices, apply settings and check
compliance with this policy.

## 3 Requirements for all devices

Every device covered by this policy must meet the requirements in this section. Devices that do not
meet them lose access to Halvenroot systems until the user or IT corrects the fault.

### 3.1 Operating system

The operating system must be no more than one major version behind the current release. Users
install operating system updates when device management prompts them to.

### 3.2 Encryption

Devices must be encrypted at rest. Device management checks encryption at enrolment and continues
to check it while the device is in use.

### 3.3 Screen lock

Screens must lock after 10 minutes of inactivity. Users also lock their screen whenever they leave
the device unattended, even for a short time.

### 3.4 Lost or stolen devices

Lost or stolen devices must be reported to the IT Service Desk within 2 hours of discovering the loss.
Contact the IT Service Desk at servicedesk@halvenroot.example.com or +1-202-555-0142. Report the
loss even if you expect to find the device again.

### 3.5 Use and endpoint protection

Devices are used for authorised Halvenroot business purposes only. Every laptop and desktop runs
the endpoint protection software approved by IT, kept up to date, and users must not disable or
remove it.

## 4 Laptops and desktops

Employees are issued a company laptop or desktop. Contractors may use their own laptop only if it is enrolled in Halvenroot device management.

The type of device an employee receives depends on their job duties and is agreed with their line
manager. IT enrols every company laptop and desktop in Halvenroot device management before it is
handed over.

Laptops and desktops run macOS or Windows.

## 5 Mobile devices

Mobile devices run iOS or Android and are enrolled in Halvenroot device management. Company data is accessed on them only through the managed email and chat apps.

Users must not copy company data from the managed apps into personal apps, personal storage or
personal accounts. If a mobile device is lost or stolen, section 3.4 applies.

## 6 Removable media

Removable media can carry company data outside the controls in this policy and can bring malicious
software onto a device.

### 6.1 USB storage devices

USB storage devices are blocked on Halvenroot devices. Device management enforces the block, and
users must not try to work around it.

### 6.2 Exceptions

Exceptions follow the Policy Exceptions Process. An exception applies only while it is approved and
in date; when it ends, the block in section 6.1 applies again.

## 7 Shared kiosk devices

Shared kiosk devices are the terminals on the warehouse floor that several workers use during a
shift to view orders and operate warehouse systems. Because they are shared, they have their own
rules.

### 7.1 Kiosk rules

Shared kiosk devices on the warehouse floor follow Annex B of this policy, a signed memo kept as a scanned page.

## 8 Document control

- Owner: IT Operations Manager
- Approver: CISO
- Version: 1.2
- Effective date: 2025-11-03

Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors.
