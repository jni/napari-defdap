import numpy as np
from scipy import ndimage as ndi
import trackpy as tpy
from skimage import measure


def _add_non_indexed(seg, time_axis=0):
    non_indexed = seg <= 0
    struct_slice = [slice(None),] * seg.ndim
    struct_slice[time_axis] = slice(1, 2)
    structure = ndi.generate_binary_structure(seg.ndim, 1)[tuple(struct_slice)]
    axes = tuple(i for i in range(seg.ndim) if i != time_axis)
    max_label = np.max(seg, axis=axes, keepdims=True)
    labeled = ndi.label(non_indexed, structure) + max_label
    output = np.where(non_indexed, labeled, seg)
    return output


def _slice(ndim, ax, i):
    output = [slice(None),] * ndim
    output[ax] = i
    return tuple(output)


def points_from_seg(seg, time_axis=0, include_non_indexed=True):
    coords_iter = []
    full_seg = _add_non_indexed(seg) if include_non_indexed else seg
    for i in range(full_seg.shape[time_axis]):
        seg_t = full_seg[_slice(full_seg.ndim, time_axis, i)]
        seg_clipped = np.clip(seg_t, 0, None)
        props = measure.regionprops_table(
                seg_clipped, properties=('centroid',)
                )
        coords = np.column_stack(
                [props[f'centroid-{i}'] for i in range(seg_t.ndim)]
                )
        coords_iter.append(coords)
    return coords_iter


def tracks_from_seg(seg, time_axis=0):
    coords_iter = points_from_seg(seg, time_axis)
    linked = tpy.link_iter(coords_iter, 8., adaptive_stop=0.5, adaptive_step=0.5)
    linked_arrays = []
    for coords, (t, ids) in zip(coords_iter, linked):
        tarr, idsarr = np.broadcast_arrays(t, ids)
        linked_arrays.append(np.column_stack((idsarr, tarr, coords)))
    return np.concatenate(linked_arrays, axis=0)