import numpy as np
import xarray as xr

import regridcart as rc
from regridcart import __version__


def test_version():
    assert __version__ == "0.1.0"


def test_latlon_aligned_data():
    """
    Test cropping and resampling of data with x- and y-coordinates given by
    longitude and latitude values respecively (i.e. the underlying grid
    coordinates follow the latitude and longitude directions)
    """
    # TODO: add test to ensure the resampling values are correct instead of
    # just ensuring that no exceptions are raised

    dlat, dlon = 0.1, 0.1
    lat_span = [5.0, 20.0]
    lon_span = [-70.0, -30.0]

    lat0 = 0.5 * (lat_span[0] + lat_span[1])
    lon0 = 0.5 * (lon_span[0] + lon_span[1])

    target_domain = rc.LocalCartesianDomain(
        central_latitude=lat0,
        central_longitude=lon0,
        l_meridional=1000.0e3,
        l_zonal=3000.0e3,
    )

    lats = np.arange(*lat_span, dlat)
    lons = np.arange(*lon_span, dlon)

    ds = xr.Dataset(coords=dict(lat=lats, lon=lons))

    # make a field to interpolate
    ds["phi"] = np.sin(ds.lat) * np.cos(ds.lon)

    da_phi = ds.phi
    da_phi_cropped = rc.crop_field_to_domain(domain=target_domain, da=da_phi)

    dx = 50.0e3  # [m]
    da_phi_resampled = rc.resample(target_domain, da=da_phi_cropped, dx=dx)
    assert da_phi_resampled is not None


def test_latlon_aux_coord_data():
    """
    Test cropping and resample where the data isn't given on a grid which is
    lat/lon aligned, but rather the latitudes and longitudes are given with
    auxilliary variables
    """
    target_domain = rc.LocalCartesianDomain(
        central_latitude=14.0,
        central_longitude=-48,
        l_meridional=1000.0e3,
        l_zonal=3000.0e3,
    )

    # generate some sample data on a regular lat/lon grid
    ds = xr.Dataset(
        coords=dict(x=np.arange(-20.0, 20.0, 0.5), y=np.arange(-10.0, 10.0, 0.5))
    )

    # the lat/lon coords will be simply given as rotations here
    theta = 20.0 * 3.14 / 180.0
    ds.coords["lon"] = np.cos(theta) * ds.x - np.sin(theta) * ds.y - 48.0
    ds.coords["lat"] = np.sin(theta) * ds.x + np.cos(theta) * ds.y + 14.0

    ds["phi"] = np.cos(ds.x / 4.0) * np.sin(ds.y)

    da_phi = ds.phi
    da_phi_cropped = rc.crop_field_to_domain(
        domain=target_domain, da=da_phi, pad_pct=0.0
    )

    dx = 50.0e3  # [m]
    Nx = np.round(target_domain.l_zonal / dx)
    Ny = np.round(target_domain.l_meridional / dx)
    da_phi_resampled = rc.resample(target_domain, da=da_phi_cropped, dx=dx)
    assert da_phi_resampled.x.count() == Nx
    assert da_phi_resampled.y.count() == Ny
