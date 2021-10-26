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

    return da_resampled
