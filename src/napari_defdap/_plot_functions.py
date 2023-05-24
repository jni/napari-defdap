import numpy as np
from ._slips import get_slipsystem_info2

def plot_slip_detection_plot(dicmap, grain_id, max_shear_along_angles, *, ax):
    max_shear_along_angles_periodic = np.concatenate(
            [max_shear_along_angles] * 2 + [max_shear_along_angles[0:1]]
            )
    angles = np.linspace(0, 2*np.pi, 361, endpoint=True)
    ax.plot(angles, max_shear_along_angles_periodic)
    slip_system_df = get_slipsystem_info2(grain_id, dicmap)
    slip_system_df['angle_deg_180'] = (slip_system_df['angle_deg'] + 180) % 360
    for row in slip_system_df.itertuples(index=False):
        ax.vlines(
                np.radians([row.angle_deg, row.angle_deg_180]),
                ymin=0, ymax=1.05 * np.max(max_shear_along_angles),
                colors=row.color,
                )
    ax.set_title('Band angle distribution')
    ax.set_xlabel('Angle in degrees')


def plot_shear(prop, *, ax):
    minr, minc, maxr, maxc = prop.bbox
    ax.imshow(prop.intensity_image,
              aspect='equal',
              extent=[minr - 0.5, maxr + 0.5, maxc + 0.5, minc - 0.5])
    ax.set_aspect('equal')