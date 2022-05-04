import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import mplcursors
import numpy as np


# define class Field and its attributes
class Field:
    def __init__(self, field_name):
        self.field = field_name


# define class Well and its attributes
class Well(Field):
    def __init__(self, well_name, field_name):
        super().__init__(field_name)  # passes field name to Parent class
        self.NAME = well_name
        self.START = -999
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
        self.logs = pd.DataFrame()


# function to read well attributes and well logs from las file
def read_las(file_loc):
    # Dictionary to store well information and dataframe for logs
    well_dict = {}
    with open(file_loc) as las:
        # Boolean used to check start of actual data rather than header
        start_log_type = False
        well_attributes = ["START", "STOP", "STEP", "NULL", "DATE", "NAME", "FIELD",
                           "LONG", "LATI", "XCOORD", "YCOORD", "KB", "GL"]
        numeric_attributes = ["START", "STOP", "STEP", "NULL", "LONG", "LATI", "XCOORD", "YCOORD", "KB", "GL"]
        start_log_idx = 0
        # read all lines in CPI and finds the num at which readings start as well as other important well info
        for num, lines in enumerate(las.readlines(), start=0):
            # if to find the start the readings start (skips Header)
            if "~A" in lines:
                Start_log_readings = True
                start_log_idx = num
                break
            # to find well attributes
            for attribute in well_attributes:
                if attribute in lines.upper().split():
                    attribute_value = lines[lines.find(".")+1:lines.find(":")].strip()
                    # for numerical attributes
                    if attribute in numeric_attributes:
                        try:
                            well_dict[attribute] = float(attribute_value)
                        except ValueError:
                            # checks if attribute_value can still be split
                            if len(attribute_value.split())>0:
                                try:
                                    float(attribute_value.split()[-1])
                                    well_dict[attribute] = float(attribute_value.split()[-1])
                                except ValueError:
                                    # else append None
                                    well_dict[attribute] = np.nan
                    else:
                        well_dict[attribute] = attribute_value
    # Creates well logs names
    with open(file_loc) as las:
        log_names = las.readlines()[start_log_idx].split()[1:]  # [1:] to drop ~A
    # Creates well logs dataframe
    logs_df = pd.read_csv(file_loc, sep="\s+", skiprows=start_log_idx + 1, header=None)
    logs_df.columns = log_names
    return well_dict, logs_df


# calculate petrophysics by depth
def petrophysics_by_depth(var_well, top_interval=-999.0, bottom_interval=-999.0):
    # corrects top and bottom interval
    if top_interval == -999 or top_interval < var_well.START:
        top_interval = var_well.START
    if bottom_interval == -999 or bottom_interval > var_well.STOP:
        bottom_interval = var_well.STOP
    # Calculates pay properties
    filtered_data = var_well.logs.loc[top_interval:bottom_interval, :]
    filtered_data = filtered_data[filtered_data["PayFlag"] == 1]
    net_pay = sum(filtered_data["PayFlag"].to_list())
    pay_poro = sum(filtered_data["PHIE"].to_list()) / len(filtered_data["PHIE"].to_list())
    pay_sw = sum(filtered_data["SW"].to_list()) / len(filtered_data["SW"].to_list())
    final_net_pay = net_pay * var_well.STEP
    # calculates reservoir properties
    filtered_data = var_well.logs.loc[top_interval:bottom_interval, :]
    filtered_data = filtered_data[filtered_data["ResFlag"] == 1]
    net_reservoir = sum(filtered_data["ResFlag"].to_list())
    res_poro = sum(filtered_data["PHIE"].to_list()) / len(filtered_data["PHIE"].to_list())
    res_sw = sum(filtered_data["SW"].to_list()) / len(filtered_data["SW"].to_list())
    final_net_reservoir = net_reservoir * var_well.STEP
    result_df = pd.DataFrame(columns=["WELL", "Type", "Net", "PHIE", "SW"])
    result_df.loc[0, :] = [var_well.NAME, "Reservoir", final_net_reservoir, round(res_poro, 3), round(res_sw, 3)]
    result_df.loc[1, :] = [var_well.NAME, "Pay", final_net_pay, round(pay_poro, 3), round(pay_sw, 3)]
    return result_df


def plot_cpi_by_depth(var_well, required_top_depth=-999.0, required_bottom_depth=-999.0):
    # corrects top and bottom interval
    if required_top_depth == -999 or required_top_depth < var_well.START:
        required_top_depth = var_well.START
    if required_bottom_depth == -999 or required_bottom_depth > var_well.STOP:
        required_bottom_depth = var_well.STOP
        # Plot CPI as a figure
    fig = plt.figure()
    label = var_well.NAME + " CPI"
    fig.suptitle(label)
    # prepare logs using log types to be consistent between wells
    logs = var_well.logs.copy()
    Depth = logs.index
    plot_vars = ["GR", "BS", "CAL", "RDEEP", "RMED", "RSHAL", "RMICRO", "NPHIL", "RHOB",
                 "ResFlag", "PayFlag", "PHIE", "SW"]
    for a_var in plot_vars:
        if a_var not in logs.columns:
            logs[a_var] = np.nan
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
    ax3 = fig.add_subplot(162)
    ax3.set_xlabel("Res, ohm.m")
    ax3.plot(logs["RDEEP"], Depth, color="red", linewidth=1)
    ax3.plot(logs["RMED"], Depth, color="blue", linewidth=1)
    ax3.plot(logs["RSHAL"], Depth, color="green", linewidth=1)
    ax3.plot(logs["RMICRO"], Depth, color="black", linewidth=0.7)
    ax3.grid(which='both')  # plots grid
    ax3.set_ylim(required_bottom_depth, required_top_depth)
    ax3.axes.yaxis.set_ticklabels([])  # Removes Y axis labels
    ax3.set_xlim([0.1, 1000])
    ax3.semilogx()
    # plot Neutron Density logs
    ax4 = fig.add_subplot(163)
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
    ax4.axes.yaxis.set_ticklabels([])  # Removes Y axis labels
    # moves the 2nd x-axis to bottom of the plot
    ax5.axes.xaxis.set_ticks_position("bottom")
    ax5.axes.xaxis.set_label_position("bottom")
    ax5.spines["bottom"].set_position(("axes", -0.15))
    # Plot ResFlag and PayFlag
    ax6 = fig.add_subplot(164)
    ax6.plot(logs["ResFlag"], Depth, color="gray", linewidth=0.1)
    ax6.set_xlim([0, 2])
    ax6.set_xlabel("ResFlag")
    ax6.fill_betweenx(Depth, 0, logs["ResFlag"], color="yellow")
    ax6.grid(axis="y")  # plots grid
    ax6.set_ylim(required_bottom_depth, required_top_depth)
    ax6.axes.yaxis.set_ticklabels([])
    ax7 = ax6.twiny()
    ax7.set_xlabel("PayFlag")
    ax7.plot(logs["PayFlag"], Depth, color="gray", linewidth=0.1)
    ax7.set_xlim([2, 0])
    ax7.fill_betweenx(Depth, 0, logs["PayFlag"], color="red")
    ax7.axes.xaxis.set_ticks_position("bottom")
    ax7.axes.xaxis.set_label_position("bottom")
    ax7.spines["bottom"].set_position(("axes", -0.15))
    # plot porosity
    ax8 = fig.add_subplot(165)
    ax8.set_xlabel("PHIE")
    ax8.plot(logs["PHIE"], Depth, color="black")
    ax8.set_xlim([0.3, 0])
    ax8.xaxis.set_ticks(np.arange(0.3, -0.05, -0.1))
    ax8.set_ylim(required_bottom_depth, required_top_depth)
    ax8.grid()
    ax8.axes.yaxis.set_ticklabels([])
    # plot SW
    ax9 = fig.add_subplot(166)
    ax9.set_xlabel("SW")
    ax9.plot(logs["SW"], Depth, color="gray", linewidth=0.5)
    ax9.set_xlim([0, 1])
    ax9.xaxis.set_ticks(np.arange(0, 1.1, 0.25))
    ax9.fill_betweenx(Depth, logs["SW"], 1, color="green")
    ax9.set_ylim(required_bottom_depth, required_top_depth)
    ax9.grid()
    ax9.axes.yaxis.set_ticklabels([])
    # Fine tune and plot figure
    for axis in fig.get_axes():  # loop to get all axis
        axis.xaxis.label.set_fontsize(8)
        for label in (axis.get_xticklabels()):  # loop to get all x-axis labels
            label.set_fontsize(8)
    fig.tight_layout()
    fig.subplots_adjust(top=0.92, wspace=0.2)

    # Dynamic hover values
    c2 = mplcursors.cursor(hover=True)

    # change background color
    @c2.connect("add")
    def _(sel):
        sel.annotation.get_bbox_patch().set(fc="white")

    # show plot
    plt.show()


# read well data
well_props, well_logs_df = read_las("WKAL A-23 CPI.las")
# create well variable
my_well = Well(well_props["NAME"], well_props["FIELD"])
# assign attributes
for a_key in well_props.keys():
    if a_key != "NAME" and a_key != "FIELD":
        setattr(my_well, a_key, well_props[a_key])
# replace na in logs df
well_logs_df.replace(my_well.NULL, np.nan, inplace=True)
# set index as depth
well_logs_df.set_index(keys="DEPTH", inplace=True, drop=True)
my_well.logs = well_logs_df
print(vars(my_well))

# Calculate Petrophysics by depth
CPI_summary = petrophysics_by_depth(my_well)
print(CPI_summary)

# plot CPI
plot_cpi_by_depth(my_well, 14100, 14300)
