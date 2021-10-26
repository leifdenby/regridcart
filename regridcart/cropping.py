import numpy as np
import cartopy.crs as ccrs

from .crs import parse_cf as parse_cf_crs
from . import coords


def crop_field_to_bbox(da, x_range, y_range, pad_pct=0.1, x_dim="x", y_dim="y"):
    if x_dim not in da.dims or y_dim not in da.dims:
        raise Exception(
            f"The coordinates selected for cropping (`{x_dim}` and `{y_dim}`)"
            f" are not present in the provided DataArray ({', '.join(da.coords.keys())})"
        )
    x_min, x_max = x_range
    y_min, y_max = y_range

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


def _latlon_box_to_integer_values(bbox):
    """
    Round bounding-box lat/lon values to nearest integer values in direction
    that ensure that original area is contained with the new bounding box
    """
    # bbox: [W, E, S, N]
    fns = [np.floor, np.ceil, np.floor, np.ceil]
    bbox_truncated = np.array([fn(v) for (fn, v) in zip(fns, bbox)])
    return bbox_truncated


def _crop_with_latlon_aligned_crid(domain, da, pad_pct):
    x_dim, y_dim = "lon", "lat"
    latlon_box = _latlon_box_to_integer_values(domain.latlon_bounds)
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

    return crop_field_to_bbox(
        da=da,
        x_range=x_range,
        y_range=y_range,
        pad_pct=pad_pct,
        x_dim=x_dim,
        y_dim=y_dim,
    )


def _crop_with_latlon_aux_grid(domain, da, pad_pct):
    assert da.lat.dims == da.lon.dims
    assert len(da.lat.dims) == 2
    x_dim, y_dim = da.lat.dims

    latlon_box = _latlon_box_to_integer_values(domain.latlon_bounds)
    bbox_lons = latlon_box[..., 0]
    bbox_lats = latlon_box[..., 1]

    mask = (
        (bbox_lons.min() < da.lon)
        * (bbox_lons.max() > da.lon)
        * (bbox_lats.min() < da.lat)
        * (bbox_lats.max() > da.lat)
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
    if _has_spatial_coord(da=da, c="x") and _has_spatial_coord(da=da, c="y"):
        raise NotImplementedError
    if coords.on_latlon_aligned_grid(da):
        da_cropped = _crop_with_latlon_aligned_crid(
            domain=domain, da=da, pad_pct=pad_pct
        )
    elif coords.has_latlon_coords(da):
        da_cropped = _crop_with_latlon_aux_grid(domain=domain, da=da, pad_pct=pad_pct)
    elif "grid_mapping" in da.attrs:
        crs = parse_cf_crs(da)
        # the source data is stored in its own projection and so we want to
        # crop using the coordinates of this projection
        latlon_box = _latlon_box_to_integer_values(domain.latlon_bounds)
        xs, ys, _ = crs.transform_points(ccrs.PlateCarree(), *latlon_box.T).T
        x_min, x_max = np.min(xs), np.max(xs)
        y_min, y_max = np.min(ys), np.max(ys)
        x_range = [x_min, x_max]
        y_range = [y_min, y_max]
    else:
        raise NotImplementedError(da)

    return da_cropped
