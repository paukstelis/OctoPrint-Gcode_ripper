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
        self.scaleFactor = ko.observable(1.0);
        self.modifyA = ko.observable(1);
        self.split_moves = ko.observable(1);
        self.min_seg_length = ko.observable(1.0);
        self.origin = ko.observable("center");
        self.gcodeFiles = ko.observableArray();
        self.selectedGCodeFile = ko.observable("");
        self.selectedImageFile = ko.observable("");
        self.newimage = ko.observable("");
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
                    gcodeFiles.sort((a,b) => { return a.name.localeCompare(b.name) });
                    self.gcodeFiles = gcodeFiles;
                    populateFileSelector(gcodeFiles, "#gcode_file_select", "machinecode");
                })
                .fail(function() {
                    console.error("Failed to fetch GCode files.");
                });
        };

        function fetchImageFiles() {
            $.ajax({
                url: API_BASEURL + "files/local/templates",
                type: "GET",
                success: function(response) {
                    var gcodeFiles = response.children;
                    console.log(gcodeFiles);
                    gcodeFiles.sort((a,b) => { return a.name.localeCompare(b.name) });
                    self.gcodeFiles = gcodeFiles;
                },
                error: function(xhr, status, error) {
                    console.error("Failed to fetch files: ", error);
                }
                
            });
        }

        function populateFileSelector(files, elem, type) {
            var fileSelector = $(elem);
            fileSelector.empty();
            fileSelector.append($("<option>").text("Select file").attr("value", ""));
            var i = 0;
            files.forEach(function(file) {
                if (file.type === type) {
                    var option = $("<option>")
                        .text(file.display)
                        .attr("value", file.name)
                        .attr("download",file.refs.download)
                        .attr("img_url", file.bgs_imgurl)
                        .attr("index", i); // Store metadata in data attribute
                    fileSelector.append(option);
                }
                i++;
            });
        }

        $("#gcode_file_select").on("change", function() {
            //console.log("file selection changed");
            //console.log($(this).val());
            var image_name = $("#gcode_file_select option:selected").attr("img_url");
            var download_path = $("#gcode_file_select option:selected").attr("download");
            var objindex = $("#gcode_file_select option:selected").attr("index");
            self.selectedGCodeFile = self.gcodeFiles[objindex];
            console.log(objindex);
            if (image_name) {
                download_path = download_path.substring(0,download_path.lastIndexOf("/"));
                var fullpath = download_path+"/"+image_name;
                $("#file_image").attr("src", fullpath).show();
            } else {
                $("#file_image").hide();
            }
        });

        $("#edit_meta_list").on("change", function() {
            self.selectedImageFile = $("#edit_meta_list option:selected").attr("value");
            console.log(self.selectedImageFile);
        });

        $("#diameter_input").on("change", function() {
            console.log($(this).val());
        });

        $('#edit_meta_overlay').on('show.bs.modal', function (event) {
            var newtitle = "Assign image for "+self.selectedGCodeFile.name;
            //self.fetchGCodeFiles();
            fetchImageFiles();
            //console.log(self.gcodeFiles);
            populateFileSelector(self.gcodeFiles,"#edit_meta_list","model");
            $(this).find('h4#filetoedit').text(newtitle);
         });
        

        // Function to submit API call with data
        self.writeGCode = function() {
            //get file object
            
            var data = {
                diameter: self.diameter(),
                filename: self.selectedGCodeFile,
                rotationAngle: self.rotationAngle(),
                modifyA: self.modifyA(),
                scalefactor: self.scaleFactor(),
                split_moves: self.split_moves(),
                min_seg: self.min_seg_length(),
                origin: self.origin(),
            };

            OctoPrint.simpleApiCommand("gcode_ripper", "write_gcode", data)
                .done(function(response) {
                    console.log("GCode written successfully.");
                })
                .fail(function() {
                    console.error("Failed to write GCode.");
                });
        };

        self.show_meta_overlay = function() {
            //console.log(self.selectedGCodeFile);
            //probably a better way to check this
            if (self.selectedGCodeFile.name.length < 3) {
                alert("Select a Gcode file from the drop down menu first.");
                return;
            }

            showDialog("#edit_meta_overlay", function(dialog){
                //console.log("Confirmed");
                OctoPrint.simpleApiCommand("gcode_ripper", "editmeta", 
                    {   
                        "filename": self.selectedGCodeFile,
                        "imagefile": self.selectedImageFile
                    });
                    
                    dialog.modal('hide');
            });
        }

        function showDialog(dialogId, confirmFunction){
            var myDialog = $(dialogId);
            var confirmButton = $("button.btn-confirm", myDialog);
            var cancelButton = $("button.btn-cancel", myDialog);
            //var dialogTitle = $("#filetoedit", myDialog);
            //dialogTitle.innerText = title;
            confirmButton.unbind("click");
            confirmButton.bind("click", function() {
                //alert ("Do something");
                confirmFunction(myDialog);
            });
            myDialog.modal({
                //minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });
        }

        self.onBeforeBinding = function () {
            self.fetchGCodeFiles();
            //populateFileSelector(gcodeFiles, "#gcode_file_select", "machinecode");
           
        }

        // Fetch GCode files on initialization
        self.fetchGCodeFiles();
        //populateFileSelector(gcodeFiles, "#gcode_file_select", "machinecode");

        self.updateFiles = function() {
            self.fetchGCodeFiles();
            //populateFileSelector(gcodeFiles, "#gcode_file_select", "machinecode");
        }

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin == 'gcode_ripper' && data.type == 'grbl_state') {
                self.zPos(Number.parseFloat(data.z).toFixed(2));
                self.calc_diameter = (Number.parseFloat(self.diameter()) + (self.zPos()*2));
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
