# forms — Tab and Shift-Tab move between fields

A form is one frame holding several fields (`draw_frame(height=N)`, `place_row`, `after_field`; see `specs/util.md`,
Frames), and later one labelled child box per field. Today Enter is the only way to leave a field, and the caller reads
each field in order. Tab and Shift-Tab should move forward and back between the fields of a form.

The sign-in is the first form. Its specific case (the moniker and password fields) is in
`auth-frame-tab-between-fields.md`; this note covers forms in general.

## Open

- [ ] Let Tab leave the current field and move to the next field of the form, without accepting the field's value
- [ ] Let Shift-Tab move to the previous field, keeping what was typed in each field
- [ ] Decide what Tab does on the last field (wrap to the first, or do nothing), and what Shift-Tab does on the first
- [ ] Decide how a field hands control back to the caller: `inputstring` returns on Enter today, so Tab needs a return
      value that says "next" or "previous" as well as the text
- [ ] Decide whether Tab in a masked field (`inputpassword`, `mask=""`) moves without showing anything
- [ ] Keep the cursor rule: after a field is left, the cursor is placed by `place_row` from the frame's own rows, with no
      terminal query
- [ ] Check the form at 24x80 from the top line, reply path, after each Tab and Shift-Tab
