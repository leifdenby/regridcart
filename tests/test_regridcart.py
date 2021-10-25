import numpy as np
import regridcart as rc
import xarray as xr
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
    target_domain = rc.LocalCartesianDomain(
        central_latitude=14.0,
        central_longitude=-48,
        l_meridional=1000.0e3,
        l_zonal=3000.0e3,
    )

    dlat, dlon = 0.1, 0.1
    lat_span = [5.0, 20.0]
    lon_span = [-70.0, -30.0]

    lat0 = 0.5 * (lat_span[0] + lat_span[1])
    lon0 = 0.5 * (lon_span[0] + lon_span[1])

    lats = np.arange(*lat_span, dlat)
    lons = np.arange(*lon_span, dlon)

    ds = xr.Dataset(coords=dict(lat=lats, lon=lons))

    # make a field to interpolate
    ds["phi"] = np.sin(ds.lat) * np.cos(ds.lon)

    da_phi = ds.phi
    da_phi_cropped = rc.crop_field_to_domain(
        domain=target_domain, da=da_phi, pad_pct=0.0
    )

    dx = 50.0e3  # [m]
    da_phi_resampled = rc.resample(target_domain, da=da_phi_cropped, dx=dx)
