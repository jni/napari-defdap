"""
see: https://napari.org/stable/plugins/guides.html?#widgets
"""
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from skimage import measure
from napari_matplotlib.base import NapariMPLWidget
from qtpy.QtWidgets import QHBoxLayout, QWidget

from ._plot_functions import plot_slip_detection_plot
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
            self.ax = self.mpl.figure.add_subplot(projection='polar')
            self.ax.set_theta_zero_location('S')
        self.grains_layer = next(layer for layer in napari_viewer.layers if
                                 type(layer).__name__ == 'Labels')
        self.intensity_layer = next(layer for layer in napari_viewer.layers
                                    if type(layer).__name__ == 'Image')
        self.props = measure.regionprops(
                np.clip(self.grains_layer.data, 0, None),
                intensity_image=self.intensity_layer.data,
                )
        self.dic = self.grains_layer.metadata['dicmap']
        self.ebsd = self.grains_layer.metadata['ebsdmap']
        self.callback = self.grains_layer.events.selected_label.connect(
                self._update_plots
                )

    def _update_plots(self, event):
        with plt.style.context('dark_background'):
            self.ax.clear()
            self.ax.set_theta_zero_location('S')
        k = self.grains_layer.selected_label - 1
        radon_values = compute_radon(self.dic, k, self.props[k])
        with plt.style.context('dark_background'):
            plot_slip_detection_plot(self.dic, k, radon_values, ax=self.ax)
            self.ax.figure.canvas.draw_idle()
