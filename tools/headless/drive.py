# Drives the X display :77: drive.py shot out.png | click x y [button] | move x y | type text | key keysym | wheel up|down [ctrl] ...
import sys, time
from Xlib import X, XK, display
from Xlib.ext import xtest
from PIL import Image
d = display.Display(':77')
root = d.screen().root
def sync(): d.sync(); time.sleep(0.15)
def press(code, down): xtest.fake_input(d, X.KeyPress if down else X.KeyRelease, code)
def key(name):
    mods = []
    parts = name.split('+')
    for m in parts[:-1]:
        mods.append(d.keysym_to_keycode(XK.string_to_keysym({'ctrl':'Control_L','shift':'Shift_L','alt':'Alt_L'}[m])))
    ks = XK.string_to_keysym(parts[-1])
    code = d.keysym_to_keycode(ks)
    shift = d.keycode_to_keysym(code, 0) != ks and d.keycode_to_keysym(code, 1) == ks
    if shift: mods.append(d.keysym_to_keycode(XK.string_to_keysym('Shift_L')))
    for m in mods: press(m, True)
    press(code, True); press(code, False)
    for m in reversed(mods): press(m, False)
    sync()
args = sys.argv[1:]
while args:
    c = args.pop(0)
    if c == 'shot':
        g = root.get_geometry()
        raw = root.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xffffffff)
        Image.frombytes('RGB', (g.width, g.height), raw.data, 'raw', 'BGRX').save(args.pop(0))
    elif c in ('click', 'move'):
        x, y = int(args.pop(0)), int(args.pop(0))
        xtest.fake_input(d, X.MotionNotify, x=x, y=y); sync()
        if c == 'click':
            xtest.fake_input(d, X.ButtonPress, 1); xtest.fake_input(d, X.ButtonRelease, 1); sync()
    elif c == 'type':
        for ch in args.pop(0):
            key({' ':'space','-':'minus','.':'period',',':'comma','@':'at','+':'plus','/':'slash','_':'underscore'}.get(ch, ch))
    elif c == 'key':
        key(args.pop(0))
    elif c == 'wheel':
        button = 4 if args.pop(0) == 'up' else 5
        ctrl = bool(args) and args[0] == 'ctrl'
        if ctrl:
            args.pop(0)
            press(d.keysym_to_keycode(XK.string_to_keysym('Control_L')), True); sync()
        xtest.fake_input(d, X.ButtonPress, button); xtest.fake_input(d, X.ButtonRelease, button); sync()
        if ctrl:
            press(d.keysym_to_keycode(XK.string_to_keysym('Control_L')), False); sync()
    elif c == 'sleep':
        time.sleep(float(args.pop(0)))
