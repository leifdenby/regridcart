"""
common interface for getting lat/lon coordinates for a dataset whether these
are given directly as variables or must be calculated from the projection
information
"""
import cartopy.crs as ccrs
import numpy as np
import xarray as xr

from .crs import NoProjectionInformationFound, parse_cf

try:
    # ensures xr.DataArray.rio is available
    import rioxarray  # noqa

    HAS_RIO = True
except ImportError:
    HAS_RIO = False


def has_latlon_coords(da):
    return "lat" in da.coords and "lon" in da.coords


def on_latlon_aligned_grid(da):
    if not has_latlon_coords(da):
        return False

    return len(da.lat.shape) == 1 and len(da.lon.shape)


def parse_crs(da):
    """
    Get the lat/lon coordinate positions using projection information stored in
    a xarray.DataArray
    """
    # first we try parsing any projection information stored in a CF-compliant
    # manner
    crs = None
    try:
        crs = parse_cf(da)
    except NoProjectionInformationFound:
        pass

    # second, if the data was loaded with rioxarray there may be a `crs`
    # attribute available that way
    if crs is None and hasattr(da, "rio"):
        crs_rio = getattr(da.rio, "crs")
        # rio returns its own projection class type, let's turn it into a
        # cartopy projection
        crs = ccrs.Projection(crs_rio)

    # third, we look for a user-defined attribute
    if crs is None and "crs" in da.attrs:
        crs = da.attrs["crs"]

    return crs


def get_latlon_coords_using_crs(da, x_coord="x", y_coord="y"):
    """
    Get the lat/lon coordinate positions using projection information stored in
    a xarray.DataArray
    """
    crs = parse_crs(da)

    if crs is None:
        raise NoProjectionInformationFound

    latlon = ccrs.PlateCarree().transform_points(
        crs,
        *np.meshgrid(da[x_coord].values, da[y_coord].values),
    )[:, :, :2]
    da_lat = xr.DataArray(
        latlon[..., 1],
        dims=(y_coord, x_coord),
        coords={x_coord: da[x_coord], y_coord: da[y_coord]},
    )
    da_lon = xr.DataArray(
        latlon[..., 0],
        dims=(y_coord, x_coord),
        coords={x_coord: da[x_coord], y_coord: da[y_coord]},
    )

    return dict(lat=da_lat, lon=da_lon)
