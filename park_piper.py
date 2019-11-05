###############
## LIBRARIES ##
###############
import click
from copy import deepcopy
from pprint import pprint

from arcgis.gis import GIS
from arcgis import features
import geopandas as gpd

##################
##  FUNCTION(S) ##
##################
def agol_to_gdf(fset):
    gdf = gpd.read_file(fset.to_geojson)
    gdf.crs = {'init': f'epsg:{fset.spatial_reference["latestWkid"]}'}
    gdf['geometry'] = gdf['geometry'].to_crs(epsg = 4326)
    return gdf

def park_piper(gis, piper_item, piper_layer, piper_feature_id_field, piper_update_field, parks_item, parks_layer, parks_transfer_field):

    # Parks
    parks_flayer = gis.content.get(parks_item).layers[parks_layer]
    parks_fset = parks_flayer.query()
    parks_gdf = agol_to_gdf(parks_fset)

    # Piper features
    piper_flayer = gis.content.get(piper_item).layers[piper_layer]
    ## Create a featureset of the full piper dataset
    piper_full_fset = piper_flayer.query()
    ## Create a featureset and GeoDataFrame of the features that will be updated
    piper_to_update_fset = piper_flayer.query(where = f"{piper_update_field} IS NULL")
    try:
        piper_to_update_gdf = agol_to_gdf(piper_to_update_fset)
        # Assign parks to piper points that need to be updated
        piper_to_update_gdf[piper_update_field] = piper_to_update_gdf.apply(lambda x: parks_gdf.loc[parks_gdf['geometry'].contains(x['geometry'])][parks_transfer_field].iloc[0] if len(parks_gdf.loc[parks_gdf['geometry'].contains(x['geometry'])]) > 0 else "Park Unknown", axis = 1)

        features_for_update = []
        all_features = piper_full_fset.features

        for id in piper_to_update_gdf[piper_feature_id_field]:
            original_feature = [f for f in all_features if f.attributes[piper_feature_id_field] == id][0]
            feature_to_be_updated = deepcopy(original_feature)
            print(f'------------- {id} -------------')
            matching_row = piper_to_update_gdf.loc[piper_to_update_gdf[piper_feature_id_field] == id]
            print(id, ' >>> ', matching_row)
            feature_to_be_updated.attributes[piper_update_field] = matching_row[piper_update_field].values[0]
            features_for_update.append(feature_to_be_updated)

        print(features_for_update)
        piper_flayer.edit_features(updates = features_for_update)
    except Exception as e:
        print(e)
        pass


@click.command()
@click.argument('portal')
@click.argument('username')
@click.argument('password')
@click.option('--piper_item', help = 'Item ID of piper item on ArcGIS Online')
@click.option('--piper_layer', default = 0, show_default = True, help = 'Layer number in service being updated')
@click.option('--piper_feature_id_field', default = 'OBJECTID', show_default = True, help = 'Unique ID field for piper layer')
@click.option('--piper_update_field', default = 'NAME', show_default = True, help = 'Field in piper layer to update')
@click.option('--parks_item', help = 'Item ID of parks item on ArcGIS Online')
@click.option('--parks_layer', default = 0, show_default = True, help = 'Layer number in parks servce')
@click.option('--parks_transfer_field', default = 'NAME', show_default = True, help = 'Field in parks layer to transfer over to piper update field')
def main(portal, username, password, piper_item, piper_layer, piper_feature_id_field, piper_update_field, parks_item, parks_layer, parks_transfer_field):
    gis = GIS(portal, username, password)
    park_piper(gis, piper_item, piper_layer, piper_feature_id_field, piper_update_field, parks_item, parks_layer, parks_transfer_field)


if __name__ == "__main__":
    main()