import napari

viewer = napari.Viewer()
shear_layer, grains_layer = viewer.open(
        '/Users/jni/Dropbox/Dongchen Shared Juan developing script/'
        'Shared with Juan/step21.defdap.yml')

dock_widget, widget = viewer.window.add_plugin_dock_widget('napari-defdap')

grains_layer.selected_label = 64

napari.run()