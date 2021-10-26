"""
common interface for getting lat/lon coordinates for a dataset whether these
are given directly as variables or must be calculated from the projection
information
"""
import cartopy.crs as ccrs
import numpy as np

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


def using_crs(da):
    pass


def is_cartesian(da):
    pass


def _find_xy_coords(da):
    def find_coord(standard_name):
        for c in da.coords:
            if da[c].attrs.get("standard_name") == standard_name:
                return c
        raise Exception(f"coordinate with standard_name `{standard_name}` not found")

    x_coord = find_coord("projection_x_coordinate")
    y_coord = find_coord("projection_y_coordinate")
    return da[x_coord], da[y_coord]


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
    except NoProjectionInformationFound:
        pass

    # second, if the data was loaded with rioxarray there may be a `crs`
    # attribute available that way
    if crs is None and hasattr(da, "rio"):
        crs = getattr(da.rio, "crs")

    # third, we look for a user-defined attribute
    if crs is None and "crs" in da.attrs:
        crs = da.attrs["crs"]

    if crs is None:
        raise NoProjectionInformationFound

    da_x, da_y = _find_xy_coords(da=da)

    latlon = ccrs.PlateCarree().transform_points(
        crs,
        *np.meshgrid(da_x.values, da_y.values),
    )[:, :, :2]
    lat = latlon[..., 1]
    lon = latlon[..., 0]

    return dict(lat=lat, lon=lon)
