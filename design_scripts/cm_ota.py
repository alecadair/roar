import sys, os, getpass, shutil, operator, collections, copy, re, math

sys.path.append('/home/aadair/Documents/GradSchoolGeneral/LCAS/ICU')
from cid import *

def parallel(x1, x2):
    return 1/((1/x1) + 1/x2)

def create_spice_netlist_for_place_and_route(nf1_2, nf3_4, nf5_6, nf7_8):
    print("TODO")

def total_current_ota(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1, kgm2, gain_spec):
    p_factor = 1
    kcgs_8 = nom_pcorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2*p_factor)
    kcgd_8 = nom_pcorner.lookup(param1="kgm", param2="kcgd", param1_val=kgm2*p_factor)
    kcds_8 = nom_pcorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2*p_factor)
    kcgs_6 = nom_ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2)
    kcds_6 = nom_ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2)
    kcgs_4 = nom_pcorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm1*p_factor)
    kgds_6 = nom_ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    kgds_8 = nom_pcorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    kcout = kcgs_8 + kcds_8 + kcgs_6 + kcds_6
    beta_num = kgm1 - 2*math.pi*alpha*gbw*kcgs_4
    beta_denom = 1/(2*math.pi*alpha*gbw*(kcgs_8 + kcgd_8))
    beta = beta_num*beta_denom
    m1_current_term1 = 2*math.pi*gbw*cload/(beta*kgm1)
    m1_current_term2 = 1/(1 - 2*math.pi*gbw*kcout/kgm1)
    m1_current = m1_current_term1*m1_current_term2
    total_current = m1_current + beta*m1_current
    gain = kgm1/(kgds_6 + kgds_8)
    beta_valid = True
    gain_valid = True
    if beta < 1:
        beta_valid = False
    if gain < gain_spec:
        gain_valid = False
    return total_current, beta_valid, gain_valid

def plot_results_krummenechar_ota_stage1(nom_ncorner, nom_pcorner, alpha, gbw, cload):
    gain = 60
    kgm_n_v = nom_ncorner.df["kgm"]
    kgm_p_v = nom_pcorner.df["kgm"]
    max_n = max(kgm_n_v)
    max_p = max(kgm_p_v)
    min_n = min(kgm_n_v)
    min_p = min(kgm_p_v)
    kgm_min = min(min_n, min_p)
    kgm_max = max(max_n, max_p)
    #kgm_max = 18
    kgm_max = 18
    kgm_min = 4
    if kgm_min < 0:
        kgm_min = 0.001
    kgm1_vals = np.linspace(kgm_min, kgm_max, 50)
    kgm2_vals = np.linspace(kgm_min, kgm_max, 50)
    kgm1_grid, kgm2_grid = np.meshgrid(kgm1_vals, kgm2_vals)
    z = np.zeros_like(kgm1_grid)
    beta_valid_grid = np.zeros_like(kgm1_grid)
    gain_valid_grid = np.zeros_like(kgm1_grid)
    zlim_min = 0.6
    zlim_max = 20
    for i in range(len(kgm1_vals)):
        for j in range(len(kgm2_vals)):
            total_current, beta_valid, gain_valid = total_current_ota(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1_vals[i], kgm2_vals[j], gain_spec=gain)
            total_current = total_current*1e6
            if total_current <= 0:
                total_current = zlim_max
            else:
                total_current = total_current
                if total_current > zlim_max:
                    total_current = zlim_max
            #if beta_valid == False:
            #    total_current = np.nan
            #if gain_valid == False:
            #    total_current = np.nan
            z[i, j] = total_current
            beta_valid_grid[i, j] = beta_valid
            gain_valid_grid[i, j] = gain_valid
    #z = total_current_ota(nom_ncorner,nom_pcorner,alpha, gbw, cload, kgm1, kgm2)
    font_properties = {'family': 'Arial', 'weight': 'bold'}
    fig = plt.figure(figsize=(12,6))
    ax = fig.add_subplot(121, projection='3d')

    #plot where kgm1 = kgm2
    diagonal_mask = np.isclose(kgm1_grid, kgm2_grid)
    ax.plot(kgm1_grid[diagonal_mask], kgm2_grid[diagonal_mask], z[diagonal_mask], color='black', linewidth=2, label="kgm1 = kgm2")
    surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap='winter', edgecolor='none', alpha=0.8)
    #surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap='viridis', edgecolor='none', alpha=0.8)
    #surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap='cividis', edgecolor='none', rstride=10, cstride=10)
    #ax.set_zscale('log')
    #ax.set_xscale('log')
    #ax.set_yscale('log')
    ax.set_zlim(zlim_min, zlim_max)

    ax.set_xlabel("kgm1", fontdict=font_properties)
    ax.set_ylabel("kgm2", fontdict=font_properties)
    ax.set_zlabel("Total Current [uA]", fontdict=font_properties)

    cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
    cbar.set_label('Total Current [uA]', fontdict=font_properties)
    surf.set_clim(zlim_min, zlim_max)  # Set the colorbar limits to match the z-axis limits
    cbar.ax.yaxis.set_tick_params(labelsize=10, width=2)  # Adjust tick parameters if needed
    # Overlay red X's for NaN values
    nan_mask = np.isnan(z)
    beta_false_mask = beta_valid_grid == False
    beta_mask = np.where(beta_false_mask)

    gain_false_mask = gain_valid_grid == False
    gain_mask = np.where(gain_false_mask)

    # Plot the 'X' at positions where total_current_ota is NaN
    #ax.scatter(kgm1_grid[beta_mask], kgm2_grid[beta_mask], np.full_like(kgm1_grid[beta_mask], zlim_min), color='r', marker='x', s=50, label="Beta < 1")
    #ax.scatter(kgm1_grid[gain_mask], kgm2_grid[gain_mask], np.full_like(kgm1_grid[gain_mask], zlim_min), color='g', marker='x', s=50, label="Gain < 60")

    beta_false_mask = beta_valid_grid == False
    ax.scatter(kgm1_grid[beta_false_mask], kgm2_grid[beta_false_mask], np.full_like(kgm1_grid[beta_false_mask], zlim_min), color='r', marker='x', s=50, label="Beta < 1")

    # Overlay green X's for invalid gain values
    gain_false_mask = gain_valid_grid == False
    ax.scatter(kgm1_grid[gain_false_mask], kgm2_grid[gain_false_mask], np.full_like(kgm1_grid[gain_false_mask], zlim_min), color='g', marker='x', s=50, label="Gain < 60")


    # Add a grid for better readability
    ax.xaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax.yaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax.zaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax.legend()


    ax2 = fig.add_subplot(122)
    contour = ax2.contourf(kgm1_grid, kgm2_grid, z, levels=20, cmap='winter')
    #ax2.scatter(kgm1_grid[nan_mask], kgm2_grid[nan_mask], color='red', marker='x', s=50, label="Infeasible Region")
    ax2.scatter(kgm1_grid[beta_mask], kgm2_grid[beta_mask], color='r', marker='x', s=50, label="Beta < 1 Region")
    ax2.scatter(kgm1_grid[gain_mask], kgm2_grid[gain_mask], color='g', marker='x', s=50, label="Gain < 50")




    #ax2.plot(kgm1_vals, kgm1_vals, color="black", linewidth=2, label="kgm1 = kgm2")
    # Add color bar to show total current magnitude
    cbar2 = fig.colorbar(contour, ax=ax2)
    cbar2.set_label('log10(Total Current (ota))', fontdict=font_properties)

    # Set axis labels with custom font properties
    ax2.set_xlabel('kgm1', fontdict=font_properties)
    ax2.set_ylabel('kgm2', fontdict=font_properties)

    # Add gridlines for better readability
    ax2.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Show the legend for the contour plot
    ax2.legend()

    # Adjust layout for better spacing
    plt.tight_layout()

    plt.show()

    print("TODO")


def krummenechar_ota_stage1(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    av= 50
    #bw = 250e6
    bw = 5e5
    gbw = bw * av
    cload = 250e-15


    inverse_tan_thirty = math.tan(30*math.pi/180)
    inverse_tan_thirty = math.tan(30*math.pi/180)
    alpha = 1/inverse_tan_thirty
    two_pi_alpha_gbw = 2*math.pi*alpha*gbw
    f2 = alpha*gbw
    ids_min1, kgm1 = nfet_device.magic_equation(gbw, cload=cload, epsilon=10, beta_factor=1, show_plot=False, new_plot=False)
    kgm_n = kgm1
    #kgm_p = kgm1*(1/2)
    kgm_p = kgm1*.8
    #kgm_p = kgm_n
    kcgs1_2 = nom_ncorner.lookup(param1="kgm", param2="kcgg", param1_val=kgm1)
    kcgd1_2 = nom_ncorner.lookup(param1="kgm", param2="kcgd", param1_val=kgm1)
    kcds1_2 = nom_ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm1)
    kcgs3_4 = nom_pcorner.lookup(param1="kgm", param2="kcgg", param1_val=kgm_p)
    kcgd3_4 = nom_pcorner.lookup(param1="kgm", param2="kcgd", param1_val=kgm_p)
    kcds3_4 = nom_pcorner.lookup(param1="kgm", param2="kcds", param1_val=kgm_p)
    kgm1_2 = kgm1
    kgm3_4 = kgm_p
    kgm5_6 = kgm1
    kgm7_8 = kgm_p
    gm_gds1_2 = nom_ncorner.lookup(param1="kgm", param2="gm/gds", param1_val=kgm1)
    gm_gds5_6 = gm_gds1_2
    gm_gds3_4 = nom_pcorner.lookup(param1="kgm", param2="gm/gds", param1_val=kgm_p)
    gm_gds7_8 = gm_gds3_4
    two_pi_alpha_gbw_kcgs3_4 = two_pi_alpha_gbw*kcgs3_4
    beta_num = kgm3_4 - two_pi_alpha_gbw_kcgs3_4
    #beta_denom = two_pi_alpha_gbw*(kcgs3 + (1 + av)*kcgd3)
    beta_denom = two_pi_alpha_gbw*(kcgs3_4 + kcgd3_4)
    beta = beta_num/beta_denom
    ids_min = ids_min1/beta
    ids1_2 = ids_min
    ids5_6 = beta*ids1_2

    gm1_2 = kgm1_2*ids_min
    gm3_4 = kgm3_4*ids_min
    ids_branch2 = ids_min*beta
    gm5_6 = kgm5_6*ids_branch2
    gm7_8 = kgm7_8*ids_branch2
    iden1_2 = nom_ncorner.lookup(param1="kgm", param2="iden", param1_val=kgm1_2)
    iden3_4 = nom_pcorner.lookup(param1="kgm", param2="iden", param1_val=kgm3_4)

    w1_2 = ids_min/iden1_2
    print("W 1,2: " + str(w1_2))
    w3_4 = ids_min/iden3_4
    print("W 3,4: " + str(w3_4))
    w5_6 = ids_branch2/iden1_2
    print("W 5,6: " + str(w5_6))
    w7_8 = ids_branch2/iden3_4
    print("W 7,8: " + str(w7_8))

    print("")
    print("DIVIDE BY 2 FOR MIN NUMBER OF FINGERS")
    w1_2_half = w1_2/1
    print("W 1,2: " + str(w1_2_half))
    w3_4_half = w3_4/1
    print("W 3,4: " + str(w3_4_half))
    w5_6_half = w5_6/1
    print("W 5,6: " + str(w5_6_half))
    w7_8_half = w7_8/1
    print("W 7,8: " + str(w7_8_half))

    print("")
    print("ROUND TO 2 DRC finger width")
    multiple = 0.84e-6
    w1_2_rounded = round(w1_2_half/multiple)*multiple
    print("W 1,2: " + str(w1_2_rounded))
    w3_4_rounded = round(w3_4_half/multiple)*multiple
    print("W 3,4: " + str(w3_4_rounded))
    w5_6_rounded = round(w5_6_half/multiple)*multiple
    print("W 5,6: " + str(w5_6_rounded))
    w7_8_rounded = round(w7_8_half/multiple)*multiple
    print("W 7,8: " + str(w7_8_rounded))

    print("")
    print("DIVIDE finger width")
    finger_width = 840e-9
    w1_2_fingers  = w1_2_rounded/finger_width
    print("W 1,2: " + str(w1_2_fingers))
    w3_4_fingers = w3_4_rounded/finger_width
    print("W 3,4: " + str(w3_4_fingers))
    w5_6_fingers = w5_6_rounded/finger_width
    print("W 5,6: " + str(w5_6_fingers))
    w7_8_fingers = w7_8_rounded/finger_width
    print("W 7,8: " + str(w7_8_fingers))
    print("ITAIL: " + str(ids_min*2))

    print("")
    w1_2_fingers  = w1_2_fingers*2
    print("W 1,2: " + str(w1_2_fingers))
    w3_4_fingers = w3_4_fingers*2
    print("W 3,4: " + str(w3_4_fingers))
    w5_6_fingers = w5_6_fingers*2
    print("W 5,6: " + str(w5_6_fingers))
    w7_8_fingers = w7_8_fingers*2
    print("W 7,8: " + str(w7_8_fingers))
    print("W 9,10: " + str(w1_2_fingers))
    print("ITAIL: " + str(ids_min*2))
    print("")

    gds5_6 = gm5_6/gm_gds5_6
    gds7_8 = gm7_8/gm_gds7_8
    gain = (beta*gm1_2)/(gds5_6 + gds7_8)
    gds_o = gds5_6 + gds7_8
    r_out = 1/gds_o
    cout = kcds3_4*ids5_6 + kcgs3_4*ids5_6 + kcds1_2*ids1_2 + kcgs1_2*ids1_2 + cload

    bandwidth_measured = 1/(2*math.pi*cout*r_out)

    print("Gain: " + str(gain) + " V/V")
    #print("Gain: " + str(20*math.log10(gain)) + " dB")
    print("GBW: " + str((gain*bandwidth_measured)*1e-6) + " MHz")
    bandwidth_predicted = gbw/gain
    print("f2: " + str(f2*1e-6) + " Mhz")
    print("3dB BW: " + str(bandwidth_measured*1e-6) + " MHz")
    print("3dB BW Predict: " + str(bandwidth_predicted*1e-6) + " MHz")
    print("")
    print("IDS1,2: " + str(ids1_2*1e6) + " uA")
    print("IDS5,6: " + str(ids5_6*1e6) + " uA")
    print("")
    print("Beta: " + str(beta))
    print("Alpha: " + str(alpha))
    print("")
    print("kgm 1,2: " + str(kgm1_2))
    print("kgm 3,4; " + str(kgm3_4))
    print("kgm 5,6 " + str(kgm5_6))
    print("kgm 7,8 " + str(kgm7_8))
    print("")
    plot_results_krummenechar_ota_stage1(nom_ncorner, nom_pcorner, alpha, gbw, cload)
    return w1, gm1, kgm1, w2, gm2, kgm2




nfet_device = CIDDevice(device_name="nfet_150n", vdd=1.8,
                        lut_directory="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500",
                        corner_list=None)
pfet_device = CIDDevice(device_name="pfet_150n", vdd=1.8,
                        lut_directory="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500",
                        corner_list=None)
nfet_nominal = CIDCorner(corner_name="nfet_150n_nominal",
                   lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt27.csv",
                   vdd=1.8)

pfet_nominal = CIDCorner(corner_name="pet_150n_nominal",
                   lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt27.csv",
                   vdd=1.8)

#av1 = math.sqrt(av)
av1 = 100
bw = 500e3
cload1 = 50e-15
w1, gm1, kgm1, w2, gm2, kgm2 = krummenechar_ota_stage1(av=av1, bw=bw, cload=cload1, nfet_device=nfet_device,
                                                       pfet_device=pfet_device, nom_ncorner=nfet_nominal, nom_pcorner=pfet_nominal)




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
