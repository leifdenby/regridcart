"""
interface for using xesmf interpolation backend
"""
import warnings
from pathlib import Path

import xesmf
from xesmf.backend import esmf_regrid_build, esmf_regrid_finalize


class SilentRegridder(xesmf.Regridder):
    """
    Wrapper class for xesmf regridder which doesn't print logging info to console
    """

    def _write_weight_file(self):
        if Path(self.filename).exists():
            if self.reuse_weights:
                return  # do not compute it again, just read it
            else:
                Path(self.filename).unlink()

        regrid = esmf_regrid_build(
            self._grid_in, self._grid_out, self.method, filename=self.filename
        )
        esmf_regrid_finalize(regrid)  # only need weights, not regrid object


def _save_weights(da, new_grid, regridder_tmpdir, method):
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


def resample(da, old_grid, new_grid, method, keep_attrs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regridder = xesmf.Regridder(
            ds_in=old_grid,
            ds_out=new_grid,
            method=method,
        )
        da_resampled = regridder(da)

    da_resampled = regridder(da)

    # add cartesian coordinates to regridded data
    da_resampled["x"] = new_grid.x
    da_resampled["y"] = new_grid.y

    # for plotting later using the grid's transform (crs) the y-coordinates
    # must be first
    da_resampled = da_resampled.transpose(..., "y", "x")

    return da_resampled
