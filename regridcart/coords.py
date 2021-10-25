"""
common interface for getting lat/lon coordinates for a dataset whether these
are given directly as variables or must be calculated from the projection
information
"""


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
