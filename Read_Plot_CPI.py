import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import gc
from pprint import pprint


# define class Field and its attributes
class Field:
    def __init__(self, field_name):
        self.FLD = field_name


# define class Well and its attributes
class Well(Field):
    def __init__(self, well_name, field_name):
        super().__init__(field_name)  # passes field name to Parent class
        self.WELL = well_name
        self.STRT = -999
        self.STOP = -999
        self.STEP = -999
        self.NULL = -999
        self.KB = -999
        self.GL = -999
        self.DATE = datetime(1900, 1, 1)
        self.XCOORD = -999
        self.YCOORD = -999
        self.LATI = -999
        self.LONG = -999
        self.logs_info = {}
        self.original_logs = pd.DataFrame()
        self.standard_logs = pd.DataFrame()
        self.missing_logs = []


# Function to create well
def create_well(las_file):
    # read well data
    well_props, well_logs_info, well_logs_df = read_las(las_file)
    # create well variable
    created_well = Well(well_props["WELL"], well_props["FLD"])
    # assign attributes
    for a_key in well_props.keys():
        if a_key != "WELL" and a_key != "FLD":
            setattr(created_well, a_key, well_props[a_key])
    # correct date
    created_well.DATE = pd.to_datetime(created_well.DATE)
    # add well logs information
    created_well.logs_info = well_logs_info
    # replace na in logs df
    well_logs_df.replace(created_well.NULL, np.nan, inplace=True)
    # set index as depth
    well_logs_df.set_index(keys="DEPTH", inplace=True, drop=True)
    # store logs DF
    created_well.original_logs = well_logs_df
    created_well.missing_logs, created_well.standard_logs = std_logs(well_logs_info, well_logs_df)
    return created_well


# function to read well attributes and well logs from las file
def read_las(file_loc):
    # Dictionary to store well information and dataframe for logs
    well_dict = {}
    with open(file_loc) as las:
        # Boolean used to check start of actual data rather than header
        well_attributes = ["WELL NAME", "FIELD", "LAS FILE CREATION DATE",
                           "START DEPTH", "STOP DEPTH", "STEP VALUE", "NULL VALUE",
                           "KB ELEVATION", "GL ELEVATION",
                           "LONGITUDE", "LATITUDE", "X OR EAST-WEST COORDINATE", "Y OR NORTH-SOUTH COORDINATE"]
        numeric_attributes = well_attributes[3:]
        start_curve_info = False
        start_log_idx = 0
        logs_info = {}
        # read all lines in CPI and finds the num at which readings start as well as other important well info
        for num, lines in enumerate(las.readlines(), start=0):
            # if to find the start of the log (skips Header)
            if "~A" in lines:
                start_log_idx = num
                break
            # Find well attributes
            for attribute in well_attributes:
                if attribute == lines.upper().strip().split(":")[-1].strip():
                    attribute_name = lines[:lines.find(".")].strip()
                    # corrects for .FT 1000 for example
                    if len(lines[lines.find(".")+1:lines.find(":")].strip().split())> 1:
                        attribute_value = lines[lines.find(".") + 1:lines.find(":")].strip().split()[-1]
                    else:
                        attribute_value = lines[lines.find(".")+1:lines.find(":")].strip()
                    # for numerical attributes
                    if attribute in numeric_attributes:
                        try:
                            well_dict[attribute_name] = float(attribute_value)
                        except ValueError:
                            well_dict[attribute_name] = np.nan
                    else:
                        well_dict[attribute_name] = attribute_value
            # Find Curve information
            if start_curve_info and lines[0] != "#":
                # corrects for unnamed logs
                if lines.upper().split()[-1] != ":":
                    logs_info[lines.split()[0]] = lines.split()[-1]
                else:
                    logs_info[lines.split()[0]] = lines.split()[0]
            # if to find the start of curve information
            if "~CURVE" in lines:
                start_curve_info = True
    # Creates well logs dataframe
    logs_df = pd.read_csv(file_loc, sep="\s+", skiprows=start_log_idx + 1, header=None)
    logs_df.columns = logs_info.keys()
    return well_dict, logs_info, logs_df


# function to standardize well logs
def std_logs(logs_info, logs_df):
    default_logs = {'BS': 'BitSize', 'CAL': 'Caliper', 'GR': 'GammaRay', 'SP': 'SP',
                    'BADHOLE': 'BADHOLE', 'TEMP': 'Temp',
                    'Kair': 'Kair', 'Koil': 'Koil', 'Kstress': 'Kstress', 'Kwater': 'Kwater',
                    'NPHIL': 'Neutron', 'PE': 'PEF', 'RHOB': 'Density', 'DTC': 'Sonic', 'DRHO': 'Correction',
                    'PayFlag': 'PayFlag', 'ResFlag': 'ResFlag',
                    'PHIE': 'PHIE', 'PHIT': 'PHIT', 'SW': 'SW', 'BVW': 'BVW',
                    'RDEEP': 'DeepRes', 'RMICRO': 'MicroRes', 'RSHAL': 'ShalRes', 'RMED': 'MedRes',
                    'VAnhy': 'VAnhy', 'VCL': 'VCL', 'VCoal': 'VCoal', 'VDCL': 'VDCL', 'VDolo': 'VDolo',
                    'VLime': 'VLime', 'VSalt': 'VSalt', 'VSand': 'VSand', 'VWCL': 'VWCL', 'VSilt': 'VSilt',
                    'VSand2': 'VSand2', 'VSilt2': 'VSilt2'}
    # list of missing logs
    missing = []
    # new Dataframe to store standard logs
    new_logs_df = pd.DataFrame()
    new_logs_df.index = logs_df.index
    for key, val in default_logs.items():
        if val in logs_info.values():
            new_logs_df[key] = logs_df[list(logs_info.keys())[list(logs_info.values()).index(val)]]
        else:
            missing.append(key)
    return missing, new_logs_df


# calculate petrophysics by depth
def petrophysics_by_depth(var_well, top_interval=-999.0, bottom_interval=-999.0):
    # corrects top and bottom interval
    if top_interval == -999 or top_interval < var_well.STRT or top_interval > var_well.STOP:
        top_interval = var_well.STRT
    if bottom_interval == -999 or bottom_interval > var_well.STOP or bottom_interval < var_well.STRT:
        bottom_interval = var_well.STOP
    # Calculates pay properties
    filtered_data = var_well.standard_logs.loc[top_interval:bottom_interval, :]
    filtered_data = filtered_data[filtered_data["PayFlag"] == 1]
    net_pay = sum(filtered_data["PayFlag"].to_list())
    pay_poro = sum(filtered_data["PHIE"].to_list()) / len(filtered_data["PHIE"].to_list())
    pay_sw = sum(filtered_data["SW"].to_list()) / len(filtered_data["SW"].to_list())
    final_net_pay = net_pay * var_well.STEP
    # calculates reservoir properties
    filtered_data = var_well.standard_logs.loc[top_interval:bottom_interval, :]
    filtered_data = filtered_data[filtered_data["ResFlag"] == 1]
    net_reservoir = sum(filtered_data["ResFlag"].to_list())
    res_poro = sum(filtered_data["PHIE"].to_list()) / len(filtered_data["PHIE"].to_list())
    res_sw = sum(filtered_data["SW"].to_list()) / len(filtered_data["SW"].to_list())
    final_net_reservoir = net_reservoir * var_well.STEP
    result_df = pd.DataFrame(columns=["WELL", "Type", "Net", "PHIE", "SW"])
    result_df.loc[0, :] = [var_well.WELL, "Reservoir", final_net_reservoir, round(res_poro, 3), round(res_sw, 3)]
    result_df.loc[1, :] = [var_well.WELL, "Pay", final_net_pay, round(pay_poro, 3), round(pay_sw, 3)]
    return result_df


# Plots CPI by user Depth
def plot_cpi_by_depth(var_well, required_top_depth=-999.0, required_bottom_depth=-999.0):
    # corrects top and bottom interval
    if required_top_depth == -999 or required_top_depth < var_well.STRT or required_top_depth > var_well.STOP:
        required_top_depth = var_well.STRT
    if required_bottom_depth == -999 or required_bottom_depth > var_well.STOP or required_bottom_depth < var_well.STRT:
        required_bottom_depth = var_well.STOP
    # prepare logs using log types to be consistent between wells
    logs = var_well.standard_logs.copy()
    Depth = logs.index
    plot_vars = ["GR", "BS", "CAL", "RDEEP", "RMED", "RSHAL", "RMICRO", "NPHIL", "RHOB",
                 "ResFlag", "PayFlag", "PHIE", "SW"]
    for a_var in plot_vars:
        if a_var not in logs.columns:
            logs[a_var] = np.nan
    # Plot CPI as a figure
    fig = plt.figure()
    label = var_well.WELL + " CPI"
    fig.suptitle(label)
    # Plot the GR, Bit size & CAL logs
    ax1 = fig.add_subplot(161)
    ax2 = ax1.twiny()
    ax1.set_xlabel("GR, API")
    ax1.plot(logs["GR"], Depth, color="green", linewidth=1)
    ax1.set_xlim([0, 200])
    ax1.axes.xaxis.set_ticks_position("bottom")
    ax1.grid()
    ax2.set_xlabel("Bit Size & CAL, in")
    ax2.plot(logs["BS"], Depth, color="black", linestyle="dashed", linewidth=1)
    ax2.plot(logs["CAL"], Depth, color="black", linewidth=1)
    ax2.set_xlim([6, 16])
    ax2.fill_betweenx(Depth, logs["BS"], logs["CAL"], color="gray", where=logs["BS"] < logs["CAL"])
    ax2.fill_betweenx(Depth, logs["CAL"], logs["BS"], color="yellow", where=logs["BS"] > logs["CAL"])
    ax2.set_ylim(required_bottom_depth, required_top_depth)
    ax2.xaxis.set_ticks(np.arange(6, 18, 2))
    # moves the 2nd x-axis to bottom of the plot
    ax2.axes.xaxis.set_ticks_position("bottom")
    ax2.axes.xaxis.set_label_position("bottom")
    ax2.spines["bottom"].set_position(("axes", -0.15))
    # Plot Res Logs
    ax3 = fig.add_subplot(162, sharey=ax1)
    ax3.set_xlabel("Res, ohm.m")
    ax3.plot(logs["RDEEP"], Depth, color="red", linewidth=1)
    ax3.plot(logs["RMED"], Depth, color="blue", linewidth=1)
    ax3.plot(logs["RSHAL"], Depth, color="green", linewidth=1)
    ax3.plot(logs["RMICRO"], Depth, color="black", linewidth=0.7)
    ax3.grid(which='both')  # plots grid
    ax3.set_ylim(required_bottom_depth, required_top_depth)
    plt.setp(ax3.get_yticklabels(), visible=False)  # Hide yaxis
    ax3.set_xlim([0.1, 1000])
    ax3.semilogx()
    # plot Neutron Density logs
    ax4 = fig.add_subplot(163, sharey=ax1)
    ax4.set_xlabel("Neutron")
    ax4.plot(logs["NPHIL"], Depth, color="gray", linewidth=1)
    ax4.set_xlim([0.45, -0.15])
    ax4.xaxis.set_ticks(np.arange(0.45, -0.27, -0.12))
    ax5 = ax4.twiny()
    ax5.set_xlabel("Density")
    ax5.plot(logs["RHOB"], Depth, color="red", linewidth=1)
    ax5.plot((1.95+((0.45-logs["NPHIL"])/0.6)), Depth, color="green", linewidth=1) # re-plot for filling
    ax5.set_xlim([1.95, 2.95])
    ax5.xaxis.set_ticks(np.arange(1.95, 3.15, 0.2))
    ax5.fill_betweenx(Depth, logs["RHOB"], (1.95+((0.45-logs["NPHIL"])/0.6)), color="yellow",
                      where=logs["RHOB"] < 2.95-(logs["NPHIL"]/0.3))   # converting Neutron to same scale
    ax5.grid()  # plots grid
    ax4.grid()  # plots grid
    ax4.set_ylim(required_bottom_depth, required_top_depth)
    plt.setp(ax4.get_yticklabels(), visible=False)  # Hide yaxis
    # moves the 2nd x-axis to bottom of the plot
    ax5.axes.xaxis.set_ticks_position("bottom")
    ax5.axes.xaxis.set_label_position("bottom")
    ax5.spines["bottom"].set_position(("axes", -0.15))
    # Plot ResFlag and PayFlag
    ax6 = fig.add_subplot(164, sharey=ax1)
    ax6.plot(logs["ResFlag"], Depth, color="gray", linewidth=0.1)
    ax6.set_xlim([0, 2])
    ax6.set_xlabel("ResFlag")
    ax6.fill_betweenx(Depth, 0, logs["ResFlag"], color="yellow")
    ax6.grid(axis="y")  # plots grid
    ax6.set_ylim(required_bottom_depth, required_top_depth)
    plt.setp(ax6.get_yticklabels(), visible=False)  # Hide yaxis
    ax7 = ax6.twiny()
    ax7.set_xlabel("PayFlag")
    ax7.plot(logs["PayFlag"], Depth, color="gray", linewidth=0.1)
    ax7.set_xlim([2, 0])
    ax7.fill_betweenx(Depth, 0, logs["PayFlag"], color="red")
    ax7.axes.xaxis.set_ticks_position("bottom")
    ax7.axes.xaxis.set_label_position("bottom")
    ax7.spines["bottom"].set_position(("axes", -0.15))
    # plot porosity
    ax8 = fig.add_subplot(165, sharey=ax1)
    ax8.set_xlabel("PHIE")
    ax8.plot(logs["PHIE"], Depth, color="black")
    ax8.set_xlim([0.3, 0])
    ax8.xaxis.set_ticks(np.arange(0.3, -0.05, -0.1))
    ax8.set_ylim(required_bottom_depth, required_top_depth)
    plt.setp(ax8.get_yticklabels(), visible=False)  # Hide yaxis
    ax8.grid()
    # plot SW
    ax9 = fig.add_subplot(166, sharey=ax1)
    ax9.set_xlabel("SW")
    ax9.plot(logs["SW"], Depth, color="gray", linewidth=0.5)
    ax9.set_xlim([0, 1])
    ax9.xaxis.set_ticks(np.arange(0, 1.1, 0.25))
    ax9.fill_betweenx(Depth, logs["SW"], 1, color="green")
    ax9.set_ylim(required_bottom_depth, required_top_depth)
    plt.setp(ax9.get_yticklabels(), visible=False)  # Hide yaxis
    ax9.grid()
    # Fine tune and plot figure
    for axis in fig.get_axes():  # loop to get all axis
        axis.xaxis.label.set_fontsize(8)
        for label in (axis.get_xticklabels()):  # loop to get all x-axis labels
            label.set_fontsize(8)
    fig.tight_layout()
    fig.subplots_adjust(top=0.92, wspace=0.2)

    # Dynamic hover values
    dynamic_cursor = True
    if dynamic_cursor:
        c2 = mplcursors.cursor(hover=True)

        # change background color
        @c2.connect("add")
        def _(sel):
            sel.annotation.get_bbox_patch().set(fc="white")

    # show plot
    plt.show()


# Plots petrophysical parameters distribution
def plot_dist_by_depth(var_well, top_interval=-999.0, bottom_interval=-999.0):
    # corrects top and bottom interval
    if top_interval == -999 or top_interval < var_well.STRT or top_interval > var_well.STOP:
        top_interval = var_well.STRT
    if bottom_interval == -999 or bottom_interval > var_well.STOP or bottom_interval < var_well.STRT:
        bottom_interval = var_well.STOP
    # Calculates pay properties
    pay_data = var_well.standard_logs.loc[top_interval:bottom_interval, :].copy()
    pay_data = pay_data[pay_data["PayFlag"] == 1]
    # calculates reservoir properties
    res_data = var_well.standard_logs.loc[top_interval:bottom_interval, :].copy()
    res_data = res_data[res_data["ResFlag"] == 1]
    # prepare data for plotting
    plot_vars = ["PHIE", "SW"]
    for a_var in plot_vars:
        if a_var not in pay_data.columns:
            pay_data[a_var] = np.nan
        if a_var not in res_data.columns:
            res_data[a_var] = np.nan
    # plot dist
    ax1 = plt.subplot(221)
    ax1.hist(res_data["PHIE"], bins="auto")
    ax1_1 = ax1.twinx()
    ax1_1.hist(res_data["PHIE"], bins="auto", cumulative=1, density=True, histtype='step', color="orange", linewidth=1.5)
    plt.title("Reservoir Porosity Distribution")
    ax1.grid()
    ax2 = plt.subplot(222)
    ax2.hist(pay_data["PHIE"], bins="auto")
    ax2_1 = ax2.twinx()
    ax2_1.hist(pay_data["PHIE"], bins="auto", cumulative=1, density=True, histtype='step', color="orange", linewidth=1.5)
    plt.title("Pay Porosity Distribution")
    ax2.grid()
    ax3 = plt.subplot(223)
    ax3.hist(res_data["SW"], bins="auto")
    ax3_1 = ax3.twinx()
    ax3_1.hist(res_data["SW"], bins="auto", cumulative=1, density=True, histtype='step', color="orange", linewidth=1.5)
    plt.title("Reservoir Water Saturation Distribution")
    ax3.grid()
    ax4 = plt.subplot(224)
    ax4.hist(pay_data["SW"], bins="auto")
    ax4_1 = ax4.twinx()
    ax4_1.hist(pay_data["SW"], bins="auto", cumulative=1, density=True, histtype='step', color="orange", linewidth=1.5)
    plt.title("Reservoir Water Saturation Distribution")
    ax4.grid()
    plt.suptitle("Petrophysical analysis Summary")
    plt.tight_layout()
    print("Reservoir Summary")
    print(res_data[["PHIE", "SW"]].describe())
    print("Pay Summary")
    print(pay_data[["PHIE", "SW"]].describe())
    plt.show()


# Create well
my_well = create_well("Temp_Well.las")
# print well info
for well in gc.get_objects():
    if isinstance(well, Well):
        pprint(vars(well))
# Calculate Petrophysics by depth
CPI_summary = petrophysics_by_depth(my_well, 14100, 14300)
# plot CPI
plot_cpi_by_depth(my_well, 14100, 14300)
# plot Petrophysics Distribution
plot_dist_by_depth(my_well, 14100, 14300)
