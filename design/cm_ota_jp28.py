#
# Nordic Design Example for OTA Design using C/ID Software
# Software Can be found at https://github.com/uulcas/cid
#

# import basic python auxiliary libraries
import sys, os, getpass, shutil, operator, collections, copy, re, math

import control

# import cid software
from cid import *
from scipy import signal
from scipy.signal import freqs
import control.matlab as ml

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


def ota_stage_design2(nfet_device, nfet_tt, pfet_device, pfet_tt, av, bw, cload):
    #calculate gbw
    gbw = av*bw

    #find optimal current and kgm for M5
    ids_min5, kgm_opt5 = nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)

    #calculate P Load gm/id
    kgm_opt6 = 0.333*kgm_opt5

    #Iterate for exact minimum current for second stage
    ids_epsilon = 100.0
    cload_opt = cload
    ids_iter = ids_min5
    while ids_epsilon >= 0.025:
        kcgs6 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt6)
        kcds6 = pfet_tt.lookup(param1="kgm", param2="kcds", param1_val=kgm_opt6)
        cgs6 = ids_min5*kcgs6
        cds6 = ids_min5*kcds6
        cload_opt = cgs6 + cds6 + cload
        ids_min5, kgm_opt5 = nfet_device.magic_equation(gbw=gbw, cload=cload_opt, epsilon=10, show_plot=False, new_plot=False)
        ids_epsilon = abs(1 - ids_min5/ids_iter)
        ids_iter = ids_min5


    #c alculate optimal gms
    gm5 = kgm_opt5*ids_min5
    gm6 = kgm_opt6*ids_min5

    #lookup current density for optimal Kgm of M5
    iden5 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt5)

    #Calculate W5 from current density
    w5 = ids_min5/iden5
    # W5 sized
    print("W5: " + str(w5) + ", L5: " + str(nfet_tt.length) + ", gm5: " + str(gm5) + ", id: " + str(ids_min5) + ", gm/id,5: " + str(kgm_opt5))

    iden6 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    w6 = ids_min5/iden6
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min5) + ", gm/id,6: " + str(kgm_opt6))
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

def plot_response_ota(nfet_device, nfet_tt, pfet_device, pfet_tt, av, bw, cload):
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







# Define variables for look uptable directories
tsmc_moonlight_luts = "/projects01/moonlight4503/design/methodics/ala1/Moonlight_trunk/cds_run/characterization/LUTS_TSMC"
gf22_halti_luts = "/hizz/pro/lteng4448/design/methodics/ala1/ala1_lteng4448/cds_run/ICU_param/characterization/LUTS_GF22"
macronix180_luts_1p8_rvt = "/projects01/tau4496/design/methodics/ala1/Tau_trunk/cds_run/characterization/LUT_1P8_RVT"
macronix180_luts_5p0_lvt = "/projects01/tau4496/design/methodics/ala1/Tau_trunk/cds_run/characterization/LUT_5V_LVT"

# Extract only typical corners
macronix_5v_lvt_n, macronix_5v_lvt_p = create_devices_typical_devices(macronix180_luts_5p0_lvt, vdd=5.0)
macronix_1p8_rvt_n, macronix_5v_rvt_p = create_devices_typical_devices(macronix180_luts_1p8_rvt, vdd=1.8)
tsmc_moonlight_n, tsmc_moonlight_p = create_devices_typical_devices(tsmc_moonlight_luts, vdd=0.9)
gf22_n, gf22_p = create_devices_typical_devices(gf22_halti_luts, vdd=0.8)

# Create CIDDevices from LUTs
gf22_n_device = CIDDevice(device_name="gf22n", lut_directory=gf22_halti_luts + "/LUT_N_360n",
                            corner_list=None, vdd=0.8)

gf22_p_device = CIDDevice(device_name="gf22n", lut_directory=gf22_halti_luts + "/LUT_P_360n",
                      corner_list=None, vdd=0.8)

gf22_n_tt = CIDCorner(corner_name="ttroom",
                      lut_csv=gf22_halti_luts + "/LUT_N_360n/nfetttroom.csv",
                      vdd=0.8)

gf22_p_tt = CIDCorner(corner_name="ttroom",
                      lut_csv=gf22_halti_luts + "/LUT_P_360n/pfetttroom.csv",
                      vdd=0.8)

macronix_5v_n_tt = CIDDevice(device_name="macronix", lut_directory=macronix180_luts_5p0_lvt + "/LUT_N_800n",
                             corner_list=None, vdd=5.0)
macronix_5v_p_tt = CIDDevice(device_name="macronix", lut_directory=macronix180_luts_5p0_lvt + "/LUT_N_800n",
                             corner_list=None, vdd=5.0)

collections_list_n = [gf22_n, tsmc_moonlight_n, macronix_5v_lvt_n, macronix_1p8_rvt_n]
macronix180_luts = "/projects01/proton-mx4508/design/methodics/krm1/TECH-8015-sandbox/cds_run/CID_Characterization"

# Extract only typical corners
macronix_5v_lvt_n, macronix_5v_lvt_p = create_devices_typical_devices(
    macronix180_luts_5p0_lvt, vdd=5.0
)
macronix_1p8_rvt_n, macronix_5v_rvt_p = create_devices_typical_devices(
    macronix180_luts_1p8_rvt, vdd=1.8
)
tsmc_moonlight_n, tsmc_moonlight_p = create_devices_typical_devices(
    tsmc_moonlight_luts, vdd=0.9
)
gf22_n, gf22_p = create_devices_typical_devices(gf22_halti_luts, vdd=0.8)

# Create CIDDevices from LUTs
gf22_n_device = CIDDevice(
    device_name="gf22n",
    lut_directory=gf22_halti_luts + "/LUT_N_360n",
    corner_list=None,
    vdd=0.8,
)

macronix180_n_device = CIDDevice(
    device_name="L18B1",
    lut_directory=macronix180_luts + "/LUT_N_1.0u",
    corner_list=None,
    vdd=0.8,
)

#macronix_5v_n_tt.plot_processes_params(param1="kgm", param2="ft", show_plot=True)
#macronix_5v_n_tt.plot_processes_params(param1="kgm", param2="gm/gds", show_plot=True)
#macronix_5v_n_tt.plot_processes_params(param1="kgm", param2="gmidft", show_plot=True)
#macronix_5v_n_tt.magic_equation(gbw=1e9, cload=10e-15,show_plot=True)
# Specifications
# noise to be added, all fixed length devices for now
av = 400
bw = 10e06
cload1 = 200e-15
cload2 = 200e-15
gbw = bw * av

def corner_sort(corner):
    return(corner.corner_name)

def plot_opt_curve_ota(nfet_device, pfet_device, nfet_tt, pfet_tt, av, bw, cload, beta, epsilon):
    print("TODO")


def plot_ldo_output_noise():
    ldo_psrr_file = "/home/adair/Documents/UU/LASCAS2023/LDO_Equi_Output_Noise.csv"
    df = pd.read_csv(ldo_psrr_file)
    fontsize = 12
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5,3))
    plt.semilogx(df['x'], df['y']*1e9)
    plt.ylabel(r"Noise [$\mathrm{n}V / \sqrt{Hz}$]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"LDO Noise Figure", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.tight_layout()
    print("Generated")


def plot_ldo_loopgain_phase():
    ldo_psrr_file = "/home/adair/Documents/UU/LASCAS2023/LDO_LG_Phase.csv"
    df = pd.read_csv(ldo_psrr_file)
    fontsize = 12
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5,3))
    plt.semilogx(df['x'], df['y'])
    plt.ylabel(r"Phase [$\degree$]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"LDO Loop Phase", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.tight_layout()
    plt.show()
    print("Generated")

def plot_ota_loopgain_phase(f, mag_cal, H):
    ldo_psrr_file = "/home/adair/Documents/ISCAS2024/iscas_phase.csv"
    df = pd.read_csv(ldo_psrr_file)
    fontsize = 12
    x = df['x']
    H_x = H(x)
    phase_hx = np.angle(H_x)
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5,3))
    plt.semilogx(df['x'], df['y'], label="simulation")
    plt.semilogx(x, phase_hx, color="orange", linestyle="dashed", label="calculated")
    plt.ylabel(r"Phase [$\degree$]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"LDO Loop Phase", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.tight_layout()
    plt.show()
    print("Generated")

def plot_ota_loop_gain(f, mag_cal, H):
    ldo_psrr_file = "/home/adair/Documents/ISCAS2024/iscas_gain.csv"
    df = pd.read_csv(ldo_psrr_file)
    fontsize = 12
    x = df['x']
    H_x = H(x)
    db_hx = 20*np.log10(np.abs(H_x))
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5, 3))
    plt.semilogx(df['x'], df['y'], label="simulated")
    plt.semilogx(x, db_hx, color="orange", linestyle="dashed", label="calculated")
    plt.ylabel(r"Amplitude [dB]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"OTA Loop Gain", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.legend()
    plt.tight_layout()
    print("Generated")

def plot_ldo_loop_gain():
    ldo_psrr_file = "/home/adair/Documents/UU/LASCAS2023/LDO_LG_Mag.csv"
    df = pd.read_csv(ldo_psrr_file)
    fontsize = 12
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5,3))
    plt.semilogx(df['x'], df['y'])
    plt.ylabel(r"Amplitude [dB]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"LDO Loop Gain", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.tight_layout()
    print("Generated")


def plot_ldo_psrr():
    ldo_psrr_file = "/home/adair/Documents/UU/LASCAS2023/LDO_PSRR.csv"
    df = pd.read_csv(ldo_psrr_file)
    fontsize = 12
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5,3))
    plt.semilogx(df['x'], df['y'])
    plt.ylabel(r"Amplitude [dB]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"LDO Power Supply Rejection Ratio", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.tight_layout()
    print("Generated")

def plot_kc2_ota(nfet_device, pfet_device, nfet_tt, pfet_tt, av, bw, cload, beta, epsilon):
    font = {'fontname':'Arial'}
    #fig = plt.figure(figsize=(5,2))
    show_plot = True
    gbw = av * bw
    gbw = 50e6
    beta = 3
    cload = 100e-15
    ids_min1, kgm_opt1= nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    #ids_min1, kgm_opt1, ax1, fig1 = nfet_tt.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=False)
    kgm_n = nfet_tt.df["kgm"]
    kgm_p = pfet_tt.df["kgm"]
    kcdg_n = nfet_tt.df["kcgd"]
    kcdg_p = pfet_tt.df["kcgd"]
    kcds_n = nfet_tt.df["kcds"]
    kcds_p = pfet_tt.df["kcds"]
    kcdb_n = nfet_tt.df["kcdb"]
    kcdb_p = pfet_tt.df["kcdb"]
    kcdd_n = nfet_tt.df["kcdd"]
    kcdd_p = pfet_tt.df["kcdd"]
    kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
    kco_n = kcdg_n + kcds_n + kcdb_n
    kco_p = kcdg_p + kcds_p + kcdb_p
    nfet_tt.df["kco"] = kco_n
    pfet_tt.df["kco"] = kco_p
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    kco_opt_n = 0
    kco_opt_p = 0
    kgm_opt_n = 0
    kgm_opt_p = 0
    kgm_pn_ratio = 0.5
    color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
              'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
              'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
    for i in range(0, len(kgm_n)):
        first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
        kgm_ni = kgm_n[i]
        kgm_pi = kgm_ni*kgm_pn_ratio
        kco_ip = pfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_pi)
        kco_in = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_ni)
        second = 1/(1 - (2*np.pi*gbw*(kco_ip + kco_in)/kgm_n[i]))
        ids = first*second
        if ids > 0:
            kgm_arr.append(kgm_n[i])
            id1_arr.append(ids)
        if ids <= ids_min1 and ids > 0 and kgm_ni > 15:
            ids_min1 = ids
            kgm_opt1 = kgm_n[i]
            kgm_opt_n = kgm_opt1
            kgm_opt_p = kgm_pi
            kco_opt = kco[i]
            kco_opt_n = kco_in
            kco_opt_p = kco_ip
    kco_opt_np = kco_opt_n + kco_opt_p
    kco_opt = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    #plt.plot(kgm_n, kco)
    #plt.show()
    #plt.cla()
    if show_plot == True:
        #ax = fig.add_subplot(1, 1, 1)

        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                  'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                  'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        for i in range(0, len(kgm_n)):
            first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
            second = 1/(1 - (2*np.pi*gbw*kco[i]/kgm_n[i]))
            ids = first*second
            if ids > 0:
                kgm_arr.append(kgm_n[i])
                id1_arr.append(ids)
            if ids <= ids_min1 and ids > 0:
                ids_min1 = ids
                kgm_opt1 = kgm_n[i]
                kco_opt = kco[i]
        linestyle = ['solid', 'solid', 'solid', 'dotted', 'dotted', 'dotted', 'dashed', 'dashed', 'dashed']
        legends = ["Fast -25 C", "Typical -25 C", "Slow -25 C","Fast 25 C", "Typical 25 C", "Slow 25 C", "Fast 75 C", "Typical 75 C", "Slow 75 C", ]
        nfet_device.corners.sort(key=corner_sort)
        pfet_device.corners.sort(key=corner_sort)
        for i in range(0, len(nfet_device.corners)):
            ncorner = nfet_device.corners[i]
            pcorner = pfet_device.corners[i]
            kgm_n = ncorner.df["kgm"]
            kcdg_n = ncorner.df["kcgd"]
            kcdg_p = pcorner.df["kcgd"]
            kcds_n = ncorner.df["kcds"]
            kcds_p = pcorner.df["kcds"]
            kcdb_n = ncorner.df["kcdb"]
            kcdb_p = pcorner.df["kcdb"]
            kcdd_n = ncorner.df["kcdd"]
            kcdd_p = pcorner.df["kcdd"]
            kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
            kcn = kcdg_n + kcds_n + kcdb_n
            kcp = kcdg_p + kcds_p + kcdb_p
            #plt.plot(kgm_n, kco)
            #plt.show()
            #plt.cla()
            id1_arr = []
            kgm_arr = []
            kco_arr = []
            kcn_arr = []
            kcp_arr = []
            ids_min1 = 1e6
            kgm_opt1 = 1e6
            kco_opt = 0
            for j in range(0, len(kgm_n)):
                kco_j = kco[j]
                kcn_j = kcn[j]
                kcp_j = kcp[j]
                first = 2*np.pi*gbw*cload/(beta*kgm_n[j])
                second = 1/(1 - (2*np.pi*gbw*kco[j]/kgm_n[j]))
                ids = first*second
                if ids > 0:
                    kgm_arr.append(kgm_n[j])
                    id1_arr.append(ids*1e9)
                    kco_arr.append(kco_j*1e15)
                    kcn_arr.append(kcn_j)
                    kcp_arr.append(kcp_j)
                if ids <= ids_min1 and ids > 0:
                    ids_min1 = ids
                    kgm_opt1 = kgm_n[j]
                    kco_opt = kco[j]
            #plt.plot(kgm_arr, kco_arr, linestyle=linestyle[i])

            #ax.plot(kgm_arr, id1_arr, linestyle="solid")
            #ax.plot(kgm_arr, kco_arr, linestyle="solid")
            #ax.plot(kgm_arr, kcn_arr, linestyle="dashed")
            #ax.plot(kgm_arr, kcp_arr, linestyle="dotted")
        #ax.set_xticklabels(fontsize=20)
        #ax.set_yticklabels(fontsize=20)
        #ax.set_xlabel("Kgm [S/A]")

    #ids_min1 = ids_min1/beta
    ids_min3 = ids_min1

    #plt.show()

    kgm_opt3 = kgm_pn_ratio*kgm_opt1


    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min3

    #lookup current density for optimal Kgm of M5
    iden1 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)
    iden3 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    #Calculate W5 from current density
    w1 = ids_min1/iden1
    w3 = ids_min3/iden3

    # W1 and W3 sized
    print("W1: " + str(w1) + ", L1: " + str(nfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    print("W3: " + str(w3) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm3) + ", id: " + str(ids_min3) + ", gm/id,3: " + str(kgm_opt3))

    kgm_opt6 = kgm_opt1
    kgm_opt8 = kgm_opt3
    ids_min6 = beta*ids_min1
    ids_min8 = ids_min6
    #kcgs6 = nfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt6)
    #kcds7 = pfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt7)



    iden6 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    iden8 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt8)
    w6 = ids_min6/iden6
    w8 = ids_min8/iden8
    gm6 = kgm_opt6*ids_min6
    gm8 = kgm_opt8*ids_min8
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min6) + ", gm/id,6: " + str(kgm_opt6))
    print("W8: " + str(w8) + ", L8: " + str(pfet_tt.length) + ", gm8: " + str(gm8) + ", id: " + str(ids_min8) + ", gm/id,6: " + str(kgm_opt8))
    predicted_gbw = beta*gm1/(2*np.pi*(cload + (kco_opt_np*ids_min6)))
    print("predicted gbw: " + str(predicted_gbw))
    gain = gm1*beta
    print("co n " + str(kco_opt_n*ids_min6))
    print("co p: " + str(kco_opt_p*ids_min6))
    kcgg_p = pfet_tt.lookup(param1="kgm", param2="kcgg", param1_val=kgm_opt8)
    non_dom_pole = gm1/((1+beta)*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    non_dom_pole = non_dom_pole/(2*np.pi)
    dom_pole = gm1*beta/(kco_opt_p*ids_min6 + kco_opt_n*ids_min6 + cload)
    dom_pole = dom_pole/(2*np.pi)
    ro2_n = nfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt1)/gm6
    ro2_p = pfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt3)/gm8
    ro1_n = 1/gm1
    ro1_p = 1/gm3
    ro1 = parallel(ro1_n, ro1_p)
    ro2 = parallel(ro2_n, ro2_p)
    non_dom_pole = 1/(2*np.pi*ro1*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    gain = gm1*beta*ro2
    gain_db = 20*math.log10(gain)
    bw = gbw/gain
    print("non dominant pole: " + str(non_dom_pole))
    print("dominant pole: " + str(dom_pole))
    print("gain: " + str(gain))
    print("gain_db: " + str(gain_db))
    print("3-db BW: " + str(bw))
    b, a = signal.butter(1, bw*2*np.pi, 'low', analog=True)
    w, h = signal.freqs(b, a)
    df = pd.read_csv("/home/adair/Documents/UU/LASCAS2023/out_db20_lascas.csv")
    fontsize = 8
    font = {'fontname':'Arial', 'size':fontsize}
    #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
    #ax.title.set_size(fontsize)
    font = {'fontname':'Arial', 'size':fontsize}
    #plt.semilogx(w, 20*np.log10(abs(h)) + gain_db, linestyle='dashed')
    legends = ["Typical 25 C"]
    plt.figure(figsize=(5,2))
    plt.semilogx(df['freq'], df['amp'])
    plt.ylabel(r"Amplitude [dB]", fontdict=font,weight='bold')
    plt.xlabel(r"Frequency [Hz]", fontdict=font, weight='bold')
    #plt.legend(legends, loc="lower right")
    plt.title(r"OTA Simulated Frequency Response ", fontdict=font, weight='bold')
    #ax.plot.xticks(fontsize=20)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.grid(True, which="major", axis="both")
    plt.grid(True, which="minor", axis="both")
    plt.figure(figsize=(5,2))
    #plt.plot(kgm_arr, id1_arr, linestyle=linestyle[8])
    #plt.show()
    ibias = ids_min1*2
    print("ibias: " + str(ibias))
    return ibias

def plot_ota_frequency_response(nfet_device, pfet_device, nfet_tt, pfet_tt, av, bw, cload, beta, epsilon):
    font = {'fontname':'Arial'}
    fig = plt.figure()
    show_plot = True
    gbw = av * bw
    gbw = 50e6
    beta = 3
    cload = 100e-15
    ids_min1, kgm_opt1= nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    #ids_min1, kgm_opt1, ax1, fig1 = nfet_tt.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=False)
    kgm_n = nfet_tt.df["kgm"]
    kgm_p = pfet_tt.df["kgm"]
    kcdg_n = nfet_tt.df["kcgd"]
    kcdg_p = pfet_tt.df["kcgd"]
    kcds_n = nfet_tt.df["kcds"]
    kcds_p = pfet_tt.df["kcds"]
    kcdb_n = nfet_tt.df["kcdb"]
    kcdb_p = pfet_tt.df["kcdb"]
    kcdd_n = nfet_tt.df["kcdd"]
    kcdd_p = pfet_tt.df["kcdd"]
    kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
    kco_n = kcdg_n + kcds_n + kcdb_n
    kco_p = kcdg_p + kcds_p + kcdb_p
    nfet_tt.df["kco"] = kco_n
    pfet_tt.df["kco"] = kco_p
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    kco_opt_n = 0
    kco_opt_p = 0
    kgm_opt_n = 0
    kgm_opt_p = 0
    kgm_pn_ratio = 0.5
    color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
              'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
              'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
    for i in range(0, len(kgm_n)):
        first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
        kgm_ni = kgm_n[i]
        kgm_pi = kgm_ni*kgm_pn_ratio
        kco_ip = pfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_pi)
        kco_in = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_ni)
        second = 1/(1 - (2*np.pi*gbw*(kco_ip + kco_in)/kgm_n[i]))
        ids = first*second
        if ids > 0:
            kgm_arr.append(kgm_n[i])
            id1_arr.append(ids)
        if ids <= ids_min1 and ids > 0 and kgm_ni > 15:
            ids_min1 = ids
            kgm_opt1 = kgm_n[i]
            kgm_opt_n = kgm_opt1
            kgm_opt_p = kgm_pi
            kco_opt = kco[i]
            kco_opt_n = kco_in
            kco_opt_p = kco_ip
    kco_opt_np = kco_opt_n + kco_opt_p
    kco_opt = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    #plt.plot(kgm_n, kco)
    #plt.show()
    #plt.cla()
    if show_plot == True:
        ax = fig.add_subplot(1, 1, 1)

        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                  'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                  'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        for i in range(0, len(kgm_n)):
            first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
            second = 1/(1 - (2*np.pi*gbw*kco[i]/kgm_n[i]))
            ids = first*second
            if ids > 0:
                kgm_arr.append(kgm_n[i])
                id1_arr.append(ids)
            if ids <= ids_min1 and ids > 0:
                ids_min1 = ids
                kgm_opt1 = kgm_n[i]
                kco_opt = kco[i]
        linestyle = ['solid', 'solid', 'solid', 'dotted', 'dotted', 'dotted', 'dashed', 'dashed', 'dashed']
        legends = ["Fast -25 C", "Typical -25 C", "Slow -25 C","Fast 25 C", "Typical 25 C", "Slow 25 C", "Fast 75 C", "Typical 75 C", "Slow 75 C", ]
        nfet_device.corners.sort(key=corner_sort)
        pfet_device.corners.sort(key=corner_sort)
        for i in range(0, len(nfet_device.corners)):
            ncorner = nfet_device.corners[i]
            pcorner = pfet_device.corners[i]
            kgm_n = ncorner.df["kgm"]
            kcdg_n = ncorner.df["kcgd"]
            kcdg_p = pcorner.df["kcgd"]
            kcds_n = ncorner.df["kcds"]
            kcds_p = pcorner.df["kcds"]
            kcdb_n = ncorner.df["kcdb"]
            kcdb_p = pcorner.df["kcdb"]
            kcdd_n = ncorner.df["kcdd"]
            kcdd_p = pcorner.df["kcdd"]
            kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
            kcn = kcdg_n + kcds_n + kcdb_n
            kcp = kcdg_p + kcds_p + kcdb_p
            #plt.plot(kgm_n, kco)
            #plt.show()
            #plt.cla()
            id1_arr = []
            kgm_arr = []
            kco_arr = []
            kcn_arr = []
            kcp_arr = []
            ids_min1 = 1e6
            kgm_opt1 = 1e6
            kco_opt = 0
            for j in range(0, len(kgm_n)):
                kco_j = kco[j]
                kcn_j = kcn[j]
                kcp_j = kcp[j]
                first = 2*np.pi*gbw*cload/(beta*kgm_n[j])
                second = 1/(1 - (2*np.pi*gbw*kco[j]/kgm_n[j]))
                ids = first*second
                if ids > 0:
                    kgm_arr.append(kgm_n[j])
                    id1_arr.append(ids*1e9)
                    kco_arr.append(kco_j*1e15)
                    kcn_arr.append(kcn_j)
                    kcp_arr.append(kcp_j)
                if ids <= ids_min1 and ids > 0:
                    ids_min1 = ids
                    kgm_opt1 = kgm_n[j]
                    kco_opt = kco[j]
            #plt.plot(kgm_arr, kco_arr, linestyle=linestyle[i])

            #ax.plot(kgm_arr, id1_arr, linestyle="solid")
            #ax.plot(kgm_arr, kco_arr, linestyle="solid")
            #ax.plot(kgm_arr, kcn_arr, linestyle="dashed")
            #ax.plot(kgm_arr, kcp_arr, linestyle="dotted")
        #ax.set_xticklabels(fontsize=20)
        #ax.set_yticklabels(fontsize=20)
        #ax.set_xlabel("Kgm [S/A]")
        fontsize = 12
        font = {'fontname':'Arial', 'size':fontsize}
        ax.set_ylabel("Id M1 [uA]")
        #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
        #ax.title.set_size(fontsize)
        font = {'fontname':'Arial', 'size':fontsize}
        plt.ylabel(r"$\mathcal{C}_o$ [fF/A]", fontdict=font,weight='bold')
        plt.xlabel(r"$\bf{K_{gm}}$ [S/A]", fontdict=font, weight='bold')
        plt.legend(legends, loc="lower right")
        plt.title(r"OTA $\mathcal{C}_o$ vs $\bf{K_{gm}}$ With 9 Corners", fontdict=font, weight='bold')
        #ax.plot.xticks(fontsize=20)
        plt.xticks(fontsize=fontsize)
        plt.yticks(fontsize=fontsize)
        plt.grid()
        #plt.plot(kgm_arr, id1_arr, linestyle=linestyle[8])
        plt.show()

    #ids_min1 = ids_min1/beta
    ids_min3 = ids_min1

    #plt.show()

    kgm_opt3 = kgm_pn_ratio*kgm_opt1


    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min3

    #lookup current density for optimal Kgm of M5
    iden1 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)
    iden3 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    #Calculate W5 from current density
    w1 = ids_min1/iden1
    w3 = ids_min3/iden3

    # W1 and W3 sized
    print("W1: " + str(w1) + ", L1: " + str(nfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    print("W3: " + str(w3) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm3) + ", id: " + str(ids_min3) + ", gm/id,3: " + str(kgm_opt3))

    kgm_opt6 = kgm_opt1
    kgm_opt8 = kgm_opt3
    ids_min6 = beta*ids_min1
    ids_min8 = ids_min6
    #kcgs6 = nfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt6)
    #kcds7 = pfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt7)



    iden6 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    iden8 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt8)
    w6 = ids_min6/iden6
    w8 = ids_min8/iden8
    gm6 = kgm_opt6*ids_min6
    gm8 = kgm_opt8*ids_min8
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min6) + ", gm/id,6: " + str(kgm_opt6))
    print("W8: " + str(w8) + ", L8: " + str(pfet_tt.length) + ", gm8: " + str(gm8) + ", id: " + str(ids_min8) + ", gm/id,6: " + str(kgm_opt8))
    predicted_gbw = beta*gm1/(2*np.pi*(cload + (kco_opt_np*ids_min6)))
    print("predicted gbw: " + str(predicted_gbw))
    print("co n " + str(kco_opt_n*ids_min6))
    print("co p: " + str(kco_opt_p*ids_min6))
    kcgg_p = pfet_tt.lookup(param1="kgm", param2="kcgg", param1_val=kgm_opt8)
    non_dom_pole = gm1/((1+beta)*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    non_dom_pole = non_dom_pole/(2*np.pi)
    dom_pole = gm1*beta/(kco_opt_p*ids_min6 + kco_opt_n*ids_min6 + cload)
    dom_pole = dom_pole/(2*np.pi)
    ro1_n = nfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt1)
    ro1_p = pfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt3)
    ro1_n = 1/gm1
    ro1_p = 1/gm3
    ro1 = parallel(ro1_n, ro1_p)
    non_dom_pole = 1/(2*np.pi*ro1*(kcgg_p*ids_min1 + kcgg_p*ids_min8))

    print("non dominant pole: " + str(non_dom_pole))
    print("dominant pole: " + str(dom_pole))

    ibias = ids_min1*2
    print("ibias: " + str(ibias))
    return ibias

def plot_kgm_id_ota(nfet_device, pfet_device, nfet_tt, pfet_tt, av, bw, cload, beta, epsilon):
    font = {'fontname':'Arial'}
    fig = plt.figure()
    show_plot = True
    gbw = av * bw
    gbw = 50e6
    beta = 3
    cload = 50e-15
    ids_min1, kgm_opt1= nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    #ids_min1, kgm_opt1, ax1, fig1 = nfet_tt.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=False)
    kgm_n = nfet_tt.df["kgm"]
    kgm_p = pfet_tt.df["kgm"]
    kcdg_n = nfet_tt.df["kcgd"]
    kcdg_p = pfet_tt.df["kcgd"]
    kcds_n = nfet_tt.df["kcds"]
    kcds_p = pfet_tt.df["kcds"]
    kcdb_n = nfet_tt.df["kcdb"]
    kcdb_p = pfet_tt.df["kcdb"]
    kcdd_n = nfet_tt.df["kcdd"]
    kcdd_p = pfet_tt.df["kcdd"]
    kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
    kco_n = kcdg_n + kcds_n + kcdb_n
    kco_p = kcdg_p + kcds_p + kcdb_p
    nfet_tt.df["kco"] = kco_n
    pfet_tt.df["kco"] = kco_p
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    kco_opt_n = 0
    kco_opt_p = 0
    kgm_opt_n = 0
    kgm_opt_p = 0
    kgm_pn_ratio = 0.5
    color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
              'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
              'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
    for i in range(0, len(kgm_n)):
        first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
        kgm_ni = kgm_n[i]
        kgm_pi = kgm_ni*kgm_pn_ratio
        kco_ip = pfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_pi)
        kco_in = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_ni)
        second = 1/(1 - (2*np.pi*gbw*(kco_ip + kco_in)/kgm_n[i]))
        ids = first*second
        if ids > 0:
            kgm_arr.append(kgm_n[i])
            id1_arr.append(ids)
        if ids <= ids_min1 and ids > 0 and kgm_ni > 15:
            ids_min1 = ids
            kgm_opt1 = kgm_n[i]
            kgm_opt_n = kgm_opt1
            kgm_opt_p = kgm_pi
            kco_opt = kco[i]
            kco_opt_n = kco_in
            kco_opt_p = kco_ip
    kco_opt_np = kco_opt_n + kco_opt_p
    kco_opt = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    #plt.plot(kgm_n, kco)
    #plt.show()
    #plt.cla()
    if show_plot == True:
        ax = fig.add_subplot(1, 1, 1)

        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                  'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                  'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        for i in range(0, len(kgm_n)):
            first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
            second = 1/(1 - (2*np.pi*gbw*kco[i]/kgm_n[i]))
            ids = first*second
            if ids > 0:
                kgm_arr.append(kgm_n[i])
                id1_arr.append(ids)
            if ids <= ids_min1 and ids > 0 and ids < 1e-3:
                ids_min1 = ids
                kgm_opt1 = kgm_n[i]
                kco_opt = kco[i]
        linestyle = ['solid', 'solid', 'solid', 'dotted', 'dotted', 'dotted', 'dashed', 'dashed', 'dashed']
        legends = ["Fast -25 C", "Typical -25 C", "Slow -25 C","Fast 25 C", "Typical 25 C", "Slow 25 C", "Fast 75 C", "Typical 75 C", "Slow 75 C", ]
        nfet_device.corners.sort(key=corner_sort)
        pfet_device.corners.sort(key=corner_sort)
        for i in range(0, len(nfet_device.corners)):
            ncorner = nfet_device.corners[i]
            pcorner = pfet_device.corners[i]
            kgm_n = ncorner.df["kgm"]
            kcdg_n = ncorner.df["kcgd"]
            kcdg_p = pcorner.df["kcgd"]
            kcds_n = ncorner.df["kcds"]
            kcds_p = pcorner.df["kcds"]
            kcdb_n = ncorner.df["kcdb"]
            kcdb_p = pcorner.df["kcdb"]
            kcdd_n = ncorner.df["kcdd"]
            kcdd_p = pcorner.df["kcdd"]
            kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
            kcn = kcdg_n + kcds_n + kcdb_n
            kcp = kcdg_p + kcds_p + kcdb_p
            #plt.plot(kgm_n, kco)
            #plt.show()
            #plt.cla()
            id1_arr = []
            kgm_arr = []
            kco_arr = []
            kcn_arr = []
            kcp_arr = []
            ids_min1 = 1e6
            kgm_opt1 = 1e6
            kco_opt = 0
            for j in range(0, len(kgm_n)):
                kco_j = kco[j]
                kcn_j = kcn[j]
                kcp_j = kcp[j]
                first = 2*np.pi*gbw*cload/(beta*kgm_n[j])
                second = 1/(1 - (2*np.pi*gbw*kco[j]/kgm_n[j]))
                ids = first*second
                if ids > 0 and ids < 1e-3:
                    kgm_arr.append(kgm_n[j])
                    id1_arr.append(ids*1e9)
                    kco_arr.append(kco_j*1e15)
                    kcn_arr.append(kcn_j)
                    kcp_arr.append(kcp_j)
                if ids <= ids_min1 and ids > 0:
                    ids_min1 = ids
                    kgm_opt1 = kgm_n[j]
                    kco_opt = kco[j]
            plt.plot(kgm_arr, id1_arr, linestyle=linestyle[i])

            #ax.plot(kgm_arr, id1_arr, linestyle="solid")
            #ax.plot(kgm_arr, kco_arr, linestyle="solid")
            #ax.plot(kgm_arr, kcn_arr, linestyle="dashed")
            #ax.plot(kgm_arr, kcp_arr, linestyle="dotted")
        #ax.set_xticklabels(fontsize=20)
        #ax.set_yticklabels(fontsize=20)
        #ax.set_xlabel("Kgm [S/A]")
        fontsize = 12
        font = {'fontname':'Arial', 'size':fontsize}
        plt.ylabel("Id M1 [nA]", fontdict=font, weight='bold')
        #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
        #ax.title.set_size(fontsize)
        #plt.ylabel(r"$\mathcal{C}_o$ [fF/A]", fontdict=font,weight='bold')
        plt.xlabel(r"$\bf{K_{gm}}$ [S/A]", fontdict=font, weight='bold')
        plt.legend(legends, loc="upper left")
        #plt.title(r"OTA $\mathcal{C}_o$ vs $\bf{K_{gm}}$ With 9 Corners", fontdict=font, weight='bold')
        plt.title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict=font, weight='bold')
        #ax.plot.xticks(fontsize=20)
        plt.xticks(fontsize=fontsize)
        plt.yticks(fontsize=fontsize)
        plt.grid()
        plt.tight_layout()
        #plt.plot(kgm_arr, id1_arr, linestyle=linestyle[8])
        plt.show()
    #ids_min1 = ids_min1/beta
    ids_min3 = ids_min1

    #plt.show()

    kgm_opt3 = kgm_pn_ratio*kgm_opt1


    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min3

    #lookup current density for optimal Kgm of M5
    iden1 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)
    iden3 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    #Calculate W5 from current density
    w1 = ids_min1/iden1
    w3 = ids_min3/iden3

    # W1 and W3 sized
    print("W1: " + str(w1) + ", L1: " + str(nfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    print("W3: " + str(w3) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm3) + ", id: " + str(ids_min3) + ", gm/id,3: " + str(kgm_opt3))

    kgm_opt6 = kgm_opt1
    kgm_opt8 = kgm_opt3
    ids_min6 = beta*ids_min1
    ids_min8 = ids_min6
    #kcgs6 = nfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt6)
    #kcds7 = pfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt7)



    iden6 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    iden8 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt8)
    w6 = ids_min6/iden6
    w8 = ids_min8/iden8
    gm6 = kgm_opt6*ids_min6
    gm8 = kgm_opt8*ids_min8
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min6) + ", gm/id,6: " + str(kgm_opt6))
    print("W8: " + str(w8) + ", L8: " + str(pfet_tt.length) + ", gm8: " + str(gm8) + ", id: " + str(ids_min8) + ", gm/id,6: " + str(kgm_opt8))
    predicted_gbw = beta*gm1/(2*np.pi*(cload + (kco_opt_np*ids_min6)))
    print("predicted gbw: " + str(predicted_gbw))
    gain = gm1*beta
    print("co n " + str(kco_opt_n*ids_min6))
    print("co p: " + str(kco_opt_p*ids_min6))
    kcgg_p = pfet_tt.lookup(param1="kgm", param2="kcgg", param1_val=kgm_opt8)
    non_dom_pole = gm1/((1+beta)*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    non_dom_pole = non_dom_pole/(2*np.pi)
    dom_pole = gm1*beta/(kco_opt_p*ids_min6 + kco_opt_n*ids_min6 + cload)
    dom_pole = dom_pole/(2*np.pi)
    ro2_n = nfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt1)/gm6
    ro2_p = pfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt3)/gm8
    ro1_n = 1/gm1
    ro1_p = 1/gm3
    ro1 = parallel(ro1_n, ro1_p)
    ro2 = parallel(ro2_n, ro2_p)
    non_dom_pole = 1/(2*np.pi*ro1*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    gain = gm1*beta*ro2
    gain_db = 20*math.log10(gain)
    bw = gbw/gain
    print("non dominant pole: " + str(non_dom_pole))
    print("dominant pole: " + str(dom_pole))
    print("gain: " + str(gain))
    print("gain_db: " + str(gain_db))
    print("3-db BW: " + str(bw))
    ibias = ids_min1*2
    print("ibias: " + str(ibias))
    return ibias


def plot_kc_ota(nfet_device, pfet_device, nfet_tt, pfet_tt, av, bw, cload, beta, epsilon):
    font = {'fontname':'Arial'}
    fig = plt.figure()
    show_plot = True
    gbw = av * bw
    gbw = 50e6
    beta = 3
    cload = 100e-15
    ids_min1, kgm_opt1= nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    #ids_min1, kgm_opt1, ax1, fig1 = nfet_tt.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=False)
    kgm_n = nfet_tt.df["kgm"]
    kgm_p = pfet_tt.df["kgm"]
    kcdg_n = nfet_tt.df["kcgd"]
    kcdg_p = pfet_tt.df["kcgd"]
    kcds_n = nfet_tt.df["kcds"]
    kcds_p = pfet_tt.df["kcds"]
    kcdb_n = nfet_tt.df["kcdb"]
    kcdb_p = pfet_tt.df["kcdb"]
    kcdd_n = nfet_tt.df["kcdd"]
    kcdd_p = pfet_tt.df["kcdd"]
    kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
    kco_n = kcdg_n + kcds_n + kcdb_n
    kco_p = kcdg_p + kcds_p + kcdb_p
    nfet_tt.df["kco"] = kco_n
    pfet_tt.df["kco"] = kco_p
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    kco_opt_n = 0
    kco_opt_p = 0
    kgm_opt_n = 0
    kgm_opt_p = 0
    kgm_pn_ratio = 0.5
    color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
              'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
              'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
    for i in range(0, len(kgm_n)):
        first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
        kgm_ni = kgm_n[i]
        kgm_pi = kgm_ni*kgm_pn_ratio
        kco_ip = pfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_pi)
        kco_in = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_ni)
        second = 1/(1 - (2*np.pi*gbw*(kco_ip + kco_in)/kgm_n[i]))
        ids = first*second
        if ids > 0:
            kgm_arr.append(kgm_n[i])
            id1_arr.append(ids)
        if ids <= ids_min1 and ids > 0 and kgm_ni > 15:
            ids_min1 = ids
            kgm_opt1 = kgm_n[i]
            kgm_opt_n = kgm_opt1
            kgm_opt_p = kgm_pi
            kco_opt = kco[i]
            kco_opt_n = kco_in
            kco_opt_p = kco_ip
    kco_opt_np = kco_opt_n + kco_opt_p
    kco_opt = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    #plt.plot(kgm_n, kco)
    #plt.show()
    #plt.cla()
    if show_plot == True:
        ax = fig.add_subplot(1, 1, 1)

        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                  'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                  'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        for i in range(0, len(kgm_n)):
            first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
            second = 1/(1 - (2*np.pi*gbw*kco[i]/kgm_n[i]))
            ids = first*second
            if ids > 0:
                kgm_arr.append(kgm_n[i])
                id1_arr.append(ids)
            if ids <= ids_min1 and ids > 0:
                ids_min1 = ids
                kgm_opt1 = kgm_n[i]
                kco_opt = kco[i]
        linestyle = ['solid', 'solid', 'solid', 'dotted', 'dotted', 'dotted', 'dashed', 'dashed', 'dashed']
        legends = ["Fast -25 C", "Typical -25 C", "Slow -25 C","Fast 25 C", "Typical 25 C", "Slow 25 C", "Fast 75 C", "Typical 75 C", "Slow 75 C", ]
        nfet_device.corners.sort(key=corner_sort)
        pfet_device.corners.sort(key=corner_sort)
        for i in range(0, len(nfet_device.corners)):
            ncorner = nfet_device.corners[i]
            pcorner = pfet_device.corners[i]
            kgm_n = ncorner.df["kgm"]
            kcdg_n = ncorner.df["kcgd"]
            kcdg_p = pcorner.df["kcgd"]
            kcds_n = ncorner.df["kcds"]
            kcds_p = pcorner.df["kcds"]
            kcdb_n = ncorner.df["kcdb"]
            kcdb_p = pcorner.df["kcdb"]
            kcdd_n = ncorner.df["kcdd"]
            kcdd_p = pcorner.df["kcdd"]
            kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
            kcn = kcdg_n + kcds_n + kcdb_n
            kcp = kcdg_p + kcds_p + kcdb_p
            #plt.plot(kgm_n, kco)
            #plt.show()
            #plt.cla()
            id1_arr = []
            kgm_arr = []
            kco_arr = []
            kcn_arr = []
            kcp_arr = []
            ids_min1 = 1e6
            kgm_opt1 = 1e6
            kco_opt = 0
            for j in range(0, len(kgm_n)):
                kco_j = kco[j]
                kcn_j = kcn[j]
                kcp_j = kcp[j]
                first = 2*np.pi*gbw*cload/(beta*kgm_n[j])
                second = 1/(1 - (2*np.pi*gbw*kco[j]/kgm_n[j]))
                ids = first*second
                if ids > 0:
                    kgm_arr.append(kgm_n[j])
                    id1_arr.append(ids*1e9)
                    kco_arr.append(kco_j*1e15)
                    kcn_arr.append(kcn_j)
                    kcp_arr.append(kcp_j)
                if ids <= ids_min1 and ids > 0:
                    ids_min1 = ids
                    kgm_opt1 = kgm_n[j]
                    kco_opt = kco[j]
            plt.plot(kgm_arr, kco_arr, linestyle=linestyle[i])

            #ax.plot(kgm_arr, id1_arr, linestyle="solid")
            #ax.plot(kgm_arr, kco_arr, linestyle="solid")
            #ax.plot(kgm_arr, kcn_arr, linestyle="dashed")
            #ax.plot(kgm_arr, kcp_arr, linestyle="dotted")
        #ax.set_xticklabels(fontsize=20)
        #ax.set_yticklabels(fontsize=20)
        #ax.set_xlabel("Kgm [S/A]")
        fontsize = 12
        font = {'fontname':'Arial', 'size':fontsize}
        ax.set_ylabel("Id M1 [uA]")
        #ax.set_title("M1 Optimal Drain Current vs Kgm With 9 Corners",fontdict)
        #ax.title.set_size(fontsize)
        font = {'fontname':'Arial', 'size':fontsize}

        plt.ylabel(r"$\mathcal{C}_o$ [fF/A]", fontdict=font,weight='bold')
        plt.xlabel(r"$\bf{K_{gm}}$ [S/A]", fontdict=font, weight='bold')
        plt.legend(legends, loc="lower right")
        plt.title(r"OTA $\mathcal{C}_o$ vs $\bf{K_{gm}}$ With 9 Corners", fontdict=font, weight='bold')
        #ax.plot.xticks(fontsize=20)
        plt.xticks(fontsize=fontsize)
        plt.yticks(fontsize=fontsize)
        plt.grid()
        #plt.plot(kgm_arr, id1_arr, linestyle=linestyle[8])
        plt.show()
    #ids_min1 = ids_min1/beta
    ids_min3 = ids_min1

    #plt.show()

    kgm_opt3 = kgm_pn_ratio*kgm_opt1


    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min3

    #lookup current density for optimal Kgm of M5
    iden1 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)
    iden3 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    #Calculate W5 from current density
    w1 = ids_min1/iden1
    w3 = ids_min3/iden3

    # W1 and W3 sized
    print("W1: " + str(w1) + ", L1: " + str(nfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    print("W3: " + str(w3) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm3) + ", id: " + str(ids_min3) + ", gm/id,3: " + str(kgm_opt3))

    kgm_opt6 = kgm_opt1
    kgm_opt8 = kgm_opt3
    ids_min6 = beta*ids_min1
    ids_min8 = ids_min6
    #kcgs6 = nfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt6)
    #kcds7 = pfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt7)



    iden6 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    iden8 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt8)
    w6 = ids_min6/iden6
    w8 = ids_min8/iden8
    gm6 = kgm_opt6*ids_min6
    gm8 = kgm_opt8*ids_min8
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min6) + ", gm/id,6: " + str(kgm_opt6))
    print("W8: " + str(w8) + ", L8: " + str(pfet_tt.length) + ", gm8: " + str(gm8) + ", id: " + str(ids_min8) + ", gm/id,6: " + str(kgm_opt8))
    predicted_gbw = beta*gm1/(2*np.pi*(cload + (kco_opt_np*ids_min6)))
    print("predicted gbw: " + str(predicted_gbw))
    gain = gm1*beta
    print("co n " + str(kco_opt_n*ids_min6))
    print("co p: " + str(kco_opt_p*ids_min6))
    kcgg_p = pfet_tt.lookup(param1="kgm", param2="kcgg", param1_val=kgm_opt8)
    non_dom_pole = gm1/((1+beta)*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    non_dom_pole = non_dom_pole/(2*np.pi)
    dom_pole = gm1*beta/(kco_opt_p*ids_min6 + kco_opt_n*ids_min6 + cload)
    dom_pole = dom_pole/(2*np.pi)
    ro2_n = nfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt1)/gm6
    ro2_p = pfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt3)/gm8
    ro1_n = 1/gm1
    ro1_p = 1/gm3
    ro1 = parallel(ro1_n, ro1_p)
    ro2 = parallel(ro2_n, ro2_p)
    non_dom_pole = 1/(2*np.pi*ro1*(kcgg_p*ids_min1 + kcgg_p*ids_min8))
    gain = gm1*beta*ro2
    gain_db = 20*math.log10(gain)
    bw = gbw/gain
    print("non dominant pole: " + str(non_dom_pole))
    print("dominant pole: " + str(dom_pole))
    print("gain: " + str(gain))
    print("gain_db: " + str(gain_db))
    print("3-db BW: " + str(bw))
    ibias = ids_min1*2
    print("ibias: " + str(ibias))
    return ibias

def calculate_kgm_opt_ota(nfet_tt, pfet_tt,gbw=0,cload=0,beta=1):
    kgm_n = nfet_tt.df["kgm"]
    kgm_p = pfet_tt.df["kgm"]
    kcdg_n = nfet_tt.df["kcgd"]
    kcdg_p = pfet_tt.df["kcgd"]
    kcds_n = nfet_tt.df["kcds"]
    kcds_p = pfet_tt.df["kcds"]
    kcdb_n = nfet_tt.df["kcdb"]
    kcdb_p = pfet_tt.df["kcdb"]
    kcdd_n = nfet_tt.df["kcdd"]
    kcdd_p = pfet_tt.df["kcdd"]
    kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
    kco_n = kcdg_n + kcds_n + kcdb_n
    kco_p = kcdg_p + kcds_p + kcdb_p
    nfet_tt.df["kco"] = kco_n
    pfet_tt.df["kco"] = kco_p
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    id1_arr = []
    kgm_arr = []
    ids_min1 = 1e6
    kgm_opt1 = 1e6
    kco_opt = 0
    kco_opt_n = 0
    kco_opt_p = 0
    kgm_opt_n = 0
    kgm_opt_p = 0
    kgm_pn_ratio = 1
    color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
              'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
              'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
    for i in range(0, len(kgm_n)):
        first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
        kgm_ni = kgm_n[i]
        kgm_pi = kgm_ni*kgm_pn_ratio
        kco_ip = pfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_pi)
        kco_in = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_ni)
        second = 1/(1 - (2*np.pi*gbw*2*(kco_ip + kco_in)/kgm_n[i]))
        ids = first*second
        if ids > 0:
            kgm_arr.append(kgm_n[i])
            id1_arr.append(ids)
        if ids <= ids_min1 and ids > 0 and kgm_ni > 15:
            ids_min1 = ids
            kgm_opt1 = kgm_n[i]
            kgm_opt_n = kgm_opt1
            kgm_opt_p = kgm_pi
            kco_opt = kco[i]
            kco_opt_n = kco_in
            kco_opt_p = kco_ip
    return(kgm_opt1, ids_min1, kco_opt_n, kco_opt_p)

def cm_ota2(nfet_device, pfet_device, nfet_tt, pfet_tt, av, bw, cload, beta, epsilon):
    fig = plt.figure()
    show_plot = True
    #gbw = av * bw
    #gbw = 50e6
    #beta = 3
    cload = 100e-15
    gbw = 10e6
    ids_min1, kgm_opt1 = nfet_device.magic_equation(gbw=gbw, cload=cload, epsilon=10, show_plot=False, new_plot=False)
    alpha = 1.732051
    kcgs4 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt1)
    kcgs8 = kcgs4
    kcgd8 = pfet_tt.lookup(param1="kgm", param2="kcgd", param1_val=kgm_opt1)
    beta_num = kgm_opt1 - 2*math.pi*alpha*gbw*kcgs4
    beta_denom = 2*math.pi*alpha*gbw*(kcgs8 + 51*kcgd8)
    beta = beta_num/beta_denom
    kgm_opt_min = 2000
    ids_min1 = 20000
    kco_opt_n = 20000
    kco_opt_p = 20000
    for i in range(0, len(nfet_device.corners)):
        nfet_c = nfet_device.corners[i]
        pfet_c = nfet_device.corners[i]
        kgm_opt11, ids_min11, kco_opt_n1, kco_opt_p1 = calculate_kgm_opt_ota(nfet_tt=nfet_c, pfet_tt=pfet_c,gbw=gbw, cload=cload, beta=1)
        if kgm_opt_min >= kgm_opt11:
            kgm_opt_min = kgm_opt11
            kgm_opt1 = kgm_opt11
            ids_min1 = ids_min11
            kco_opt_n = kco_opt_n1
            kco_opt_p = kco_opt_p1
    #ids_min1, kgm_opt1, ax1, fig1 = nfet_tt.magic_equation(gbw=gbw, cload=cload, show_plot=False, new_plot=False)
    #kgm_opt1, ids_min1, kco_opt_n, kco_opt_p = calculate_kgm_opt_ota(nfet_tt, pfet_tt, 1)
    kco_opt_np = kco_opt_n + kco_opt_p
    kgm_n = nfet_tt.df["kgm"]
    kgm_p = pfet_tt.df["kgm"]
    kcdg_n = nfet_tt.df["kcgd"]
    kcdg_p = pfet_tt.df["kcgd"]
    kcds_n = nfet_tt.df["kcds"]
    kcds_p = pfet_tt.df["kcds"]
    kcdb_n = nfet_tt.df["kcdb"]
    kcdb_p = pfet_tt.df["kcdb"]
    kcdd_n = nfet_tt.df["kcdd"]
    kcdd_p = pfet_tt.df["kcdd"]
    kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
    kco_n = kcdg_n + kcds_n + kcdb_n
    kco_p = kcdg_p + kcds_p + kcdb_p
    nfet_tt.df["kco"] = kco_n
    pfet_tt.df["kco"] = kco_p

    kco_opt = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    alpha = 1.732051
    kcgs4 = pfet_tt.lookup(param1="kgm", param2="kcgs", param1_val=kgm_opt1)
    kcgs8 = kcgs4
    kcgd8 = pfet_tt.lookup(param1="kgm", param2="kcgd", param1_val=kgm_opt1)
    beta_num = kgm_opt1 - 2*math.pi*alpha*gbw*kcgs4
    beta_denom = 2*math.pi*alpha*gbw*(kcgs8 + 51*kcgd8)
    beta = beta_num/beta_denom
    #plt.plot(kgm_n, kco)
    #plt.show()
    #plt.cla()
    if show_plot == True:
        ax = fig.add_subplot(1, 1, 1)

        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        id1_arr = []
        kgm_arr = []
        ids_min1 = 1e6
        kgm_opt1 = 1e6
        kco_opt = 0
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                  'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                  'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        for i in range(0, len(kgm_n)):
            first = 2*np.pi*gbw*cload/(beta*kgm_n[i])
            second = 1/(1 - (2*np.pi*gbw*kco[i]/kgm_n[i]))
            ids = first*second
            if ids > 0:
                kgm_arr.append(kgm_n[i])
                id1_arr.append(ids)
            if ids <= ids_min1 and ids > 0:
                ids_min1 = ids
                kgm_opt1 = kgm_n[i]
                kco_opt = kco[i]
        for i in range(0,len(nfet_device.corners)):
            ncorner = nfet_device.corners[i]
            pcorner = pfet_device.corners[i]
            kgm_n = ncorner.df["kgm"]
            kcdg_n = ncorner.df["kcgd"]
            kcdg_p = pcorner.df["kcgd"]
            kcds_n = ncorner.df["kcds"]
            kcds_p = pcorner.df["kcds"]
            kcdb_n = ncorner.df["kcdb"]
            kcdb_p = pcorner.df["kcdb"]
            kcdd_n = ncorner.df["kcdd"]
            kcdd_p = pcorner.df["kcdd"]
            kco = kcdg_n + kcdg_p + kcds_n + kcds_p + kcdb_n + kcdb_p
            kcn = kcdg_n + kcds_n + kcdb_n
            kcp = kcdg_p + kcds_p + kcdb_p
            #plt.plot(kgm_n, kco)
            #plt.show()
            #plt.cla()
            id1_arr = []
            kgm_arr = []
            kco_arr = []
            kcn_arr = []
            kcp_arr = []
            ids_min1 = 1e6
            kgm_opt1 = 1e6
            kco_opt = 0
            for j in range(0, len(kgm_n)):
                kco_j = kco[j]
                kcn_j = kcn[j]
                kcp_j = kcp[j]
                first = 2*np.pi*gbw*cload/(beta*kgm_n[j])
                second = 1/(1 - (2*np.pi*gbw*kco[j]/kgm_n[j]))
                ids = first*second
                if ids > 0:
                    kgm_arr.append(kgm_n[j])
                    id1_arr.append(ids*1e6)
                    kco_arr.append(kco_j)
                    kcn_arr.append(kcn_j)
                    kcp_arr.append(kcp_j)
                if ids <= ids_min1 and ids > 0:
                    ids_min1 = ids
                    kgm_opt1 = kgm_n[j]
                    kco_opt = kco[j]
            linestyle = "solid"
            if i > 2:
                linestyle = "dashed"
            if i > 5:
                linestyle = "dotted"
            ax.plot(kgm_arr, id1_arr, linestyle=linestyle)
            #ax.plot(kgm_arr, kco_arr, linestyle="solid")
            #ax.plot(kgm_arr, kcn_arr, linestyle="dashed")
            #ax.plot(kgm_arr, kcp_arr, linestyle="dotted")
        ax.set_xlabel("Kgm [S/A]")
        ax.set_ylabel("Id M1 [uA]")
        ax.set_title("M1 Optimal Drain Current vs Kgm With 9 corners")
        plt.plot(kgm_arr, id1_arr)
        plt.show()
    #ids_min1 = ids_min1/beta
    ids_min3 = ids_min1

    #plt.show()
    kgm_pn_ratio = 1
    kgm_opt3 = kgm_pn_ratio*kgm_opt1
    first = 2*np.pi*gbw*cload/(beta*kgm_opt1)
    kco_ip = pfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    kco_in = nfet_tt.lookup(param1="kgm", param2="kco", param1_val=kgm_opt1)
    second = 1/(1 - (2*np.pi*gbw*2*(kco_ip + kco_in)/kgm_opt1))
    ids = first*second
    ids_min1 = ids
    ids_min3 = ids_min1

    #calculate optimal gms
    gm1 = kgm_opt1*ids_min1
    gm3 = kgm_opt3*ids_min3

    #lookup current density for optimal Kgm of M5
    iden1 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt1)
    iden3 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt3)
    #Calculate W5 from current density
    w1 = ids_min1/iden1
    w3 = ids_min3/iden3
    
    # W1 and W3 sized
    print("W1: " + str(w1) + ", L1: " + str(nfet_tt.length) + ", gm1: " + str(gm1) + ", id: " + str(ids_min1) + ", gm/id,1: " + str(kgm_opt1))
    print("W3: " + str(w3) + ", L1: " + str(pfet_tt.length) + ", gm1: " + str(gm3) + ", id: " + str(ids_min3) + ", gm/id,3: " + str(kgm_opt3))
    
    kgm_opt6 = kgm_opt1
    kgm_opt8 = kgm_opt3
    ids_min6 = beta*ids_min1
    ids_min8 = ids_min6
    #kcgs6 = nfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt6)
    #kcds7 = pfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt7)



    iden6 = nfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt6)
    iden8 = pfet_tt.lookup(param1="kgm", param2="iden", param1_val=kgm_opt8)
    w6 = ids_min6/iden6
    w8 = ids_min8/iden8
    gm6 = kgm_opt6*ids_min6
    gm8 = kgm_opt8*ids_min8
    # W6 Now sized
    print("W6: " + str(w6) + ", L6: " + str(pfet_tt.length) + ", gm6: " + str(gm6) + ", id: " + str(ids_min6) + ", gm/id,6: " + str(kgm_opt6))
    print("W8: " + str(w8) + ", L8: " + str(pfet_tt.length) + ", gm8: " + str(gm8) + ", id: " + str(ids_min8) + ", gm/id,6: " + str(kgm_opt8))
    print("co n " + str(kco_opt_n*ids_min6))
    print("co p: " + str(kco_opt_p*ids_min6))
    kcgg_8 = pfet_tt.lookup(param1="kgm", param2="kcgg", param1_val=kgm_opt8)
    kcdd_3 = pfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt3)
    kcdd_1 = nfet_tt.lookup(param1="kgm", param2="kcdd", param1_val=kgm_opt1)
    #non_dom_pole = non_dom_pole/(2*np.pi)
    # TODO INVESTIGATE EXTRA 2
    predicted_gbw = beta*gm1/(2*np.pi*(cload + (2*kco_opt_np*ids_min6)))
    ro1_n = nfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt1)
    ro1_p = pfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt3)
    ro1_n = 1/gm1
    ro1_p = 1/gm3
    ro6_n = nfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt6)
    ro8_p = pfet_tt.lookup(param1="kgm", param2="gmro", param1_val=kgm_opt8)
    ro6_n = ro6_n/gm6
    ro8_p = ro8_p/gm8
    rout = parallel(ro6_n, ro8_p)
    dom_pole1 = gbw
    dom_pole = 1/(2*np.pi*rout*(cload + (kco_opt_np*ids_min6)))
    ro1 = parallel(ro1_n, ro1_p)
    # TODO INVESTIGATE EXTRA 2 - bw is half differiantial circuit
    gain = beta*gm1*(rout)

    non_dom_pole = 1/(2*2*np.pi*ro1*(kcdd_3*ids_min1 + kcdd_1*ids_min1 + (1 + gain)*kcgg_8*ids_min8))
    predicted_gbw = predicted_gbw/2
    non_dom_pole = non_dom_pole/2
    dom_pole = dom_pole/2
    print("non dominant pole Mhz: " + str(non_dom_pole*1e-6))
    print("dominant pole Mhz: " + str(dom_pole*1e-6))
    print("Gain Bandwidth Mhz: " + str(predicted_gbw*1e-6))
    gain = beta*gm1*(rout)
    print("Gain V/V: " + str(gain))

    wt_wp1 = predicted_gbw/non_dom_pole
    arctan_unity = np.arctan(wt_wp1)
    phase_degrees = arctan_unity*180/np.pi
    phase_margin = 90 - phase_degrees
    print("Phase Margin Degees: " + str(phase_margin))
    ibias = ids_min1*2
    print("ibias: " + str(ibias))
    vgs_1 = nfet_tt.lookup(param1="kgm", param2="VGS", param1_val=kgm_opt1)
    vdd_tech = nfet_tt.vdd
    r_drop = vdd_tech - vgs_1
    r_bias = r_drop/ibias
    print("Rbias KOhm: " + str(r_bias*1e-3))
    print("Beta: " + str(beta))
    #plot_ota_loop_gain()
    #plot_ota_loopgain_phase()
    omega_1 = dom_pole*2*math.pi
    omega_2 = non_dom_pole*2*math.pi
    f = np.logspace(-5, 8, 5000)
    w = 2*np.pi*f
    s = 1.0j*w
    part1 = control.TransferFunction(gain*omega_1, [1, omega_1])
    part2 = control.TransferFunction(omega_2, [1, omega_2])
    H = part1*part2



    #num = np.array([50])
    #denom = np.polymul(np.array([1, 1]), np.array([1/omega_1, 1/omega_2]))
    #H = ml.tf(num, denom)
    poles = ml.pole(H)
    zeros = ml.zero(H)
    print(H)

    mag_cal, phase_cal, w = ml.bode(H)

    #plot_ota_loop_gain(f, mag_cal, H)
    plot_ota_loopgain_phase(f, mag_cal, H)

    plt.show()
    print(H)
    return ibias

# Create CIDDevices from LUTs
tsmc28_n_device = CIDDevice(device_name="tsmc28n", lut_directory="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac/nch_18_mac/LUT_N_1u/",
                            corner_list=None, vdd=1.8)

tsmc28_p_device = CIDDevice(device_name="tsmc28p", lut_directory="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac/pch_18_mac/LUT_P_1u/",
                      corner_list=None, vdd=1.8)

tsmc28_n_tt = CIDCorner(corner_name="ttroom",
                      lut_csv="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac/nch_18_mac/LUT_N_1u/nfetttroom.csv",
                      vdd=1.8)

tsmc28_p_tt = CIDCorner(corner_name="ttroom",
                      lut_csv="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac/pch_18_mac/LUT_P_1u/pfetttroom.csv",
                      vdd=1.8)

av = 25
bw = 1e6
gbw = av*bw
cload = 1e-12
beta = 1.5
#plot_ota_loop_gain()
#splot_ldo_loop_gain()
#plot_ldo_output_noise()
#plot_ldo_loopgain_phase()
#plot_ldo_psrr()
cm_ota2(nfet_device=tsmc28_n_device, pfet_device=tsmc28_p_device,
        nfet_tt=tsmc28_n_tt, pfet_tt=tsmc28_p_tt, av=av, bw=bw, cload=cload,
        beta=beta, epsilon=1e-6)

plot_kgm_id_ota(nfet_device=tsmc28_n_device, pfet_device=tsmc28_p_device,
        nfet_tt=tsmc28_n_tt, pfet_tt=tsmc28_p_tt, av=av, bw=bw, cload=cload,
        beta=7, epsilon=1e-6)





plot_kc2_ota(nfet_device=tsmc28_n_device, pfet_device=tsmc28_p_device,
        nfet_tt=tsmc28_n_tt, pfet_tt=tsmc28_p_tt, av=av, bw=bw, cload=cload,
        beta=7, epsilon=1e-6)

plot_kgm_id_ota(nfet_device=tsmc28_n_device, pfet_device=tsmc28_p_device,
        nfet_tt=tsmc28_n_tt, pfet_tt=tsmc28_p_tt, av=av, bw=bw, cload=cload,
        beta=7, epsilon=1e-6)


av2 = math.sqrt(av)
av1 = math.sqrt(av)
gbw1 = av1*bw
gbw2 = av2*bw
# Size stage 1, this example is only for tt corner at room temperature
cload1 = ota_stage_design2(nfet_device=gf22_n_device, nfet_tt=gf22_n_tt, pfet_device=gf22_p_device, pfet_tt=gf22_p_tt,
                  av=av2, bw=bw, cload=cload2)
cc = 0.2*cload2
cload1 = cload1 + cc*(1 + av2)
ota_stage_design1(nfet_device=gf22_n_device, nfet_tt=gf22_n_tt, pfet_device=gf22_p_device, pfet_tt=gf22_p_tt,
                  av=av1, bw=bw, cload=cload1)


print("DONE")


