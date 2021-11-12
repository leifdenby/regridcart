# `regridcart` Regridding lat/lon to local Cartesian coordinates

This package takes care of regridding data defined with latitude/longitude
coordinates onto a local Cartesian grid of a fixed resolution. To use it you
simply define the domain you want to regrid onto and then call the `resample`
method.

## Usage

```python
import regridcart as rc
import xaray as xr

da_src = xr.open_dataarray("...")

target_domain = rc.LocalCartesianDomain(
    central_latitude=lat0,
    central_longitude=lon0,
    l_meridional=1000.0e3,
    l_zonal=3000.0e3,
)

dx = 1.0e3 # new resoluion 1km
da_regridded = rc.resample(target_domain, da=da_src, dx=dx)
```

The provided data-array is assumed to have latitude/longitude
coordinates defined by one of the following:

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

The package also implements cropping (`rc.crop_field_to_domain`), plotting
domain outline (`domain.plot_outline`) and can also with data already on a
Cartesian grid with `rc.CartesianDomain`. See
[notebooks/examples.ipynb](notebooks/examples.ipynb) for detailed examples.


# Installation

`regridcart` can be installed with `pip` from [pypi](https://pypi.org/), but it
relies on `cartopy` and `xesmf` which in turn rely on `proj` and `emsf`, these
can most easily be installed with
[conda](https://docs.conda.io/en/latest/miniconda.html#installing):


```bash
conda install xarray cartopy xesmf -c conda-forge
pip install regridcart
```
