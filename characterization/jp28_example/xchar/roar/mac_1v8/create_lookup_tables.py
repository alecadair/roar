
#
# Author: Alec S. Adair
# This script generates all lookuptables for a given PDK
#

import os
import shutil

def create_lookup_tables():

    nfet = "nfet"
    pfet = "pfet"

    ss = "ss"
    tt = "tt"
    ff = "ff"

    cold = "cold"
    room = "room"
    hot = "hot"

    nsscold = nfet + ss + cold
    nttcold = nfet + tt + cold
    nffcold = nfet + ff + cold
    nssroom = nfet + ss + room
    nttroom = nfet + tt + room
    nffroom = nfet + ff + room
    nsshot = nfet + ss + hot
    ntthot = nfet + tt + hot
    nffhot = nfet + ff + hot

    psscold = pfet + ss + cold
    pttcold = pfet + tt + cold
    pffcold = pfet + ff + cold
    pssroom = pfet + ss + room
    pttroom = pfet + tt + room
    pffroom = pfet + ff + room
    psshot = pfet + ss + hot
    ptthot = pfet + tt + hot
    pffhot = pfet + ff + hot

    lengths = ["150n", "250n", "500n", "1u", "1.5u", "2u", "3u", "4u"]

    ncorners = [nsscold, nttcold, nffcold,
                nssroom, nttroom, nffroom,
                nsshot, ntthot, nffhot]

    pcorners = [psscold, pttcold, pffcold,
                pssroom, pttroom, pffroom,
                psshot, ptthot, pffhot]

    for length in lengths:
        sim_string = "simulator lang=spectre"
        n_sim_echo = "echo " + sim_string + " > n_netlist_" + length
        p_sim_echo = "echo " + sim_string + " > p_netlist_" + length
        os.system(n_sim_echo)
        os.system(p_sim_echo)
        param_string = "parameters L=" + length
        n_echo = "echo " + param_string + "  >> n_netlist_" + length
        p_echo = "echo " + param_string + "  >> p_netlist_" + length
        os.system(n_echo)
        os.system(p_echo)
        n_cat = "cat n_netlist_template >> n_netlist_" + length
        p_cat = "cat p_netlist_template >> p_netlist_" + length
        os.system(n_cat)
        os.system(p_cat)
        n_copy = "cp n_netlist_" + length + " n_netlist"
        p_copy = "cp p_netlist_" + length + " p_netlist"
        os.system(n_copy)
        os.system(p_copy)
        lookuptable_dir_n = "LUT_N_" + length
        lookuptable_dir_p = "LUT_P_" + length
        n_mkdir = "mkdir " + lookuptable_dir_n
        p_mkdir = "mkdir " + lookuptable_dir_p
        if os.path.exists(lookuptable_dir_n):
            shutil.rmtree(lookuptable_dir_n)
        if os.path.exists(lookuptable_dir_p):
            shutil.rmtree(lookuptable_dir_p)
        os.system(n_mkdir)
        os.system(p_mkdir)

        for ncorner in ncorners:
            spectre_command = "spectremdl -format psfascii -batch nfet_characterization.mdl -design " + ncorner + ".scs"
            os.system(spectre_command)
            mv_command = "mv techLUT.csv " + lookuptable_dir_n + "/" + ncorner + ".csv"
            os.system(mv_command)
            os.system("./clean")
        for pcorner in pcorners:
            spectre_command = "spectremdl -format psfascii -batch nfet_characterization.mdl -design " + pcorner + ".scs"
            os.system(spectre_command)
            mv_command = "mv techLUT.csv " + lookuptable_dir_p + "/" + pcorner + ".csv"
            os.system(mv_command)
            os.system("./clean")

create_lookup_tables()
