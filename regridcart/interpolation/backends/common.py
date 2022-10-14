"""
Common interface for lat/lon interpolation backends
"""
from .xesmf import resample as xesmf_resample


def resample(
    da, old_grid, new_grid, keep_attrs=True, method="bilinear", backend="xemsf"
):
    if backend == "xesmf":
        da_resampled = xesmf_resample(
            da=da,
            old_grid=old_grid,
            new_grid=new_grid,
            method=method,
            keep_attrs=keep_attrs,
        )
    else:
        raise NotImplementedError(backend)

    if keep_attrs:
        da_resampled.attrs.update(da.attrs)

    # as of xesmf >= 0.6.3 the lat/lon coords aren't copied any more
    # I don't have time to understand
    # https://github.com/pangeo-data/xESMF/pull/175, but I think that PR was
    # actually meant to fix something that to me wasn't broken before. so I
    # will copy in the new lat/lon here if they are missing

    for c in ["lat", "lon"]:
        if c not in da_resampled.coords:
            da_resampled[c] = new_grid[c]

    return da_resampled
