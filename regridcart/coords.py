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
    import rioxarray  # ensures xr.DataArray.rio is available

    HAS_RIO = True
except ImportError:
    HAS_RIO = False


def has_latlon_coords(da):
    return "lat" in da.coords and "lon" in da.coords


def on_latlon_aligned_grid(da):
    if not has_latlon_coords(da):
        return False

    return len(da.lat.shape) == 1 and len(da.lon.shape)


def _find_xy_coords(da):
    """
    Using CF-conventions for grid projectino information look for the name of
    the x- and y-coordinates in the DataArray
    """

    def find_coord(standard_name):
        for c in da.coords:
            if da[c].attrs.get("standard_name") == standard_name:
                return c
        raise Exception(f"coordinate with standard_name `{standard_name}` not found")

    x_coord = find_coord("projection_x_coordinate")
    y_coord = find_coord("projection_y_coordinate")
    return x_coord, y_coord


def get_latlon_coords_using_crs(da):
    """
    Get the lat/lon coordinate positions using projection information stored in
    a xarray.DataArray
    """
    # first we try parsing any projection information stored in a CF-compliant
    # manner
    crs = None
    try:
        crs = parse_cf(da)
        x_coord, y_coord = _find_xy_coords(da=da)
    except NoProjectionInformationFound:
        pass

    # second, if the data was loaded with rioxarray there may be a `crs`
    # attribute available that way
    if crs is None and hasattr(da, "rio"):
        crs_rio = getattr(da.rio, "crs")
        # rio returns its own projection class type, let's turn it into a
        # cartopy projection
        crs = ccrs.Projection(crs_rio)
        x_coord, y_coord = "x", "y"

    # third, we look for a user-defined attribute
    if crs is None and "crs" in da.attrs:
        crs = da.attrs["crs"]
        x_coord, y_coord = _find_xy_coords(da=da)

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
