import numpy as np
import pytest
from shapely.geometry import shape

try:
    from rasterio.transform import Affine
    import rasterio.crs
    _HAS_RASTERIO = True
except ImportError:
    _HAS_RASTERIO = False

from src.postprocessing.polygon import mask_to_polygons


@pytest.mark.skipif(not _HAS_RASTERIO, reason="rasterio required for CRS reprojection tests")
def test_mask_to_polygons_epsg4326():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:60, 20:60] = 1

    # Transform in degrees: origin (75.0, 10.0), pixel size 0.001 deg
    transform = Affine.translation(75.0, 10.0) * Affine.scale(0.001, -0.001)
    crs = rasterio.crs.CRS.from_epsg(4326)

    polys = mask_to_polygons(mask, transform=transform, crs=crs)
    assert len(polys) == 1

    entry = polys[0]
    assert "polygon_geojson_geo" in entry
    assert "centroid_geo" in entry
    assert entry["area_m2_approx"] is not None
    assert entry["area_m2_approx"] > 0

    lon, lat = entry["centroid_geo"]
    assert 75.0 <= lon <= 75.1
    assert 9.9 <= lat <= 10.0


@pytest.mark.skipif(not _HAS_RASTERIO, reason="rasterio required for CRS reprojection tests")
def test_mask_to_polygons_projected_utm_reprojects_to_4326():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:60, 20:60] = 1

    # Transform in UTM Zone 43N meters (Arabian Sea / West Coast of India)
    # origin easting=500000m, northing=1000000m, pixel size 10m
    transform = Affine.translation(500000.0, 1000000.0) * Affine.scale(10.0, -10.0)
    crs = rasterio.crs.CRS.from_epsg(32643)

    polys = mask_to_polygons(mask, transform=transform, crs=crs)
    assert len(polys) == 1

    entry = polys[0]
    assert entry["polygon_geojson_geo"] is not None

    geo_shape = shape(entry["polygon_geojson_geo"])
    # Verify coordinates are geographic longitude / latitude (EPSG:4326)
    minx, miny, maxx, maxy = geo_shape.bounds
    assert -180.0 <= minx <= 180.0
    assert -90.0 <= miny <= 90.0
    assert 74.0 <= minx <= 76.0  # Approx UTM Zone 43N longitude
    assert 8.0 <= miny <= 10.0   # Approx latitude

    # Centroid in degrees
    lon, lat = entry["centroid_geo"]
    assert 74.0 <= lon <= 76.0
    assert 8.0 <= lat <= 10.0

    # Area in m2 from projected raster
    assert entry["area_m2_approx"] > 0
    # 40x40 pixels * (10m x 10m) = ~160,000 m2
    assert 100_000 <= entry["area_m2_approx"] <= 200_000
