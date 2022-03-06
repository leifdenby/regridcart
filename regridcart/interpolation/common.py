import xarray as xr

from ..coords import (
    NoProjectionInformationFound,
    get_latlon_coords_using_crs,
    has_latlon_coords,
)
from ..cropping import crop_field_to_domain
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
    apply_crop=True,
):
    """
    Resample a data-array onto a domain at specific resolution `dx` (given in
    meters). The data-array is expected to have coordinates defined using one
    of the following:

    1. `lat` and `lon` coordinates along which the data is aligned, i.e. `lat`
       and `lon` are given as 1D arrays
    2. `lat` and `lon` are given as auxilliary variables so that the data isn't
       aligned along the lat/lon directions, but rather the `lat` and `lon` of
       every datapoint is given
    3. the data-array has projection information defined in a CF-compliant
       manner using the `grid_mapping` attribute
       (http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/build/ch05s06.html)
    4. the data-array was loaded from a raster-file using
       `rioxarray.open_rasterio` so that the projection information is
       available via `da.rio.crs`

    By default the input array will be cropped before resampling
    (`apply_crop=True`)

    """

    old_grid = None
    new_grid = domain.get_grid(dx=dx)

    if apply_crop:
        da = crop_field_to_domain(domain=domain, da=da)

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
