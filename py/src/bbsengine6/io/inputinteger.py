from .inputstring import inputstring

# @see https://stackoverflow.com/questions/9043551/regex-that-matches-integers-only
def inputinteger(prompt:str, oldvalue:int|str|None=None, **kwargs) -> int | list[int] | None:
  oldvalue = int(oldvalue) if oldvalue is not None else ""
  filter = kwargs.get("filter", r"^([+-]?[1-9]\d*|0)[ ,]?$")
  buf = inputstring(prompt, str(oldvalue), filter=filter, **kwargs)

  if buf is None or buf == "":
    return None
  
#  print(f"type(buf)={type(buf)!r}")
  if type(buf) is list:
    res = []
    for b in buf:
      try:
        res.append(int(b))
      except Exception:
        return
#    echo(f"res={res!r}", level="debug")
    return res
  else:
#    echo("inputinteger.100: plain int, not a list", level="debug")
    try:
      res = int(buf)
    except:
      return
    else:
      return res
