"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""
import os
import numpy as np
import yaml
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
    ALLOWED_EXTENSIONS = '.defdap.yml'
    if isinstance(path, list):
        if not all(p.endswith(ALLOWED_EXTENSIONS) for p in path):
            return None
    elif not path.endswith(ALLOWED_EXTENSIONS):
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
    directory = os.path.split(path)[0]
    with open(path, mode='r') as fin:
        data = yaml.safe_load(fin)
    dic_params = data['dic']
    ebsd_params = data['ebsd']
    scale = dic_params['scale']
    dicmap = hrdic.Map(directory, dic_params['file'])
    xcrop, ycrop = (crop := dic_params['crop'])['x'], crop['y']
    dicmap.setCrop(xMin=xcrop[0], xMax=xcrop[1], yMin=ycrop[0], yMax=ycrop[1])
    dicmap.setScale(micrometrePerPixel=scale)

    ebsd_fn = os.path.join(directory, ebsd_params['file'])
    ebsdmap = ebsd.Map(ebsd_fn)
    ebsdmap.buildQuatArray()
    ebsdmap.findBoundaries()
    ebsdmap.findGrains(minGrainSize=ebsd_params['min_grain_size'])
    ebsdmap.calcGrainMisOri(calcAxis=False)
    ebsdmap.calcAverageGrainSchmidFactors(
            loadVector=np.array(ebsd_params['load_vector']))
    dicmap.homogPoints = np.array(dic_params['homolog_points'])
    ebsdmap.homogPoints = np.array(ebsd_params['homolog_points'])
    dicmap.linkEbsdMap(ebsdmap, transformType=ebsd_params['transform_type'])
    dicmap.findGrains(algorithm=ebsd_params['find_grains_algorithm'])

    # optional kwargs for the corresponding viewer.add_* method
    add_kwargs = {
            'scale': [scale, scale],
            'metadata': {'dicmap': dicmap, 'ebsdmap': ebsdmap},
            }
    image_data = dicmap.crop(dicmap.data.max_shear)
    grains = dicmap.grains

    return [(image_data, add_kwargs, 'image'), (grains, add_kwargs, 'labels')]
