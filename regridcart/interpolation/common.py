import xarray as xr

from ..coords import (
    NoProjectionInformationFound,
    get_latlon_coords_using_crs,
    has_latlon_coords,
)
from .backends.common import resample as resample_common


def _cartesian_resample(domain, da, dx):
    new_grid = domain.get_grid(dx=dx)
    da_resampled = da.interp_like(new_grid)
    return da_resampled


def resample(
    domain,
    da,
    dx,
    method="bilinear",
    keep_attrs=False,
    backend="xesmf",
):
    """
    Resample a xarray DataArray onto this tile with grid made of NxN points
    """

    old_grid = None
    new_grid = domain.get_grid(dx=dx)

    if has_latlon_coords(da):
        coords = {}
        coords["lat"] = da.coords["lat"]
        coords["lon"] = da.coords["lon"]
        old_grid = xr.Dataset(coords=coords)

    if old_grid is None:
        try:
            coords = get_latlon_coords_using_crs(da=da)
            old_grid = xr.Dataset(coords=coords)
        except NoProjectionInformationFound:
            pass

    if old_grid is None:
        raise NotImplementedError(da.coords)

    da_resampled = resample_common(
        da=da,
        old_grid=old_grid,
        new_grid=new_grid,
        method=method,
        backend=backend,
        keep_attrs=keep_attrs,
    )

    return da_resampled
