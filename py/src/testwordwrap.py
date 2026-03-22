from bbsengine6 import io

width = 80
# buf = """{brown}Bacon{/all} ipsum dolor amet short ribs brisket{cursorleft:5}{red}{wait:0} venison rump {/all}{wait:0}drumstick pig sausage prosciutto chicken spare ribs salami picanha doner. Kevin capicola sausage, buffalo bresaola venison turkey shoulder picanha ham pork tri-tip meatball meatloaf ribeye. Doner spare ribs andouille bacon sausage. Ground round jerky brisket pastrami shank.{f6:3}
# Lorem Ipsum is the single greatest threat. We are not - we are not keeping up with other websites. Lorem Ipsum best not make any more threats to your website. It will be met with fire and fury like the world has never seen. Does everybody know that pig named Lorem Ipsum? An ‘extremely credible source’ has called my office and told me that Barack Obama’s placeholder text is a fraud.
#
# {f6}:smile:{f6}{obviouslyinvalidcommand}"""
# buf = "{var:inputcolor}{italic}input color here{/italic}{/all}{f6}"
buf = """{indent:5}{brown}Bacon{/all} ipsum dolor amet short ribs brisket{red}{wait:0} venison rump {/all}{wait:0}drumstick pig sausage prosciutto chicken spare ribs salami picanha doner. Kevin capicola sausage, buffalo bresaola venison turkey shoulder picanha ham pork tri-tip meatball meatloaf ribeye. Doner spare ribs andouille bacon sausage. Ground round jerky brisket pastrami shank.{f6}
Lorem Ipsum is the single greatest threat. We are not - we are not keeping up with other websites. Lorem Ipsum best not make any more threats to your website. It will be met with fire and fury like the world has never seen. Does everybody know that pig named Lorem Ipsum? An ‘extremely credible source’ has called my office and told me that Barack Obama’s placeholder text is a fraud.
{f6}{brown}Bacon{/all} ipsum dolor amet short ribs brisket{cursorleft:5}{red}{wait:0} venison rump {/all}{wait:0}drumstick pig sausage prosciutto chicken spare ribs salami picanha doner. Kevin capicola sausage, buffalo bresaola venison turkey shoulder picanha ham pork tri-tip meatball meatloaf ribeye. Doner spare ribs andouille bacon sausage. Ground round jerky brisket pastrami shank.
{f6:2}Lorem Ipsum is the single greatest threat. We are not - we are not keeping up with other websites. Lorem Ipsum best not make any more threats to your website. It will be met with fire and fury like the world has never seen. Does everybody know that pig named Lorem Ipsum? An ‘extremely credible source’ has called my office and told me that Barack Obama’s placeholder text is a fraud.
{inputcolor}{'foo':'bar', 'baz':42}{/all}{f6}"""
# buf = "{indent:5}abcdefg{cursorleft:3}12345{cursordown:2}HIJK{cursorup:2}67890{acs:hline:5}{f6:3}this is even more text to see if the indent works properly"
for section in range(1, width // 10 + 1):
    io.echo(f"         {section}", end="")
io.echo("{f6}", end="")
for sesion in range(1, width // 10 + 1):
    io.echo(f".........0", end="")
io.echo("{f6}")

io.echo(buf, wordwrap=True, width=width)
