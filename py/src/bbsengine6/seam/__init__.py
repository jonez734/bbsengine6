"""The seam: the contract between a domain (back end) and any front end.

Spec: handbook/specs/front-end-seam.md. Modules:

- ``codes``: the one result-code vocabulary.
- ``results``: ActionResult, what a request returns.
- ``kinds``: the per-domain registry of event kinds.
- ``events``: Event, the bounded log, and per-front-end subscriptions.
- ``requests``: the typed request a front end sends.
- ``domain``: Domain, which ties the above together.
- ``wire``: the JSON form of the types.

A consumer imports these. It does not redefine them. Nothing in this package imports the terminal
layer (``io``) at module level.
"""
