set pdk_root $env(PDK_ROOT)
set roar_home $env(ROAR_HOME)
set roar_eda $env(ROAR_EDA)
set roar_design $env(ROAR_DESIGN)

source $roar_eda/sky130.magicrc
gds read $roar_design/cm_ota/gds_25c/cm_ota_align/CURRENT_MIRROR_OTA_0.gds
load CURRENT_MIRROR_OTA_0
extract unique
extract all
ext2spice
exit

