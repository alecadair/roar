#!/usr/bin/tclsh

# Set the netlist output file path
set netlist_file "xschem_netlist.spice"

# Set the instance list output file path
set output_file "xschem_instance_list.txt"

# Generate the netlist using xschem's built-in netlisting command
xschem::netlist -file $netlist_file

# Open the output file for writing instance list
set out_fp [open $output_file "w"]

# Print header in the output file
puts $out_fp "Instance List for Schematic"
puts $out_fp "----------------------------\n"

# Open the netlist file for reading
set netlist_fp [open $netlist_file "r"]

# Read the netlist file line by line
while {[gets $netlist_fp line] >= 0} {
    # Check if the line contains an instance (typically starts with X, M, R, C, etc.)
    if {[regexp {^[XMRCLV]} $line]} {
        # Extract the instance name and component (first two tokens)
        set tokens [split $line]
        set instance_name [lindex $tokens 0]
        set component [lindex $tokens 1]

        # Print the instance name and component to the output file
        puts $out_fp "Instance: $instance_name"
        puts $out_fp "Component: $component"

        # Print the remaining tokens as parameters
        set param_list [lrange $tokens 2 end]
        puts $out_fp "Parameters: $param_list"

        # Add a separator for readability
        puts $out_fp "----------------------------\n"
    }
}

# Close both files
close $netlist_fp
close $out_fp

# Inform the user that the export is complete
puts "Instance list has been exported to $output_file"

