#!/usr/bin/env python3
"""
Clearine
Yet Another GTK3-based logout-window overlay for independent windowmanager

usage:

   -h  --help  show help docs

 configuration file location:

   Clearine basically read configuration from  "~/.config/clearine.conf"  .
   if that file is unavailable, I will read from  "/etc/clearine.conf"  insteads.

 configuration format:

   [main]
     # set background opacity
     opacity = 0.8
     # set padding left and right
     gap-left = 100
     gap-right = 50

   [command]
     # set command to launch when the button is clicked
     logout = openbox --exit
     restart = systemctl reboot
     shutdown = systemctl poweroff

   [card]
     # set background color and border radius for card
     background-color = #e1e5e8
     border-radius = 20

   [button]
     # button theme name
     theme = Clearine-Fallback
     # button item sort
     items = logout, restart, shutdown, cancel
     # set button text font and text color
     label-font = DejaVu Sans Book 9
     label-size = 9
     label-color = #101314
     # set button width and height
     width = 100
     height = 70
     # set button icon width and height
     icon-width = 32
     icon-height = 32
     # set per-button margin
     margin-bottom = 30
     margin-left = 10
     margin-right = 10
     margin-top = 30
     # set spacing between button
     spacing = 10

   [widget]
     # set widget first line font, size, color and format
     firstline-font = DejaVu Sans ExtraLight
     firstline-size = 90
     firstline-color = #e1e5e8
     firstline-format = %H.%M
     # set widget second line font, size, color and format
     secondline-font = DejaVu Sans Book
     secondline-size = 14
     secondline-color = #e1e5e8
     secondline-format = %A, %d %B %Y

author  - Nanda Vera <codeharuka.yusa@gmail.com> 
source  - https://github.com/yuune/clearine
license - MIT [see LICENSE file for more]
"""

import os
import sys
import time
import getopt
import signal
import logging
import subprocess
import configparser

try:
    import gi

except:
    print("no modules named 'gi', please install python-gobject")
    sys.exit()

try:
    import cairo

except:
    print("no modules named 'cairo', please install python-cairo")
    sys.exit()

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import Gtk, Gdk, Pango, GObject as gobject
from gi.repository.GdkPixbuf import Pixbuf

config = {}

class Clearine(Gtk.Window):
    def __init__(self):
        # initialize a fullscreen window
        Gtk.Window.__init__(self)

        self.connect('destroy', Gtk.main_quit)
        self.connect('draw', self.draw_background)
        self.connect("delete-event", Gtk.main_quit)
        self.connect('key-press-event', self.on_keypressed)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_app_paintable(True)
        self.fullscreen()
        self.fetch_dotconf()
        self.realize_content()
        self.show_all()
        self.set_keep_above(True)

    def fetch_dotconf(self):
        # fetch a plain-text clearine.conf configuration
        global config

        status = logging.getLogger(self.__class__.__name__)
        dotcat = configparser.ConfigParser()
        file_home = "%s/.config/clearine.conf" % os.environ['HOME']
        file_sys = "/etc/clearine.conf"

        try:
            if os.path.exists(file_home):
                dotcat.read(file_home)
            elif os.path.exists(file_sys):
                dotcat.read(file_sys)
        except:
            status.error("failed to find configuration file.  exiting.")
            sys.exit()

        def find_key(data, section, key, default):
            try:
                if data is "arr":
                    return dotcat.get(section, key).split(",")
                if data is "str":
                    return dotcat.get(section, key, raw=True)
                if data is "int":
                    return dotcat.getint(section, key)
                if data is "flo":
                    return dotcat.getfloat(section, key)
                if data is "clr":
                    data = dotcat.get(section, key, raw=True)
                    if data.startswith("#"):
                        return data
                    elif data.startswith("{") and data.endswith("}"):
                        data = data.lstrip('{').rstrip('}')
                        return self.xrdb(data)

            except:
                status.info("failed to find key named '%s' in section '[%s]'.  use fallback value insteads." % (key, section))
                return default

        config["button-label-font"]        = find_key("str", "button", "label-font",        "DejaVu Sans Book")
        config["button-label-size"]        = find_key("int", "button", "label-size",        9)
        config["button-label-color"]       = find_key("clr", "button", "label-color",       "#101314")
        config["button-height"]            = find_key("int", "button", "height",            70)
        config["button-icon-height"]       = find_key("int", "button", "icon-height",       32)
        config["button-icon-width"]        = find_key("int", "button", "icon-width",        32)
        config["button-items"]             = find_key("arr", "button", "items",             "logout, restart, shutdown, cancel")
        config["button-margin-bottom"]     = find_key("int", "button", "margin-bottom",     30)
        config["button-margin-left"]       = find_key("int", "button", "margin-left",       10)
        config["button-margin-right"]      = find_key("int", "button", "margin-right",      10)
        config["button-margin-top"]        = find_key("int", "button", "margin-top",        30)
        config["button-spacing"]           = find_key("int", "button", "spacing",           10)
        config["button-theme"]             = find_key("str", "button", "theme",             "default-clearine")
        config["button-width"]             = find_key("int", "button", "width",             100)
        config["card-background-color"]    = find_key("clr", "card",   "background-color",  "#e1e5e8")
        config["card-border-radius"]       = find_key("int", "card",   "border-radius",     20)
        config["main-gap-left"]            = find_key("int", "main",   "gap-left",          100)
        config["main-gap-right"]           = find_key("int", "main",   "gap-right",         50)
        config["main-opacity"]             = find_key("flo", "main",   "opacity",           0.8)
        config["widget-firstline-font"]    = find_key("str", "widget", "firstline-font",    "DejaVu Sans ExtraLight")
        config["widget-firstline-size"]    = find_key("int", "widget", "firstline-size",    90)
        config["widget-firstline-color"]   = find_key("clr", "widget", "firstline-color",   "#e1e5e8")
        config["widget-firstline-format"]  = find_key("str", "widget", "firstline-format",  "%H.%M")
        config["widget-secondline-font"]   = find_key("str", "widget", "secondline-font",   "DejaVu Sans Book")
        config["widget-secondline-size"]   = find_key("int", "widget", "secondline-size",    14)
        config["widget-secondline-color"]  = find_key("clr", "widget", "secondline-color",  "#e1e5e8")
        config["widget-secondline-format"] = find_key("str", "widget", "secondline-format", "%A, %d %B %Y")
        config["command-logout"]           = find_key("str", "command", "logout",           "pkexec pkill X")
        config["command-restart"]          = find_key("str", "command", "restart",          "pkexec reboot -h now")
        config["command-shutdown"]         = find_key("str", "command", "shutdown",         "pkexec shutdown -h now")

    def realize_content(self):
        # Setup all content inside Gtk.Window
        button_group = Gtk.VBox()
        button_group.set_margin_top(config["button-margin-top"])
        button_group.set_margin_start(config["button-margin-left"])
        button_group.set_margin_bottom(config["button-margin-bottom"])
        button_group.set_margin_end(config["button-margin-right"])
        button_group.set_spacing(config["button-spacing"])

        card = Gtk.VBox()
        card.pack_end(button_group, False, False, False)

        container = Gtk.Grid()
        container.set_halign(Gtk.Align.END)
        container.set_valign(Gtk.Align.CENTER)
        container.attach(card, 1, 1, 1, 1)

        self.first_widget = Gtk.Label()
        self.first_widget.set_label(time.strftime(config["widget-firstline-format"]))

        self.second_widget = Gtk.Label()
        self.second_widget.set_label(time.strftime(config["widget-secondline-format"]))

        widgets = Gtk.Grid()
        widgets.set_valign(Gtk.Align.CENTER)
        widgets.attach(self.first_widget, 1, 1, 1, 1)
        widgets.attach(self.second_widget, 1, 2, 1, 1)

        content = Gtk.Box()
        content.set_margin_start(config["main-gap-left"])
        content.set_margin_end(config["main-gap-right"])
        content.pack_start(widgets, False, False, False)
        content.pack_end(container, False, False, False)

        gobject.timeout_add(200, self.update_widgets)
        self.card_style = Gtk.CssProvider()
        self.card_css = """
            .clearine-button {{
                background: {_cbg};
                color: {_bcol};
                font-family: '{_bfont}';
                font-size: {_bsize}px;
                box-shadow: none;
            }}
            .clearine-card {{
                background: {_cbg};
                border-width:0;
                border-radius:{_crad}px;
            }}
            .clearine-widget-first {{
                color: {_w1col};
                font-family:'{_w1font}';
                font-size: {_w1size}px;
            }}
            .clearine-widget-second {{
                color: {_w2col};
                font-family:'{_w2font}';
                font-size: {_w2size}px;
            }}
            """.format(
                _bsize=str(config["button-label-size"]),
                _bcol=str(config["button-label-color"]),
                _bfont=str(config["button-label-font"]),
                _cbg=str(config["card-background-color"]),
                _crad=str(config["card-border-radius"]),
                _w1col=str(config["widget-firstline-color"]),
                _w2col=str(config["widget-secondline-color"]),
                _w1font=str(config["widget-firstline-font"]),
                _w2font=str(config["widget-secondline-font"]),
                _w1size=str(config["widget-firstline-size"]),
                _w2size=str(config["widget-secondline-size"]),
            )

        self.card_style.load_from_data(self.card_css.encode())

        Gtk.StyleContext.add_class(card.get_style_context(), "clearine-card")
        Gtk.StyleContext.add_class(self.first_widget.get_style_context(), "clearine-widget-first")
        Gtk.StyleContext.add_class(self.second_widget.get_style_context(), "clearine-widget-second")

        Gtk.StyleContext.add_provider(card.get_style_context(), self.card_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.StyleContext.add_provider(self.first_widget.get_style_context(), self.card_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.StyleContext.add_provider(self.second_widget.get_style_context(), self.card_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        for button in config["button-items"]:
            try:
                count += 1
            except NameError:
                count = 1

            self.draw_button(button, button_group, count)        

        self.add(content)

    def update_widgets(self):
        # update first and second-line widget
        self.first_widget.set_label(time.strftime(config["widget-firstline-format"]))
        self.second_widget.set_label(time.strftime(config["widget-secondline-format"]))

    def draw_button(self, name, widget, index):
        # setup a buttons inside card
        status = logging.getLogger(self.__class__.__name__)
        button_name = name.strip()

        icon_atsystem = "%s/%s/clearine" % ("%s/share/themes" % sys.prefix, config["button-theme"])
        icon_athome = "%s/.themes/%s/clearine" % (os.environ['HOME'], config["button-theme"])
        icon_default = "%s/%s/clearine" % ("%s/share/themes" % sys.prefix, 'default-clearine')

        try:
            if os.path.exists("%s/%s.png" % (icon_athome, button_name)):
                iconfile = "%s/%s.png" % (icon_athome, button_name)
            if os.path.exists("%s/%s.png" % (icon_atsystem, button_name)):
                iconfile = "%s/%s.png" % (icon_atsystem, button_name)
            if os.path.exists("%s/%s.svg" % (icon_athome, button_name)):
                iconfile = "%s/%s.svg" % (icon_athome, button_name)
            if os.path.exists("%s/%s.svg" % (icon_atsystem, button_name)):
                iconfile = "%s/%s.svg" % (icon_atsystem, button_name)
        except:
            status.info("icon '%s' at '%s' theme  doesn't exist.  we use fallback theme insteads." % (button_name, config["button-theme"]))
            iconfile = "%s/%s.svg" % (icon_default, button_name)

        icon_buffer = Pixbuf.new_from_file_at_size(iconfile, config["button-icon-width"], config["button-icon-height"])

        icon = Gtk.Image()
        icon.set_from_pixbuf(icon_buffer)
        icon.set_margin_bottom(10)
        icon.set_margin_top(10)

        button = Gtk.Button()
        button.set_always_show_image(True)
        button.set_image_position(2)
        button.set_label(button_name.capitalize())
        button.set_image(icon)
        button.connect("clicked", self.do, button_name)
        button.set_size_request(config["button-width"], config["button-height"])
        button.set_can_focus(True)

        Gtk.StyleContext.add_class(button.get_style_context(), "clearine-button")
        Gtk.StyleContext.add_provider(button.get_style_context(), self.card_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        widget.pack_start(button, False, False, False)

    def to_rgba(self, hex):
        # convert hex color to RGBA
        color = Gdk.RGBA()
        color.parse(hex)
        return color 

    def xrdb(self, request):
        result = {}
        query = subprocess.Popen(['xrdb', '-query'],stdout=subprocess.PIPE)
        for line in iter(query.stdout.readline, b''):
            lined = line.decode()
            key, value, *_ = lined.split(':')
            key = key.lstrip('*').lstrip('.')
            value = value.strip()
            result[key] = value

        return result[request]

    def draw_background(self, widget, context):
        # setup a semi-transparent background
        context.set_source_rgba(0, 0, 0, config["main-opacity"])
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)

    def do(self, widget, button):
        # handle every button action
        if button == 'cancel':
            sys.exit()
        else:
            os.system(config["command-%s" % button])

    def on_keypressed (self, widget, event):
        # handling an event when user press some key
        if event.keyval == Gdk.KEY_Escape:
            sys.exit()

class SignalHandler():
    def __init__(self):
        self.SIGINT = False

    def SIGINT(self, signal, fram):
        self.SIGINT = True

def main():
    status_format = logging.StreamHandler(sys.stdout)
    status_format.setFormatter(logging.Formatter("Clearine: %(message)s"))
    status = logging.getLogger()
    status.addHandler(status_format)
    status.setLevel(logging.INFO)
    
    try:
        if len(sys.argv) > 1:
            options, arguments = getopt.getopt(sys.argv[1:], "h", ["help"])
            for option, argument in options:
                if option in ("-h", "--help"):
                    print (__doc__)
                    return 0
    except:
        status.error("unused options '%s'.  see -h (or --help) for more information" % sys.argv[1])
        return 2




    handle = SignalHandler()
    signal.signal(signal.SIGINT, handle.SIGINT)

    Clearine()
    Gtk.main()

if __name__ == "__main__":
    sys.exit(main())
