"""
Utilities to create (approximate) regular Cartesian gridded data from lat/lon satelite data
"""
import itertools
import warnings

import cartopy.crs as ccrs
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import shapely.geometry as geom
import xarray as xr


class CartesianDomain:
    def __init__(self, l_meridional, l_zonal, x_c=0.0, y_c=0.0):
        self.l_meridional = l_meridional
        self.l_zonal = l_zonal
        self.x_c = x_c
        self.y_c = y_c

    @property
    def spatial_bounds(self):
        """
        The spatial distance bounds of the domain represented by the (x,y)
        position (in meters) of the four corners of the domain
        """
        corners_dir = list(itertools.product([1, -1], [1, -1]))
        corners_dir.insert(0, corners_dir.pop(2))

        corners = np.array([self.l_zonal / 2.0, self.l_meridional / 2.0]) * np.array(
            corners_dir
        )

        corners[..., 0] += self.x_c
        corners[..., 1] += self.y_c

        return corners

    @property
    def spatial_bounds_geometry(self):
        """return a shapely Geometry"""
        return geom.Polygon(self.spatial_bounds)

    def get_grid(self, dx):
        """
        Get an xarray Dataset containing the discrete positions (in meters)
        """
        # compute number of grid points first instead of using np.arange to
        # avoid floating point stepping not always giving the same number of
        # data points
        Nx = np.round(self.l_zonal / dx)
        Ny = np.round(self.l_meridional / dx)
        xmin = self.x_c - self.l_zonal / 2.0 + dx / 2.0
        ymin = self.y_c - self.l_meridional / 2.0 + dx / 2.0
        x_ = xmin + dx * np.arange(Nx)
        y_ = ymin + dx * np.arange(Ny)

        da_x = xr.DataArray(
            x_,
            attrs=dict(long_name="zonal distance", units="m"),
            dims=("x",),
        )
        da_y = xr.DataArray(
            y_,
            attrs=dict(long_name="meridional distance", units="m"),
            dims=("y",),
        )

        ds = xr.Dataset(coords=dict(x=da_x, y=da_y))

        return ds

    def get_grid_extent(self):
        """
        Return grid extent compatible with matplotlib.imshow
        [x0 ,x1, y0, y1] in Cartesian coordinates
        """
        return [
            self.x_c - self.l_zonal / 2.0,
            self.x_c + self.l_zonal / 2.0,
            self.y_c - self.l_meridional / 2.0,
            self.y_c + self.l_meridional / 2.0,
        ]

    def plot_outline(self, ax=None, alpha=0.6, set_ax_extent=False, **kwargs):
        if ax is None:
            fig_height = 4
            fig_width = fig_height * self.l_zonal / self.l_meridional
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            ax.margins(0.5)

        bounds_patch = mpatches.Rectangle(
            xy=[self.x_c - self.l_zonal / 2.0, self.y_c - self.l_meridional / 2.0],
            width=self.l_zonal,
            height=self.l_meridional,
            alpha=alpha,
            **kwargs,
        )
        ax.add_patch(bounds_patch)
        if set_ax_extent:
            extent = [
                self.x_c - self.l_zonal / 2.0,
                self.x_c + self.l_zonal / 2.0,
                self.y_c - self.l_meridional / 2.0,
                self.y_c + self.l_meridional / 2.0,
            ]
            ax.set_extent(extent)
        return ax

    def serialize(self):
        data = dict(
            x_c=float(self.x_c),
            y_c=float(self.y_c),
            l_zonal=float(self.l_zonal),
            l_meridional=float(self.l_meridional),
        )
        return data

    def validate_dataset(self, ds):
        """
        Ensure the required coordinates exist in the dataset for it to map
        to the defined domain
        """
        # TODO: might want to check for some cartesian coordinates here
        pass

    _str_print = ["x_c", "y_c", "l_zonal", "l_meridional"]

    def __str__(self):
        attrs = ", ".join(f"{s}={getattr(self, s):g}" for s in self._str_print)
        return f"{self.__class__.__name__}({attrs})"


class LocalCartesianDomain(CartesianDomain):
    """
    Domain representing the tangent plane projection centered at specific
    latitude and longitude
    """

    _str_print = [
        "x_c",
        "y_c",
        "l_zonal",
        "l_meridional",
        "central_latitude",
        "central_longitude",
    ]

    def __init__(
        self,
        central_latitude,
        central_longitude,
        l_meridional,
        l_zonal,
        x_c=0.0,
        y_c=0.0,
    ):
        super().__init__(l_meridional=l_meridional, l_zonal=l_zonal, x_c=x_c, y_c=y_c)
        self.central_latitude = central_latitude
        self.central_longitude = central_longitude

        self.crs = ccrs.LambertAzimuthalEqualArea(
            central_latitude=central_latitude, central_longitude=central_longitude
        )

    @property
    def latlon_bounds(self):
        """
        The spatial distance bounds of the domain represented by the (lat,lon)
        position (in degrees) of the four corners of the domain
        """
        corners = self.spatial_bounds
        latlon_pts = ccrs.PlateCarree().transform_points(
            x=corners[..., 0] - self.x_c,
            y=corners[..., 1] - self.y_c,
            src_crs=self.crs,
            z=np.zeros_like(corners[..., 0]),
        )

        return latlon_pts

    def latlon_from_xy(self, x, y):
        """
        Calculate the latlon coordinates from xy-coordinates in the domain
        """
        x = np.atleast_1d(x)
        y = np.atleast_1d(y)
        latlon_pts = ccrs.PlateCarree().transform_points(
            x=x, y=y, src_crs=self.crs, z=np.zeros_like(x)
        )

        return latlon_pts[..., 0], latlon_pts[..., 1]

    def get_grid(self, dx):
        """
        Get an xarray Dataset containing the discrete positions (in meters)
        with their lat/lon positions with grid resolution dx (in meters)
        """
        ds_grid_cart = super().get_grid(dx=dx)

        ds_grid = ds_grid_cart.copy()

        ds_grid["x"] = ds_grid.x - self.x_c
        ds_grid["y"] = ds_grid.y - self.y_c

        for c in "xy":
            ds_grid[c].attrs.update(ds_grid_cart[c].attrs)

        x, y = np.meshgrid(ds_grid.x, ds_grid.y, indexing="ij")
        lons, lats = self.latlon_from_xy(x=x, y=y)

        ds_grid["lon"] = xr.DataArray(
            lons,
            dims=("x", "y"),
            coords=dict(x=ds_grid.x, y=ds_grid.y),
            attrs=dict(standard_name="grid_longitude", units="degree"),
        )
        ds_grid["lat"] = xr.DataArray(
            lats,
            dims=("x", "y"),
            coords=dict(x=ds_grid.x, y=ds_grid.y),
            attrs=dict(standard_name="grid_latitude", units="degree"),
        )

        # the (x,y)-positions are only approximate with the projection
        for c in ["x", "y"]:
            ds_grid[c].attrs["long_name"] = (
                "approximate " + ds_grid[c].attrs["long_name"]
            )

        ds_grid.attrs["crs"] = self.crs

        return ds_grid

    def plot_outline(self, ax=None, alpha=0.6, set_ax_extent=False, **kwargs):
        if ax is None:
            fig_height = 4
            fig_width = fig_height * self.l_zonal / self.l_meridional
            fig, ax = plt.subplots(
                figsize=(fig_width, fig_height), subplot_kw=dict(projection=self.crs)
            )
            ax.gridlines(linestyle="--", draw_labels=True)
            ax.coastlines(resolution="10m", color="grey")
            ax.margins(0.5)
        else:
            if getattr(ax, "projection").__class__ != self.crs.__class__:
                warnings.warn(
                    "The outline plot uses a rectangular patch the edges of which"
                    f" are not currently correctly projected unless the {self.crs.__class__.__name__}"
                    " projection is used for the axes"
                )
            pass

        bounds_patch = mpatches.Rectangle(
            xy=[-self.l_zonal / 2.0, -self.l_meridional / 2.0],
            width=self.l_zonal,
            height=self.l_meridional,
            alpha=alpha,
            transform=self.crs,
            **kwargs,
        )
        ax.add_patch(bounds_patch)
        if set_ax_extent:
            pad = 1.2
            extent = [
                self.x_c - pad * self.l_zonal / 2.0,
                self.x_c + pad * self.l_zonal / 2.0,
                self.y_c - pad * self.l_meridional / 2.0,
                self.y_c + pad * self.l_meridional / 2.0,
            ]
            ax.set_extent(extent, crs=self.crs)
        return ax

    def serialize(self):
        data = super().serialize()
        data["central_latitude"] = float(self.central_latitude)
        data["central_longitude"] = float(self.central_longitude)
        return data

    def validate_dataset(self, ds):
        """
        Ensure the required coordinates exist in the dataset for it to map
        to the defined domain
        """
        required_coords = ["lat", "lon"]
        missing_coords = list(filter(lambda c: c not in ds.coords, required_coords))
        if len(missing_coords) > 0:
            raise Exception(
                "The provided dataset is missing the following coordinates "
                f"`{', '.join(missing_coords)}` which are required to make the "
                f" dataset valid for a{self.__class__.__name__} domain"
            )


def deserialise_domain(data):
    if "central_longitude" in data and "central_latitude" in data:
        return LocalCartesianDomain(**data)
    else:
        return CartesianDomain(**data)
