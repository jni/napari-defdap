"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""
import os
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import remove_small_objects
import yaml
from defdap import hrdic, ebsd


def _add_non_indexed(seg, time_axis=0, min_size=0):
    ndim = seg.ndim
    non_indexed = seg <= 0
    axes = tuple(i for i in range(ndim) if i != time_axis)
    max_label = np.max(seg, axis=axes)
    labeled = np.zeros_like(seg)
    for i in range(seg.shape[time_axis]):
        idx_ = [slice(None),] * ndim
        idx_[time_axis] = i
        idx = tuple(idx_)
        labeled_i = ndi.label(non_indexed[idx])[0] + max_label[i]
        if min_size > 0:
            remove_small_objects(
                    labeled_i, min_size=min_size, out=labeled[idx]
                    )
        else:
            labeled[idx] = labeled_i
    output = np.where(non_indexed, labeled, seg)
    return output


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

    timepoints = data.get('time', [data])
    n = len(timepoints)
    dicmaps = {}
    ebsdmaps = {}
    grains_list = []
    max_shear_list = []
    phase_list = []
    for i, dat in enumerate(timepoints):
        dicmap, ebsdmap, _g, _m, _p = read_timepoint(dat, directory)
        dicmaps[(i,) * (n > 1)] = dicmap
        ebsdmaps[(i,) * (n > 1)] = ebsdmap
        grains_list.append(_g)
        max_shear_list.append(_m)
        phase_list.append(_p)
    min_grain_size = timepoints[0]['ebsd']['min_grain_size']
    squeeze = 0 if n == 1 else slice(None)
    grains = _add_non_indexed(
            np.stack(grains_list), min_size=min_grain_size
            )[squeeze]
    max_shear = np.stack(max_shear_list)[squeeze]
    phase = np.stack(phase_list)[squeeze]

    ndim = max_shear.ndim
    clim = np.quantile(max_shear, [0.01, 0.99])
    if clim[1] == clim[0]:
        clim[1] += 1
    # optional kwargs for the corresponding viewer.add_* method
    joint_kwargs = {
            'scale': (1,) * (ndim - 2) + (dicmap.scale, dicmap.scale),
            'metadata': {'dicmap': dicmaps, 'ebsdmap': ebsdmaps},
            }
    max_shear_kwargs = {
            **joint_kwargs,
            'contrast_limits': clim,
            'colormap': 'viridis',
            'name': 'max_shear',
            }
    label_kwargs = {
            **joint_kwargs,
            'name': 'grains',
            'blending': 'translucent_no_depth',
            }
    phase_kwargs = {
            **joint_kwargs,
            'name': 'phase',
            'blending': 'translucent_no_depth',
            'features': {
                    'index': np.arange(len(ebsdmap.phases) + 1),
                    'names': ['not indexed'] + [p.name for p in ebsdmap.phases],
                    },
            }

    return [(max_shear, max_shear_kwargs, 'image'),
            (grains, label_kwargs, 'labels'),
            (phase, phase_kwargs, 'labels'),]


def read_timepoint(data, directory):
    """Read a single timepoint containing both DIC and EBSD data.

    Parameters
    ----------
    data : dict
        A dictionary containing loading parameters for DIC and EBSD maps,
        including their homolog points for affine warping the EBSD to the
        DIC frame.
    directory : pathlib.Path | str
        Where to look for the image data files.

    Returns
    -------
    dicmap : defdap.hrdic.Map
        The DIC map.
    ebsdmap : defdap.ebsd.Map
        The EBSD map.
    grains : np.ndarray
        The grains array (containing grainid - 1 at each pixel).
    max_shear : np.ndarray
        The max shear array.
    phase : np.ndarray
        The phase array
    """
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
    ebsdmap.data.generate(
        'grain_boundaries',
        misori_tol=ebsd_params.get('misorientation_tolerance', 10)
    )
    # ebsdmap.data.grain_boundaries = ebsdmap.find_boundaries(
    #         misori_tol=ebsd_params.get('misorientation_tolerance', 10)
    #         )[0]
    ebsdmap.find_grains(min_grain_size=ebsd_params['min_grain_size'])
    # ebsdmap.calcGrainMisOri(calcAxis=False)
    ebsdmap.calc_average_grain_schmid_factors(
        load_vector=np.array(ebsd_params['load_vector']))
    dicmap.frame.homog_points = np.array(dic_params['homolog_points'])
    ebsdmap.frame.homog_points = np.array(ebsd_params['homolog_points'])
    dicmap.link_ebsd_map(ebsdmap, transform_type=ebsd_params['transform_type'])
    grains_raw = dicmap.find_grains(
        algorithm=ebsd_params['find_grains_algorithm']
    )
    # dicmap.data.grains = grains_raw
    max_shear = np.nan_to_num(dicmap.crop(dicmap.data.max_shear))
    grains = dicmap.crop(grains_raw)
    phase = dicmap.crop(dicmap.warp_to_dic_frame(
            ebsdmap.data.phase, order=0, preserve_range=True
            ))
    return dicmap, ebsdmap, grains, max_shear, phase
