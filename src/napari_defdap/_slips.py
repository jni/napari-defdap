import numpy as np
import pandas as pd
from scipy import ndimage
from skimage.transform import radon
from skimage import filters


def sb_angle(shear_map, threshold=None, median_filter=None):
    """Compute slip band angles based on shear map.

    Uses a threshold to reduce noise, optionally followed by a median filter,
    then a radon transform to find the angles.

    Parameters
    ----------
    shear_map : numpy ndarray, shape (M, N)
        The input shear map.
    threshold : float
        Threshold value for the array.
    median_filter : int or None
        The size of the median filter to apply for denoising. None means no
        median filter is applied.
    plot : bool or str
        False, or a path to a file in which to save the plot.

    Returns
    -------
    profile_filt : list of float
        Maximum intensity of radon transform at that angle.
    angles_index : tuple[array of int, properties dict]
        Positions of peaks in the profile as found by scipy.signal.find_peaks.
    """
    if threshold != None:
        shear_map_filt = shear_map > threshold
    else:
        shear_map_filt = shear_map

    if median_filter != None:
        shear_map_filt = ndimage.median_filter(shear_map_filt,
                                               size=median_filter)

    sin_map = radon(shear_map_filt)
    profile_filt = np.max(sin_map, axis=0)

    return profile_filt.tolist()


def compute_radon(dicmap, grain_id, regionprop,
                  threshold_func=filters.threshold_mean,
                  threshold_multiplier=1.6, minimum_threshold=0.013):
    values = np.asarray(dicmap[grain_id].data.max_shear)
    threshold_value = max(threshold_multiplier * threshold_func(values),
                          minimum_threshold)
    grain_map = regionprop.intensity_image
    grain_map[~regionprop.image] = np.nan
    angle_list = sb_angle(grain_map, threshold=threshold_value,
                          median_filter=3)
    return np.asarray(angle_list)


def get_slipsystem_info2(grainID, DicMap):
    """Grab slip system for a specific grain.

    Parameters
    ----------
    grainID : int
        The ID of the grain to examine.
    DicMap : defdap.hrdic.Map object
        The DIC map.

    Returns
    -------
    info_frame : list of lists
        Contains Slip plane labels, schmid factors, and slip trace angles.
    """

    #Load the slip systems for the current phase
    ssGroup = DicMap[grainID].ebsd_grain.phase.slipSystems

    #Calculate the schmid factor of each slip system
    schmidFactor = DicMap[grainID].ebsd_grain.averageSchmidFactors

    #Calculate the slip trace angles
    DicMap[grainID].ebsd_grain.calcSlipTraces()
    ST_Angle = np.rad2deg(DicMap[grainID].ebsd_grain.slipTraceAngles) % 360

    ids = np.arange(1, 5)
    labels = [ssGroup[i][0].slipPlaneLabel for i in range(4)]
    sfs = [max(schmidFactor[i]) for i in range(4)]
    angles = [ST_Angle[i] for i in range(4)]
    frame = pd.DataFrame({
        'slip_plane': ids,
        'sp_label': labels,
        'sf': sfs,
        'angle_deg': angles,
        'color': ['blue', 'green', 'red', 'purple'],
    })
    return frame

