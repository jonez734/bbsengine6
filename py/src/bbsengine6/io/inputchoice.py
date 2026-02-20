from .echo import echo
from .getch import getch_str as getch

# @since 20230105 backported from ttyio6 (bugfix)
# @see https://ballingt.com/nonblocking-stdin-in-python-3/
# @since 20230512 renamed from 'inputchar' in ttyio5 @BCBREAK
def inputchoice(prompt:str, options:str, default:str|None="", **kwargs) -> str | None:
  args = kwargs.get("args", None)
  noneok = kwargs.get("noneok", False)
  help = kwargs.get("help", None)

  rewriteprompt = kwargs.get("rewriteprompt", False)

  default = default.upper() if default is not None else ""

  options = options.upper()
  # echo(f"bbsengine.io.input.100: {options=} {rewriteprompt=}", level="debug")
  if rewriteprompt is True:
    prompt = f"{{var:promptcolor}}{prompt} [{{var:optioncolor}}{options.replace(default, f'({default})')}{{var:promptcolor}}]: {{var:inputcolor}}"
#  options = "".join(sorted(options))

  echo(prompt, end="", flush=True)

  done = False
  while not done:
    ch = getch() # .decode("UTF-8")
    if ch is not None:
      ch = ch.upper()

    if ch == "KEY_ENTER":
      if noneok is True:
        return None
      elif default is not None and default != "":
        return default
      else:
        echo("{bell}", end="", flush=True)
        continue
    elif (ch == "?" or ch == "KEY_HELP"): #  and callable(helpcallback) is True:
      echo("help")
      if callable(help):
        help(**kwargs)
      elif type(help) is str:
        echo(help)
      echo(prompt, end="", flush=True)
    elif ch is not None:
        if ch[:4] == "KEY_" or ch in options:
            break
        echo("{bell}", end="", flush=True)
        continue
     
  return ch
