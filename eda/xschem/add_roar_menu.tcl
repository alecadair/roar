## Add a custom menu in xschem

## Create a menu entry 'Test'.  '.menubar' is xschem's main menu frame.
menubutton .menubar.roar -text "ROAR" -menu .menubar.roar.menu -padx 3 -pady 0
menu .menubar.roar.menu -tearoff 0

## Create a couple of entries
.menubar.roar.menu add command -label "Launch ROAR" -command {
    # Retrieve the ROAR_HOME environment variable (which should be set globally)
    if { [info exists env(ROAR_HOME)] } {
        set roar_home $env(ROAR_HOME)
    } else {
        puts "Error: ROAR_HOME is not set!"
        return
    }
    puts "Launching ROAR"
    set roar_home $env(ROAR_HOME)    
    set roar_py "$roar_home/src/gui4.py"
    puts $roar_home
    puts $roar_py    
    exec python3 $roar_py &    
}
.menubar.roar.menu add command -label "Export Design To ROAR" -command {
    puts "Select Filepath"
}

## make the menu appear in xschem window
pack .menubar.roar -side left
## or place it before some other menu entry:
# pack .menubar.test -before .menubar.file -side left

## To remove the menu without destroying it:
# pack forget .menubar.test


################################################################
## adding a button in the menubar (not in the toolbar) 
################################################################
# button .menubar.test -pady 0 -highlightthickness 0 -text Test -command {puts Test}
# pack  .menubar.test -side left

