# coding=utf-8
from __future__ import absolute_import

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
        self.modifyA = False
        self.scalefactor = float(1)
        self.origin = "center"
        self.mapping = "Y2A"
        self.split_moves = True
        self.min_seg = 1.0
        self.datafolder = None
        self.template_name = None
        #self.watched_path = self._settings.global_get_basefolder("watched")
    ##~~ SettingsPlugin mixin
    def initialize(self):
        self.datafolder = self.get_plugin_data_folder()

    #integrated directly from upload anything plugin by 
    @property
    def allowed(self):
        if self._settings is None:
            return ""
        else:
            return str(self._settings.get(["allowed"]))
        
    def get_settings_defaults(self):
            return ({'allowed': 'png, gif, jpg'})

    def get_extension_tree(self, *args, **kwargs):
        return dict(model=dict(uploadanything=[x for x in self.allowed.replace(" ", "").split(",") if x != '']))
    

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
        #print("Getting template gcodes from data directory")
        for file in os.listdir(self.datafolder):
            if file.endswith('.gcode'):
                self.template_gcode.append(file)

    def generate_gcode(self):
        gcr = G_Code_Rip.G_Code_Rip()
        gcode_file = self.selected_file
        gcr.Read_G_Code("{}/{}".format(self._settings.getBaseFolder("uploads"), gcode_file), XYarc2line=True, units="mm")
        self.mapping = "Y2A"
        polar = False
        wrapdiam = self.start_diameter + 2*(self.currentZ)
        output_name = "D{0}_R{1}_".format(int(wrapdiam), int(self.rotation))
        output_path = output_name+self.template_name
        path_on_disk = "{}/{}".format(self._settings.getBaseFolder("watched"), output_path)
        sf = self.scalefactor
        temp,minx,maxx,miny,maxy,minz,maxz  = gcr.scale_rotate_code(gcr.g_code_data,[sf,sf,1,1],self.rotation,split_moves=self.split_moves,min_seg_length=self.min_seg)
        midx = (minx+maxx)/2
        midy = (miny+maxy)/2
        #determine origin position
        if self.origin == "center":
            x_zero = midx
            y_zero = midy
        if self.origin == "left":
            x_zero = minx
            y_zero = midy
        if self.origin == "right":
            x_zero = maxx
            y_zero = midy
            
        #Refactor for polar coordinate case
        if self.start_diameter < maxx:
            output_name = "POLAR_R{0}_".format(int(self.rotation))
            output_path = output_name+self.template_name
            path_on_disk = "{}/{}".format(self._settings.getBaseFolder("watched"), output_path)
            self.mapping = "Polar"
            polar = True
            wrapdiam=0.5

        temp = gcr.scale_translate(temp,translate=[x_zero,y_zero,0.0])
        gcr.scaled_trans = temp
        minx = minx - x_zero
        maxx = maxx - x_zero
        miny = miny - y_zero
        maxy = maxy - y_zero
        if not polar:
            mina = math.degrees(miny/(wrapdiam/2))
            maxa = math.degrees(maxy/(wrapdiam/2))
            maxarc = (abs(mina) + abs(maxa))
        pre = "DOBANGLE\nDIAM {0}\n".format(wrapdiam)

        if self.modifyA and not polar:
            pre = pre + "DOMODA\nMAXARC {0:.3f}".format(maxarc)

        with open(path_on_disk,"w") as newfile:
            for line in gcr.generategcode(temp, Rstock=wrapdiam/2, no_variables=True, Wrap=self.mapping, preamble=pre, postamble="STOPBANGLE", FSCALE="None"):
                newfile.write(f"\n{line}")
    
    def update_image(self):
        self._file_manager.set_additional_metadata("local",self.selected_file,"bgs_imgurl",self.selected_image,overwrite=True)

    def get_api_commands(self):
        return dict(
            write_gcode=[],
            editmeta=[]
        )
    
    def on_api_command(self, command, data):
        
        if command == "write_gcode":
            #print(data)
            self.selected_file = data["filename"]["path"]
            self.template_name = data["filename"]["display"]
            self.start_diameter = float(data["diameter"])
            self.rotation = float(data["rotationAngle"])
            self.modifyA = bool(data["modifyA"])
            self.scalefactor = float(data["scalefactor"])
            self.origin = data["origin"]
            self.mapping = "Y2A"
            self.split_moves = bool(data["split_moves"])
            self.min_seg = float(data["min_seg"])
            self.generate_gcode()

        if command == "editmeta":
            self.selected_file = data["filename"]["path"]
            self.selected_image = data["imagefile"]
            self.update_image()

    def hook_gcode_received(self, comm_instance, line, *args, **kwargs):
        # look for a status message
        if 'MPos' in line or 'WPos' in line:
            self.process_grbl_status_msg(line)
        return line
    
    def process_grbl_status_msg(self, msg):
        #need to redefine much of this if we have more axes

        match = re.search(r'<(-?[^,]+)[,|][WM]Pos:(-?[\d\.]+),(-?[\d\.]+),(-?[\d\.]+),?(-?[\d\.]+)?,?(-?[\d\.]+)?', msg)
        self.currentZ = float(match.groups(1)[3])
        #print(self.currentZ)

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
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.hook_gcode_received,
        "octoprint.filemanager.extension_tree": __plugin_implementation__.get_extension_tree
    }
