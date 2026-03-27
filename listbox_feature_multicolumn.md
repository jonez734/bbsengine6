# listbox feature: multi-column

- build on bbsengine6/py/src/bbsengine6/listbox.py
- modify such that it has the ability to display more than one column of items, a number which is specified in the constructor
- column count of at least one
- some way to specify "as many columns as will fit" (optional)
- clean, robust, thread safe code which must not break BC
- column width is calculated as the max rendered_length() of that column plus at least one
- if there is only one column, each item should fill the entire row like it does now.

- if there are two or more columns:
  * KEY_DOWN to the bottom of a column, current item becomes item 0 of next
    column on the next key_down.
  * when current item is on last item on last column, do go to first item of
    next page, {{bel}} if not available.
  * if there is a column to the right, KEY_RIGHT moves to it. keep the row
    the same.
  * if there is a column to the left, KEY_LEFT moves to it, wrap around
  * if there is not a collumn to the right, wrap around
  * KEY_END goes to last item of current column
  * KEY_HOME goes to first item of current column
