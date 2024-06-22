/*
 * View model for OctoPrint-Gcode_ripper
 *
 * Author: PP
 * License: AGPLv3
 */
$(function() {
    function Gcode_ripperViewModel(parameters) {
        var self = this;
        self.files = parameters[0].listHelper
        self.diameter = ko.observable(0);
        self.calc_diameter = ko.observable(0);
        self.rotationAngle = ko.observable(0);
        self.modifyA = ko.observable(1);
        self.scaleFactor = ko.observable(1);
        self.gcodeFiles = ko.observableArray();
        self.selectedGCodeFile = ko.observable("");
        self.thumbnail_url = ko.observable('/static/img/tentacle-20x20.png');
        self.xPos = ko.observable("");
        self.yPos = ko.observable("");
        self.zPos = ko.observable("");

        tab = document.getElementById("tab_plugin_gcode_ripper_link");
        tab.innerHTML = tab.innerHTML.replace("Gcode_ripper Plugin", "GCode Templates");

        // Function to fetch list of GCode files
        self.fetchGCodeFiles = function() {
            OctoPrint.files.listForLocation("local/templates", false)
                .done(function(data) {
                    var gcodeFiles = data.children
                    console.log(gcodeFiles);
                    self.gcodeFiles = gcodeFiles;
                })
                .fail(function() {
                    console.error("Failed to fetch GCode files.");
                });
        };

        // Function to submit API call with data
        self.writeGCode = function() {
            var data = {
                diameter: self.diameter(),
                filename: self.selectedGCodeFile(),
                rotationAngle: self.rotationAngle(),
                modifyA: self.modifyA(),
                scalefactor: self.scaleFactor(),
            };

            OctoPrint.simpleApiCommand("gcode_ripper", "write_gcode", data)
                .done(function(response) {
                    console.log("GCode written successfully.");
                })
                .fail(function() {
                    console.error("Failed to write GCode.");
                });
        };
        self.onBeforeBinding = function () {
            self.fetchGCodeFiles();
        }
        // Fetch GCode files on initialization
        self.fetchGCodeFiles();
    }
    

    self.updateDiameter = function() {
        self.calc_diameter = self.diameter + 2*self.zPos;
        return self.calc_diameter;
    }

    self.updateThumb = function() {
        imagepath = self.selectedGCodeFile
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: Gcode_ripperViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ["filesViewModel","accessViewModel"],
        // Elements to bind to, e.g. #settings_plugin_gcode_ripper, #tab_plugin_gcode_ripper, ...
        elements: [ "#tab_plugin_gcode_ripper","#tab_plugin_bettergrblsupport" ]
    });
});
