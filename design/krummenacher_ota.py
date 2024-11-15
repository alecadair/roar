import sys, os, getpass, shutil, operator, collections, copy, re, math

sys.path.append('/home/aadair/Documents/GradSchoolGeneral/LCAS/ICU')
from cid import *

def parallel(x1, x2):
    return 1/((1/x1) + 1/x2)

def magic_equation_nmos_diode_pload(ncorner, pcorner, gbw, cload, show_plot=False, new_plot=True, ax1=None, fig1=None, color="blue"):
    graph_data_x = []
    graph_data_y = []
    #graph = show_plot
    min_ids = 1000000000
    kgm_col_n  = ncorner.df["kgm"]
    cgg_col_n = ncorner.df["cgg"]
    kcgd_col_n = ncorner.df["kcgd"]
    ids_col_n = ncorner.df["ids"]
    kgm_col_p = pcorner.df["kgm"]
    cgg_col_p = pcorner.df["cgg"]
    kcgd_col_p = pcorner.df["kcgd"]
    ids_col_p = pcorner.df["ids"]
    kgm_col_inv = kgm_col_n/kgm_col_p
    kcgd_col_inv = kcgd_col_n + kcgd_col_p
    kcgg_col_n = ncorner.df["kcgg"]
    kcgg_col_p = pcorner.df["kcgg"]
    kcgg_col_inv = kcgg_col_n + kcgg_col_p
    #print(kcgd_col)
    #print(self.df)
    kgm_opt = 0
    for i in range(len(kgm_col_inv)):
        kcgd = kcgg_col_inv[i]
        #cgg = cgg_col[i]
        kgm = kgm_col_inv[i]
        strong_inv = 2*math.pi*gbw*cload/kgm
        #weak_inv = (1 - (2*math.pi*(kcgd/kgm)))*kgm
        weak_inv = 1/(1 - (2*math.pi*gbw*kcgd)/kgm)
        ids = strong_inv*weak_inv
        #if show_plot:
        if ids >= 0:
            graph_data_y.append(ids)
            graph_data_x.append(kgm)
        if ids <= min_ids and ids > 0:
            min_ids = ids
            kgm_opt = kgm
    if show_plot:
        if new_plot:
            fig1, ax1 = plt.subplots()
            plt.plot(graph_data_x, graph_data_y, color=color)
            if show_plot == True:
                plt.show()
            #plt.savefig("magic_equation.png")
        else:
            ax1.plot(graph_data_x, graph_data_y, color=color)
        ax1.set_xlabel("kgm")
        ax1.set_ylabel("id")
    return min_ids, kgm_opt

def magic_equation_inverter(ncorner, pcorner, gbw, cload, show_plot=False, new_plot=True, ax1=None, fig1=None, color="blue"):
    graph_data_x = []
    graph_data_y = []
    #graph = show_plot
    min_ids = 1000000000
    kgm_col_n  = ncorner.df["kgm"]
    cgg_col_n = ncorner.df["cgg"]
    kcgd_col_n = ncorner.df["kcgd"]
    ids_col_n = ncorner.df["ids"]
    kgm_col_p = ncorner.df["kgm"]
    cgg_col_p = ncorner.df["cgg"]
    kcgd_col_p = ncorner.df["kcgd"]
    ids_col_p = ncorner.df["ids"]
    kgm_col_inv = kgm_col_n + kgm_col_p
    kcgd_col_inv = kcgd_col_n + kcgd_col_p
    kcgg_col_n = ncorner.df["kcgg"]
    kcgg_col_p = pcorner.df["kcgg"]
    kcgg_col_inv = kcgg_col_n + kcgg_col_p
    #print(kcgd_col)
    #print(self.df)
    kgm_opt = 0
    for i in range(len(kgm_col_inv)):
        kcgd = kcgg_col_inv[i]
        #cgg = cgg_col[i]
        kgm = kgm_col_inv[i]
        strong_inv = 2*math.pi*gbw*cload/kgm
        #weak_inv = (1 - (2*math.pi*(kcgd/kgm)))*kgm
        weak_inv = 1/(1 - (2*math.pi*gbw*kcgd)/kgm)
        ids = strong_inv*weak_inv
        #if show_plot:
        if ids >= 0:
            graph_data_y.append(ids)
            graph_data_x.append(kgm)
        if ids <= min_ids and ids > 0:
            min_ids = ids
            kgm_opt = kgm
    if show_plot:
        if new_plot:
            fig1, ax1 = plt.subplots()
            plt.plot(graph_data_x, graph_data_y, color=color)
            if show_plot == True:
                plt.show()
            #plt.savefig("magic_equation.png")
        else:
            ax1.plot(graph_data_x, graph_data_y, color=color)
        ax1.set_xlabel("kgm")
        ax1.set_ylabel("id")
        ax1.set_title("Inverter Based Amplifer Id vs Kgm C Load = 500fF")
    return min_ids, kgm_opt
# Design function for Krummenacher OTA

def krummenechar_ota_stage1(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    av = 1.37
    bw = 100e6
    gbw = bw *av
    cload = 50e-15
    ids_min, kgm1 = nfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    ids_minp, kgm1p = pfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    #ids_minratio, kgmratio = magic_equation_nmos_diode_pload(ncorner=nom_ncorner, pcorner=nom_pcorner,
    #                                                gbw=gbw, cload=cload, show_plot=True, new_plot=True, ax1=None, fig1=None,
    #                                color="blue")
    kgm1p = kgm1/av
    gm2p = kgm1p * ids_minp
    iden2p = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm1p)
    w2p = ids_minp/iden2p
    gm1 = kgm1 * ids_min
    vdd = 0.9
    vds = vdd/2
    kgm2 = kgm1/av
    #kgm2 = kgm1p - 4.4
    iden1 = nom_ncorner.lookup(param1="kgm", param2="iden", param1_val=kgm1)
    w1 = ids_min/iden1
    gm2 = kgm2 * ids_min
    iden2 = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm2)
    w2 = ids_min/iden2
    return w1, gm1, kgm1, w2, gm2, kgm2

def krummenechar_ota_stage2(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    av = 1.3
    bw = 100e6
    gbw = bw *av
    cload = 50e-15
    ids_min, kgm1 = pfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    ids_minp, kgm1p = pfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    #ids_minratio, kgmratio = magic_equation_nmos_diode_pload(ncorner=nom_ncorner, pcorner=nom_pcorner,
    #                                                gbw=gbw, cload=cload, show_plot=True, new_plot=True, ax1=None, fig1=None,
    #                                color="blue")
    kgm1p = kgm1/av
    gm2p = kgm1p * ids_minp
    iden2p = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm1p)
    w2p = ids_minp/iden2p
    gm1 = kgm1 * ids_min
    vdd = 0.9
    vds = vdd/2
    kgm2 = kgm1/av
    #kgm2 = kgm1p - 4.4
    iden1 = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm1)
    w1 = ids_min/iden1
    gm2 = kgm2 * ids_min
    iden2 = nom_ncorner.lookup(param1="kgm", param2="iden", param1_val=kgm2)
    w2 = ids_min/iden2
    return w1, gm1, kgm1, w2, gm2, kgm2

def krummenechar_ota_stage3(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    gbw = av*bw
    ids_min, kgm8_7 = magic_equation_inverter(ncorner=nom_ncorner, pcorner=nom_pcorner,
                                             gbw=gbw, cload=cload, show_plot=True, new_plot=True,
                                             ax1=None, fig1=None, color="blue")
    gbw = bw *av
    #ids_min, kgm7 = nfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    #ids_min, kgm8 = pfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    kgm8 = kgm8_7/2
    kgm7 = kgm8_7/2
    gm8 = kgm8 * ids_min
    iden8 = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm8)
    iden7 = nom_ncorner.lookup(param1="kgm", param2="iden", param1_val=kgm7)

    w8 = ids_min/iden8
    w7 = ids_min/iden7
    w6 = w8
    w8 = w7
    kcgd7 = nom_ncorner.lookup(param1="kgm", param2="kcgg", param1_val=kgm7)
    kcgd8 = nom_pcorner.lookup(param1="kgm", param2="kcgg", param1_val=kgm8)
    cgd8 = kcgd8*ids_min
    cgd7 = kcgd7*ids_min
    gm9 = kgm7 * ids_min
    vdd = 0.9
    vds = vdd/2
    #kgm2 = kgm1/av - 2/vds
    #iden1 = nom_ncorner.lookup(param1="kgm", param2="iden", param1_val=kgm1)
    #w1 = ids_min/iden1
    #gm2 = kgm2 * ids_min
    #iden2 = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm2)
    #w2 = ids_min/iden2
    return 0
    return w1, gm1, kgm1, w2, gm2, kgm2

def krummenechar_ota_stage1_device(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    gbw = bw * av
    ids_min, kgm_opt = nfet_device.magic_equation(gbw, cload=cload, epsilon=5)
    cid_corner = nom_ncorner
    pcorner = nom_pcorner
    vgs_m1 = nom_ncorner.lookup(param1="kgm", param2="VGS", param1_val=kgm_opt)

    #ids_min, kgm_opt = cid_corner.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=True)
    gm = kgm_opt * ids_min
    #kgm_opt = 20
    #ids_min = 30e-06
    #ids_min = cid_corner.lookup(param1="kgm", param2="ids", param1_val=kgm_opt)
    #gm = kgm_opt*ids_min

    #kgm_opt = 20.0

    #gm = kgm_opt * ids_min
    iden_input = cid_corner.lookup(param1="kgm", param2="iden", param1_val=kgm_opt)
    width_input = ids_min / iden_input
    ro_1 = cid_corner.lookup(param1="kgm", param2="ro", param1_val=kgm_opt)
    g_load = gm / av - 1 / ro_1
    r_load = 1 / g_load
    # This lookup needs to be for p type device
    kgm_load = pcorner.lookup(param1="ro", param2="kgm", param1_val=r_load)
    kgm_load = kgm_opt/2
    iden_load = pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm_load)
    width_load = ids_min / iden_load
    print(str(ids_min) + " " + str(kgm_opt))
    kgm_input = kgm_opt
    width_input = width_input
    width_load = width_load
    return width_input, kgm_input, width_load, kgm_load

def krummenechar_ota_stage1mm(av, bw, cload, cid_corner, pcorner):
    gbw = bw * av

    ids_min, kgm_opt = cid_corner.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=True)
    gm = kgm_opt * ids_min
    #kgm_opt = 20
    #ids_min = 30e-06
    #ids_min = cid_corner.lookup(param1="kgm", param2="ids", param1_val=kgm_opt)
    #gm = kgm_opt*ids_min

    #kgm_opt = 20.0

    #gm = kgm_opt * ids_min
    iden_input = cid_corner.lookup(param1="kgm", param2="iden", param1_val=kgm_opt)
    width_input = ids_min / iden_input
    ro_1 = cid_corner.lookup(param1="kgm", param2="ro", param1_val=kgm_opt)
    g_load = gm / av - 1 / ro_1
    r_load = 1 / g_load
    # This lookup needs to be for p type device
    kgm_load = pcorner.lookup(param1="ro", param2="kgm", param1_val=r_load)
    kgm_load = kgm_opt/3
    iden_load = pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm_load)
    width_load = ids_min / iden_load
    print(str(ids_min) + " " + str(kgm_opt))
    kgm_input = kgm_opt
    width_input = width_input
    width_load = width_load
    return width_input, kgm_input, width_load, kgm_load

def krummenechar_ota_stage2fds(av, bw, cload, cid_corner, pcorner):
    gbw = bw * av

    ids_min, kgm_opt = cid_corner.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=True)
    gm = kgm_opt * ids_min
    # kgm_opt = 20
    # ids_min = 30e-06
    # ids_min = cid_corner.lookup(param1="kgm", param2="ids", param1_val=kgm_opt)
    # gm = kgm_opt*ids_min

    # kgm_opt = 20.0

    # gm = kgm_opt * ids_min
    iden_input = cid_corner.lookup(param1="kgm", param2="iden", param1_val=kgm_opt)
    width_input = ids_min / iden_input
    ro_1 = cid_corner.lookup(param1="kgm", param2="ro", param1_val=kgm_opt)
    g_load = gm / av - 1 / ro_1
    r_load = 1 / g_load
    # This lookup needs to be for p type device
    kgm_load = pcorner.lookup(param1="ro", param2="kgm", param1_val=r_load)
    kgm_load = kgm_opt / 3
    iden_load = pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm_load)
    width_load = ids_min / iden_load
    print(str(ids_min) + " " + str(kgm_opt))
    kgm_input = kgm_opt
    width_input = width_input
    width_load = width_load
    return width_input, kgm_input, width_load, kgm_load

    # Instantiate Corner Lookup


# cid_test_corner = CIDCorner(corner_name="tt28",
#                                lut_csv="/home/aadair/Documents/GradSchoolGeneral/LCAS/ICU/UU_github_release/lookup_tables/tsmc_n_lvt_100n_27c_tt.csv",
#                                vdd=0.9)

lookup_table_dir = "/research/ece/lcas/prj/jp28/adair/characterization/lookuptables_short_l/"
lookup_table_dir_short_l = "/research/ece/lcas/prj/jp28/adair/characterization/lookuptables_short_l/"
lookup_table_dir_med_l = "/research/ece/lcas/prj/jp28/adair/characterization/lookuptables_med_l/"
lookup_table_dir_long_l = "/research/ece/lcas/prj/jp28/adair/characterization/lookuptables_long_l/"
lookup_table_dir = lookup_table_dir_long_l


nsscold = CIDCorner(corner_name="nsscold_minl",
                   lut_csv=lookup_table_dir + "nfetsscold.csv",
                   vdd=0.9)
nttcold = CIDCorner(corner_name="nttcold_minl",
                   lut_csv=lookup_table_dir + "nfetttcold.csv",
                   vdd=0.9)
nffcold = CIDCorner(corner_name="nffcold_minl",
                   lut_csv=lookup_table_dir + "nfetffcold.csv",
                   vdd=0.9)
nssroom = CIDCorner(corner_name="nssroom_minl",
                   lut_csv=lookup_table_dir + "nfetssroom.csv",
                   vdd=0.9)
nttroom = CIDCorner(corner_name="nttroom_minl",
                   lut_csv=lookup_table_dir + "nfetttroom.csv",
                   vdd=0.9)
nffroom = CIDCorner(corner_name="nffroom_minl",
                   lut_csv=lookup_table_dir + "nfetffroom.csv",
                   vdd=0.9)
nsshot = CIDCorner(corner_name="nsshot_minl",
                  lut_csv=lookup_table_dir + "nfetsshot.csv",
                  vdd=0.9)

ntthot = CIDCorner(corner_name="ntthot_minl",
                                lut_csv=lookup_table_dir +"nfettthot.csv",
                                vdd=0.9)
nffhot = CIDCorner(corner_name="nffhot_minl",
                  lut_csv=lookup_table_dir + "nfetffhot.csv",
                  vdd=0.9)


psscold = CIDCorner(corner_name="psscold_minl",
                   lut_csv=lookup_table_dir + "pfetsscold.csv",
                   vdd=0.9)
pttcold = CIDCorner(corner_name="pttcold_minl",
                   lut_csv=lookup_table_dir + "pfetttcold.csv",
                   vdd=0.9)
pffcold = CIDCorner(corner_name="pffcold_minl",
                   lut_csv=lookup_table_dir + "pfetffcold.csv",
                   vdd=0.9)
pssroom = CIDCorner(corner_name="pssroom_minl",
                   lut_csv=lookup_table_dir + "pfetssroom.csv",
                   vdd=0.9)
pttroom = CIDCorner(corner_name="pttroom_minl",
                   lut_csv=lookup_table_dir + "pfetttroom.csv",
                   vdd=0.9)
pffroom = CIDCorner(corner_name="pffroom_minl",
                   lut_csv=lookup_table_dir + "pfetffroom.csv",
                   vdd=0.9)
psshot = CIDCorner(corner_name="psshot_minl",
                  lut_csv=lookup_table_dir + "pfetsshot.csv",
                  vdd=0.9)

ptthot = CIDCorner(corner_name="ptthot_minl",
                                lut_csv=lookup_table_dir +"pfettthot.csv",
                                vdd=0.9)
pffhot = CIDCorner(corner_name="pffhot_minl",
                  lut_csv=lookup_table_dir + "pfetffhot.csv",
                  vdd=0.9)

n_short_tt_room = CIDCorner(corner_name="nttroom_shortl",
                   lut_csv=lookup_table_dir_short_l + "nfetttroom.csv",
                   vdd=0.9)

p_short_tt_room = CIDCorner(corner_name="pttroom_medl",
                   lut_csv=lookup_table_dir_short_l + "pfetttroom.csv",
                   vdd=0.9)


n_med_tt_room = CIDCorner(corner_name="nttroom_medl",
                   lut_csv=lookup_table_dir_med_l + "nfetttroom.csv",
                   vdd=0.9)

p_med_tt_room = CIDCorner(corner_name="pttroom_medl",
                   lut_csv=lookup_table_dir_med_l + "pfetttroom.csv",
                   vdd=0.9)

n_med_tt_cold = CIDCorner(corner_name="nttcold_medl",
                   lut_csv=lookup_table_dir_med_l + "nfetttcold.csv",
                   vdd=0.9)

p_med_tt_cold = CIDCorner(corner_name="pttcold_medl",
                   lut_csv=lookup_table_dir_med_l + "pfetttcold.csv",
                   vdd=0.9)

n_med_tt_hot = CIDCorner(corner_name="ntthot_medl",
                   lut_csv=lookup_table_dir_med_l + "nfettthot.csv",
                   vdd=0.9)

p_med_tt_hot = CIDCorner(corner_name="pttcold_medl",
                   lut_csv=lookup_table_dir_med_l + "pfettthot.csv",
                   vdd=0.9)


n_long_tt_room = CIDCorner(corner_name="nttroom_longl",
                   lut_csv=lookup_table_dir_long_l + "nfetttroom.csv",
                   vdd=0.9)

p_long_tt_room = CIDCorner(corner_name="pttroom_longl",
                   lut_csv=lookup_table_dir_long_l + "pfetttroom.csv",
                   vdd=0.9)

n_long_tt_hot = CIDCorner(corner_name="ntthot_longl",
                   lut_csv=lookup_table_dir_long_l + "nfettthot.csv",
                   vdd=0.9)

p_long_tt_hot = CIDCorner(corner_name="ptthot_longl",
                   lut_csv=lookup_table_dir_long_l + "pfettthot.csv",
                   vdd=0.9)

fig1, ax1 = plt.subplots()

# Choose Target Length
# Get Closest Length Available in LUT
# l = cid_test_corner.get_bucket_for_length("nfet", target_l)

# set specifications of amplifier
# noise to be added, all fixed length devices for now
av = 225
bw = 2e06
cload1 = 250e-15
cload2 = 250e-15
gbw = bw * av


color_list = ['red', 'blue', 'green', 'yellow', 'magenta', 'black', 'purple']
ncorner_list = [nsscold, nttcold, nffcold, nssroom, nttroom, nffroom, nsshot, nffhot]
pcorner_list = [psscold, pttcold, pffcold, pssroom, pttroom, pffroom, psshot, pffhot]
#ncorner_list = [n_long_tt_room]
color_index = 0
cid_test_corner = ntthot
pcorner = psshot
#cid_test_corner.plot_processes_params("kgm", "kcgs", show_plot=True)
#cid_test_corner.plot_processes_params("kgm", "dkcgs", show_plot=True)
#cid_test_corner.plot_processes_params("kgm", "iden", show_plot=True)
#cid_test_corner.plot_processes_params("kgm", "gmro", show_plot=True)

tsmc28_luts = "/research/ece/lcas/prj/jp28/adair/characterization/"
short_l_nfet = CIDDevice(device_name="short_l_nfet", vdd=0.9,
                         lut_directory=tsmc28_luts + "lookuptables_short_l/nfet_lookuptables_short_l",
                         corner_list=None)

med_l_nfet = CIDDevice(device_name="med_l_nfet", vdd=0.9,
                       lut_directory=tsmc28_luts + "lookuptables_med_l/nfet_lookuptables_med_l",
                       corner_list=None)

long_l_nfet = CIDDevice(device_name="long_l_nfet", vdd=0.9,
                        lut_directory=tsmc28_luts + "lookuptables_long_l/nfet_lookuptables_long_l",
                        corner_list=None)

short_l_pfet = CIDDevice(device_name="short_l_pfet", vdd=0.9,
                         lut_directory=tsmc28_luts + "lookuptables_short_l/pfet_lookuptables_short_l",
                         corner_list=None)

med_l_pfet = CIDDevice(device_name="med_l_pfet", vdd=0.9,
                       lut_directory=tsmc28_luts + "lookuptables_med_l/pfet_lookuptables_med_l",
                       corner_list=None)

long_l_pfet = CIDDevice(device_name="long_l_pfet", vdd=0.9,
                        lut_directory=tsmc28_luts + "lookuptables_long_l/pfet_lookuptables_long_l",
                        corner_list=None)
av1 = math.sqrt(av)


legends = []
for corner in long_l_nfet.corners:
    av1 = math.sqrt(av)
    gbw = av1*bw
    if color_index >= len(color_list):
        color_index = 0
    #corner = ncorner_list[i]
    corner.magic_equation(gbw=gbw, cload=cload1, show_plot=True, new_plot=False,
                          fig1=fig1, ax1=ax1, color=color_list[color_index])
    color_index = color_index + 1
ax1.set_ylabel("Drain Current")
ax1.set_xlabel("gm/Id")
ax1.set_title("Drain Current vs gm/Id, C Load = 500fF")
plt.show()
av1 = 1.75
bw = 3e6
cload1 = 500e-15
cload3 = 500e-15
av3 =20
bw3 = 2e6

w_in1, gm1, kgm_in1, w_load1, gmload, kgm_load1 = krummenechar_ota_stage1(av=av1, bw=bw, cload=cload1,
                                                                    nfet_device=long_l_nfet,
                                                                    pfet_device=short_l_pfet,
                                                                    nom_ncorner=n_long_tt_room,
                                                                    nom_pcorner=p_long_tt_room)
w_in1, gm1, kgm_in1, w_load1, gmload, kgm_load1 = krummenechar_ota_stage2(av=av1, bw=bw, cload=cload1,
                                                                    nfet_device=long_l_nfet,
                                                                    pfet_device=short_l_pfet,
                                                                    nom_ncorner=n_long_tt_room,
                                                                    nom_pcorner=p_long_tt_room)
krummenechar_ota_stage3(av=av3, bw=bw3, cload=cload3, nfet_device=med_l_nfet,
                        pfet_device=med_l_pfet, nom_ncorner=n_med_tt_room, nom_pcorner=p_med_tt_room)

cload1 = 100e-15
w6, gm6, kgm6, w5, gm5, kgm5 = krummenechar_ota_stage2(av=av1, bw=bw, cload=cload1,
                                                             nfet_device=long_l_nfet,
                                                             pfet_device=long_l_pfet,
                                                             nom_ncorner=n_long_tt_room,
                                                             nom_pcorner=p_long_tt_room)

cload1 = 50e-15
w1, gm1, kgm1, w2, gm2, kgm2 = krummenechar_ota_stage1(av=av1, bw=bw, cload=cload1, nfet_device=long_l_nfet,
                                                       pfet_device=long_l_pfet, nom_ncorner=n_long_tt_room, nom_pcorner=p_long_tt_room)



"""
for i in range(len(ncorner_list)):
    av1 = math.sqrt(av)
    gbw = av1*bw
    if color_index >= len(color_list):
        color_index = 0
    corner = ncorner_list[i]
    corner.magic_equation(gbw=gbw, cload=cload1, show_plot=True, new_plot=False,
                          fig1=fig1, ax1=ax1, color=color_list[color_index])
    color_index = color_index + 1

plt.show()
av1 = math.sqrt(av)
w_in1, kgm_in1, w_load1, kgm_load1 = krummenechar_ota_stage1(av1, bw, cload1, cid_test_corner, pcorner)
w_in2, kgm_in2, w_load2, kgm_load2 = krummenechar_ota_stage2(av, bw, cload2, cid_test_corner)

cid_test_corner.plot_processes_params("kgm", "gm", show_plot=True)
cid_test_corner.plot_processes_params("kgm", "ft", show_plot=True)
cid_test_corner.plot_processes_params("kgm", "gmro", show_plot=True)
cid_test_corner.plot_processes_params("kgm", "iden", show_plot=True)
"""
