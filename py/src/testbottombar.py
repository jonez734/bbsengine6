import argparse
from bbsengine6 import screen, io

def setarea(args, buf, stack=False, **kwargs) -> None:
    player = kwargs.get("player", None)
    help = kwargs.get("help", None)

    def rightside():
        debug = True if args is not None and args.debug is True else False

        if player is not None:
            if player.isdirty() is True:
                isdirty = "*"
            else:
                isdirty = ""

            if player.turncount >= libplayer.TURNSPERDAY:
                player.turncount = libplayer.TURNSPERDAY

            turnremain = libplayer.TURNSPERDAY - player.turncount

            debug = " | debug" if args is not None and args.debug is True else ""

            coinres = player.getresource("coins")
            coinres["emoji"] = ""
            return f"empyre {{black}}|{{engine.areacolor}} {util.pluralize(turnremain, 'turn remains', 'turns remain')} {{black}}|{{engine.areacolor}} {isdirty}{player.moniker} {{black}}|{{engine.areacolor}} {util.pluralize(player.coins, **coinres)}{debug}"

        else:
            if debug is True:
                return "debug"
            else:
                return ""

    screen.setbottombar(buf, rightside, stack)
    #if args.debug is True:
    #    io.echo(f"empyre.setarea.100: {buf=} {stack=} {screen.areastack=}", level="debug")
    return

args = argparse.Namespace(debug=True)
io.util.screen_init()
io.util.setbottombar("this is the left side")
#screen.init()
#setarea(args, "this is the left side")
#io.inputboolean("done? ")
