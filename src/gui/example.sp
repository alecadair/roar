* Differential Pair Example
.subckt diff_pair in1 in2 vdd vss out1 out2
M1 out1 in1 vss vss nmos W=1u L=180n
M2 out2 in2 vss vss nmos W=1u L=180n
M3 out1 out2 vdd vdd pmos W=2u L=180n
M4 out2 out1 vdd vdd pmos W=2u L=180n
.ends diff_pair

* Testbench
VDD vdd 0 1.8V
VSS vss 0 0V
VIN1 in1 0 DC 0.9V AC 1m
VIN2 in2 0 DC 0.9V AC 1m
X1 in1 in2 vdd vss out1 out2 diff_pair
.tran 1n 10n
.ac dec 10 1K 1G
.end
