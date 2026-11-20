# demo_authenticate

**use acs characters**

## step 1

+----] zoid6 auth: casino [---------+
| moniker:                          |
*-----------------------------------+
^ cursor after pressing enter

## step 2 - password box joined with moniker box. difference is use of {rtee} and {ltee) instead of corners.

+----] casino auth [----------------+
| moniker:  jam                     |
+------------------------------------
| password:                         |
+-----------------------------------+

moniker=jam
password=[redacted]

# auth without joined boxes

+----] zoid6 auth: casino [---------+
| moniker:                          |
+------------------------------------

+----] zoid6 auth: casino jam [-----+
| password:                         |
+------------------------------------

- new user form (moved to separate todo file)

this is the current layout (one frame, two rows; from the pty, top line):

┌─┤ zoid6 auth ├──────────┐
│moniker: zoid            │
│password:                │
└─────────────────────────┘

the moniker is read on the first row; its Enter leaves the cursor one row below it (after_field), so the password row is
reached with a relative move (place_row). no box or label surrounds each field.

this is what it should look like (the target, with a box per field):

┌─┤ moniker ├─────────────┐
│ moniker: jam            │
├─────────────────────────┤
│ password:               │
└----------───────────────┘

- focus on making sure the 'password' prompt is positioned correctly. 


- the password child has the topborder twice, one with the {rtee} and one
  with corners.

- it should be this if we are doing nested children:

+-] zoid6 auth [────────---+
|                          |
| +─┤ moniker ├──────────+ |
│ | moniker: jam         | │
| +──────────────────────+ |
| | password:            | |
| +----------------------+ |
|                          |
+--------------------------+
