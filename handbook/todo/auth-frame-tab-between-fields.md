# auth frame — Tab and Shift-Tab between fields

The sign-in frame grows a password box under the moniker when Enter is pressed (`bed/src/bed/tools/presentation.py`,
`prompt_credentials`, using bbsengine6 `extend_frame`). Enter is the only way to move between the two fields today.

For forms in general (any number of fields in one frame), see `form-tab-and-shift-tab.md`.

Tab and Shift-Tab are deliberately left for later. Adding them changes how `inputstring` hands a field back to the
caller, so it is a separate change from the frame growing.

## Open

- [ ] Let Tab move from the moniker field to the password field without accepting the moniker
- [ ] Let Shift-Tab move back from the password field to the moniker field, keeping what was typed
- [ ] Decide what Tab does on the password field (wrap to moniker, or do nothing)
- [ ] Confirm the join line stays continuous when focus moves between the boxes
