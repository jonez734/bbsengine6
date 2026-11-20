# new user form — moniker, password, email

A new-user form in one frame: the sign-in frame (`draw_frame`, `extend_frame`, `place_child`) grows an email box under
the password box. The sign-in itself stays a two-box flow (moniker, password). Sketch: `py/src/demo_authenticate.md`.

## Layout

```
+----] zoid6 new user [-------------+
| moniker:  jam                     |
+------------------------------------
| password: [redacted]              |
+------------------------------------
| email:                            |
+-----------------------------------+
```

## Decided

- The title is `zoid6 auth` for sign-in and `zoid6 new user` for the form.
- After Enter at the password prompt, the password row shows `password: [redacted]`. It shows even when nothing was
  typed, so the field does not reveal whether anything was entered. The label is written after input ends, not while
  typing; the typing rule (`mask=""`, nothing displayed, cursor at the field start) is unchanged.
- The label is a constant, so it does not reveal the password length.

## Open

- [ ] Decide whether `[redacted]` belongs in the library (a redacted display for a finished password field) or stays in
      the caller. The demo does it with `place_child` and a label, with no change to `inputstring`.
- [ ] Decide whether the email field is required, and whether an empty email is accepted.
- [ ] Decide what Enter on the email field does (accept the form, or move to a confirm step).
- [ ] Confirm the frame grows by one child without the join line breaking at the bottom of a small terminal.
- [ ] Check the new-user form at 24x80 from the top line, reply path (the same check as the sign-in frame).
