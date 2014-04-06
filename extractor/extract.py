#!/usr/bin/python2
# -*- coding: utf-8 -*-
import logging
import logging.config

import rtree
import shapely.wkb
from shapely.prepared import prep

from exposm.settings import settings, admin_levels

# setup logging, has to be after osmext.settings
logging.config.dictConfig(settings.get('logging'))
logger = logging.getLogger(__file__)

from exposm.writer import AdminLevelWriter
from exposm.reader import AdminLevelReader
from exposm.utils import osm_id_exists, check_bad_geom, intersect_geom


def main():
    # setup index
    spat_index_0 = rtree.index.Index()
    # extract countries
    admin_level_0 = {}

    lyr_save = AdminLevelWriter('/tmp/out/admin_level_0.shp')
    lyr_read = AdminLevelReader(settings.get('sources').get('osm_data_file'))

    feature_id = 0

    logger.info('Started exporting admin_level_0 boundaries!')

    for feature in lyr_read.readData():

        # get data
        osm_id = feature.GetField('osm_id')
        admin_level = feature.GetField('admin_level')
        name = feature.GetField('name')
        name_en = feature.GetField('name:en')
        geom_raw = feature.GetGeometryRef()

        bad_geom = check_bad_geom(geom_raw, osm_id)
        # BONKERS features usually crash QGIS, we need to skip those
        if bad_geom or not(osm_id_exists(osm_id, name)):
            # skip further processing
            continue

        geom = shapely.wkb.loads(geom_raw.ExportToWkb())

        # process national level boundary
        if admin_level == '2':
            feature_data = [
                ('osm_id', osm_id),
                ('name', name),
                ('name_en', name_en),
                ('adminlevel', admin_level),
                ('is_in', None)
            ]
            lyr_save.saveFeature(feature_data, geom_raw)
            admin_level_0.update({feature_id: (osm_id, prep(geom))})

            spat_index_0.insert(feature_id, geom.envelope.bounds)
            logger.debug('Index %s, record %s', feature_id, osm_id)

            feature_id += 1

    lyr_read.datasource.Destroy()
    lyr_save.datasource.Destroy()

    # extract states
    admin_level_1 = {}
    # create index
    spat_index_1 = rtree.index.Index()

    feature_id = 0

    lyr_save = AdminLevelWriter('/tmp/out/admin_level_1.shp')
    lyr_read = AdminLevelReader(settings.get('sources').get('osm_data_file'))

    for feature in lyr_read.readData():

        osm_id = feature.GetField('osm_id')
        admin_level = feature.GetField('admin_level')
        name = feature.GetField('name')
        name_en = feature.GetField('name:en')
        geom_raw = feature.GetGeometryRef()

        bad_geom = check_bad_geom(geom_raw, osm_id)
        # BONKERS features usually crash QGIS, we need to skip those
        # osm_id is crucial for establishing feature relationship
        if bad_geom or not(osm_id_exists(osm_id, name)):
            continue

        geom = shapely.wkb.loads(geom_raw.ExportToWkb())

        # check spatial relationship
        # representative point is guaranteed within polygon
        geom_repr = geom.representative_point()
        # check index intersection

        is_in = intersect_geom(geom_repr, spat_index_0, admin_level_0, osm_id)

        # check for specific admin level mapping
        if is_in in admin_levels.get('per_country'):
            search_admin_level = (
                admin_levels.get('per_country')
                .get(is_in)
                .get('admin_level_1')
            )
            logger.info(
                'Using custom admin_level for %s (%s)',
                admin_levels.get('per_country')
                .get(is_in).get('meta').get('name'), is_in
            )
        else:
            search_admin_level = (
                admin_levels.get('default').get('admin_level_1')
            )

        # check current feature admin level
        if admin_level == str(search_admin_level):

            feature_data = [
                ('osm_id', osm_id),
                ('name', name),
                ('name_en', name_en),
                ('adminlevel', admin_level),
                ('is_in', is_in)
            ]
            lyr_save.saveFeature(feature_data, geom_raw)

            admin_level_1.update({feature_id: (osm_id, prep(geom))})

            spat_index_1.insert(feature_id, geom.envelope.bounds)
            logger.debug('Index %s, record %s', feature_id, osm_id)

            feature_id += 1

    lyr_read.datasource.Destroy()
    lyr_save.datasource.Destroy()

    # extract counties
    lyr_save = AdminLevelWriter('/tmp/out/admin_level_2.shp')
    lyr_read = AdminLevelReader(settings.get('sources').get('osm_data_file'))

    for feature in lyr_read.readData():

        osm_id = feature.GetField('osm_id')
        admin_level = feature.GetField('admin_level')
        name = feature.GetField('name')
        name_en = feature.GetField('name:en')
        geom_raw = feature.GetGeometryRef()

        bad_geom = check_bad_geom(geom_raw, osm_id)
        # BONKERS features usually crash QGIS, we need to skip those
        if bad_geom or not(osm_id_exists(osm_id, name)):
            # skip further processing
            continue

        geom = shapely.wkb.loads(geom_raw.ExportToWkb())

        # representative point is guaranteed within polygon
        geom_repr = geom.representative_point()
        # check index intersection
        is_in = intersect_geom(
            geom_repr, spat_index_0, admin_level_0, osm_id
        )

        is_in_state = intersect_geom(
            geom_repr, spat_index_1, admin_level_1, osm_id
        )

        # check for specific admin level mapping
        if is_in in admin_levels.get('per_country'):
            search_admin_level = (
                admin_levels.get('per_country')
                .get(is_in)
                .get('admin_level_2')
            )
            logger.info(
                'Using custom admin_level for %s (%s)',
                admin_levels.get('per_country')
                .get(is_in).get('meta').get('name'), is_in
            )
        else:
            search_admin_level = (
                admin_levels.get('default').get('admin_level_2')
            )

        # check current feature admin level
        if admin_level == str(search_admin_level):
            feature_data = [
                ('osm_id', osm_id),
                ('name', name),
                ('name_en', name_en),
                ('adminlevel', admin_level),
                ('is_in', is_in_state)
            ]
            lyr_save.saveFeature(feature_data, geom_raw)

    lyr_read.datasource.Destroy()
    lyr_save.datasource.Destroy()


if __name__ == '__main__':
    main()
