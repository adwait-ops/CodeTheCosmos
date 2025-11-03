import matplotlib.pyplot as plt
import numpy as np
# import mesaplot as mp
from mesaplot import mesaPlot as mp
from matplotlib.colors import LogNorm, Normalize, ListedColormap
from matplotlib.patches import Patch, Wedge

from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from mpl_toolkits.axes_grid1 import make_axes_locatable
from tqdm.notebook import tqdm
from os import makedirs, path
from imageio_ffmpeg import get_ffmpeg_exe

import cmasher as cmr # for additional colormaps
import astropy.units as u

import blackbody as bb
## learning git
def perceived_color(m, time_ind=-1, raxis="log_R", fps=10, fig=None, ax=None, show_time_label=True, time_label_loc=(),
                    time_unit="Myr", fig_size=(5.5, 4), axis_lim=-99, axis_label="", theta1=0, theta2=360,
                    hrd_inset=True, show_hrd_ticks_and_labels=False, show_total_mass=True, show_surface=True,
                    output_fname="perceived_color", anim_fmt=".mp4",
                    time_scale_type="model_number"):
    """
    What the parameters mean and what data type they are:
    --------------------------------------------------------

    m : mesaPlot object
        Already loaded a history file.
    time_ind : int or tuple (start_index, end_index, step=1) or (start_index, end_index, step)
        If int: create the plot at the index `time_ind`. 
        If tuple: create an animation from start index to end index with intervals of step.
    raxis : str
        Default axis to use as radius of the circle.
    fps : int
        Number of frames per second for the animation.
    fig : Figure object
        If set, plot on existing figure.
    ax : Axes object
        If set, plot on provided axis.
    show_time_label : boolean
        If set, insert a label that gives the age of the stellar object (in Myr).
    time_label_loc : tuple
        Location of the time label on the plot as fraction of the maximal size.
    time_unit : str
        Valid astropy time unit.
    fig_size : tuple
        Size of the figure in inches.
    axis_lim : float
        Value to set for the maximum limit of the x and y axis.
    axis_label : str
        Label of the x and y axis.
    theta1: int or float
        Start angle for the wedge.
    theta2 : int or float
        End angle for the wedge.
    hrd_inset : boolean
        If set, add an inset HRD where the location of the current model is indicated with a circle.
    show_hrd_ticks_and_labels : Boolean
        If set, display the axis ticks and labels of the inset HRD
    show_total_mass : boolean
        If set, display the value of the total mass of the model in the bottom right corner.
    show_surface : boolean,
        If set, show the outer boundary of the stellar object.
    output_fname : str
        Name of the output file.
    anim_fmt : str
        Format to use for saving an animation.
    time_scale_type : str
        One of `model_number`, `linear`, or `log_to_end`. For `model_number`, the time follows the moment when a new MESA model was saved. For `linear`, the time follows linear steps in star_age. For `log_to_end`, the time axis is tau = log10(t_final - t), where t_final is the final star_age of the model.
    
    Returns
    -------
    fig, ax
    """
#add_inset_hrd

    if fig is None:
        fig = plt.figure()
        fig.set_size_inches(fig_size)
    if ax is None:
        ax = plt.gca()

    start_ind, end_ind, ind_step = check_time_indeces(time_ind, m.hist.star_age)

    # Read radius data from the model. If the axis is a "log_" quantity convert to linear
    raw_r = m.hist.data[raxis]
    if isinstance(raxis, str) and raxis[:3] == "log":
        # convert log10(radius) -> radius
        r = 10 ** raw_r
    else:
        r = raw_r

    # Determine axis limits in the same (linear) units as `r` so the full circle fits.
    if axis_lim == -99:
        axis_lim = 1.05 * r.max()

    # replace smallest values with constant ratio
    smallest_radius_ratio = 0.01
    too_small = (r / axis_lim < smallest_radius_ratio)
    if np.any(too_small):
        r[too_small] = axis_lim * smallest_radius_ratio

    # Plot star as circle with color derived from Teff
    color = bb.teff2rbg([10 ** m.hist.log_Teff[start_ind]])[0]

    lw = 0
    if show_surface:
        lw = 1.1
    circle = Wedge((0, 0), r[start_ind], theta1=theta1, theta2=theta2, facecolor=color, edgecolor='k',
                   lw=lw)
    ax.add_artist(circle)

    # Add time label (use mesaPlot helper when available, otherwise fall back to plain text)
    if show_time_label:
        time = m.hist.star_age[start_ind]
        text = add_time_label(time, ax, time_label_loc=time_label_loc, time_unit=time_unit)

    # Set axis for plotting correctly sized circles
    ax.set_xlim([-axis_lim, axis_lim])
    ax.set_ylim([-axis_lim, axis_lim])
    ax.set_aspect('equal', adjustable='box')

    set_axis_ticks_and_labels(ax, raxis=raxis, axis_label=axis_label)



    if hrd_inset:
        axins, point = add_inset_hrd(m, ax=ax, time_index=start_ind,
                                     show_hrd_ticks_and_labels=show_hrd_ticks_and_labels)


    # Add mass label
    if show_total_mass:
        mass_text = ax.text(0.87, 0.05, "{}".format(round(m.hist.star_mass[start_ind], 1)) +
                            "$\,\\rm{M}_{\odot}$", transform=ax.transAxes, ha="center", va="center")

    # Create animation
    if end_ind != start_ind:
        # Create animation
        indices = range(start_ind, end_ind, ind_step)
        indices = rescale_time(indices, m, time_scale_type=time_scale_type)
        r = r[indices]
        t = m.hist.star_age[indices]
        log_teff = m.hist.log_Teff[indices]
        log_l = m.hist.log_L[indices]
        star_mass = m.hist.star_mass[indices]
        colors_ary = bb.teff2rgb(10 ** log_teff)

        frames = len(indices)
        fps = fps
        bar = tqdm(total=frames)

        def init():
            circle.radius = r[0]
            circle.set_facecolor(colors_ary[0])
            ax.add_patch(circle)
            time = (t[0] * u.yr).to(time_unit)
            text.set_text("t = " + time.round(3).to_string())
            return circle, point

        def animate(ind):
            bar.update()
            time = (t[ind] * u.yr).to(time_unit)
            r_cur = r[ind]
            color = colors_ary[ind]
            circle.set_radius(r_cur)
            circle.set_facecolor(color)

           # Add time location
            if show_time_label:
                text.set_text("t = " + time.round(3).to_string())

            if hrd_inset:
                point.set_data([log_teff[ind]], [log_l[ind]])

            if show_total_mass:
                mass_text.set_text("{}".format(round(star_mass[ind], 1)) + "$\,\\rm{M}_{\odot}$")

            return circle, point

        print("Creating animation")

        ani = mp.FuncAnimation(fig, animate, init_func=init, frames=frames, interval=1000 / fps, blit=False, repeat=False)
        plt.subplots_adjust(top=0.99, left=0.12, right=0.89, hspace=0, wspace=0, bottom=0.1)

        # Save animation
        ani.save(output_fname + anim_fmt, writer="ffmpeg", extra_args=['-vcodec', 'libx264'])

    return fig, ax

def check_time_indeces(time_ind, star_age):
    """Check time indices.
    
    Check if time indices are correctly set and define start_ind and end_ind.
    
    Parameters
    ----------
    time_ind: int or tuple (start_index, end_index, step=1) or (start_index, end_index, step)
        If int: create the plot at the index `time_ind`.
    star_age: array
        Ages of star from MESA history file
    
    Returns
    -------
    start_ind, end_ind, ind_step
    """
    if type(time_ind) is not tuple and type(time_ind) is not list and type(time_ind) is not np.ndarray:
        start_ind = int(time_ind)
        if start_ind < 0:
            start_ind += len(star_age)
        end_ind = start_ind
        ind_step = 1
    elif len(time_ind) == 2 or len(time_ind) == 3:
        start_ind = int(time_ind[0])
        end_ind = int(time_ind[1])

        # Make sure all indices are positive
        if start_ind < 0:
            start_ind += len(star_age)
        if end_ind < 0:
            end_ind += len(star_age)

        if start_ind == end_ind:
            # Issue warning when same values for start and end index
            raise Warning("No animation will be created because the start and end index have the same value")

        ind_step = 1
        if len(time_ind) == 3:
            ind_step = int(time_ind[2])
            if ind_step <= 0:
                raise ValueError("ind_step must be an integer larger than 0")
    else:
        raise TypeError("time_index must be an integer or a tuple of integers (start_ind, end_ind, step=1)")

    return start_ind, end_ind, ind_step

def set_axis_ticks_and_labels(ax, raxis="star_mass", axis_label=""):
    """ Format axis ticks.
    
    Format the axis ticks such that no negative values are shown.
    
    Parameters
    ----------
    ax : matplotlib axis object
    raxis: str
        Valid column name for a MESA history file. This sets the value used for the outer radius of the star.
    axis_label : str
        User defined axis label.
        
    Returns
    -------
    None
    """
    # Set axis properties
    label = axis_label

    if label == "":
        label = raxis
        if raxis == "log_R" or raxis == "radius":
            label = "Radius" + "$ \,[\\rm{R}_\odot]$"
        elif raxis == "star_mass" or raxis == "mass":
            label = "Mass" + "$\,[\\rm{M}_\odot]$"
        elif "_" in label:
            label = label.replace("_", " ")
    ax.set_xlabel(label)
    ax.set_ylabel(label)
    # Change number of ticks to avoid excessive number
    plt.locator_params(nbins=6)
    ax.xaxis.set_major_locator(plt.MaxNLocator(6))
    ax.yaxis.set_major_locator(plt.MaxNLocator(6))
    # Change y tick labels
    if raxis[:3] == "log":
        ticks = ax.get_yticks()
        new_ticks = []
        for t in ticks:
            if abs(t) < 1:
                new = '{:.2g}'.format(abs(np.sign(t)) * 10 ** abs(t))
            else:
                new = '{:.0f}'.format(abs(np.sign(t)) * 10 ** abs(t))
            new_ticks.append(new)
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_yticklabels(new_ticks)
        ax.set_xticklabels(new_ticks)
    else:
        ticks = ax.get_yticks()
        min_tick = abs(ax.get_xticks().min())
        new_ticks = ['{:.1f}'.format(abs(t)) for t in ticks]
        if min_tick < 1:
            new_ticks = ['{:.2g}'.format(abs(t)) for t in ticks]
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_yticklabels(new_ticks)
        ax.set_xticklabels(new_ticks)


def add_inset_hrd(m, time_index=100, ax=None, axins=None, fraction="20%", indices=None,
                  loc="lower left", bbox_to_anchor=None, show_hrd_ticks_and_labels=False):
    """ Add inset HRD.
    
    Add an inset HRD to a plot that highlights the current time-step.
    
    Parameters
    ----------
    m : mesaPlot object
    ax : axis object
    indices : None, list or ndarray
        Selected indices for plotting
    fraction : string
        Fraction of the parent axis used for setting the size of the inset
    axins : None or Axes
        If provided, inset axis to use.
    time_index : int
        Time index to highlight on inset plot.
    loc : str or int
        Matplotlib location to put the inset axis on the parent axis.
    bbox_to_anchor : tuple (x, y, width, height)
        Bounding box for the axis
    show_hrd_ticks_and_labels : Boolean
        If set, display the axis ticks and labels of the inset HRD
    Returns
    -------
    (axins, point): Axes
        Created inset axis, and the point moving on the plot.
    """
    # TODO: adapt to only show chosen range of time_ind
    if ax is None:
        ax = plt.gca()
    if indices is None:
        indices = np.arange(len(m.hist.log_Teff))

    if axins is None:
        axins = inset_axes(ax,
                           width=fraction,  # width = % of parent_bbox
                           height=fraction,  # height : 1 inch
                           loc=loc,
                           bbox_to_anchor=bbox_to_anchor
                           )
        axins.invert_xaxis()
        # move axis ticks
        axins.tick_params(axis='y', which='both', labelright=True, labelleft=False, direction='in')
        axins.tick_params(axis='x', which='both', labeltop=True, labelbottom=False, direction='in')
        axins.yaxis.set_ticks_position('right')
        axins.xaxis.set_ticks_position('top')

        # Add labels
        if show_hrd_ticks_and_labels:
            axins.set_xlabel("$\log_{10}(T_{\\rm{eff}}/\\mathrm{K})$",
                             fontsize=int(0.65 * plt.rcParams.get("font.size")))
            axins.set_ylabel("$\log_{10}(L/\\mathrm{L}_{\\odot})$", rotation=90,
                             fontsize=int(0.65 * plt.rcParams.get("font.size")))
            axins.yaxis.set_label_position('right')
            axins.xaxis.set_label_position('top')
            plt.setp(axins.get_xticklabels(),
                     fontsize=int(0.55 * plt.rcParams.get("font.size")))
            plt.setp(axins.get_yticklabels(),
                     fontsize=int(0.55 * plt.rcParams.get("font.size")))
            # fix the number of ticks on the inset axes
            axins.yaxis.get_major_locator().set_params(nbins=3)
            axins.xaxis.get_major_locator().set_params(nbins=3)
        else:
            axins.xaxis.set_ticks([])
            axins.yaxis.set_ticks([])
        # For better output, use all the models within the range selected for the background evolution on the HRD
        axins.plot(m.hist.log_Teff[indices[0]:indices[-1] + 1], m.hist.log_L[indices[0]:indices[-1] + 1], "b", lw=1.25)

    # Add marker for current location
    point, = axins.plot([m.hist.log_Teff[indices][time_index]], [m.hist.log_L[indices][time_index]], ls=None,
                        marker="o", color="yellow", mec="k", mew=1, alpha=0.6)
    return axins, point

def add_time_label(age, ax, time_label_loc=None, time_unit="Myr"):
    """ Add time label.
    
    Add a time label in the upper left corner of a diagram.
    
    Parameters
    ----------
    age : float
        Age of the stellar object.
    ax : matplotlib Axes object
    time_label_loc : None or tuple 
        Default None, the custom location of the time label in units of the Axes coordinate; (0, 0) is bottom left of the axes, and (1, 1) is top right of the axes
    time_unit: str
        Unit of the time. 
    
    Returns
    -------
    matplotlib Artist object
    """
    # If location not specified, place it in the upper left corner
    if len(time_label_loc) == 0:
        time_label_loc = (0.05, 0.95)

    time = (age * u.yr).to(time_unit)
    text = ax.text(time_label_loc[0], time_label_loc[1], "t = " + time.round(1).to_string(),
                   transform=ax.transAxes)
    return text

def find_closest(ary, value):
    return np.abs(ary - value).argmin()

def rescale_time(indices, m, time_scale_type="model_number"):
    """Rescale the time.
    
    Rescale time indices depending on the time_type.
    
    Parameters
    ----------    
    indices : np.array or list of int
        Containing selected indices.
    m : mesa Object
    time_scale_type : str
        One of `model_number`, `linear`, or `log_to_end`. For `model_number`, the time follows the moment when a new MESA model was saved. For `linear`, the time follows linear steps in star_age. For `log_to_end`, the time axis is tau = log10(t_final - t), where t_final is the final star_age of the model.
    
    Returns
    -------
    ind_select : list
        New list of indices that reflect the rescaling in time.
    """
    age = m.hist.star_age
    if time_scale_type == "model_number":
        return indices
    elif time_scale_type == "linear":
        val_select = np.linspace(age[indices[0]], age[indices[-1]], len(indices))
        ind_select = [find_closest(val, age) for val in val_select]
        return ind_select
    elif time_scale_type == "log_to_end":
        time_diff = (age[-1] - age)
        # Avoid invalid values for log
        time_diff[time_diff <= 0] = 1e-5
        logtime = np.log10(time_diff)
        # Find indices
        val_select = np.linspace(logtime[indices[0]], logtime[indices[-1]], len(indices))
        ind_select = [find_closest(val, logtime) for val in val_select]
        return ind_select
    else:
        raise ValueError('Invalid time_type. Choose one of "model_number", "linear", or "log_to_end"')
    
    #mp.