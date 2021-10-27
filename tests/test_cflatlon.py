import worldview_dl
import datetime
import pytz
import rioxarray as rxr
import regridcart as rc
import xarray as xr
import io
import urllib
from regridcart.coords import get_latlon_coords_using_crs


def test_raster_crs():
    t_now = datetime.datetime.now().replace(tzinfo=pytz.utc)
    t = t_now - datetime.timedelta(hours=2)

    fn_image = "GOES_test.tiff"

    worldview_dl.download_image(
        fn=fn_image,
        time=t,
        bbox=[10.0, -60.0, 15.0, -50.0],  # SWNE
        layers=["GOES-East_ABI_Band2_Red_Visible_1km"],
        image_format=fn_image.split(".")[-1],
        resolution=0.01,
    )

    target_domain = rc.LocalCartesianDomain(
        central_latitude=12.0,
        central_longitude=-55.0,
        l_meridional=100.0e3,
        l_zonal=200.0e3,
    )

    da = rxr.open_rasterio(fn_image)

    da_cropped = rc.crop_field_to_domain(domain=target_domain, da=da, pad_pct=0.0)

    dx = 10.0e3  # [m]
    da_resampled = rc.resample(target_domain, da=da_cropped, dx=dx)
    assert da_resampled is not None


def test_goes16_crs():
    url = "http://noaa-goes16.s3.amazonaws.com/ABI-L2-ACHAF/2021/001/15/OR_ABI-L2-ACHAF-M6_G16_s20210011520211_e20210011529519_c20210011530561.nc"

    req = urllib.request.Request(url)

    with urllib.request.urlopen(req) as resp:
        ds = xr.open_dataset(io.BytesIO(resp.read()))
        da = ds.HT
        da.coords[da.grid_mapping] = ds[da.grid_mapping]

        for k, v in da.coords[da.grid_mapping].attrs.items():
            try:
                da.coords[da.grid_mapping].attrs[k] = float(v)
            except ValueError:
                pass

    target_domain = rc.LocalCartesianDomain(
        central_latitude=12.0,
        central_longitude=-55.0,
        l_meridional=100.0e3,
        l_zonal=200.0e3,
    )

    da_cropped = rc.crop_field_to_domain(domain=target_domain, da=da, pad_pct=0.0)

    dx = 10.0e3  # [m]
    da_resampled = rc.resample(target_domain, da=da_cropped, dx=dx)
    assert da_resampled is not None
