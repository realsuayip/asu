Feature Rundown
===============

Here is a summary of major features.

Authentication & Account Management
-----------------------------------
* OAuth 2.0 (Authorization Code with PKCE & Client Credentials)
* Two-factor authentication
* CRUD operations
* Blocking operations
* Following operations

  * Follow requests
  * Ability to mark profile as 'private'

* Profile pictures

  * Thumbnail generation
  * Image validation

    * Image scaling & compression on upload
    * Mime type validation

Verification
------------
All flows employ email confirmation.

* Registration flow

  * No account generation before email validation.
* Password reset flow
* Email change flow

Messaging
---------
* CRUD operations
* One-to-one conversations & messaging
* Message requests
* Read receipts
* Ability to disable messages from strangers
* Instant messaging with WebSocket

  *  Ticket-based authentication
