#
# Nordic Design Example for OTA Design using C/ID Software
# Software Can be found at https://github.com/uulcas/cid
#

# import basic python auxiliary libraries
import sys, os, getpass, shutil, operator, collections, copy, re, math

# import cid software
from cid import *


# define function for parallel operator
def parallel(x1, x2):
    return 1/((1/x1) + 1/x2)

# function for creating typical room temperature cid objects
# this function returns two CIDCornerCollections objects for N and P device types,
# the collections contain all data for all lengths under analysis
def create_devices_typical_devices(lut_dir, vdd=0.0):
    #two lists for n and p devices
    n_list = []
    p_list = []
    #iterate through all directories in lut base directory
    for dirpath, dirnames, filenames in os.walk(lut_dir):
        for dirname in dirnames:
            # Perform operations on each directory
            lut_path = os.path.join(dirpath, dirname)
            corner_file = ""
            # Create corners for n and p tt room temp corners
            # Append corners ro respective lists
            if "N" in dirname:
                corner_file = "nfetttroom.csv"
                corner_path = os.path.join(lut_path, corner_file)
                tt_room = CIDCorner(corner_name="ttroom",
                                    lut_csv=corner_path,
                                    vdd=vdd)
                n_list.append(tt_room)
            else:
                corner_file = "pfetttroom.csv"
                corner_path = os.path.join(lut_path, corner_file)
                tt_room = CIDCorner(corner_name="ttroom",
                                    lut_csv=corner_path,
                                    vdd=vdd)
                p_list.append(tt_room)
    n_tt_room = CIDCornerCollection(collection_name="n_tt_room", corner_list=n_list)
    p_tt_room = CIDCornerCollection(collection_name="p_tt_room", corner_list=p_list)
    return n_tt_room, p_tt_room

def plotting_examples():
    # n_corners1p8 = macronix_1p8_rvt_n.corners
    # n_corners5 = macronix_5v_lvt_n.corners
    # n_corners5.extend(n_corners1p8)
    # mac_corners_n = CIDCornerCollection(collection_name="mac_n_corners", corner_list=n_corners5)

    # mac_corners_n.plot_processes_params("kgm", "ft", show_plot=True)
    # mac_corners_n.plot_processes_params("kgm", "gm/gds", show_plot=True)
    # macronix_1p8_rvt_n.plot_processes_params("kgm", "ft", show_plot=True)
    # macronix_1p8_rvt_n.plot_processes_params("kgm", "ids", show_plot=True)
    # macronix_5v_lvt_n.plot_processes_params("kgm", "ft", show_plot=True)
    macronix_5v_lvt_n.plot_processes_params("kgm", "ids", show_plot=True)
    # p_2u_gf22 = CIDDevice(device_name="gf22_p_2u", vdd=0.8,
    #                        lut_directory=gf22_luts + "LUT_P_2u",
    #                        corner_list=None)
    # n_20n_gf22.magic_equation(gbw=1e9, cload=10e-15,show_plot=True)
    # n_20n_gf22.plot_processes_params("kgm", "vth", show_plot=True)
    # n_20n_gf22.plot_processes_params("kgm", "vds", show_plot=True)
    # n_20n_gf22.plot_processes_params("kgm", "gmidft", show_plot=True)
    # n_20n_gf22.plot_processes_params("kgm", "gm/gds", show_plot=True)
    # n_20n_gf22.plot_processes_params("kgm", "iden", show_plot=True)
    # n_20n_gf22.plot_processes_params("kgm", "kcgs", show_plot=True)
    # n_20n_gf22.magic_equation(gbw=1e9, cload=10e-15,show_plot=True)
    # p_240n_gf22.plot_processes_params("kgm", "gm/gds", show_plot=True)
    # p_240n_gf22.plot_processes_params("kgm", "gds/gm", show_plot=True)
    # p_240n_gf22.plot_processes_params("kgm", "iden", show_plot=True)
    # n_180n_mac180.plot_processes_params("kgm", "gm/gds", show_plot=True)
    # n_180n_mac180.plot_processes_params("kgm", "ft", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "gds", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "ids", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "gm/gds", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "ft", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "gmidft", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "iden", show_plot=True)
    n_gf22_lengths.plot_processes_params("kgm", "kcgs", show_plot=True)

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


def krummenacher_stage_design1(nfet_device, nfet_tt, pfet_device, pfet_tt, av, bw, cload):
    #calculate gbw
    gbw = av*bw
    #find optimal current and kgm for M5
    ids_min1, kgm_opt1 = pfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    #iterate between
    kgm_opt3 = 0.333*kgm_opt1
    ids_epsilon = 100.0
    cload_opt = cload
    ids_iter = ids_min1
    while ids_epsilon >= 0.025:

        kcgs3 = nfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt3)
        kcds3 = nfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt3)
        cgs3 = ids_min1*kcgs3
        cds3 = ids_min1*kcds3
        cload_opt = cgs3 + cds3 + cload
        ids_min1, kgm_opt1 = pfet_device.magic_equation(gbw=gbw, cload=cload_opt, epsilon=10, show_plot=False,
                                                        new_plot=False)
        ids_epsilon = abs(1 - ids_min1/ids_iter)
        ids_iter = ids_min1

    if ids_min1 <= 0:
        print("Cannot Converge")
        return -1

    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min1
    #lookup current density for optimal Kgm of M5
    iden1 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)

    #Calculate W5 from current density
    w1 = ids_min1/iden1
    # W5 sized
    print("W1: " + str(w1) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    iden3 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    w3 = ids_min1/iden3

    print("W3: " + str(w3) + ", L3: " + str(nfet_tt.length) + ", gm3: " + str(gm3) + ", id: " + str(ids_min1) + ", gm/id,3: " + str(kgm_opt3))
    kcgs1 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt1)
    kcds1 = pfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt1)
    cgs1 = ids_min1 * kcgs1
    cds1 = ids_min1 * kcds1
    input_cap = cgs1 + cds1
    return input_cap

def ota_stage_design2(nfet_device, nfet_tt, pfet_device, pfet_tt, av, bw, cload, beta):
    #calculate gbw
    gbw = av*bw

    #find optimal   current and kgm for M5
    ids_min5, kgm_opt5 = nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=20, show_plot=False, new_plot=False)

    #calculate P Load gm/id
    kgm_opt6 = 0.5*kgm_opt5

    #Iterate for exact minimum current for second stage
    ids_epsilon = 100.0
    cload_opt = cload
    ids_iter = ids_min5
    while ids_epsilon >= 0.025:
        kcgs6 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt6)
        kcds6 = pfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt6)
        cgs6 = ids_min5*kcgs6*beta
        cds6 = ids_min5*kcds6*beta
        cload_opt = cgs6 + cds6 + cload
        ids_min5, kgm_opt5 = nfet_device.magic_equation(gbw=gbw, cload=cload_opt, epsilon=50, show_plot=False, new_plot=False)
        ids_epsilon = abs(1 - ids_min5/ids_iter)
        ids_iter = ids_min5


    #c alculate optimal gms
    gm5 = kgm_opt5*ids_min5*beta
    gm6 = kgm_opt6*ids_min5*beta

    #lookup current density for optimal Kgm of M5
    iden5 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt5)

    #Calculate W5 from current density
    w5 = (ids_min5*beta)/iden5
    # W5 sized
    print("W5: " + str(w5) + ", L5: " + str(nfet_tt.length) + ", gm5: " + str(gm5) + ", id: " + str(ids_min5*beta) + ", gm/id,5: " + str(kgm_opt5))

    iden6 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    w6 = (ids_min5*beta)/iden6
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min5*beta) + ", gm/id,6: " + str(kgm_opt6))
    kcgs5 = nfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt5)
    kcds5 = nfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt5)
    cgs5 = ids_min5 * kcgs5
    cds5 = ids_min5 * kcds5
    input_cap = cgs5 + cds5
    return input_cap



def ota_stage_design1(nfet_device, nfet_tt, pfet_device, pfet_tt, av, bw, cload):
    #calculate gbw
    gbw = av*bw
    #find optimal current and kgm for M5
    ids_min1, kgm_opt1 = nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=50, show_plot=False, new_plot=False)
    #iterate between
    kgm_opt3 = 0.5*kgm_opt1
    ids_epsilon = 100.0
    cload_opt = cload
    ids_iter = ids_min1
    while ids_epsilon >= 0.025:

        kcgs3 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt3)
        kcds3 = pfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt3)
        cgs3 = ids_min1*kcgs3
        cds3 = ids_min1*kcds3
        cload_opt = cgs3 + cds3 + cload
        ids_min1, kgm_opt1 = pfet_device.magic_equation(gbw=gbw, cload=cload_opt, epsilon=10, show_plot=False,
                                                        new_plot=False)
        ids_epsilon = abs(1 - ids_min1/ids_iter)
        ids_iter = ids_min1

    if ids_min1 <= 0:
        print("Cannot Converge")
        return -1

    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min1
    #lookup current density for optimal Kgm of M5
    iden1 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)

    #Calculate W5 from current density
    w1 = ids_min1/iden1
    # W5 sized
    print("W1: " + str(w1) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    iden3 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    w3 = ids_min1/iden3

    print("W3: " + str(w3) + ", L3: " + str(nfet_tt.length) + ", gm3: " + str(gm3) + ", id: " + str(ids_min1) + ", gm/id,3: " + str(kgm_opt3))
    kcgs1 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt1)
    kcds1 = pfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt1)
    cgs1 = ids_min1 * kcgs1
    cds1 = ids_min1 * kcds1
    input_cap = cgs1 + cds1
    return input_cap

def cm_ota(nfet_device, nfet_tt, pfet_device, pfet_tt, av, bw, cload):
    #calculate gbw
    gbw = av*bw
    current_gain = 10
    #find optimal current and kgm for M5
    ids_min1, kgm_opt1 = pfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    #iterate between
    kgm_opt3 = 0.333*kgm_opt1
    ids_epsilon = 100.0
    cload_opt = cload
    ids_iter = ids_min1
    while ids_epsilon >= 0.025:

        kcgs3 = nfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt3)
        kcds3 = nfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt3)
        cgs3 = ids_min1*kcgs3
        cds3 = ids_min1*kcds3
        cload_opt = cgs3 + cds3 + cload
        ids_min1, kgm_opt1 = pfet_device.magic_equation(gbw=gbw, cload=cload_opt, epsilon=10, show_plot=False,
                                                        new_plot=False)
        ids_epsilon = abs(1 - ids_min1/ids_iter)
        ids_iter = ids_min1

    if ids_min1 <= 0:
        print("Cannot Converge")
        return -1

    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min1
    #lookup current density for optimal Kgm of M5
    iden1 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)

    #Calculate W5 from current density
    w1 = ids_min1/iden1
    # W5 sized
    print("W1: " + str(w1) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    iden3 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    w3 = ids_min1/iden3

    print("W3: " + str(w3) + ", L3: " + str(nfet_tt.length) + ", gm3: " + str(gm3) + ", id: " + str(ids_min1) + ", gm/id,3: " + str(kgm_opt3))
    kcgs1 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt1)
    kcds1 = pfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt1)
    cgs1 = ids_min1 * kcgs1
    cds1 = ids_min1 * kcds1
    input_cap = cgs1 + cds1
    return input_cap
# Choose length of all transistors in design
# length is chosen on randomly in this example
#
def choose_length_for_tech(collection, av, bw, cload):
    gbw = av*bw
    opt_length = 0
    opt_gain = 0

    #Look at at each length and look for optimal point
    ids, kgm = collection.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=True, new_plot=True, fig1=None, ax1=None)

    #For this example will use naive method
    #Choosing length on average transistors
    max_gain = 0
    min_gain = 100000e10
    opt_length = None
    for corner in collection.corners:
        length = corner.length
        gain = 0

    return opt_length

color_list = ['red', 'blue', 'green', 'yellow', 'magenta', 'black', 'purple']





#Define LUTs directory
tsmc_28_1v8_luts = "/research/ece/lcas/prj/jp28/xchar/roar/mac_1v8/LUTs_mac_1v8"


# Extract only typical corners
tsmc_28_1v8_n, tsmc_28_1v8_p = create_devices_typical_devices(tsmc_28_1v8_luts, vdd=1.8)
collections_list_n = [tsmc_28_1v8_n]

av = 100
bw = 1e06
cload1 = 200e-15
cload2 = 200e-15
gbw = bw * av
#macronix_5v_n_tt.magic_equation()

for tech in collections_list_n:
    # set gain specs for each stage in opamp design
    av1 = av
    av2 = av
    gbw1 = av1 * bw
    gbw2 = av2 * bw

    tech_n_tt = CIDCorner(corner_name="nttroom",
                          lut_csv=tsmc_28_1v8_luts + "/LUT_N_250n/nfetttroom.csv",
                          vdd=1.8)
    tech_p_tt = CIDCorner(corner_name="pttroom",
                          lut_csv=tsmc_28_1v8_luts + "/LUT_P_250n/pfetttroom.csv")
    # choose length for technology
    # length is chosen on gain specification
    choose_length_for_tech(collection=tech, av=av1, bw=bw, cload=cload1)


    # Size stage 1, this example is only for tt corner at room temperature
    cload1 = ota_stage_design2(nfet_device=tsmc_28_1v8_n, nfet_tt=tech_n_tt, pfet_device=tsmc_28_1v8_p,
                               pfet_tt=tech_p_tt,
                               av=av2, bw=bw, cload=cload2, beta=10)
    # Calculate Compensation Capacitor, Just used rule of thumb for example
    #cc = 0.2 * cload2
    #cload1 = cload1 + cc * (1 + av2)

    # Size stage 2, this example if only for tt corner at room temperature
    ota_stage_design1(nfet_device=tsmc_28_1v8_n, nfet_tt=tech_n_tt, pfet_device=tsmc_28_1v8_p, pfet_tt=tech_p_tt,
                      av=av1, bw=bw, cload=cload1)
    print("DONE")


av2 = math.sqrt(av)
av1 = math.sqrt(av)
av1 = 100
av2 = 100
gbw1 = av1*bw
gbw2 = av2*bw
# Size stage 1, this example is only for tt corner at room temperature
cload1 = ota_stage_design2(nfet_device=tsmc_28_1v8_n, nfet_tt=tech_n_tt, pfet_device=gf22_p_device, pfet_tt=gf22_p_tt,
                  av=av2, bw=bw, cload=cload2)
cc = 0.2*cload2
cload1 = cload1 + cc*(1 + av2)
ota_stage_design1(nfet_device=gf22_n_device, nfet_tt=gf22_n_tt, pfet_device=gf22_p_device, pfet_tt=gf22_p_tt,
                  av=av1, bw=bw, cload=cload1)


print("DONE")


