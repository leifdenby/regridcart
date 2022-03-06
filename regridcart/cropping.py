import numpy as np

from .coords import (
    NoProjectionInformationFound,
    get_latlon_coords_using_crs,
    has_latlon_coords,
    on_latlon_aligned_grid,
)


def crop_field_to_bbox(da, x_range, y_range, pad_pct=0.1, x_dim="x", y_dim="y"):
    if x_dim not in da.dims or y_dim not in da.dims:
        raise Exception(
            f"The coordinates selected for cropping (`{x_dim}` and `{y_dim}`)"
            f" are not present in the provided DataArray ({', '.join(da.coords.keys())})"
        )
    # cast to float in case the ranges are given as ints, otherwise the `-=`
    # and `+=` operations below will fail
    x_min, x_max = np.array(x_range).astype(float)
    y_min, y_max = np.array(y_range).astype(float)

    lx = x_max - x_min
    ly = y_max - y_min

    x_min -= pad_pct * lx
    y_min -= pad_pct * ly
    x_max += pad_pct * lx
    y_max += pad_pct * ly

    # handle coordinates that aren't monotonically increasing
    if da[x_dim][0] > da[x_dim][-1]:
        x_slice = slice(x_max, x_min)
    else:
        x_slice = slice(x_min, x_max)

    if da[y_dim][0] > da[y_dim][-1]:
        y_slice = slice(y_max, y_min)
    else:
        y_slice = slice(y_min, y_max)

    da_cropped = da.sel({x_dim: x_slice, y_dim: y_slice})

    if da_cropped[x_dim].count() == 0 or da_cropped[y_dim].count() == 0:
        raise DomainBoundsOutsideOfInputException

    return da_cropped


class DomainBoundsOutsideOfInputException(Exception):
    pass


def _has_spatial_coord(da, c):
    return c in da and da[c].attrs.get("units") == "m"


def _latlon_box_adjust_sigfigs(bbox, decimals=2):
    """
    Round bounding-box lat/lon values to nearest number of significant figures
    in direction that ensure that original area is contained with the new
    bounding box
    """
    # bbox: [W, E, S, N]
    fns = [np.floor, np.ceil, np.floor, np.ceil]
    scaling = 10 ** decimals

    def _af(fn):
        return lambda v: fn(v * scaling) / scaling

    bbox_truncated = np.array([_af(fn)(v) for (fn, v) in zip(fns, bbox)])
    return bbox_truncated


def _crop_with_latlon_aligned_crid(domain, da, pad_pct):
    x_dim, y_dim = "lon", "lat"
    latlon_box = _latlon_box_adjust_sigfigs(domain.latlon_bounds)
    xs = latlon_box[..., 0]
    ys = latlon_box[..., 1]
    x_min, x_max = np.min(xs), np.max(xs)
    y_min, y_max = np.min(ys), np.max(ys)
    if da[x_dim][-1] > 180.0:
        if x_max < 0.0:
            x_min += 360.0
            x_max += 360.0
        else:
            raise NotImplementedError
    x_range = [x_min, x_max]
    y_range = [y_min, y_max]

    bounds_checks = [
        ("W", x_min, da[x_dim].min().data),
        ("E", da[x_dim].max().data, x_max),
        ("S", y_min, da[y_dim].min().data),
        ("N", da[y_dim].max().data, y_max),
    ]

    for edge, v1, v2 in bounds_checks:
        if v1 < v2:
            raise DomainBoundsOutsideOfInputException(f"{edge}: {v1} < {v2}")

    return crop_field_to_bbox(
        da=da,
        x_range=x_range,
        y_range=y_range,
        pad_pct=pad_pct,
        x_dim=x_dim,
        y_dim=y_dim,
    )


def _crop_with_latlon_aux_grid(domain, da, da_lat, da_lon, pad_pct):
    assert da_lat.dims == da_lon.dims
    assert len(da_lat.dims) == 2
    y_dim, x_dim = da_lat.dims

    latlon_box = _latlon_box_adjust_sigfigs(domain.latlon_bounds)
    bbox_lons = latlon_box[..., 0]
    bbox_lats = latlon_box[..., 1]

    mask = (
        (bbox_lons.min() < da_lon)
        * (bbox_lons.max() > da_lon)
        * (bbox_lats.min() < da_lat)
        * (bbox_lats.max() > da_lat)
    )

    if np.count_nonzero(mask) == 0:
        raise Exception(
            "lat/lon bounds are outside of the domain",
            f"domain bounds (W, E), (S, N): ({da_lon.min().item()}, {da_lon.max().item()})"
            f", ({da_lat.min().item()}, {da_lat.max().item()}). "
            f"bbox bounds (W, E), (S, N): ({bbox_lons.min().item()}, {bbox_lons.max().item()})"
            f", ({bbox_lats.min().item()}, {bbox_lats.max().item()})",
        )

    da_masked = da.where(mask, drop=True)

    x_min = da_masked[x_dim].min()
    x_max = da_masked[x_dim].max()
    y_min = da_masked[y_dim].min()
    y_max = da_masked[y_dim].max()

    x_range = (x_min, x_max)
    y_range = (y_min, y_max)

    return crop_field_to_bbox(
        da=da,
        x_range=x_range,
        y_range=y_range,
        pad_pct=pad_pct,
        x_dim=x_dim,
        y_dim=y_dim,
    )


def crop_field_to_domain(domain, da, pad_pct=0.1):
    """
    Crop a data-array to a domain. The data-array is expected to have
    coordinates defined using one of the following:

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

    """
    da_cropped = None

    # first we see if the provided xr.DataArray has `lat` and `lon` coordinates
    # given with data-array defined along these coordinates
    if on_latlon_aligned_grid(da):
        da_cropped = _crop_with_latlon_aligned_crid(
            domain=domain, da=da, pad_pct=pad_pct
        )
    # second option is that `lat` and `lon` are given as auxilliary variables
    # (or coordinates), but that the data isn't actually defined along the lat
    # and lon directions (i.e. `lat` and `lon` are 2D arrays in the data-array)
    elif has_latlon_coords(da):
        da_cropped = _crop_with_latlon_aux_grid(
            domain=domain, da=da, pad_pct=pad_pct, da_lat=da.lat, da_lon=da.lon
        )

    # third we try extracting projection information from the data-array and
    # getting the lat/lon coordinates that way
    if da_cropped is None:
        try:
            coords = get_latlon_coords_using_crs(da)
            da_cropped = _crop_with_latlon_aux_grid(
                domain=domain,
                da=da,
                pad_pct=pad_pct,
                da_lat=coords["lat"],
                da_lon=coords["lon"],
            )
        except NoProjectionInformationFound:
            pass

    if da_cropped is None:
        raise NotImplementedError(da.coords)

    return da_cropped
