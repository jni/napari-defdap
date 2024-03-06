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
    dicmap = hrdic.Map(os.path.join(directory, dic_params['file']))
    xcrop, ycrop = (crop := dic_params['crop'])['x'], crop['y']
    dicmap.set_crop(left=xcrop[0], right=xcrop[1],
                    top=ycrop[0], bottom=ycrop[1])
    dicmap.set_scale(scale)

    ebsd_fn = os.path.join(directory, ebsd_params['file'])
    ebsdmap = ebsd.Map(ebsd_fn)
    #ebsdmap.find_boundaries()
    ebsdmap.find_grains(min_grain_size=ebsd_params['min_grain_size'])
    #ebsdmap.calcGrainMisOri(calcAxis=False)
    ebsdmap.calc_average_grain_schmid_factors(
            load_vector=np.array(ebsd_params['load_vector']))
    dicmap.frame.homog_points = np.array(dic_params['homolog_points'])
    ebsdmap.frame.homog_points = np.array(ebsd_params['homolog_points'])
    dicmap.link_ebsd_map(ebsdmap, transform_type=ebsd_params['transform_type'])
    grains_raw = dicmap.find_grains(
            algorithm=ebsd_params['find_grains_algorithm']
            )
    #dicmap.data.grains = grains_raw
    image_data = dicmap.crop(dicmap.data.max_shear)
    grains = dicmap.crop(grains_raw)
    clim = np.quantile(image_data, [0.01, 0.99])
    # optional kwargs for the corresponding viewer.add_* method
    joint_kwargs = {
            'scale': [scale, scale],
            'metadata': {'dicmap': dicmap, 'ebsdmap': ebsdmap},
            }
    image_kwargs = {
            **joint_kwargs,
            'contrast_limits': clim,
            'colormap': 'viridis',
            'name': 'max_shear'
            }
    label_kwargs = {**joint_kwargs, 'name': 'grains'}

    return [(image_data, image_kwargs, 'image'),
            (grains, label_kwargs, 'labels')]
