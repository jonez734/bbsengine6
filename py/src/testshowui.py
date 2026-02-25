from bbsengine6 import io

def showui(args, ui, _ui):
  io.echo(f"{ui=} {_ui=}", level="debug")
  if ui is None or len(ui) == 0:
    io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: None", end="")
    if _ui is not None:
      _ui.sort()
      io.echo(f" (was: {', '.join(_ui)})")
    else:
      io.echo()
    return

  if ui is not None:
    ui.sort()
  if _ui is not None:
    _ui.sort()
  
  if ui != _ui:
      if _ui is None:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: None)")
      else:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: {', '.join(_ui)})")
  else:
    io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(_ui)}")

showui(None, None, ["alpha"])
