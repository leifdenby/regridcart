from pyresample import geometry


def get_pyresample_area_def(N, domain):
    """
    When using satpy scenes we're better off using pyresample instead of
    xesmf since it appears faster (I think because it uses dask)
    """

    L = domain.size
    area_id = "tile"
    description = "Tile local cartesian grid"
    proj_id = "ease_tile"
    x_size = N
    y_size = N
    area_extent = (-L, -L, L, L)
    proj_dict = {
        "a": 6371228.0,
        "units": "m",
        "proj": "laea",
        "lon_0": domain.lon0,
        "lat_0": domain.lat0,
    }
    area_def = geometry.AreaDefinition(
        area_id, description, proj_id, proj_dict, x_size, y_size, area_extent
    )

    return area_def
