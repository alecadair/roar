.subckt current_mirror_ota vss vdd vout vinn vinp id
M10 id id vss vss sky130_fd_pr__nfet_01v8 L=500e-9 w=4.2e-7 nf=20
M9 source id vss vss sky130_fd_pr__nfet_01v8 L=500e-9 w=4.2e-7 nf=20
M1 ds1 vinn source vss sky130_fd_pr__nfet_01v8 L=500e-9 w=4.2e-7 nf=20
M2 ds2 vinp source vss sky130_fd_pr__nfet_01v8 L=500e-9 w=4.2e-7 nf=20
M3 ds1 ds1 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-9 w=4.2e-7 nf=6
M4 ds2 ds2 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-9 w=4.2e-7 nf=6
M5 ds3 ds3 vss vss sky130_fd_pr__nfet_01v8 L=500e-9 w=4.2e-7 nf=160
M6 vout ds3 vss vss sky130_fd_pr__nfet_01v8 L=500e-9 w=4.2e-7 nf=160
M7 ds3 ds1 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-9 w=4.2e-7 nf=48
M8 vout ds2 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-9 w=4.2e-7 nf=48
.ends current_mirror_ota
