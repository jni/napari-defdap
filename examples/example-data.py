import napari

viewer = napari.Viewer()
shear_layer, grains_layer = viewer.open(
        '/Users/jni/Dropbox/Dongchen Shared Juan developing script/'
        'Shared with Juan/step21.defdap.yml',
        plugin='napari-defdap'
        )

dock_widget, widget = viewer.window.add_plugin_dock_widget('napari-defdap')

grains_layer.selected_label = 64
grains_layer.mode = 'pick'

dicmap = shear_layer.metadata['dicmap']
ebsdmap = shear_layer.metadata['ebsdmap']

g = dicmap.grains[63]
eg = g.ebsd_grain

napari.run()
