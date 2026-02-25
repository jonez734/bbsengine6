from bbsengine6 import io

while True:
    ch = io.getch()
    if ch == "KEY_ESC":
        break
    if ch:
        print(f"{ch=} ", end="", flush=True)
print
print

