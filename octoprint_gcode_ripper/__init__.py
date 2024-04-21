# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util
import re
import os
import math
from . import G_Code_Rip as G_Code_Rip

class Gcode_ripperPlugin(octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin
):

    def __init__(self):
        self.template_gcode = []
        self.selected_file = None
        self.currentZ = 0
        self.start_diameter = float(0)
        self.current_diameter = float(0)
        self.rotation = float(0)
        self.scalefactor = float(1)
        self.mapping = "Y2A"
        self.datafolder = None
        self.template_name = None
        #self.watched_path = self._settings.global_get_basefolder("watched")
    ##~~ SettingsPlugin mixin
    def initialize(self):
        self.datafolder = self.get_plugin_data_folder()
    
    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/gcode_ripper.js"],
            "css": ["css/gcode_ripper.css"],
            "less": ["less/gcode_ripper.less"]
        }

    ##~~ Softwareupdate hook
    def _get_templates(self):
        self.template_gcode = []
        print("Getting template gcodes from data directory")
        for file in os.listdir(self.datafolder):
            if file.endswith('.gcode'):
                self.template_gcode.append(file)

    def generate_gcode(self):
        gcr = G_Code_Rip.G_Code_Rip()
        gcode_file = self.selected_file
        gcr.Read_G_Code("{}/{}".format(self._settings.getBaseFolder("uploads"), gcode_file), XYarc2line=True, units="mm")
        wrapdiam = self.start_diameter + 2*(self.currentZ)
        output_name = "D{0}_R{1}_".format(int(wrapdiam), int(self.rotation))
        if self.polarize:
            output_name = "Polar_{0}".format(output_name)
        output_path = output_name+self.template_name
        path_on_disk = "{}/{}".format(self._settings.getBaseFolder("watched"), output_path)
        sf = self.scalefactor
        temp,minx,maxx,miny,maxy,minz,maxz  = gcr.scale_rotate_code(gcr.g_code_data,[1,1,1,1],self.rotation)
        midx = (minx+maxx)/2
        midy = (miny+maxy)/2
        x_zero = midx
        y_zero = midy

        temp = gcr.scale_translate(temp,translate=[x_zero,y_zero,0.0])
        gcr.scaled_trans = temp
        minx = minx - x_zero
        maxx = maxx - x_zero
        miny = miny - y_zero
        maxy = maxy - y_zero
        mina = math.degrees(miny/(wrapdiam/2))
        maxa = math.degrees(maxy/(wrapdiam/2))
        maxarc = (abs(mina) + abs(maxa))
        if not self.polarize:
            pre = "DOBANGLE\nDIAM {0}\nDOMODA\nMAXARC {1:.3f}".format(wrapdiam,maxarc)
            #pre = "DOBANGLE\nDIAM {0}\nDOMODA".format(wrapdiam)
        else:
            pre = "DOBANGLE\nDIAM {0}\n".format(wrapdiam)
        with open(path_on_disk,"w") as newfile:
            for line in gcr.generategcode(temp, Rstock=wrapdiam/2, no_variables=True, Wrap=self.mapping, preamble=pre, postamble="STOPBANGLE", FSCALE="None"):
                newfile.write(f"\n{line}")
    
    def get_api_commands(self):
        return dict(
            write_gcode=[]
        )
    
    def on_api_command(self, command, data):
        
        if command == "write_gcode":
            print(data)
            self.selected_file = data["filename"]["path"]
            self.template_name = data["filename"]["display"]
            self.start_diameter = float(data["diameter"])
            self.rotation = float(data["rotationAngle"])
            self.polarize = bool(data["polar"])
            self.scalefactor = float(data["scalefactor"])
            if self.polarize:
                self.mapping = "Polar"
            else:
                self.mapping = "Y2A"
            self.generate_gcode()

    def hook_gcode_received(self, comm_instance, line, *args, **kwargs):
        # look for a status message
        if 'MPos' in line or 'WPos' in line:
            self.process_grbl_status_msg(line)
        return line
    
    def process_grbl_status_msg(self, msg):
        #need to redefine much of this if we have more axes

        match = re.search(r'<(-?[^,]+)[,|][WM]Pos:(-?[\d\.]+),(-?[\d\.]+),(-?[\d\.]+),?(-?[\d\.]+)?,?(-?[\d\.]+)?', msg)
        self.currentZ = float(match.groups(1)[3])
        print(self.currentZ)

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "gcode_ripper": {
                "displayName": "Gcode_ripper Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "paukstelis",
                "repo": "OctoPrint-Gcode_ripper",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/paukstelis/OctoPrint-Gcode_ripper/archive/{target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Gcode_ripper Plugin"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Gcode_ripperPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        'octoprint.comm.protocol.gcode.received': __plugin_implementation__.hook_gcode_received
    }
