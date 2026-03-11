commit $(git rev-parse HEAD)
Author: opencode <opencode@anomaly.co>
Date:   $(date '+%a %b %d %H:%M:%S %Y %z')

    - bbsengine6/io/__init__.py: export getch from getch module
    - bbsengine6/io/io_getch.spec: updated to document export


Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 12 15:52:09 2023 -0500

    - bbsengine6/io/Makefile: added

commit eaca65a383796609ff258a38f9157107a2ed67f7
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 12 15:01:49 2023 -0500

    - bbsengine6/listbox.py:
      * ttyio -> io
      * handle KEY_PAGEUP and KEY_PAGEDOWN

commit fd74e3bd28e62721331d9629d5c4ce4631210033
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 12 14:39:53 2023 -0500

    - testlistbox.py:
      * moved Article2PresidentListboxItem from bbsengine6.listbox
      * renamed setvariable() to setvar()
      * added a query to get the total number of items
      * renamed ttyio.echo to bbsengine6.io.echo
      * changed title of listbox test

commit 85e0b2bf5d5d7d7ad2389c4cbeec3fc48bdda8a0
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Dec 6 22:07:36 2023 -0500

    - bbsengine6/__init__.py: added 'io'

commit 47bc967cfce8d6996eace3dd2fdeb2bfea76372f
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Dec 6 22:03:06 2023 -0500

    - bbsengine6/io/: copied from ttyio6

commit ef4b76ab4d5d1e7074196506a1ffd56fb9e2e28c
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 5 20:28:35 2023 -0500

    - bbsengine6/www/: mass commit

commit c41a50acc50d9948bc9d363ff560242d43e91752
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 5 20:27:13 2023 -0500

    - bbsengine6/www/com/config-prod.php: added

commit 462d3d1b79c2637ede98978959c4b2d21ba60062
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 5 20:26:41 2023 -0500

    - bbsengine6/skin/: mass commit

commit b5bb2f425b9082c43ddf45bd01e9fda27ff34335
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 5 20:25:50 2023 -0500

    - bbsengine6/www/php/Markdown*.php removed

commit e7ab3eac6fd0dcb4ee808d9ff7762b8625993cd3
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Dec 5 17:12:31 2023 -0500

    - bbsengine.org: copied www/Makefile

commit a2bcbb3e6cf5f01a786fb3cc6021645dab7f576c
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Dec 3 20:33:59 2023 -0500

    - bbsengine6/input.py: fixed typo in getdate()

commit 93eb0a2b134082cb8d3814a3d522b897f64fbfda
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Dec 3 20:33:10 2023 -0500

    - bbsengine6/util.py,input.py: moved inputfilename to input.py

commit ea65c4e6ff909b14f5db6a7455e5c8fc1e7f5d2a
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Dec 3 20:31:44 2023 -0500

    - bbsengine6/listbox.py: added displayitems() to Listbox

commit c9f1b63ccc04bdcd8fcbfa37c41eb6cd485dede6
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Dec 3 17:06:52 2023 -0500

    - bbsengine6/database.py: updated echo calls

commit a9fa43ca6de9bd1089eaffd5bd9da32246c7c45f
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Dec 3 16:37:55 2023 -0500

    - bbsengine6/input.py: new module. merged getdate3

commit b951d31b7b541768a9afeb3cf2708d96485be950
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Dec 3 16:35:35 2023 -0500

    - bbsengine6/menu.py: added some code that moves the cursor to the current item

commit 626983036ff10e9032f96e5836de34ad9fcadb5c
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Nov 30 20:39:14 2023 -0500

    - py/src/testmenu.py: renamed 'setvariable()' to 'setvar()' (both work currently); commented out call to screen.init() and screen.setarea()

commit dcd7b4102a832849bf41b1bfe1ba2d03e8ea5f42
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Nov 29 18:46:20 2023 -0500

    - bbsengine6/: added 'listbox' and 'input' submodules

commit 6585838eb02351e9fb7a07c9f1c1c2e805f09fb6
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Nov 26 21:06:09 2023 -0500

    - bbsengine6.listbox.ListboxItem:
      * changed _init to accept 'width'
      * added a help() method
    - bbsengine6.listbox.Listbox:
      * clamp self.terminalwidth to 100
      * .display() no longer has a terminalwidth arg
      * handling of KEY_ENTER diverted to callback
      * renamed 'mi' to 'item'

commit ba01ed98bafc824d23c112f3347d1a4cd4f923b9
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Nov 26 20:54:05 2023 -0500

    - bbsengine6.menu:
     * merged code in listbox that properly colors the current item
     * calculate terminalwidth and clamp it at 100

commit 8c7f82c04c26f5070e2a0d65c57cb858da4444bd
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sat Nov 25 16:12:59 2023 -0500

    - bbsengine6/menu.py: changed prototype for __getitem__()

commit fb8c558ef4b8bee864f342b3331ec80a39e1e6ed
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Nov 24 17:15:14 2023 -0500

    - bbsengine6/listbox.py: modified menu to behave like a single-page listbox including a callback function to handle keys

commit 18ba88f27877ddf2ceac22bf5b9edffc4bd61a5f
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Nov 1 23:13:11 2023 -0400

    - bbsengine6/py/src/test*.py: added back

commit 74a3a67569aaf6b2c266ca3c4987ab2ed6d4aff0
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Nov 1 23:11:25 2023 -0400

    - bbsengine6/py/src/con/session.py: added main()

commit 980532fb3ba21d9929ca37bdef92de120405f0c3
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Nov 1 23:10:36 2023 -0400

    - bbsengine6/py/src/con/main.py: added 'S' option to list sessions

commit 6b6ec9c44187f3b61c0a29e8a8320686f7678092
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Nov 1 22:04:39 2023 -0400

    - bbsengine6/menu.py: bare minimum change to introduce 'pagesize'

commit bff050f580be51aed22a0eb630d975405fe2fc54
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 19:30:25 2023 -0400

    - bbsengine6/form.py: added FormItemCheckbox, FormItemRadioButton, and FormItemTextBox

commit 96917bd619121cf723421466c95282cbb9d1e19e
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 19:28:29 2023 -0400

    - bbsengine6/database.py: in buildarggroup(), new kwarg 'suppress'

commit e832a92219312bee0d7c2473950e1b22a6f34388
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 19:25:38 2023 -0400

    - bbsengine/util.py: changed inputfilename() so that 'verify' is part of kw, and passed through to ttyio.inputstring()

commit 5fe1df1588baf134d207d835b963b229e2d3c045
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 19:19:47 2023 -0400

    - bbsengine6/menu.py: removed 'default' kwarg from handle()

commit 51f5cebeffdce834a9e699386cab20fd2ebc7404
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 16:17:31 2023 -0400

    - bbsengine6/module.py:
      * check() now looks for 'main', 'buildargs', 'access', and 'init' in the module, and if any are missing returns False
      * it also checks for proper argument names using the built-in 'inspect' module.
      * buildargs() must always exist, and it is now allowed to return None

commit 2e0e6c25a48c4faadc4d5e04af6c729a22ef1334
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 16:12:00 2023 -0400

    - bbsengine6/session.py:
      * wrap some echo statements in 'if args.debug' checks
      * when there is more than one session, the message displayed is now of level 'warn'
      * commented out an echo used for debugging

commit c771b5764839c6af6ae87025ed8db1bfc696f155
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 16:10:39 2023 -0400

    - bbsengine6/menu.py: 'X' option no longer has a module; wrap calls to screen.setarea() in an 'if debug' check; add a {/all} to remove some artifacts

commit 4fd7ae146463f3fb0ab8533658cabefbe055bb34
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 15:39:11 2023 -0400

    - bbsengine6/php/engine.php:
      * removed zoid6 specific choices from menu
      * added a check to be sure $menu is not null before trying to sort it
      * copied buildlabel() and normalizelabelpath() from bbsengine5

commit 77561cebb784b64a82b5b5b41624c005592f8d10
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 10:52:45 2023 -0400

    - bbsengine6/php/session.php: tweeked debugging lines

commit d7e83a68f150f99ca106f2caba15040849b616c7
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Oct 30 10:41:31 2023 -0400

    - bbsengine6/php/database.php: added disconnect()

commit b686bf2da8d73ee26febe72b100e3b1798a9f023
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Oct 27 19:54:01 2023 -0400

    - bbsengine6/menu.py:
      * removed extra {savecursor} call
      * "X" is no longer handled by Menu() as special ("exit")
      * added some screen.setarea() calls for debugging. these will eventually get wrapped into args.debug checks
      * "enter" and "key" ops have been merged into "select"

commit 703d7b3834bd86d2aadddf998487bf164da33229
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Oct 26 23:12:34 2023 -0400

    - bbsengine6/menu.py:
      * finally got HOME, END, and wrapping working. tons of "off by one" problems

commit 061ae8e9de214d8e4fe8d0c28f9f3bc3182c210b
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Oct 12 16:50:51 2023 -0400

    - bbsengine6/py/src/testmenu.py: added

commit 87a61b076adff92ad943db6eafc4ced05a8d8acb
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Sep 29 15:44:36 2023 -0400

    - bbsengine6/menu.py:
      * moved form related items to form.py
      * basically rewrote the Menu class
      * Item is a new class
      * Op is a NamedTuple

commit 1f23c1da06e9179dd6559b2fac6e465dfd4cf65e
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Sep 29 15:23:03 2023 -0400

    - bbsengine6/util.py: added 'inputfilename()', commented out some unused code, and added some debugging

commit 53869fd1e06e6fffee3c86dba76472b67f5d463d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Sep 29 15:02:33 2023 -0400

    - bbsengine6/__init__.py: added import of new 'menu' module

commit 28baaff10e3f0155880b2fb1da3f56e9a4affd26
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Sep 25 15:24:25 2023 -0400

    - bbsengine6/util.py: copied inputfilename() from bbsengine5, added verify functions verifyFileExistsReadableWritable, verifyFileExistsReadable, and verifyDirExistsWritable

commit 5b7ef688a5196029301cb6a8aee2212799699b6a
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Sep 25 15:19:46 2023 -0400

    - bbsengine6/py/src/testinputfilename.py: short test script for util.inputfilename()

commit c4463074cb3c8093f9963477ddbbefec6d7d82e1
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Sep 24 18:47:57 2023 -0400

    - bbsengine6/py/src/testinputfilename.py: added

commit 901b1afca76fbd574951726e4d013e797b6f5365
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sat Sep 9 18:54:43 2023 -0400

    - bbsengine6/py/src/skel/: added skeleton code for a bbsengine6 module

commit 848f2df5019723ec53ea3912016105b49d3a530d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Sep 4 18:54:58 2023 -0400

    - bbsengine6/session.py: minor change to debugging f-string; return new value from set()

commit f1bbfc8a30a16d5065bd4c4446a11726221ad5dc
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Sep 3 19:48:33 2023 -0400

    - bbsengine6/sig.py: added getchsigcomplete(); renamed old completer (compat with readlin) to gnusigcomplete()

commit e5c1d3a8a47edc8a52ec9eb4c3c0d128cb26040d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Sep 1 18:36:37 2023 -0400

    - bbsengine6/sig.py: added builduri(), builddict(), buildrec(), and get()

commit 5cd85f2c65be74bf877b7539bb705ce774ce21ee
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Aug 31 14:54:24 2023 -0400

    - bbsengine6/sql/getsubblurbs.sql: turns out I had already updated getsubnodes.sql to refer to blurbs but I never read the file. oops.

commit 3aa83663f8e07ec4c016b89b61f6d464b9a652fe
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Aug 31 13:25:45 2023 -0400

    - bbsengine6/sql/getreplies.sql: renamed to getsubblurbs.sql

commit 9ed7c3a225eaaddfc41a00d0711a53b0da9fc5d4
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Aug 31 13:24:14 2023 -0400

    - bbsengine6/sql/getreplies.sql: copied from socrates

commit 0c73f1e44ec15f6550a97ff213afa4f17fbfadad
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 29 20:24:16 2023 -0400

    - bbsengine6/blurb,database,form: no idea what the changes were-- diff is empty
    
    Signed-off-by: Jeff MacDonald <jam@zoidtechnologies.com>

commit 270cb211cd913f490fc8602a6cfb4a860ac51fd4
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 29 19:56:21 2023 -0400

    - bbsengine6/editor.py:
      * worked on .h (help)
      * started on other dot commands

commit eada6cef648f67daf53631c15cd9e4392cc462a8
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 29 18:26:25 2023 -0400

    - bbsengine/module.py:
      * added a lot more debugging
      * use more f-strings

commit 8bf6c913c1a78d3162683a10e19e3556446b0ac3
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 29 18:06:38 2023 -0400

    - bbsengine6/menu.py: fixed a typo in class Menu (extra curly brace)

commit 0cf78a32f5ee29504bbb3af288294d78e827dae3
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 29 18:05:07 2023 -0400

    - bbsengine6/util.py: working on filedisplay(); in inputpassword(), accept a 'mask' kwarg and pass it to inputstring(); working on datestamp() so it shows timezone properly

commit d083e96f38faa4a0bc31f501e9789195435f5f25
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 29 18:01:00 2023 -0400

    - bbsengine6/member.py: tweaked debugging echo()

commit ac33ea491c9a7c47f6fdd6bc368a94311013dd5a
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sat Aug 5 14:28:37 2023 -0400

    - bbsengine6/src/con/main.py: changed the prompt a little

commit 16abacd05dbfe947ab7a77140eac238789cee633
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sat Aug 5 13:28:57 2023 -0400

    - bbsengine6/src/con/__main__.py: added call to bbsengine.session.start()

commit fb7e46f2f2c7be9bb3012843df65506721d32232
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sat Aug 5 12:40:59 2023 -0400

    - bbsengine6/util.py:
      * renamed 'title()' to 'heading()' and tweaked the code a little
      * added collapserange(), expandrange(), rangestr(), and printr() for handling ranges like 1-42 (projectflow?)
      * copied filedisplay() from bbsengine5
      * copied diceroll() from bbsengine5

commit e2d9421fb4eceef695520fa8f8f1577324c1eb26
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Aug 4 21:56:56 2023 -0400

    - bbsengine6/module.py: args.debug -> debug; changed runsubmodule() into a passthru, needs to be evaluated

commit df672dddc094820935109cdaf223f9a774fea7ba
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Aug 4 21:54:45 2023 -0400

    - bbsengine6/screen.py: updated setarea() docs

commit d6b9d2060e239b8eb7c63461e1bce705691d62a9
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Aug 4 21:45:38 2023 -0400

    - bbsengine6/src/testsession.py,testeditor.py: added

commit 99c8ba99cfbf2caa11260b5cfb1521eb790ffc40
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Aug 4 21:37:20 2023 -0400

    - bbsengine6.session
      * added get(), set()
      * fixed start()
      * added garbagecollect()
      * added buildsession() -> dict 'session'
      * build(rec) -> dict 'session'
      * garbagecollect() is only called in start() -- php has better knobs for the moment

commit f81a68f79e76fd03eb291d8ba4814a8b7d7e0c05
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Aug 2 17:21:02 2023 -0400

    - bbsengine6/editor.py: added an 'exit' command and handling of KEY_ENTER

commit 927e39eb791d39dc15c3ee870805842ab3f1d88d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Aug 1 20:30:10 2023 -0400

    - bbsengine6/editor.py: added

commit b299aa02b84a22c40b00117e7c20de4777522c3c
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Jul 17 21:09:58 2023 -0400

    - bbsengine6/con/: added 'email', 'member', and 'session' submodules

commit 93af9faba52cabd71406d4141837cf08a294dfec
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Jun 27 20:00:38 2023 -0400

    - bbsengine6/screen.py: renamed ttyio.interpretecho() to ttyio.interpret()

commit dec1d40ffbb289d69c27704d544a63391d4a659f
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Jun 27 19:52:22 2023 -0400

    - bbsengine6/session.py: added write(), get(), updatelastactivity(), start(), build() and currentsessionid

commit 6112f8ca95cc7f15b5e4d2304077c18e36f0adc4
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Jun 27 16:11:23 2023 -0400

    - bbsengine6/py/src/setup.py: changed bbsengine6 license to GPLv2 from GPLv3.

commit 30e63310bcf4aa9fb6e546e77a4e6be5abcf5235
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Jun 27 16:10:17 2023 -0400

    - bbsengine6/con/lib.py: added setarea() and runsubmodule().

commit 89b6dd46e80bc0dca04cce3ba32942d168896d8d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Jun 27 16:09:10 2023 -0400

    - bbsengine6/con/main.py: added a menu that currently only accepts 'm' for member and calls the member submodule

commit 344e9dcf8b4740f7e8bebc9f416c6ace6c3e28a4
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Jun 27 16:06:50 2023 -0400

    - bbsengine6/con/__main__.py: added some boilerplate that calls the 'main' submodule

commit 171e6f3f29fb5a4a4f9df193a3ea79a3f50edc4a
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Jun 8 13:06:50 2023 -0400

    - bbsengine6/*.py: modified but no diff output?!

commit 1dc0a37a91bfbc626fe31a84d6d63bd8cd386a8f
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Jun 8 12:25:25 2023 -0400

    - bbsengine6/member.py:
      * renamed builddict() to buildrec() -- builds a cleaned dictionary for use in the databse (filter epoch fields, etc)
      * added build() which builds a member dictionary from a database record
      * changed getcurrentid() so it uses os.getlogin(), which is cross platform vs pwd, which does not work on windowsks
      * added getbymoniker()
      * copied setflag(), getflag(), updateflag(), and checkflag() from bbsengine5
      * added setpassword()
      * added setattributes()
      * copied verifyMemberNotFound and verifyMemberFound from bbsengine5
      * added insert()
      * commented out import of 'pwd'

commit b2fe05ee2392bdc4eb984b2f1584630962419ba2
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri May 26 19:17:14 2023 -0400

    - bbsengine6/sql/member.sql: rename 'name' to 'moniker', added a 'not null' to 'email', and removed 'shell'

commit 7f2638cfda91c1a87f29a49802b6b3ba484d20b3
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue May 23 19:03:49 2023 -0400

    - bbsengine6/sql/: replaced references to 'apache' and 'www-data' with the psql var 'web' which is set by bbsengine6.sql

commit a7c75ddb90af3d223ba5230816431f583eb6629b
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue May 23 18:42:57 2023 -0400

    - bbsengine6/sql/node.sql: renamed to blurb.sql

commit f7a63d4dfd2b865db693ffcfbe5257b06e893a93
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon May 15 20:34:54 2023 -0400

    - bbsengine6/Makefile: added

commit f823cecee238d9c57acc79f5eb10d2c7667f50e9
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon May 15 20:34:37 2023 -0400

    - bbsengine6.database: added resultiter from bbsengine5

commit 9bbe777eab065c0ec530d3539feb80b1dc0d5723
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun May 14 20:09:54 2023 -0400

    - bbsengine6/py/src/Makefile: added

commit 0d9ab44084e3dacc0e939fa944d9c014fd5985f9
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun May 14 20:09:11 2023 -0400

    - bbsengine6/py/src/setup.py: updated

commit 2af075969a48cbc403b13bb42090fd99706cc3c6
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun May 14 20:07:46 2023 -0400

    - bbsengine6/py/src/bbsengine6/: added

commit 5ef86a18ce711ae9d849bc0b177d0b9436c5a1dd
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue May 2 15:34:09 2023 -0400

    - bbsengined6/py/src/con/: added some code to __main__

commit a7ebd7e47adae39cbdefdf6163cf2627fb712756
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 30 21:13:34 2023 -0400

    - bbsengine6/py/src/con/Makefile: added

commit 3d86d8ede4b04f1a49a819eecdf038311337f61a
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 30 20:58:48 2023 -0400

    - bbsengine6/py/src/setup.py: configured for bbsengine6 including 'con'

commit cac3ca5348ef4ee0a62914f6eea7086fae32045c
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 30 20:57:53 2023 -0400

    - bbsengine6/py/src/Makefile: added

commit 78f65b3d337d2c7e8c8994547494e4963a174b9d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 30 20:45:52 2023 -0400

    - bbsengine6/py/src/setup.py: copied from bbsengine5

commit f5b080f38706d3ab1ccf0a95e43f1cd7cbc31fc0
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 30 20:39:49 2023 -0400

    - bbsengine6/py/src/con/: added

commit 1c17a3de0a5cef9fff322dd27d8cb3f822873124
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 28 20:21:31 2023 -0400

    - bbsengine6/sql/mantra.sql: renamed to fortune.sql

commit 581ad435828b75f277e32812addd86edb388c4de
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 21 20:32:44 2023 -0400

    - bbsengine6/sql/nodeview.sql -> blurbview.sql

commit 42f9fe0df01e2718575d553d3fa4fa1639792486
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Apr 17 22:19:25 2023 -0400

    - bbsengine6/skin/tmpl/notify.tmpl: some quick edits

commit 755d00b1ef611a4955e706384c7d5ac34282842a
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sat Apr 15 18:13:58 2023 -0400

    - bbsengine6/www/: copied htaccess-prod, config-prod, htpasswd-prod, Makefiles, and bbsenginedotorg.sql from bbsengine5

commit 62190377cc0c23445bfc53b620825268d7d9ae1c
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 14 21:17:39 2023 -0400

    - bbsengine6/php/engine.php: renamed displaypage() arg from 'kw' to 'data'

commit ceac73c3fac73426a93876aeaae5a001e2193cc5
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 14 21:16:14 2023 -0400

    - bbsengine6/php/database.php: use proper namespace for logentry() call

commit 4ba09e0a31ac075954a135504681c6d7c7b74ce2
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 14 21:15:41 2023 -0400

    - bbsengine6/php/Input*.php: added

commit 229d15fb002a2e03654188dba261b47ea5f1caff
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 14 21:05:28 2023 -0400

    - rewrote most of \bbsengine6\session
    - added insert() and update()
    - if a read fails, insert it as a new session
    - write() updated to use insert()
    - there is no update() yet
    - added a few calls to \bbsengine6\logentry() to track which of my functions are being called by php
    - changed validate() to return true only if the session has not expired

commit dc0b9b43ddeb474f6f4481c4483685a5a54f5906
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Fri Apr 14 17:08:58 2023 -0400

    - copied php, skin, and smarty from bbsengine5

commit 4e298d5ae264b6a9a8dd9356517598daa0e54398
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Apr 13 19:32:06 2023 -0400

    - bbsengine6/js/query.smoothState.js: copied from zoidweb4

commit 53494e79079823a8a5e146631db287a79c4676d5
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Apr 13 19:17:31 2023 -0400

    - bbsengine6/www/js/bbsengine6.js: moved to 'js' so it can be installed to engine.zoid

commit fb6a30571f3cd85068be3c4ce0c82f740781f3ce
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Apr 11 10:31:20 2023 -0400

    - bbsengine6/www/php/index.php: ported to bbsengine6, set some blurb data to null so the templates will work

commit 98f911e056880f2bac31331ec499f3b561852a9d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 9 22:01:13 2023 -0400

    - bbsengine6/js/: copied from bbsengine5/js/

commit 0aff6d63075d7997052b293fed74b2e9c5655839
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Apr 6 14:33:38 2023 -0400

    - bbsengine6/sql/newuser.sql: removed 'finn' role

commit 84794054c5dcaeb2a61090193750b7464338e019
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Thu Apr 6 14:30:42 2023 -0400

    - bbsengine6/sql/role.sql: removed 'finn' role

commit b2ef94ec0c6fdc19bdb845cdc9b1c9a9a707a6a6
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Apr 5 20:35:20 2023 -0400

    - bbsengine6/sql/bbsengine5.sql: renamed to bbsengine6.sql

commit 0d6b311ec3e343d5b37b55b8cfb023d460343600
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Apr 5 20:33:47 2023 -0400

    - bbsengine6/sql/: copied from bbsengine5

commit 639957f5a3ff5f73336783b1e7e3658ed06762cf
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Tue Apr 4 19:13:24 2023 -0400

    - bbsengine6/skin/: copied from bbsengine5/skin/

commit 005f904d59abbc4a0fa5547ada3f42419adac235
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Apr 3 19:46:11 2023 -0400

    - bbsengine6/php/: added modules session, database, and engine

commit 6460d910b39a9a27f89450d2caf6d7d0b26e9b97
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Apr 3 19:37:34 2023 -0400

    - bbsengine6/php/Makefile: added 'stage' target

commit 0f6d8c29b651f520ac735374030e83c853b275ef
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Mon Apr 3 19:35:19 2023 -0400

    - bbsengine6/www/js/: copied from bbsengine5

commit 4c190bb917ee0ad632a81cf47ff4a9a98846f33d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 2 19:53:19 2023 -0400

    - bbsengine6/: added Makefile and php/Makefile

commit e395fcd6f4893c81e5b460989e51b60ccf974f7d
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 2 19:51:02 2023 -0400

    - bbsengine6/php/database.php: switched out MDB2 for PDO

commit 382168a3b9c8ad55396bb75e8ae375c3171095ff
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 2 19:29:50 2023 -0400

    - bbsengine6/php/: added database, session, and engine

commit d09125c68278c249420f80bfa72c97f8ddbeba91
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Sun Apr 2 19:28:37 2023 -0400

    - bbsengine6/README.md: updated

commit f843f5d816c3240bb0e0d9aadb9ff1e7299c0014
Author: Jeff MacDonald <jam@zoidtechnologies.com>
Date:   Wed Aug 24 21:48:23 2022 -0400

    bbsengine6/README.md: added.
