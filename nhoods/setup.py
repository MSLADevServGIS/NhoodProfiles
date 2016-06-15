# Setup procedures -- WIP

import os
import re

import arcpy

arcpy.env.workspace = "in_memory"
# TODO: out_gdb = "//cityfiles/DEVServices/WallyG/projects/NhoodProfiles/nhoods/data/NhoodAmenities.gdb/MtStatePlane"

# DATA PROCESSING

# Nhood_buffers:
arcpy.Buffer_analysis("Nhoods", "nhood_buffers",
                      buffer_distance_or_field="100 Feet",
                      line_side="FULL", line_end_type="ROUND",
                      dissolve_option="LIST", dissolve_field="Name",
                      method="PLANAR")

# Parks:

parks = os.path.join(
    r"\\cityfiles\Shared\PARKS AND RECREATION SHARED\GIS Data",
    r"Parks Data.gdb\Parks")

arcpy.FeatureClassToFeatureClass_conversion(parks, "in_memory", "mem_parks")

# Delete Parks Fields
arcpy.DeleteField_management("mem_parks", drop_field="Reference;Rec_Date;Doc_Links;Subtype;Ownership;Origin;Maintenance;Platted_Size;Maint_Level;Status;Assessors_Parcel_No;Acres;Dev_Status;Owner_Type;Maint_Responsibility;Shape_Length;Shape_Area")


# COMMON AREAS

CAMA = r"W:\DATA\CAMA\Missoula\MissoulaOwnerParcel_shp\MissoulaOwnerParcel_shp.shp"

arcpy.Select_analysis(CAMA, "in_memory/mem_commons", '''"LegalDescr" LIKE
\'%COMMON%\'''')

# make new field "CAName"
arcpy.AddField_management("mem_commons", "CAName", "TEXT", "", "", 50)

with arcpy.da.UpdateCursor("mem_commons", ["LegalDescr", "CAName"]) as cur:
    for row in cur:
        row[1] = re.split("\W\s", row[0])[0].strip().title()
        cur.updateRow(row)


arcpy.Dissolve_management(in_features="mem_commons", out_feature_class="in_memory/mem_commons_Diss", dissolve_field="CAName", statistics_fields="", multi_part="SINGLE_PART", unsplit_lines="DISSOLVE_LINES")

# Merge

