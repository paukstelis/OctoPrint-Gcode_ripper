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
        self.zPos = ko.observable("");

        tab = document.getElementById("tab_plugin_gcode_ripper_link");
        tab.innerHTML = tab.innerHTML.replaceAll("Gcode_ripper Plugin", "GCode Templates");

        // Function to fetch list of GCode files
        self.fetchGCodeFiles = function() {
            OctoPrint.files.listForLocation("local/templates", false)
                .done(function(data) {
                    var gcodeFiles = data.children
                    //console.log(gcodeFiles);
                    self.gcodeFiles = gcodeFiles;
                    populateFileSelector(gcodeFiles);
                })
                .fail(function() {
                    console.error("Failed to fetch GCode files.");
                });
        };

        function populateFileSelector(files) {
            var fileSelector = $("#gcode_file_select");
            fileSelector.empty();
            fileSelector.append($("<option>").text("Select a G-code file").attr("value", ""));
            files.forEach(function(file) {
                if (file.type === "machinecode") {
                    var option = $("<option>")
                        .text(file.display)
                        .attr("value", file.name)
                        .attr("download",file.refs.download)
                        .attr("img_url", file.bgs_imgurl)
                        .attr("complete", file); // Store metadata in data attribute
                    fileSelector.append(option);
                }
            });
        }
    
        $("#gcode_file_select").on("change", function() {
            //console.log("file selection changed");
            self.selectedGCodeFile = $(this).complete();
            console.log($(this).val());
            var image_name = $("#gcode_file_select option:selected").attr("img_url");
            var download_path = $("#gcode_file_select option:selected").attr("download");
            if (image_name) {
                download_path = download_path.substring(0,download_path.lastIndexOf("/"));
                var fullpath = download_path+"/"+image_name;
                $("#file_image").attr("src", fullpath).show();
            } else {
                $("#file_image").hide();
            }
        });

        $("#diameter_input").on("change", function() {
            console.log($(this).val());
        });

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

        self.updateFiles = function() {
            self.fetchGCodeFiles();
        }

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin == 'gcode_ripper' && data.type == 'grbl_state') {
                self.zPos(Number.parseFloat(data.z).toFixed(2));
                self.calc_diameter() = (Number.parseFloat(self.diameter()) + (self.zPos()*2));
                //console.log(newDiam);
            }
        }        
    }
    

    OCTOPRINT_VIEWMODELS.push({
        construct: Gcode_ripperViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ["filesViewModel","accessViewModel"],
        // Elements to bind to, e.g. #settings_plugin_gcode_ripper, #tab_plugin_gcode_ripper, ...
        elements: [ "#tab_plugin_gcode_ripper", ]
    });
});
