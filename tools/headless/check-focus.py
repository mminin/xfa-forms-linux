"""Check the handoff's field transition on a fresh sample at 49.8% zoom.

Start the headless session and open samples/consent-letter-2123.pdf first.
Requires python-xlib and Pillow, like drive.py. Screenshots go into _work/.
"""

from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageChops
from Xlib import X, display

here = Path(__file__).resolve().parent
output = here.parents[1] / '_work/gui-focus'
output.mkdir(parents=True, exist_ok=True)
d = display.Display(':77')
root = d.screen().root


def drive(*args):
    subprocess.run([sys.executable, str(here / 'drive.py'), *map(str, args)], check=True)


def menus():
    result = []
    for window in root.query_tree().children:
        attrs = window.get_attributes()
        geometry = window.get_geometry()
        if (attrs.map_state == X.IsViewable and attrs.override_redirect
                and geometry.width > 200 and geometry.height > 200):
            result.append(geometry)
    return result


def wait_for_menu(opened):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = menus()
        if bool(current) == opened:
            return current
        time.sleep(0.1)
    raise AssertionError(f'Country menu did not become {"open" if opened else "closed"}')


# Exclude field values, thumbnail selection and window-title changes.
header = (260, 65, 665, 200)
drive('move', 700, 600, 'shot', output / 'before.png')
reference = Image.open(output / 'before.png').crop(header)

for i in range(5):
    drive('click', 461, 224, 'key', 'ctrl+a', 'type', f'Test {i}',
          'click', 488, 332)
    menu = wait_for_menu(True)[0]
    assert 280 <= menu.x <= 350 and 300 <= menu.y <= 360, (
        f'Country menu is misplaced: {menu.x}, {menu.y}')
    shot = output / f'round-{i + 1}.png'
    drive('move', 700, 600, 'shot', shot)
    assert ImageChops.difference(reference, Image.open(shot).crop(header)).getbbox() is None, (
        'The document moved during the field transition')
    # Select the first country, which also saves the choice and re-renders.
    drive('key', 'Home', 'key', 'Return')
    wait_for_menu(False)
    # Check typing straight into another text field after committing a name.
    drive('click', 461, 224, 'key', 'ctrl+a', 'type', f'Text {i}',
          'click', 450, 282, 'type', f'Address {i}', 'click', 488, 332)
    wait_for_menu(True)
    drive('key', 'Escape')
    wait_for_menu(False)
    print(f'Round {i + 1}: text and choice transitions passed; scroll position preserved')

print(f'PASS: screenshots in {output}')
