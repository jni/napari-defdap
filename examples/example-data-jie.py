import napari
from napari_defdap._tracks import tracks_from_seg

viewer = napari.Viewer()
shear_layer, grains_layer = viewer.open(
        '/Users/jni/data/jie-tracking-grains/data/time-series.defdap.yml',
        plugin='napari-defdap'
        )

#dock_widget, widget = viewer.window.add_plugin_dock_widget('napari-defdap')

grains_layer.selected_label = 64
grains_layer.mode = 'pick'

dicmap = list(shear_layer.metadata['dicmap'].values())[0]
ebsdmap = list(shear_layer.metadata['ebsdmap'].values())[0]

print(shear_layer.data.shape)

g = dicmap.grains[63]
eg = g.ebsd_grain

seg = grains_layer.data

tracks = tracks_from_seg(seg, time_axis=0)

pts_layer = viewer.add_points(tracks[:, 1:], size=3, scale=grains_layer.scale)
trk_layer = viewer.add_tracks(tracks, scale=grains_layer.scale)

if __name__ == '__main__':
    napari.run()
