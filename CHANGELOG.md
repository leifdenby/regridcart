# Changelog


## [Unreleased](https://github.com/leifdenby/regridcart/tree/HEAD)

[Full Changelog](https://github.com/leifdenby/regridcart/compare/v0.1.0...)

*bugfixes*

- Add support for coordinates where lat/lon positions are given in integers
  rather than floats [\#12](https://github.com/leifdenby/regridcart/pull/12)


## [v0.1.0](https://github.com/leifdenby/regridcart/tree/v0.1.0)

[Full Changelog](https://github.com/leifdenby/regridcart/compare/...v0.1.0)

First tagged release with support for cropping and regridding data on lat/lon
grids. Support for lat/lon grid defined by either 1) coordinate aligned grids
(1D coordinate arrays), 2) lat/lon coordinate given for each point separately
(e.g. 2D position arrays), 3) through CF-compliant projection info or 4)
parsable with `rasterio` package.
