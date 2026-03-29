# bottombar

- there is currently a io.screen.setbottombar() function, which accepts a
  'left', 'right', and **kwargs

- left and right are either strings or callables (in any combination)

- especially for listbox, I need a way to make the left or right side a
  list. I need to be able to append, prepend, or replace to the list.

- for example, in empyre, I might have a listbox with player names. one of
  the onkeys is 'INS' for adding a new player. I need "INS: New Player" to appear in the bottom bar
  without listing all of the other options every time.

- so the listbox should be modified such that the onkey table updates the
  bottombar with only the keys that are valid. if INS is not in the onkey
table, don't show it as an option. 

- if I have an onkey like 'e' (edit player), it should appear in the
  bottombar next to INS, but only if that option is available (sysop only)

- also in empyre, there is the player's moniker and the number of coins they
  have flush to the right. this should be preserved somehow.

- this should work for the left and right.
  * str: use it plain
  * list: step through each item with " | " in between. 
  * callable: call returns string

- also there needs to be room for "KEY_F2" when there are unread
  notifications
