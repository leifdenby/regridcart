# Changelog


## [Unreleased](https://github.com/leifdenby/regridcart/tree/HEAD)

[Full Changelog](https://github.com/leifdenby/regridcart/compare/v0.1.0...)

*enhancements*

- Check to ensure that source data is inside region being cropped/regridded to.
  [\#13](https://github.com/leifdenby/regridcart/pull/13)

*bugfixes*

- Because of float rounding issues when providing the grid-spacing as a float
  the resulting grid sometimes had one fewer grid-points than expected. This
  commit resolves this issue by rounding to the nearest integer when working
  out how many grid-points to produce when regridding.
  [\#16](https://github.com/leifdenby/regridcart/pull/16)

- Add support for coordinates where lat/lon positions are given in integers
  rather than floats [\#12](https://github.com/leifdenby/regridcart/pull/12)

*maintenance*

- add ci action to automatically publish new releases on pypi
  [\#17](https://github.com/leifdenby/regridcart/pull/17)


## [v0.1.0](https://github.com/leifdenby/regridcart/tree/v0.1.0)

[Full Changelog](https://github.com/leifdenby/regridcart/compare/...v0.1.0)

First tagged release with support for cropping and regridding data on lat/lon
grids. Support for lat/lon grid defined by either 1) coordinate aligned grids
(1D coordinate arrays), 2) lat/lon coordinate given for each point separately
(e.g. 2D position arrays), 3) through CF-compliant projection info or 4)
parsable with `rasterio` package.
