# DEPRECATED: This module is not used. Only used by deprecated output.py.
variables = {}
savedvariables = []

variables["boxcolor"] = "{darkgreen}"
variables["titlecolor"] = "{white}{bggray}"

variables["theanswer"] = 73
variables["engine.title.color"] = "{bggray}{white}"
variables["engine.title.hrcolor"] = "{darkgreen}"
variables["optioncolor"] = "{white}{bggray}"
variables["currentoptioncolor"] = "{bgwhite}{gray}"
# variables["areacolor"] = "{bggray}{white}"
variables["bottombarcolor"] = "{bggray}{white}"
variables["engine.areacolor"] = "{bggray}{white}"
variables["promptcolor"] = "{/bgcolor}{lightgray}"
variables["inputcolor"] = "{/bgcolor}{green}"
variables["normalcolor"] = "{/bgcolor}{lightgray}"
variables["highlightcolor"] = "{green}"
variables["labelcolor"] = "{/bgcolor}{lightgray}"
variables["valuecolor"] = "{/bgcolor}{green}"
variables["hrcolor"] = "{/bgcolor}{gray}"
variables["acscolor"] = "{/bgcolor}{gray}"  # @since 20220916
variables["sepcolor"] = "{lightgray}"  # @since 20220924
variables["level.debug"] = "{bglightblue}{blue}"
variables["level.warning"] = "{bgyellow}{black}"
variables["level.error"] = "{bgred}{black}"
variables["level.fail"] = "{bgred}{black}"
variables["level.ok"] = "{bggreen}{black}"
variables["level.info"] = "{bgwhite}{blue}"
variables["level.crit"] = "{bgblue}{white}"
variables["engine.menu.boxcharcolor"] = "{bglightgray}{darkgreen}"
variables["engine.menu.color"] = "{bggray}"
variables["engine.menu.shadowcolor"] = "{bgdarkgray}"
variables["engine.menu.cursorcolor"] = "{bglightgray}{blue}"
variables["engine.menu.boxcolor"] = "{bgblue}{green}"
variables["engine.menu.titlecolor"] = "{black}{bglightgray}"
variables["engine.menu.disableditemcolor"] = "{darkgray}"
variables["engine.menu.resultfailedcolor"] = "{bgred}{white}"

variables["itemcolor"] = "{blue}{bglightgray}"
variables["currentitemcolor"] = "{bgwhite}{black}"

# add 'engine.menu.resultfailedcolor'?


def set(name: str, value):
    variables[name] = value
    return


def get(name: str, default=None):
    if name in variables:
        return variables[name]
    return f"NOTFOUND:{name}"


def clear():
    global variables
    variables = {}
    return


def save():
    import copy

    savedvariables.append(copy.deepcopy(variables))
    return True


def restore():
    savedvariables.pop()
