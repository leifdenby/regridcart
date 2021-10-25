import cartopy.crs as ccrs
import xesmf

try:
    import rioxarray  # ensures xr.DataArray.rio is available

    HAS_RIO = True
except ImportError:
    HAS_RIO = False
import os
import warnings
from pathlib import Path

import numpy as np
import xarray as xr
from xesmf.backend import esmf_regrid_build, esmf_regrid_finalize

from .domain import LocalCartesianDomain


class SilentRegridder(xesmf.Regridder):
    def _write_weight_file(self):
        if os.path.exists(self.filename):
            if self.reuse_weights:
                return  # do not compute it again, just read it
            else:
                os.remove(self.filename)

        regrid = esmf_regrid_build(
            self._grid_in, self._grid_out, self.method, filename=self.filename
        )
        esmf_regrid_finalize(regrid)  # only need weights, not regrid object


def _on_latlon_grid(da):
    if "lat" in da.coords or "lon" in da.coords:
        return True
    elif "lat" in da.data_vars or "lon" in da.data_vars:
        return True

    pass


def _on_cartesian_grid(da):
    pass


def _save_weights():

    Nx_in, Ny_in = da.x.shape[0], da.y.shape[0]
    Nx_out, Ny_out = int(new_grid.x.count()), int(new_grid.y.count())

    regridder_weights_fn = "{method}_{Ny_in}x{Nx_in}_{Ny_out}x{Nx_out}" ".nc".format(
        method=method,
        Ny_in=Ny_in,
        Nx_in=Nx_in,
        Nx_out=Nx_out,
        Ny_out=Ny_out,
    )

    Path(regridder_tmpdir).mkdir(exist_ok=True, parents=True)
    regridder_weights_fn = str(regridder_tmpdir / regridder_weights_fn)


def resample(
    domain,
    da,
    dx,
    method="bilinear",
    crop_pad_pct=0.1,
    keep_attrs=False,
    regridder_tmpdir=Path("/tmp/regridding"),
    src_crs=None,
):
    """
    Resample a xarray DataArray onto this tile with grid made of NxN points

    cartesian -> cartsian
    latlon with crs -> latlon
    latlon -> latlon
    """
    using_crs = False

    if "lat" in da.coords and "lon" in da.coords:
        coords = {}
        coords["lat"] = da.coords["lat"]
        coords["lon"] = da.coords["lon"]
        old_grid = xr.Dataset(coords=coords)
        new_grid = domain.get_grid(dx=dx)
    else:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regridder = SilentRegridder(
            # filename=regridder_weights_fn,
            # reuse_weights=True,
            ds_in=old_grid,
            ds_out=new_grid,
            method=method,
        )

    da_resampled = regridder(da)

    # add cartesian coordinates to regridded data
    da_resampled["x"] = new_grid.x
    da_resampled["y"] = new_grid.y

    # for plotting later using the grid's transform (crs) the y-coordinates
    # must be first
    da_resampled = da_resampled.transpose(..., "y", "x")

    if keep_attrs:
        da_resampled.attrs.update(da.attrs)

    return da_resampled

    if src_crs is None:
        src_crs = getattr(da.rio, "crs")

    if isinstance(domain, LocalCartesianDomain) and src_crs is None:
        raise Exception(
            "The provided DataArray doesn't have a "
            "projection provided. Please provide the source transform with `src_crs`"
        )

    if src_crs is not None:
        if not ("lat" in new_grid and "lon" in new_grid):
            raise Exception(
                "The provided source-data is on a lat/lon grid. "
                "Please define a new local Cartesian domain to project this "
                "into by defining `l_zonal`, `l_meridional`, `central_latitude` "
                "and `central_longitude` in the `domain` section of the meta "
                "information."
            )

        latlon_old = ccrs.PlateCarree().transform_points(
            src_crs,
            *np.meshgrid(da.x.values, da.y.values),
        )[:, :, :2]

        old_grid["lat"] = (("y", "x"), latlon_old[..., 1])
        old_grid["lon"] = (("y", "x"), latlon_old[..., 0])

    else:
        new_grid = domain.get_grid(dx=dx)
        da_resampled = da.interp_like(new_grid)


def get_pyresample_area_def(N, domain):
    """
    When using satpy scenes we're better off using pyresample instead of
    xesmf since it appears faster (I think because it uses dask)
    """
    from pyresample import geometry

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
