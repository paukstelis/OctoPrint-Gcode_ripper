# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util
import re
import os
import math
import shutil
from . import G_Code_Rip as G_Code_Rip

class Gcode_ripperPlugin(octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.EventHandlerPlugin

):
         
    def __init__(self):
        self.template_gcode = []
        self.selected_file = None
        self.currentZ = 0
        self.start_diameter = float(0)
        self.current_diameter = float(0)
        self.rotation = float(0)
        self.modifyA = False
        self.xscalefactor = float(1)
        self.ascalefactor = float(1)
        self.origin = "center"
        self.mapping = "Y2A"
        self.chord = False
        self.split_moves = True
        self.min_seg = 1.0
        self.datafolder = None
        self.template_name = None
        self.zrelative = False
        #self.watched_path = self._settings.global_get_basefolder("watched")
    ##~~ SettingsPlugin mixin
    def initialize(self):
        self._event_bus.subscribe("LATHEENGRAVER_SEND_POSITION", self.get_position)
        storage = self._file_manager._storage("local")
        if storage.folder_exists("templates"):
            self._logger.info("Scans exists")
        else:
            storage.add_folder("templates")
            templates_folder = os.path.join(self._settings.getBaseFolder("uploads"), "templates")
            source_folder = os.path.join(self._basefolder, "static", "gcode")
            if os.path.exists(source_folder):
                for file_name in os.listdir(source_folder):
                    if file_name.endswith(".gcode"):
                        source_file = os.path.join(source_folder, file_name)
                        destination_file = os.path.join(templates_folder, file_name)
                        shutil.copy(source_file, destination_file)
                        self._logger.info(f"Copied {file_name} to templates folder")

    #integrated directly from upload anything plugin by 
    @property
    def allowed(self):
        if self._settings is None:
            return ""
        else:
            return str(self._settings.get(["allowed"]))
        
    def get_settings_defaults(self):
            return ({'allowed': 'png, gif, jpg, txt, stl'})

    def get_extension_tree(self, *args, **kwargs):
        #return dict(model=dict(uploadanything=[x for x in self.allowed.replace(" ", "").split(",") if x != '']))
        return {'model': {'png': ["png", "jpg", "jpeg", "gif", "txt", "stl"]}}
    

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/gcode_ripper.js"],
            "css": ["css/gcode_ripper.css"],
            "less": ["less/gcode_ripper.less"]
        }

    def get_position(self, event, payload):
        #self._logger.info(payload)
        self.currentZ = payload["z"]

    ##~~ Softwareupdate hook
    def _get_templates(self):
        self.template_gcode = []
        #print("Getting template gcodes from data directory")
        for file in os.listdir(self.datafolder):
            if file.endswith('.gcode'):
                self.template_gcode.append(file)

    def generate_name(self):
        #abbreviate origin
        ori = self.origin[0].upper()
        wrapdiam = self.calc_diameter()
        output_name = f"D{int(wrapdiam)}_R{int(self.rotation)}_Ori{ori}_"
        return output_name
    
    def generate_gcode(self):
        gcr = G_Code_Rip.G_Code_Rip()
        gcode_file = self.selected_file
        gcr.Read_G_Code("{}/{}".format(self._settings.getBaseFolder("uploads"), gcode_file), XYarc2line=True, units="mm")
        self.mapping = "Y2A"
        polar = False
        wrapdiam = self.calc_diameter()
        output_name = self.generate_name()
        output_path = output_name+self.template_name
        path_on_disk = "{}/{}".format(self._settings.getBaseFolder("watched"), output_path)
        xsf = self.xscalefactor
        asf = self.ascalefactor
        #self._logger.info(gcr.g_code_data[0])
        temp,minx,maxx,miny,maxy,minz,maxz  = gcr.scale_rotate_code(gcr.g_code_data,[xsf,asf,1,1],self.rotation,split_moves=self.split_moves,min_seg_length=self.min_seg)
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
        #chord check, revisit what values need to be checked
        if wrapdiam < math.sqrt(miny**2 + maxy**2):
            self.chord = False
            self._logger.info("Failed chord check, defaulting to diameter")

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

        pre = "RTCM\nDOBANGLE\nDIAM {0}\n".format(wrapdiam)

        if self.origin == "left":
            pre = pre + "ORIGIN LEFT\n"

        if self.modifyA and not polar:
            pre = pre + "DOMODA\nMAXARC {0:.3f}".format(maxarc)

        with open(path_on_disk,"w") as newfile:
            for line in gcr.generategcode(temp, 
                                          Rstock=wrapdiam/2, 
                                          no_variables=True, 
                                          Wrap=self.mapping, 
                                          preamble=pre, 
                                          chord=self.chord, 
                                          postamble="STOPBANGLE", 
                                          FSCALE="None"):
                newfile.write(f"\n{line}")

        d = dict(title="Gcode Written",text="Gcode has been written and will appear in the file section shortly.",type="info")
        self.send_le_message(d)
    
    def calc_diameter(self):
        if self.zrelative:
            return self.start_diameter + 2*(self.currentZ)
        else:
            return self.start_diameter
        
    def update_image(self):
        self._file_manager.set_additional_metadata("local",self.selected_file,"bgs_imgurl",self.selected_image,overwrite=True)
    
    def is_api_protected(self):
        return True
    
    def get_api_commands(self):
        return dict(
            write_gcode=[],
            editmeta=[]
        )
    
    def on_event(self, event, payload):
        if event == "plugin_latheengraver_send_position":
            self.get_position(event, payload)

    def on_api_command(self, command, data):
        
        if command == "write_gcode":
            #print(data)
            self.selected_file = data["filename"]["path"]
            self.template_name = data["filename"]["display"]
            self.start_diameter = float(data["diameter"])
            self.rotation = float(data["rotationAngle"])
            self.modifyA = bool(data["modifyA"])
            self.chord = bool(data["chord"])
            self.xscalefactor = float(data["xscalefactor"])
            self.ascalefactor = float(data["ascalefactor"])
            self.origin = data["origin"]
            self.mapping = "Y2A"
            self.split_moves = bool(data["split_moves"])
            self.min_seg = float(data["min_seg"])
            self.zrelative = bool(data["zrelative"])
            self.generate_gcode()

        if command == "editmeta":
            self.selected_file = data["filename"]["path"]
            self.selected_image = data["imagefile"]
            self.update_image()

    def send_le_message(self, data):
        
        payload = dict(
            type="simple_notify",
            title=data["title"],
            text=data["text"],
            hide=True,
            delay=10000,
            notify_type=data["type"]
        )

        self._plugin_manager.send_plugin_message("latheengraver", payload)

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
        "octoprint.filemanager.extension_tree": __plugin_implementation__.get_extension_tree
    }
