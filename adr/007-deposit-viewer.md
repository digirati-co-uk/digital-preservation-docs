# Deposit Viewer DRAFT

This document describes the Deposit Viewer setup of Digital presentation.

## Background 

This will allow deposits to be shared in read only mode with strict scope of a single deposit. That is a deposit will be shared on an individual basis to a single external user/email address.

## Definitions

The current Auth flow will remain unaffected by this development and current Azure Application integrations will continue.

* **Deposit:**  A url collection as per site location \deposits\xxxxxx\?
* **Deposit User:**  User who can created alter deposits.
* **Deposit Viewer:** External user who can view a single deposit, but cannot create, update or delete deposit objects/
* **external user:** User external to the application authentication setting, this could still be in the organization scope.

## MFA verification (optional)

It may be prudent to send a real time access code to the Deposit Viewer as verification step prior to access of each session. 

This can be an emailed code which is entered at start of a session. This will require email sending functionality to be available to the application. 

## Basic workflow

A user will share a link to an external Deposit user who when accessing the link on the site will be asked for a code.  Code verifies the link is access by the intended user. The Deposit user will be presented to a single deposit viewer page and not other navigation will work. 

### Link Creation 
* Deposit User will create a unique shareable link from the Deposit location they wish to share.
* Link will be tied to a target email address.
* Link has a default start (now) and expiry date time.
* Link has a target to a single deposit


## Deposit Viewing

* Deposit viewer will receive or be given the link.
* On session start a verification code will be sent via email.
* User will be asked to submit access code
* User will be taken to view Deposit page



## Link Management

* Who can see shares (inc external email addresses) ?
* Who can revoke shares ?
* Who Access logs and what is logged ?
* Can share expiry be extended ?






