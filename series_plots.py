#%%
from argparse import ArgumentError
from dataclasses import dataclass
import random
from typing import Literal, Union, Any, Collection, Sequence, List
import dearpygui.dearpygui as dpg
import statsmodels.api as sm
from fast5_research.fast5_bulk import BulkFast5
from context import Context

DpgItem = Union[int, str]
#TODO: resolve progress bar issue...

# cf. https://www.python.org/dev/peps/pep-0484/#the-numeric-tower
# int is ok where float is required
@dataclass
class SeriesData:
    # TODO/HACK: Union[Collection, Collection[Collection]] mimicks
    # *arg syntax to allow for undecided many plots to be added
    # implicitly assert len(x_datas) == len(y_datas)
    title: str
    x_label: str
    x_lims: Sequence[float]
    x_datas: Union[Collection[float], Collection[Collection[float]]]
    y_label: str
    y_lims: Sequence[float]
    y_datas: Union[Collection[float], Collection[Collection[float]]]


def _plot_series(target: DpgItem, data: SeriesData) -> None:
    with dpg.plot(label=data.title, height=-1, width=-1, parent=target) as plt:
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label=data.x_label)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=data.y_label)
        dpg.set_axis_limits(x_axis, *data.x_lims)
        dpg.set_axis_limits(y_axis, *data.y_lims)

        for x_data, y_data in zip(data.x_datas, data.y_datas):
            dpg.add_line_series(x_data, y_data, parent=y_axis)
        dpg.set_axis_limits_auto(x_axis)
        dpg.set_axis_limits_auto(y_axis)
    dpg.configure_item(target, on_close=lambda:dpg.delete_item(plt))


def _get_kdes(context: Context, *chans) -> List[sm.nonparametric.KDEUnivariate]:
    fpath = context.active_exp.fpath
    burnin = context.settings['burnin']
    kde_resolution = context.settings['kde_resolution']

    progress_bar = "Progress Bar" #context.get_progress_bar()
    dpg.configure_item(progress_bar, show=True, width=175)
    kdes = []
    for count, chan in enumerate(chans):
        dpg.set_value(progress_bar, count/len(chans))
        dpg.configure_item(progress_bar, overlay=f"Calculating KDE {count+1}/{len(chans)}")

        with BulkFast5(fpath) as fh:
            raw_data = fh.get_raw(chan)[burnin:]
        kde = sm.nonparametric.KDEUnivariate(raw_data)
        kde.fit(gridsize=min(kde_resolution,len(raw_data)))
        kdes.append(kde)
    dpg.configure_item(progress_bar, show=False)

def _get_series_data(
    context: Context,
    flavour: Literal['raw', 'dens'],
    *channels: int
) -> SeriesData:
    fpath = context.active_exp.path
    title = f"{context.active_exp.name}\nChannel {channels}"
    if flavour == "raw":
        # TODO: ensure that channels fits as type?
        with BulkFast5(fpath) as fh:
            x_data = fh.get_raw(channels)
        x_label = "index"
        x_lims = (0, 100_000)
        y_label = "current [pA]"
        y_lims = (-20, 350)
        y_data = list(range(0,len(x_data)))
    elif flavour == 'dens':
        kdes = _get_kdes(context, channels)
        x_data = [kde.support for kde in kdes]
        y_data = [kde.density for kde in kdes]
        x_label = "current [pA]"
        x_lims = (-20, 350)
        y_label = "density"
        y_lims = (-0.05, 0.2)
    else:
        raise ArgumentError(f"Flavour {flavour} is no valid series flavour. Use \'raw\' or \'dens\'")
    return SeriesData(title, x_label, x_lims, x_data, y_label, y_lims, y_data)

def show_raw(
    sender: DpgItem,
    app_data: Any,
    user_data: Context
) -> None:
    if not (channel := dpg.get_value("channel")):
        # no channel set, fail silently, TODO: add handling ie message?
        return
    series_data = _get_series_data(user_data, channel, "raw")
    dpg.add_window(label="Raw Data", width=800, height=600, show=False)
    target = dpg.last_item()
    _plot_series(target, series_data)

def show_kde(
    sender: DpgItem,
    app_data: Any,
    user_data: Context
) -> None:
    if not (channel := dpg.get_value("channel")):
        # no channel set, fail silently, TODO: add handling ie message?
        return
    series_data = _get_series_data(user_data, channel, "dens")
    dpg.add_window(label="Kernel Density", width=800, height=600, show=False)
    target = dpg.last_item()
    _plot_series(target, series_data)

def show_rand_kde(
    sender: DpgItem,
    app_data: Any,
    user_data: Context
) -> None:
    active_chans = user_data.get_active_channels()
    assert active_chans

    if len(active_chans) > 11:
        chans = random.choices(active_chans, k=10)
    else:
        chans = active_chans

    series_data = _get_series_data(user_data, chans, "dens")
    dpg.add_window(label="Kernel Density", width=800, height=600, show=False)
    target = dpg.last_item()
    _plot_series(target, series_data)