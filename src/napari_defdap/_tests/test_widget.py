import numpy as np
import pandas as pd

from napari_defdap._track_focus import set_track_focus


def test_track_focus(make_napari_viewer, qtbot):
    viewer = make_napari_viewer()
    data = np.random.random((5, 128, 128))
    viewer.add_image(data)
    tracks = np.array([
        [1, 0, 12, 12],
        [1, 1, 15, 15],
        [1, 2, 25, 25],
        [1, 3, 30, 40],
        [1, 4, 50, 50],
    ])
    tracks_layer = viewer.add_tracks(
            tracks,
            features=pd.DataFrame(tracks, columns=['track_id', 't', 'y', 'x']),
            )
    widget = set_track_focus()
    qtbot.addWidget(widget.native)
    widget(viewer, tracks_layer, 1)
    assert viewer.camera.center[-2:] == (25, 25)
