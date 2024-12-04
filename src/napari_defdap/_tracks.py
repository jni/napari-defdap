import numpy as np
from scipy import ndimage as ndi
import trackpy as tpy
from skimage import measure


def add_non_indexed(seg, time_axis=0):
    ndim = seg.ndim
    non_indexed = seg <= 0
    axes = tuple(i for i in range(ndim) if i != time_axis)
    max_label = np.max(seg, axis=axes)
    labeled = np.zeros_like(seg)
    for i in range(seg.shape[time_axis]):
        idx_ = [slice(None),] * ndim
        idx_[time_axis] = i
        idx = tuple(idx_)
        labeled[idx] = ndi.label(non_indexed[idx])[0] + max_label[i]
    output = np.where(non_indexed, labeled, seg)
    return output


def _slice(ndim, ax, i):
    output = [slice(None),] * ndim
    output[ax] = i
    return tuple(output)


def points_from_seg(seg, time_axis=0, include_non_indexed=True):
    coords_iter = []
    for i in range(seg.shape[time_axis]):
        seg_t = seg[_slice(seg.ndim, time_axis, i)]
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