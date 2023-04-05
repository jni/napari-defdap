"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""
import os
import numpy as np
from defdap import hrdic, ebsd


def _look_for_ebsd(path):
    directory = os.path.split(path)[0]
    files = [os.path.join(directory, os.path.splitext(fn)[0])
             for fn in os.listdir(directory)
             if fn.endswith('cpr')]
    return files[0]


def _ends_with_any(string, list_of_suffixes):
    return any(string.endswith(suf) for suf in list_of_suffixes)


def napari_get_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    ALLOWED_EXTENSIONS = 'txt', 'cpr', 'crc'
    if isinstance(path, list):
        if not all(_ends_with_any(p, ALLOWED_EXTENSIONS) for p in path):
            return None
    elif not _ends_with_any(path, ALLOWED_EXTENSIONS):
        return None

    # otherwise we return the *function* that can read ``path``.
    return read_defdap


def read_defdap(path):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """
    # handle both a string and a list of strings
    path = path[0] if type(path) is list else path
    # load all files into array
    scale = 25/2048  # µm
    dicmap = None
    if path.endswith('txt'):
        dicmap = hrdic.Map(*os.path.split(path))
        dicmap.setCrop(xMin=30, xMax=90, yMin=10, yMax=10)
        dicmap.setScale(micrometrePerPixel=scale)
    ebsd_fn = _look_for_ebsd(path)
    ebsdmap = ebsd.Map(ebsd_fn)
    ebsdmap.buildQuatArray()
    ebsdmap.findBoundaries()
    ebsdmap.findGrains(minGrainSize=10)
    ebsdmap.calcGrainMisOri(calcAxis=False)
    ebsdmap.calcAverageGrainSchmidFactors(
            loadVector=np.array([1, 0, 0]))
    if dicmap is not None and ebsdmap is not None:
        print('we be alignin')
        dicmap.homogPoints = np.array((
                [(343, 627), (1908, 1820), (176, 1919),
                 (1320, 409), (1560, 1068), (548, 52)]
                ))
        ebsdmap.homogPoints = np.array((
                [(323, 569), (1432, 1398), (190, 1469),
                 (999, 414), (1160, 828), (459, 175)]
                ))
        dicmap.linkEbsdMap(ebsdmap, transformType='affine')
        dicmap.findGrains(algorithm='warp')

    # optional kwargs for the corresponding viewer.add_* method
    add_kwargs = {
            'scale': [scale, scale],
            'metadata': {'dicmap': dicmap, 'ebsdmap': ebsdmap},
            }
    image_data = dicmap.crop(dicmap.data.max_shear)
    grains = dicmap.grains

    return [(image_data, add_kwargs, 'image'), (grains, add_kwargs, 'labels')]
