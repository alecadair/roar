import sys, os, getpass, shutil, operator, collections, copy, re, math
import matplotlib.ticker as mticker
#sys.path.append("/pri/ala1/Documents/CAD/roar/src")
from cid import *
from matplotlib.ticker import LogLocator
#from pyfonts import load_font
# load font
#font = load_font(
#   font_url="https://github.com/google/fonts/blob/main/apache/ultra/Ultra-Regular.ttf?raw=true"
#)

from matplotlib.font_manager import FontProperties
plt.rcParams['svg.fonttype'] = 'none'
def parallel(x1, x2):
    return 1/((1/x1) + 1/x2)

def create_spice_netlist_for_place_and_route(nf1_2, nf3_4, nf5_6, nf7_8):
    print("TODO")

def total_current_ota_v2(ncorner, pcorner, alpha, gbw, cload, kgm1, kgm2, gain_spec, thermal_noise_spec):
    f1 = 2*math.pi*gbw
    p_factor = 1
    k = 1.380649e-23
    T = 300.15
    gamma = 2/3
    gamma = 8/3
    kcgs_1 = ncorner.lookup(param1="kgm", param2="kcgs", param1_val = kgm1)
    kcds_1 = ncorner.lookup(param1="kgm", param2="kcds", param1_val = kgm1)

    kcgs_8 = pcorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2*p_factor)
    kcgd_8 = pcorner.lookup(param1="kgm", param2="kcgd", param1_val=kgm2*p_factor)
    kcds_8 = pcorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2*p_factor)
    kcgs_6 = ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2)
    kcds_6 = ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2)
    kcgs_4 = pcorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm1*p_factor)
    kcds_4 = pcorner.lookup(param1="kgm", param2="kcds", param1_val=kgm1*p_factor)
    kgds_6 = ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    kgds_8 = ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    gain = kgm1/(kgds_6 + kgds_8)
    kcout = kcgs_8 + kcds_8 + kcgs_6 + kcds_6
    beta_num = kgm1 - 2*math.pi*alpha*gbw*kcgs_4
    beta_denom = 1/(2*math.pi*alpha*gbw*(kcgs_8 + kcgd_8))
    beta = beta_num*beta_denom
    #m1_current_term1 = 2*math.pi*gbw*cload/(beta*kgm1)
    #m1_current_term2 = 1/(1 - 2*math.pi*gbw*kcout/kgm1)
    #m1_current = m1_current_term1*m1_current_term2
    #total_current = m1_current + beta*m1_current
    kcs_8 = kcgs_8 + kcgd_8
    kcs_6 = kcds_6 + kcgs_6
    total_current_num = alpha*cload*f1*f1*kcs_8 - alpha*cload*f1*f1*kcgs_4 + f1*cload*kgm1
    total_current_denom = (kgm1 - alpha*f1*kcgs_4)*(kgm1 - f1*kcout)
    total_current = total_current_num/total_current_denom
    m1_current = total_current/(1 + beta)
    m8_current = total_current - m1_current
    m6_current = m8_current
    m4_current = m1_current
    m2_cload = (kcgs_1 + kcds_1)*m1_current + kcs_8*m8_current + kcds_4*m1_current
    m4_cload = m2_cload
    m6_cload = ((kcs_6 + kcds_8 + kcgs_8)*m6_current) + cload
    m8_cload = m6_cload
    m1_gm = kgm1*m1_current
    m6_gm = kgm2*m6_current
    m8_gm = m6_gm
    m4_gm = m1_gm
    ft_m8 = m8_gm/(2*math.pi*m8_cload)
    ft_m2 = m1_gm/(2*math.pi*m2_cload)
    ft_m4 = m4_gm/(2*math.pi*m4_cload)
    ft_m6 = m6_gm/(2*math.pi*m6_cload)

    thermal_rms_noise = k*T*(ft_m2/(kgm1*m1_current) + ft_m4/(kgm1*m1_current) + ft_m6/(kgm2*m6_current) + ft_m8/(kgm2*m6_current))
    #thermal_rms_noise = (gamma*k*T*ft_m1)/(m1_current*kgm1)
    #thermal_rms_noise = 2*((8/3)*k*T)*(1/m1_gm)*(1 + 1 + 1/beta + m6_gm/(beta*beta + m1_gm))
    beta_valid = True
    gain_valid = True
    thermal_noise_valid = True
    if beta < 1:
        beta_valid = False
    if gain < gain_spec:
        gain_valid = False
    if thermal_rms_noise < thermal_noise_spec:
        thermal_noise_valid = False
    return total_current, beta, thermal_rms_noise, beta_valid, gain_valid, thermal_noise_valid, kcout


def total_current_ota(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1, kgm2, gain_spec):
    p_factor = 1
    kcgs_8 = nom_ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2*p_factor)
    kcgd_8 = nom_ncorner.lookup(param1="kgm", param2="kcgd", param1_val=kgm2*p_factor)
    kcds_8 = nom_ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2*p_factor)
    kcgs_6 = nom_ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm2)
    kcds_6 = nom_ncorner.lookup(param1="kgm", param2="kcds", param1_val=kgm2)
    kcgs_4 = nom_ncorner.lookup(param1="kgm", param2="kcgs", param1_val=kgm1*p_factor)
    kgds_6 = nom_ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
    kgds_8 = nom_ncorner.lookup(param1="kgm", param2="kgds", param1_val=kgm2)
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





def plot_results_krummenechar_ota_stage1(nom_ncorner, nom_pcorner, alpha, gain, bw, cload, therm_noise, fig, ax1, ax2, ax3, ax4,
                                         color_map, beta_color, gain_color, alpha_graph, marker_size, line_style):
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
    num_samples = 300
    if kgm_min < 0:
        kgm_min = 0.001
    kgm1_vals = np.linspace(kgm_min, kgm_max, num_samples)
    kgm2_vals = np.linspace(kgm_min, kgm_max, num_samples)
    kgm1_grid, kgm2_grid = np.meshgrid(kgm1_vals, kgm2_vals)
    z = np.zeros_like(kgm1_grid)
    beta = np.zeros_like(kgm1_grid)
    beta_valid_grid = np.zeros_like(kgm1_grid)
    gain_valid_grid = np.zeros_like(kgm1_grid)
    therm_noise_rms = np.zeros_like(kgm1_grid)
    therm_rms_noise_valid_grid = np.zeros_like(kgm1_grid)
    i_total_vector = []
    zlim_min = -0.5
    zlim_max = 10
    beta_min = -10
    beta_max = 25
    therm_rms_noise_max = 1e-6
    therm_rms_noise_min = 0
    kcout_vector = []
    for i in range(len(kgm1_vals)):
        #for j in range(len(kgm2_vals)):
            #total_current, beta1, beta_valid, gain_valid = total_current_ota(nom_ncorner, nom_pcorner, alpha, gbw, cload, kgm1_vals[i], kgm2_vals[j], gain_spec=gain)


        total_current, beta_i_j, thermal_rms_noise_i_j, beta_valid, gain_valid, thermal_noise_valid, kc_out= total_current_ota_v2(nom_ncorner, nom_pcorner, alpha, gbw, cload,
                                                                                                                           kgm1_vals[i], kgm1_vals[i], gain_spec=gain,
                                                                                                                           thermal_noise_spec=therm_noise)
        """
        total_current, beta_i_j, thermal_rms_noise_i_j, beta_valid, gain_valid, thermal_noise_valid, kc_out= total_current_ota_v2(nom_ncorner, nom_pcorner, alpha, gbw, cload,
                                                                                                                   9.4825, 9.4845, gain_spec=gain,
                                                                                                                   thermal_noise_spec=therm_noise)
        """
        total_current = total_current*1e6
        if total_current < 0 or beta_valid == False:
            total_current = np.nan
        #total_current2 = total_current2 * 1e6
        #if total_current < zlim_min:
        #    total_current = zlim_min
        #if total_current > zlim_max:
        #    total_current = zlim_max
        #if beta_i_j < beta_min:
        #    beta_i_j = beta_min
        #if beta_i_j > beta_max:
        #    beta_i_j = beta_max
        #total_current = np.log10(total_current*1e6)
        thermal_rms_noise_i_j = np.log10(thermal_rms_noise_i_j*1e9)
        i_total_vector.append(total_current)
        #if beta_valid == False:
        #    total_current = np.nan
        #if gain_valid == False:
        #    total_current = np.nan
        #z[i, j] = total_current
        #beta[i, j] = beta_i_j
        #beta_valid_grid[i, j] = beta_valid
        #gain_valid_grid[i, j] = gain_valid
        #therm_noise_rms[i, j] = thermal_rms_noise_i_j
        #therm_rms_noise_valid_grid[i, j] = thermal_noise_valid
    #z = total_current_ota(nom_ncorner,nom_pcorner,alpha, gbw, cload, kgm1, kgm2)
    #font = load_font(
    #    font_url="arialnarrow_bold.ttf"
    #)

    diagonal_mask = np.isclose(kgm1_grid, kgm2_grid)
    #fig = plt.figure(figsize=(12,6))

    #plot where kgm1 = kgm2
    #surf = ax.plot_surface(kgm1_grid, kgm2_grid, z, cmap=color_map, lw=0.5, edgecolor='k', rstride=3, cstride=3, alpha=alpha_graph)
    #surf_i_total = ax1.plot_surface(kgm1_grid, kgm2_grid, z, lw=0.5, cmap=color_map, edgecolor='royalblue', rstride=3, cstride=3, alpha=alpha_graph)
    #surf_beta = ax3.plot_surface(kgm1_grid, kgm2_grid, beta, lw=0.5, cmap=color_map, edgecolor="royalblue", rstride=3, cstride=3, alpha=alpha_graph)
    #surf_therm_noise = ax3.plot_surface(kgm1_grid, kgm2_grid, therm_noise_rms, lw=0.5, cmap=color_map, edgecolor="royalblue", rstride=3, cstride=3, alpha=alpha_graph)

    #ax1.plot(kgm1_grid[diagonal_mask], kgm2_grid[diagonal_mask], z[diagonal_mask]+0.5, color='k', linewidth=4, label="kgm1 = kgm2")
    arial_bold = FontProperties(fname="/home/adair/Documents/CAD/roar/fonts/ArialNarrow/arialnarrow_bold.ttf")
    font_size = 12
    ax1.plot(kgm1_vals, i_total_vector, line_style, linewidth=2)
    #ax3.plot(kgm1_grid[diagonal_mask], kgm2_grid[diagonal_mask], beta[diagonal_mask]+0.5, color='k', linewidth=4, label="kgm1 = kgm2")
    #ax1.set_xlabel(r'$\mathrm{\mathcal{G}_{m_{1 \rightarrow 4}}}$ [$\mathrm{V^{-1}}$]', font=arial_bold, fontsize=font_size)
    #ax1.set_ylabel(r'$\mathrm{\mathcal{G}_{m_{5 \rightarrow 8}}}$ [$\mathrm{V^{-1}}$]', font=arial_bold, fontsize=font_size)
    #ax1.set_zlabel("Total Current [uA]", font=arial_bold, fontsize=font_size)

    return i_total_vector, kgm1_vals
    ax2 = None
    ax2 = ax1.twin()


    ax3.set_xlabel(r'$\mathrm{\mathcal{G}_{m_{1 \rightarrow 4}}}$ [$\mathrm{V^{-1}}$]', font=arial_bold, fontsize=font_size)
    ax3.set_ylabel(r'$\mathrm{\mathcal{G}_{m_{5 \rightarrow 8}}}$ [$\mathrm{V^{-1}}$]', font=arial_bold, fontsize=font_size)

    ax2.set_xlabel(r'$\mathrm{\mathcal{G}_{m_{1 \rightarrow 4}}}$ [$\mathrm{V^{-1}}$]', fontdict=font_properties)
    ax2.set_ylabel(r'$\mathrm{\mathcal{G}_{m_{1 \rightarrow 4}}}$ [$\mathrm{V^{-1}}$]', fontdict=font_properties)

    ax3.set_zlabel(r'RMS Thermal Noise [$\mathrm{[uV_{RMS}}$]')
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


    z_ticks = np.array([1, 10, 100, 1000, 10000, 100000])
    current_ticks = np.array([0.01, 0.1, 1, 10, 100, 1000, 10000])
    ax1.set_zticks(np.log10(current_ticks))
    ax1.set_zticklabels(current_ticks)

    ax3.set_zticks(np.log10(z_ticks))
    ax3.set_zticklabels(z_ticks)
    # Add a grid for better readability
    ax1.xaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax1.yaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax1.zaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)

    ax1.set_xlim(kgm_min, kgm_max)
    ax1.set_ylim(kgm_min, kgm_max)
    #ax1.set_zlim(zlim_min, zlim_max)

    def log_tick_formatter(val, pos=None):
        return f"$10^{{{int(val)}}}$"  # remove int() if you don't use MaxNLocator
        # return f"{10**val:.2e}"      # e-Notation

    #ax1.zaxis.set_major_formatter(mticker.FuncFormatter(log_tick_formatter))
    #ax1.zaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax1.legend()

    ax3.xaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax3.yaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
    ax3.zaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)

    ax3.set_xlim(kgm_min, kgm_max)
    ax3.set_ylim(kgm_min, kgm_max)
    #ax3.set_zlim(beta_min, beta_max)
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
    av= 50
    #bw = 250e6
    bw = 0.75e6
    bw = 0.6e6
    #bw = 500e5
    #bw = 20e5
    gbw = bw * av
    #gbw = 37.5e6
    therm_noise = 500e-9
    #cload = 250e-15
    #cload = 250e-15
    cload = 4e-12
    tan_thirty = math.tan(30*math.pi/180)
    tan_thirty = math.tan(30*math.pi/180)
    alpha = 1/tan_thirty
    two_pi_alpha_gbw = 2*math.pi*alpha*gbw
    f2 = alpha*gbw
    """
    fet_nominal = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD_Custom_Scripts/roar/characterization/predictive_28/LUTs_1V8_mac/nch_18_mac/LUT_N_500n/nfetttroom.csv",
                             vdd=1.8)

    pfet_nominal = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD_Custom_Scripts/roar/characterization/predictive_28/LUTs_1V8_mac/pch_18_mac/LUT_P_500n/pfetttroom.csv",
                             vdd=1.8)
    nfet_hot = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD_Custom_Scripts/roar/characterization/predictive_28/LUTs_1V8_mac/nch_18_mac/LUT_N_500n/nfettthot.csv",
                             vdd=1.8)

    pfet_hot = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD_Custom_Scripts/roar/characterization/predictive_28/LUTs_1V8_mac/pch_18_mac/LUT_P_500n/pfettthot.csv",
                             vdd=1.8)
    nfet_cold = CIDCorner(corner_name="nfet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD_Custom_Scripts/roar/characterization/predictive_28/LUTs_1V8_mac/nch_18_mac/LUT_N_500n/nfetttcold.csv",
                             vdd=1.8)

    pfet_cold = CIDCorner(corner_name="pet_150n_nominal",
                             lut_csv="/home/adair/Documents/CAD_Custom_Scripts/roar/characterization/predictive_28/LUTs_1V8_mac/pch_18_mac/LUT_P_500n/pfetttcold.csv",
                             vdd=1.8)
    """

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

    nfet_device = CIDDevice(device_name="nfet_500n", vdd=1.8,
                            lut_directory="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/n_01v8/LUT_N_500",
                            corner_list=None)
    pfet_device = CIDDevice(device_name="pfet_500n", vdd=1.8,
                            lut_directory="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130/p_01v8/LUT_P_500",
                            corner_list=None)
    n_list = [nfet_cold, nfet_nominal, nfet_hot]
    p_list = [pfet_cold, pfet_nominal, pfet_hot]
    n_list = [nfet_nominal]
    p_list = [pfet_nominal]
    #fig = plt.figure(figsize=(12,6))
    #fig = plt.figure(figsize=(7,5))
    #fig = plt.figure(figsize=(10,8))
    fig, ax1 = plt.subplots(figsize=(3.5, 2.8 * 2), dpi=300)
    #ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    #ax1 = fig.add_subplot(1, 1, 1)
    #ax1 = fig.add_subplot(2, 2, 1)
    #ax2 = fig.add_subplot(2, 2, 2)
    #ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    #ax4 = fig.add_subplot(2, 2, 4)
    ax2 = None
    ax3 = None
    ax4 = None
    color_map_list = ["Blues", "Greens", "Reds"]
    beta_color_list = ["b", "g", "r"]
    line_style_list = ["r-", "g-", "b-.", "m-", "c-.", "r--", "b--", "g--", "m--"]
    alpha_graph = 0.6
    marker_size = 10
    current_vectors = []
    kgm_vectors = []
    for i in range(len(nfet_device.corners)):
        #nfet_corner = n_list[i]
        nfet_corner = nfet_device.corners[i]
        #pfet_corner = p_list[i]
        pfet_corner = pfet_device.corners[i]
        color_map = color_map_list[0]
        beta_color = beta_color_list[0]
        gain_color= beta_color_list[0]
        line_style = line_style_list[i]
        currents, kgms = plot_results_krummenechar_ota_stage1(nom_ncorner=nfet_corner,nom_pcorner=pfet_corner, alpha=alpha,gain=av, bw=bw, cload=cload, therm_noise=therm_noise,
                                             fig=fig, ax1=ax1, ax2=ax2, ax3=ax3, ax4=ax4, color_map=color_map, beta_color=beta_color,
                                             gain_color=gain_color, alpha_graph=alpha_graph, marker_size=marker_size, line_style=line_style)
        current_vectors.append(currents)
        kgm_vectors.append(kgms)
        #plt.tight_layout()

        #plt.show()
        alpha_graph = alpha_graph - 0.35
        marker_size = marker_size - 20
        print(nfet_corner.corner_name)
    arial_bold = FontProperties(fname="/home/adair/Documents/CAD/roar/fonts/ArialNarrow/arialnarrow_bold.ttf")


    def find_curve_divergence(x, curves, tolerance=0.06):
        # Loop through each x position (assume all curves have the same length)
        for j in range(len(curves[0])):
            # Get the values of all curves at the current x position
            values_at_x = np.array([curve[j] for curve in curves])

            # Find the maximum and minimum values at this x position
            max_value = np.max(values_at_x)
            min_value = np.min(values_at_x)

            # Calculate the relative difference between the max and min values
            relative_diff = np.abs((max_value - min_value) / max_value)

            # Check if the relative difference exceeds the tolerance (5%)
            if relative_diff > tolerance:
                # Return the x position and the mean of the values at this x point
                mean_value_at_x = np.mean(values_at_x)
                return x[j], mean_value_at_x

        # If no divergence is found, return None
        return None, None

    # Find the divergence point
    divergence_x, divergence_y = find_curve_divergence(kgm_vectors[0], current_vectors)
    arial_font = "/home/adair/Documents/CAD/roar/fonts/ArialNarrow/arialnarrow_bold.ttf"
    font_size = 6  # Adjust font size for labels, ticks, etc.
    font_properties = FontProperties(fname=arial_font, size=font_size)
    # Plot the divergence point on the mean curve if found
    if divergence_x is not None:
        ax1.plot(divergence_x, divergence_y, 'ko', label='Divergence Point', markersize=12)
        """
        ax1.annotate('6% Convergence\nAcross Corners',
                    xy=(divergence_x, divergence_y),
                    xytext=(divergence_x + 0.2, divergence_y + 0.5),  # Offset the text slightly from the point
                    textcoords='data',
                    arrowprops=dict(arrowstyle='->', lw=1.5),  # Optional arrow pointing to the point
                    font=arial_bold,
                    fontsize=14)
        """
        arial_font = "/home/adair/Documents/CAD/roar/fonts/ArialNarrow/arialnarrow_bold.ttf"
        font_size = 6  # Adjust font size for labels, ticks, etc.
        font_properties = FontProperties(fname=arial_font, size=font_size)
        ax1.annotate(rf'6% Divergence\n$\mathcal{{G}}_m$: {divergence_x:.2f}\n$I_{{TOTAL}}$: {divergence_y:.2f}',
             xy=(divergence_x, divergence_y),
             xytext=(divergence_x + 0.2, divergence_y + 0.5),
             fontproperties=font_properties, ha='right',
             bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))

    font_size = 8
    ax1.set_xlabel(r'Transconductance Efficiency [1/V]', font=arial_bold, fontsize=font_size)
    ax1.set_ylabel(r'Total Current Consumption [uA]', font=arial_bold, fontsize=font_size)
    ax1.set_title(r'CM OTA Current Consumption Across Corners and Temperature', font=arial_bold, fontsize=font_size)
    # Set the font properties for the y-axis numbers (left)
    #ax1.xaxis.set_tick_params(labelsize=font_size, labelrotation=0)
    #ax1.tick_params(axis='x', labelsize=font_size + 8)
    #ax1.tick_params(axis='y', labelsize=font_size + 8)

    for label in ax1.get_xticklabels():
        label.set_fontproperties(arial_bold)
    #ax1.tick_params(axis='y', labelsize=12)
    #ax1.yaxis.set_tick_params(labelsize=font_size, labelrotation=0)
    for label in ax1.get_yticklabels():
        label.set_fontproperties(arial_bold)
    minor_size = font_size - 2
    ax1.tick_params(axis='both', which='major', labelsize=font_size)
    ax1.tick_params(axis='both', which='minor', labelsize=minor_size)
    ax1.grid(True, which="both")
    ax1.set_yscale('log')

    #plt.tight_layout()
    plt.show()
    print("DONE")
    return 0

def two_stage_ota(av, w, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    av = 50
    bw = 10

def krummenechar_ota_stage1(av, bw, cload, nfet_device, pfet_device, nom_ncorner, nom_pcorner):
    av= 50
    #bw = 250e6
    #bw = 5e5
    bw = 10e6
    gbw = bw * av
    cload = 15e-15
    av= 50
    #bw = 250e6
    bw = 0.75e6
    #bw = 500e5
    #bw = 20e5
    gbw = bw * av
    gbw = 37.5e6
    therm_noise = 500e-9
    #cload = 250e-15
    #cload = 250e-15
    cload = 4e-12
    inverse_tan_thirty = math.tan(30*math.pi/180)
    inverse_tan_thirty = math.tan(30*math.pi/180)
    alpha = 1/inverse_tan_thirty
    two_pi_alpha_gbw = 2*math.pi*alpha*gbw
    f2 = alpha*gbw

    inverse_tan_thirty = math.tan(30*math.pi/180)
    inverse_tan_thirty = math.tan(30*math.pi/180)
    alpha = 1/inverse_tan_thirty
    two_pi_alpha_gbw = 2*math.pi*alpha*gbw
    f2 = alpha*gbw
    #ids_min1, kgm1 = nfet_device.magic_equation(gbw, cload=cload, epsilon=7.5, beta_factor=1, show_plot=True, new_plot=True)
    kgm1 = 9.48425
    ids_min1 = 10.08e-6

    kgm_n = kgm1
    #kgm_p = kgm1*(1/2)
    kgm_p = kgm1
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
    beta = 10.34
    ids_min = ids_min1
    ids1_2 = ids_min
    ids5_6 = beta*ids1_2

    gm1_2 = kgm1_2*ids_min
    gm3_4 = kgm3_4*ids_min
    ids_branch2 = ids_min*beta
    ids_min = 10.08e-6
    ids_branch2 = beta*ids_min
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


    return w1, gm1, kgm1, w2, gm2, kgm2


# Function to read the AC simulation data
def read_ac_simulation_data(filename):
    # Read the data file
    data = np.loadtxt(filename, skiprows=1)  # Skip the header row

    # The file format is expected to be: frequency vdb(2) vp(2)
    frequency = data[:, 0]
    magnitude_db = data[:, 4]
    phase_deg = (180/math.pi)*data[:, 6]

    return frequency, magnitude_db, phase_deg


# Function to find relevant points (DC Gain, Pole 1, Pole 2, Unity Gain Frequency)
# Function to find relevant points (DC Gain, Pole 1, Pole 2, Unity Gain Frequency)
# Function to find relevant points (DC Gain, Pole 1, Pole 2, Unity Gain Frequency)
def find_relevant_points(frequency, magnitude_db, phase_deg):
    # DC Gain: the magnitude at the lowest frequency (0 Hz or close to it)
    dc_gain = magnitude_db[0]
    # Unity Gain Frequency: the frequency where magnitude crosses 0 dB
    unity_gain_freq = None
    for i in range(len(magnitude_db) - 1):
        if magnitude_db[i] > 0 and magnitude_db[i + 1] < 0:
            unity_gain_freq = frequency[i]
            break
    # Poles: Find where phase crosses -45 degrees (Pole 1) and -135 degrees (Pole 2)
    pole_1 = None
    pole_2 = None
    for i in range(1, len(phase_deg)):
        if phase_deg[i] <= -45 and pole_1 is None:
            pole_1 = frequency[i]  # Approximate the frequency where phase crosses -45 degrees
        elif phase_deg[i] <= -135 and pole_2 is None:
            pole_2 = frequency[i]  # Approximate the frequency where phase crosses -135 degrees
            break
    return dc_gain, pole_1, pole_2, unity_gain_freq


# Function to calculate percentage difference between two values
def percentage_difference(value1, value2):
    return 100 * (value2 - value1) / value1

# Modified function to plot magnitude and phase for ideal and extracted data
def plot_ac_results(frequency, magnitude_db, phase_deg, label_suffix="", fig=None, ax1=None, ax2=None):
    # Define font path and size within the function
    arial_font = "/home/adair/Documents/CAD/roar/fonts/ArialNarrow/arialnarrow_bold.ttf"
    font_size = 6  # Adjust font size for labels, ticks, etc.
    font_properties = FontProperties(fname=arial_font, size=font_size)
    ideal = False
    # Create the figure and axes if not provided (for the first call)
    if fig is None or ax1 is None or ax2 is None:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 2.8 * 2), dpi=300)
        ideal = True

    # Find the relevant points
    dc_gain, pole_1, pole_2, unity_gain_freq = find_relevant_points(frequency, magnitude_db, phase_deg)

    # Plot magnitude in dB (Ideal or Extracted)
    ax1.plot(frequency, magnitude_db, label=f'{label_suffix}', linewidth=1)
    ax1.set_xscale('log')
    ax1.set_ylabel('Magnitude [dB]', fontproperties=font_properties)

    # Set up grid and limits if this is the first call
    if label_suffix == "Ideal":
        #ax1.set_ylim([-40, 40])
        #ax1.set_xlim([10, 10e9])
        ax1.grid(which='both', linestyle='--', linewidth=0.6)
        ax1.xaxis.set_major_locator(LogLocator(base=10.0))  # Major ticks for decades
        ax1.xaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(1.0, 10.0) * 0.1))  # Minor gridlines
        ax1.grid(which='minor', linestyle=':', linewidth=0.4)
        ax1.xaxis.set_tick_params(which='minor', length=0)  # Hide minor tick labels
        ax1.tick_params(labelsize=font_size)

    # Plot the points on the graph with larger black markers
    if dc_gain is not None:
        ax1.plot(100, np.interp(100, frequency, magnitude_db), 'ko', markersize=6)  # DC Gain point at 100 Hz
    if unity_gain_freq is not None:
        ax1.plot(unity_gain_freq, 0, 'ko', markersize=6)  # Unity Gain point

    # Annotate the DC Gain at 100 Hz with a bubble
    magnitude_100Hz = np.interp(100, frequency, magnitude_db)
    ax1.annotate(f'{label_suffix} DC Gain: {magnitude_100Hz:.2f} dB', xy=(100, magnitude_100Hz),
                 xytext=(200, magnitude_100Hz + 5),
                 fontsize=font_size, fontproperties=font_properties, ha='left',
                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))

    # Annotate Unity Gain Frequency with a bubble
    if unity_gain_freq is not None:
        ax1.annotate(f'{label_suffix} Unity Gain: {unity_gain_freq:.2e} Hz', xy=(unity_gain_freq, 0),
                     xytext=(unity_gain_freq * 1.2, -10),
                     fontsize=font_size, fontproperties=font_properties, ha='left',
                     bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))

    # Plot phase in degrees (Ideal or Extracted)
    ax2.plot(frequency, phase_deg, label=f'{label_suffix}', linewidth=1)
    ax2.set_xscale('log')
    ax2.set_xlabel('Frequency [Hz]', fontproperties=font_properties, labelpad=5)
    ax2.set_ylabel('Phase [degrees]', fontproperties=font_properties)

    # Set up grid and limits if this is the first call
    if label_suffix == "Ideal":
        ax2.grid(which='both', linestyle='--', linewidth=0.6)
        ax2.xaxis.set_major_locator(LogLocator(base=10.0))  # Major ticks for decades
        ax2.xaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(1.0, 10.0) * 0.1))  # Minor gridlines
        ax2.grid(which='minor', linestyle=':', linewidth=0.4)
        ax2.xaxis.set_tick_params(which='minor', length=0)  # Hide minor tick labels
        ax2.tick_params(labelsize=font_size)

    # Annotate the phase margin at the unity gain frequency
    if unity_gain_freq is not None:
        phase_at_unity = np.interp(unity_gain_freq, frequency, phase_deg)  # Phase at unity gain frequency
        phase_margin = 180 + phase_at_unity  # Phase margin calculation
        ax2.plot(unity_gain_freq, phase_at_unity, 'ko', markersize=6)  # Mark point at unity gain frequency
        ax2.annotate(f'{label_suffix} Phase: {phase_at_unity:.1f}°\nPhase Margin: {phase_margin:.1f}°',
                     xy=(unity_gain_freq, phase_at_unity),
                     xytext=(unity_gain_freq * 1.2, phase_at_unity - 10),
                     fontsize=font_size, fontproperties=font_properties, ha='left',
                     bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow"))

    return fig, ax1, ax2, dc_gain, unity_gain_freq, phase_margin

# Main function to execute the script and handle comparison
def plot_spice_results():
    arial_font = "/home/adair/Documents/CAD/roar/fonts/ArialNarrow/arialnarrow_bold.ttf"
    font_size = 6
    arial_bold = FontProperties(fname=arial_font, size=font_size)
    # Read ideal simulation data
    filename = '/home/adair/Documents/CAD/magic_cds/extraction_custom/ac_output.txt'
    frequency, magnitude_db, phase_deg = read_ac_simulation_data(filename)

    # Plot ideal results
    fig, ax1, ax2, dc_gain_ideal, unity_gain_ideal, phase_margin_ideal = plot_ac_results(
        frequency, magnitude_db, phase_deg, label_suffix="Ideal"
    )

    # Read extracted simulation data
    filename2 = '/home/adair/Documents/CAD/magic_cds/extraction_custom/ac_output_ext.txt'
    frequency2, magnitude_db2, phase_deg2 = read_ac_simulation_data(filename2)

    # Plot extracted results and pass in the figure and axes from the ideal plot
    fig, ax1, ax2, dc_gain_ext, unity_gain_ext, phase_margin_ext = plot_ac_results(
        frequency2, magnitude_db2, phase_deg2, label_suffix="Extracted", fig=fig, ax1=ax1, ax2=ax2
    )

    # Calculate percentage differences and annotate them
    dc_gain_diff = percentage_difference(dc_gain_ideal, dc_gain_ext)
    unity_gain_diff = percentage_difference(unity_gain_ideal, unity_gain_ext)
    phase_margin_diff = percentage_difference(phase_margin_ideal, phase_margin_ext)

    # Annotate percentage differences on the plots
    ax1.annotate(f'DC Gain Diff: {dc_gain_diff:.2f}%', xy=(200, 35), fontsize=font_size, ha='left',
                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightcyan"))

    ax1.annotate(f'Unity Gain Diff: {unity_gain_diff:.2f}%', xy=(1e7, 35), fontsize=font_size, ha='left',
                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightcyan"))

    ax2.annotate(f'Phase Margin Diff: {phase_margin_diff:.2f}%', xy=(1e7, -90), fontsize=font_size, ha='left',
                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightcyan"))


    for label in ax1.get_xticklabels():
        label.set_fontproperties(arial_bold)
    for label in ax1.get_yticklabels():
        label.set_fontproperties(arial_bold)
    minor_size = font_size - 2
    #ax1.tick_params(axis='both', which='major', labelsize=font_size)
    #ax1.tick_params(axis='both', which='minor', labelsize=minor_size)
    #ax1.tick_params(axis='y', labelsize=12)
    #ax1.yaxis.set_tick_params(labelsize=font_size, labelrotation=0)


    for label in ax2.get_xticklabels():
        label.set_fontproperties(arial_bold)
    for label in ax2.get_yticklabels():
        label.set_fontproperties(arial_bold)
    minor_size = font_size - 2
    #ax2.tick_params(axis='both', which='major', labelsize=font_size)
    #ax1.tick_params(axis='both', which='minor', labelsize=minor_size)
    ax1.legend(prop=arial_bold)
    ax2.legend(prop=arial_bold)
    # Apply tight layout and save the plots
    plt.grid(True)
    #plt.tight_layout()
    plt.savefig("ac_simulation_plot.svg", format="svg")
    plt.savefig("ac_simulation_plot.png", format="png", dpi=300)
    plt.show()


    print("TODO")


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
#plot_spice_results()
print("DONE")
w1, gm1, kgm1, w2, gm2, kgm2 = krummenechar_ota_stage1(av=av1, bw=bw, cload=cload1, nfet_device=nfet_device,
                                                       pfet_device=pfet_device, nom_ncorner=nfet_nominal, nom_pcorner=pfet_nominal)
