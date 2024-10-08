from typing import Annotated

from magicgui import magic_factory


@magic_factory(auto_call=True)
def set_track_focus(
        viewer: 'napari.viewer.Viewer',
        layer: 'napari.layers.Tracks',
        track_id: Annotated[int, {'max': 1_000_000, 'step': 1}],
        ):
    """Given a tracks layer and a track id, set camera focus on that track."""
    df = layer.features  # make sure to add the dataframe to the tracks layer
    track_locations = df.loc[df['track_id'] == track_id, ['t', 'y', 'x']]
    if track_locations.shape[0] == 0:
        return
    current_timepoint = float(viewer.dims.point[0])
    if current_timepoint not in list(track_locations.t):
        current_timepoint = track_locations.t.iloc[-1]
    new_point = track_locations[
            track_locations.t == current_timepoint
            ].to_numpy()[0] * layer.scale
    viewer.dims.point = tuple(new_point)
    if viewer.dims.ndisplay == 2:
        viewer.camera.center = new_point[1:]
    else:
        viewer.camera.center = new_point