"""
see: https://napari.org/stable/plugins/guides.html?#widgets
"""
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from skimage import measure
from napari_matplotlib.base import NapariMPLWidget
from qtpy.QtWidgets import QHBoxLayout, QWidget

from ._plot_functions import plot_slip_detection_plot, plot_shear
from ._slips import compute_radon

if TYPE_CHECKING:
    import napari


class GrainPlots(QWidget):
    def __init__(self, napari_viewer: 'napari.viewer.Viewer', parent=None):
        super().__init__(parent=parent)
        self.viewer = napari_viewer
        with plt.style.context('dark_background'):
            self.mpl = NapariMPLWidget(napari_viewer, parent=self)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.mpl)
        with plt.style.context('dark_background'):
            self.ax0 = self.mpl.figure.add_subplot(211)
            self.ax1 = self.mpl.figure.add_subplot(212, projection='polar')
            self.ax1.set_theta_zero_location('S')
        self.grains_layer = next(layer for layer in napari_viewer.layers if
                                 type(layer).__name__ == 'Labels')
        self.intensity_layer = next(layer for layer in napari_viewer.layers
                                    if type(layer).__name__ == 'Image')
        grains, shear = np.broadcast_arrays(
                self.grains_layer.data, self.intensity_layer.data
                )
        self.grains = grains
        self.shear = shear
        self.ndim = grains.ndim
        self.props = {}
        self.props_dict = {}
        for idx in np.ndindex(grains.shape[:-2]):
            self.props[idx] = measure.regionprops(
                    np.clip(grains[idx], 0, None), intensity_image=shear[idx]
                    )
            self.props_dict.update(
                    {idx + (prop.label,): prop for prop in self.props[idx]}
                    )
        self.dic = self.grains_layer.metadata['dicmap']
        self.ebsd = self.grains_layer.metadata['ebsdmap']
        self._sel_callback = self.grains_layer.events.selected_label.connect(
                self._update_plots
                )
        self._dims_callback = self.viewer.dims.events.current_step.connect(
                self._update_plots
                )
        self.grains_layer.events.selected_label()

    def _update_plots(self, event):
        with plt.style.context('dark_background'):
            self.ax0.clear()
            self.ax1.clear()
            self.ax1.set_theta_zero_location('S')
        lab = self.grains_layer.selected_label
        k = lab - 1
        d = self.viewer.dims.current_step[:-2]
        try:
            prop = self.props_dict[d + (lab,)]
        except KeyError:
            return
        radon_values = compute_radon(prop)
        dic = self.dic if self.ndim == 2 else self.dic[d]
        with plt.style.context('dark_background'):
            plot_shear(prop, ax=self.ax0)
            plot_slip_detection_plot(dic, k, radon_values, ax=self.ax1)
            self.ax1.figure.canvas.draw_idle()
