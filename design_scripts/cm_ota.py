import sys, os, getpass, shutil, operator, collections, copy, re, math
sys.path.append("/pri/ala1/Documents/CAD/roar/src")
from cid import *

def parallel(x1, x2):
    return 1/((1/x1) + 1/x2)

def create_spice_netlist_for_place_and_route(nf1_2, nf3_4, nf5_6, nf7_8):
    print("TODO")

def total_current_ota_v2(ncorner, pcorner, alpha, gbw, cload, kgm1, kgm2, gain_spec):
    f1 = 2*math.pi*gbw
    p_factor = 1
    kcgs_8 = ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2*p_factor)
    kcgd_8 = ncorner.lookup(param1="kgm", param2="kcgd", param1_val=kgm2*p_factor)
    kcds_8 = ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2*p_factor)
    kcgs_6 = ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2)
    kcds_6 = ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2)
    kcgs_4 = ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm1*p_factor)
    kgds_6 = ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    kgds_8 = ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    gain = kgm1/(kgds_6 + kgds_8)
    kcout = kcgs_8 + (kcds_8) + kcgs_6 + kcds_6
    beta_num = kgm1 - 2*math.pi*alpha*gbw*kcgs_4
    beta_denom = 1/(2*math.pi*alpha*gbw*(kcgs_8 + kcgd_8))
    beta = beta_num*beta_denom
    #m1_current_term1 = 2*math.pi*gbw*cload/(beta*kgm1)
    #m1_current_term2 = 1/(1 - 2*math.pi*gbw*kcout/kgm1)
    #m1_current = m1_current_term1*m1_current_term2
    #total_current = m1_current + beta*m1_current
    kcsg_8 = kcgs_8 + kcgd_8

    total_current_num = alpha*cload*f1*f1*kcsg_8 - alpha*cload*f1*f1*kcgs_4 + f1*cload*kgm1
    total_current_denom = (kgm1 - alpha*f1*kcgs_4)*(kgm1 - f1*kcout)
    total_current = total_current_num/total_current_denom
    beta_valid = True
    gain_valid = True
    if beta < 1:
        beta_valid = False
    if gain < gain_spec:
        gain_valid = False
    return total_current, beta, beta_valid, gain_valid


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
    return total_current, beta, beta_valid, gain_valid





def plot_results_krummenechar_ota_stage1(nom_ncorner, nom_pcorner, alpha, gain, bw, cload, fig, ax1, ax2, ax3, ax4,
                                         color_map, beta_color, gain_color, alpha_graph, marker_size):
    gbw = gain*bw
    kgm_n_v = nom_ncorner.df["kgm"]
    kgm_p_v = nom_pcorner.df["kgm"]
    max_n = max(kgm_n_v)
    max_p = max(kgm_p_v)
    min_n = min(kgm_n_v)
    min_p = min(kgm_p_v)
    kgm_min = min(min_n, min_p)
    kgm_max = max(max_n, max_p)
    #kgm_max = 18
    kgm_max = 20
    kgm_min = 0.1
    num_samples = 50
    if kgm_min < 0:
        kgm_min = 0.001
    kgm1_vals = np.linspace(kgm_min, kgm_max, num_samples)
    kgm2_vals = np.linspace(kgm_min, kgm_max, num_samples)
    kgm1_grid, kgm2_grid = np.meshgrid(kgm1_vals, kgm2_vals)
    z = np.zeros_like(kgm1_grid)
    beta = np.zeros_like(kgm1_grid)
    beta_valid_grid = np.zeros_like(kgm1_grid)
    gain_valid_grid = np.zeros_like(kgm1_grid)
    zlim_min = -0.5
    zlim_max = 10
    beta_min = -10
    beta_max = 10
    for i in range(len(kgm1_vals)):
        for j in range(len(kgm2_vals)):
            #total_current, beta1, beta_valid, gain_valid = total_current_ota(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1_vals[i], kgm2_vals[j], gain_spec=gain)
            total_current, beta_i_j, beta_valid, gain_valid = total_current_ota_v2(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1_vals[i], kgm2_vals[j], gain_spec=gain)
            total_current = total_current*1e6
            #total_current2 = total_current2 * 1e6
            if total_current < zlim_min:
                total_current = zlim_min
                total_current = total_current
            if total_current > zlim_max:
                total_current = zlim_max
            if beta_i_j < beta_min:
                beta_i_j = beta_min
            if beta_i_j > beta_max:
                beta_i_j = beta_max
            #if beta_valid == False:
            #    total_current = np.nan
            #if gain_valid == False:
            #    total_current = np.nan
            z[i, j] = total_current
            beta[i, j] = beta_i_j
            beta_valid_grid[i, j] = beta_valid
            gain_valid_grid[i, j] = gain_valid
    #z = total_current_ota(nom_ncorner,nom_pcorner,alpha, gbw, cload, kgm1, kgm2)

    font_properties = {'family': 'Arial', 'weight': 'bold'}
    #fig = plt.figure(figsize=(12,6))

    #ax = fig.add_subplot(121, projection='3d')
    #ax = ax1
    #plot where kgm1 = kgm2
    diagonal_mask = np.isclose(kgm1_grid, kgm2_grid)
    #surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap=color_map, lw=0.5, edgecolor='k', rstride=3, cstride=3, alpha=alpha_graph)
    surf_i_total = ax1.plot_surface(kgm1_grid, kgm2_grid, z, lw=0.5, cmap=color_map, edgecolor='royalblue', rstride=3, cstride=3, alpha=alpha_graph)
    surf_beta = ax3.plot_surface(kgm1_grid, kgm2_grid, beta, lw=0.5, cmap=color_map, edgecolor="royalblue", rstride=3, cstride=3, alpha=alpha_graph)
    ax1.plot(kgm1_grid[diagonal_mask], kgm2_grid[diagonal_mask], z[diagonal_mask]+0.5, color='k', linewidth=4, label="kgm1 = kgm2")
    ax1.plot(kgm1_grid[diagonal_mask], kgm2_grid[diagonal_mask], beta[diagonal_mask]+0.5, color='k', linewidth=4, label="kgm1 = kgm2")
    #surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap='viridis', edgecolor='none', alpha=0.8)
    #surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap='cividis', edgecolor='none', rstride=10, cstride=10)
    #ax.set_zscale('log')
    #ax.set_xscale('log')
    #ax.set_yscale('log')

    ax1.set_xlabel("kgm1", fontdict=font_properties)
    ax1.set_ylabel("kgm2", fontdict=font_properties)
    ax1.set_zlabel("Total Current [uA]", fontdict=font_properties)

    ax3.set_xlabel("kgm1")
    ax3.set_ylabel("kgm2")
    ax3.set_zlabel("Beta")
    #cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
    #cbar.set_label('Total Current [uA]', fontdict=font_properties)
    #surf.set_clim(zlim_min, zlim_max)  # Set the colorbar limits to match the z-axis limits
    #cbar.ax.yaxis.set_tick_params(labelsize=12, width=2)  # Adjust tick parameters if needed

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
    #ax.scatter(kgm1_grid[beta_false_mask], kgm2_grid[beta_false_mask], np.full_like(kgm1_grid[beta_false_mask], zlim_min), color=beta_color, marker='x', alpha=alpha_graph, s=marker_size, label="Beta < 1")

    # Overlay green X's for invalid gain values
    gain_false_mask = gain_valid_grid == False
    #ax.scatter(kgm1_grid[gain_false_mask], kgm2_grid[gain_false_mask], np.full_like(kgm1_grid[gain_false_mask], zlim_min), color=gain_color, marker='o', s=marker_size, alpha=alpha_graph, label="Gain < 60 V/V")

    #ax1.contour(kgm1_grid, kgm2_grid, z, zdir="x", offset=kgm_max + 8, cmap=color_map)
    #ax1.contour(kgm1_grid, kgm2_grid, z, zdir="y", offset=-8, cmap=color_map)
    #ax1.contour(kgm1_grid, kgm2_grid, z, zdir="z", offset=-2,  cmap=color_map)

    # Add a grid for better readability
    ax1.xaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax1.yaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax1.zaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)

    ax1.set_xlim(kgm_min, kgm_max)
    ax1.set_ylim(kgm_min, kgm_max)
    ax1.set_zlim(zlim_min, zlim_max)
    ax1.legend()

    ax3.xaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax3.yaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax3.zaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax3.set_xlim(kgm_min, kgm_max)
    ax3.set_ylim(kgm_min, kgm_max)
    ax3.set_zlim(beta_min, beta_max)
    ax3.legend()

    #ax2 = fig.add_subplot(122)
    contour1 = ax2.contourf(kgm1_grid, kgm2_grid, z, levels=25,  alpha=alpha_graph, cmap=color_map)
    contour2 = ax4.contourf(kgm1_grid, kgm2_grid, beta, levels=15, alpha=alpha_graph, cmap=color_map)
    #ax2.scatter(kgm1_grid[nan_mask], kgm2_grid[nan_mask], color='red', marker='x', s=50, label="Infeasible Region")
    ax2.scatter(kgm1_grid[beta_mask], kgm2_grid[beta_mask], color=beta_color, marker='x', alpha=alpha_graph, s=marker_size, label="Beta < 1 Region")
    ax2.scatter(kgm1_grid[gain_mask], kgm2_grid[gain_mask], color=gain_color, marker='o', alpha=alpha_graph, s=marker_size, label="Gain < 50")
    cbar2 = fig.colorbar(contour1, ax=ax2)
    cbar2.set_label('Total Current [uA]', fontdict=font_properties)
    cbar4 = fig.colorbar(contour2, ax=ax4)
    cbar4.set_label("Beta")
    # Set axis labels with custom font properties
    ax2.set_xlabel('kgm1', fontdict=font_properties)
    ax2.set_ylabel('kgm2', fontdict=font_properties)
    ax4.set_xlabel("kgm1")
    ax4.set_ylabel("kgm2")
    # Add gridlines for better readability
    ax2.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax4.grid(True, which='both', linestyle='--', linewidth=0.5)
    # Show the legend for the contour plot
    ax2.legend()
    ax4.legend()
    """
    num_slices = 10
    kgm1_contour_vals = np.linspace(kgm_min, kgm_max, num_slices)
    kgm2_contour_vals = np.linspace(kgm_min, kgm_max, num_slices)
    #kgm1_slices = np.linspac
    #kgm3_contour_vals = np.linspace(zlim_min, zlim_max, num_slices)
    for kgm2_slice in kgm2_contour_vals:
        kgm1_total_current = []
        for kgm1_val in kgm1_vals:
            kgm1_total_current_i, kgm1_beta, kgm1_beta_valid, kgm1_gain_valid = total_current_ota_v2(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1_val, kgm2_slice, gain_spec=gain)
            kgm1_total_current_i = kgm1_total_current_i*1e6
            if kgm1_total_current_i >= zlim_max:
                kgm1_total_current_i = zlim_max
            if kgm1_total_current_i < zlim_min:
                kgm1_total_current_i = zlim_min
            kgm1_total_current.append(kgm1_total_current_i)
        ax3.plot(kgm1_vals, kgm1_total_current, label=f'kgm2={kgm2_slice:.2f}')
    #contour2 = ax2.contourf(x, y, z, )
    #ax3.legend()
    for kgm1_slice in kgm1_contour_vals:
        kgm2_total_current = []
        for kgm2_val in kgm2_vals:
            kgm2_total_current_i, kgm2_beta, kgm2_beta_valid, kgm2_gain_valid = total_current_ota_v2(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1_slice, kgm2_val, gain_spec=gain)
            kgm2_total_current_i = kgm2_total_current_i*1e6
            if kgm2_total_current_i >= zlim_max:
                kgm2_total_current_i = zlim_max
            if kgm2_total_current_i < zlim_min:
                kgm2_total_current_i = zlim_min
            kgm2_total_current.append(kgm2_total_current_i)
        ax4.plot(kgm2_vals, kgm2_total_current, label=f'kgm1={kgm1_slice:.2f}')
    #contour2 = ax2.contourf(x, y, z, )
    #ax4.legend()
    # Adjust layout for better spacing
    #plt.tight_layout()

    #plt.show()
    """
    print("TODO")

def cm_ota_plotting():


    av= 60
    #bw = 250e6
    bw = 5e5
    #bw = 25e5
    gbw = bw * av
    cload = 250e-15


    inverse_tan_thirty = math.tan(30*math.pi/180)
    inverse_tan_thirty = math.tan(30*math.pi/180)
    alpha = 1/inverse_tan_thirty
    two_pi_alpha_gbw = 2*math.pi*alpha*gbw
    f2 = alpha*gbw
    nfet_nominal = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt27.csv",
                             vdd=1.8)

    pfet_nominal = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt27.csv",
                             vdd=1.8)
    nfet_hot = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt75.csv",
                             vdd=1.8)

    pfet_hot = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt75.csv",
                             vdd=1.8)
    nfet_cold = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt-25.csv",
                             vdd=1.8)

    pfet_cold = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt-25.csv",
                             vdd=1.8)

    n_list = [nfet_cold, nfet_nominal, nfet_hot]
    p_list = [pfet_cold, pfet_nominal, pfet_hot]
    n_list = [nfet_nominal]
    p_list = [pfet_nominal]
    #fig = plt.figure(figsize=(12,6))
    fig = plt.figure(figsize=(14,10))
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    ax2 = fig.add_subplot(2, 2, 2)
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    ax4 = fig.add_subplot(2, 2, 4)
    color_map_list = ["Blues", "Greens", "Reds"]
    beta_color_list = ["b", "g", "r"]
    alpha_graph = 0.6
    marker_size = 70
    for i in range(len(n_list)):
        nfet_corner = n_list[i]
        pfet_corner = p_list[i]
        color_map = color_map_list[i]
        beta_color = beta_color_list[i]
        gain_color= beta_color_list[i]
        plot_results_krummenechar_ota_stage1(nom_ncorner=nfet_corner,nom_pcorner=pfet_corner,alpha=alpha,gain=av, bw=bw, cload=cload,
                                             fig=fig, ax1=ax1, ax2=ax2, ax3=ax3, ax4=ax4, color_map=color_map, beta_color=beta_color,
                                             gain_color=gain_color, alpha_graph=alpha_graph, marker_size=marker_size)
        plt.tight_layout()

        plt.show()
        alpha_graph = alpha_graph - 0.35
        marker_size = marker_size - 20
        print(nfet_corner.corner_name)

    return 0

def krummenechar_ota_stage1(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    av= 60
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

    nfet_nominal = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt27.csv",
                             vdd=1.8)

    pfet_nominal = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt27.csv",
                             vdd=1.8)
    nfet_hot = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt75.csv",
                             vdd=1.8)

    pfet_hot = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt75.csv",
                             vdd=1.8)
    nfet_cold = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500/nfettt-25.csv",
                             vdd=1.8)

    pfet_cold = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500/pfettt-25.csv",
                             vdd=1.8)

    n_list = [nfet_cold, nfet_nominal, nfet_hot]
    p_list = [pfet_cold, pfet_nominal, pfet_hot]
    n_list = [nfet_nominal]
    p_list = [pfet_nominal]
    #fig = plt.figure(figsize=(12,6))
    fig = plt.figure(figsize=(15,10))
    ax1 = fig.add_subplot(121, projection='3d')
    ax2 = fig.add_subplot(122)
    color_map_list = ["Blues", "Greens", "Reds"]
    beta_color_list = ["b", "g", "r"]
    alpha_graph = 0.6
    marker_size = 70
    for i in range(len(n_list)):
        nfet_corner = n_list[i]
        pfet_corner = p_list[i]
        color_map = color_map_list[i]
        beta_color = beta_color_list[i]
        gain_color = beta_color_list[i]
        plot_results_krummenechar_ota_stage1(nfet_corner, pfet_corner, alpha, gain, bw, cload,
                                             fig, ax1, ax2, ax3, ax4, color_map, beta_color, gain_color, alpha_graph, marker_size)
        plt.tight_layout()

        plt.show()
        alpha_graph = alpha_graph - 0.35
        marker_size = marker_size - 20
        print(nfet_corner.corner_name)

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
cm_ota_plotting()
#w1, gm1, kgm1, w2, gm2, kgm2 = krummenechar_ota_stage1(av=av1, bw=bw, cload=cload1, nfet_device=nfet_device,
#                                                       pfet_device=pfet_device, nom_ncorner=nfet_nominal, nom_pcorner=pfet_nominal)




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
