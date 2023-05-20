from dataclasses import dataclass, field
from enum import Enum, Flag
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
from omegaconf import II, MISSING, SI, OmegaConf

from .plotting_structure import (
    BinnedSpectrumPlot,
    DataHistPlot,
    FermiSpectrumPlot,
    MPLCmap,
    PhotoSpectrumPlot,
)


@dataclass
class OGIP:
    fit_plot: BinnedSpectrumPlot = field(default_factory=BinnedSpectrumPlot)
    data_plot: DataHistPlot = field(default_factory=DataHistPlot)
    response_cmap: MPLCmap = MPLCmap.viridis
    response_zero_color: str = "k"


@dataclass
class Fermipy:
    fit_plot: FermiSpectrumPlot = field(default_factory=FermiSpectrumPlot)


#    data_plot: DataHistPlot = DataHistPlot()


@dataclass
class Photo:
    fit_plot: PhotoSpectrumPlot = field(default_factory=PhotoSpectrumPlot)


@dataclass
class Plugins:
    ogip: OGIP = field(default_factory=OGIP)
    photo: Photo = field(default_factory=Photo)
    fermipy: Fermipy = field(default_factory=Fermipy)


@dataclass
class TimeSeriesFit:
    fit_poly: bool = True
    unbinned: bool = False
    bayes: bool = False


@dataclass
class TimeSeries:
    light_curve_color: str = "#05716c"
    selection_color: str = "#1fbfb8"
    background_color: str = "#C0392B"
    background_selection_color: str = "#E74C3C"
    fit: TimeSeriesFit = field(default_factory=TimeSeriesFit)
