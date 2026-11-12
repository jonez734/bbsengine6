"""The UI seam: the types game code returns and emits (handbook/specs/ui-seam.md).

``codes`` holds the one code vocabulary (section 4), ``results`` the ActionResult (section 3), and
``events`` the Event and its queue (section 5). A consuming application imports these; it does not
redefine them.
"""
