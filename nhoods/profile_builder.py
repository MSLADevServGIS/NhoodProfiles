#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Neighborhood Profiler Script
Garin Wally; Feb-April 2016

This script uses an mxd map template to query neighborhood information, places
that info into an HTML template, and finally kicks those HTML files out to PDF.

This script relies on up-to-date data that is managed manually
and is described in the NhoodProfile_Documentation.docx file.

Simply double-click the script file to run.
"""

# TODO: better error handling

from __future__ import print_function
import os
import sys
from datetime import datetime
from glob import glob
from re import sub
from time import sleep

# import arcpy # -- moved due to issues with datetime, see below
import pandas as pd
from jinja2 import Environment, FileSystemLoader

# Custom libs
from tkit import cli
sys.path.insert(0, r"\\cityfiles\DEVServices\WallyG\Scripts\conversion")
import pdftools  # noqa


# Print part of the info message above
print(__doc__.split("\n\n")[0])
print("\nExecuting...\n")

status = cli.StatusLine()


# =============================================================================
# PARAMETERS

status.write("Setting parameters...")
year = datetime.now().year  # TIL arcpy botches up the datetime module import
import arcpy  # noqa

# Project directory
nhood_dir = r"\\cityfiles\DEVServices\WallyG\projects\NhoodProfiles\nhoods"

# Template names (MUST be saved in "templates" folder)
profile_template = "profile_template.html"
map_template = "nhood_template.mxd"

wards_dir = os.path.join(nhood_dir, "data", "WardReps.csv")
guides_dir = os.path.join(nhood_dir, "data", "GuidingDocs.xlsx")
desc_dir = os.path.join(nhood_dir, "descriptions")
profile_dir = os.path.join(nhood_dir, "profiles")
template_dir = os.path.join(nhood_dir, "templates")


_all_dirs = [nhood_dir, wards_dir, desc_dir, profile_dir, template_dir]

status.success()


# =============================================================================
# FUNCTIONS


def query_assets(layer_name, name_field):
    """Gets names of features that "INTERSECT" nhood_buffers.

    Args:
        layer_name (str): the name of the layer to be queried.
        name_field (str): field name of feature containing name attributes.
    Returns:
        A string of names seperated by an HTML break <br> (newline).
    """
    arcpy.SelectLayerByLocation_management(
        layers[layer_name], "INTERSECT", layers["nhood_buffers"], "",
        "NEW_SELECTION")
    assets = set([n[0] for n in arcpy.da.SearchCursor(layers[layer_name],
                  name_field)])
    arcpy.SelectLayerByAttribute_management(layers[layer_name],
                                            "CLEAR_SELECTION")
    if None in assets:
        assets.remove(None)
    if "" in assets:
        assets.remove("")
    if not assets:
        return "None"
    assets = list(assets)
    assets.sort()
    return "<br>".join(assets)


def query_nhood(field):
    """Queries attributes of the neighborhood feature.

        Args:
            field (str): the field name of attributes to be queried.
        Returns a string-ified list.
    """
    return str([row[0] for row in arcpy.da.SearchCursor(layers["Nhoods"],
                field)][0])


def get_trail_mi():
    """Queries the trail miles within a neighborhood.

    Manually pre-process trail data:
    1) Get trails from City of Missoula Parks
    2) Run intersect on the 'trails' and 'nhoods' with the output 'Line'
    3) Add that output data to the database and map template
    4) Re-calculate trail length in Miles
    """
    arcpy.SelectLayerByLocation_management(
        layers["Trails"], "WITHIN", layers["Nhoods"], "", "NEW_SELECTION")
    mi = round(sum([float(row[0]) for row in
                    arcpy.da.SearchCursor(layers["Trails"],
                                          "trail_miles")]), 1)
    arcpy.SelectLayerByAttribute_management(layers["Trails"],
                                            "CLEAR_SELECTION")
    return mi


def get_guidedocs(nhood_name):
    """Looks for neighborhood names in the open GuideDocs spreadsheet."""
    # Format for linking the plan name to the plan document on the web
    url = '<a href="{1}" title="{0}">{0}</a>'
    ndocs = []
    for doc, nhoods in guide_docs.iteritems():
        if nhood_name in list(nhoods):
            if urls[doc] is not pd.np.nan:
                ndocs.append(url.format(doc, urls[doc]))
            else:
                ndocs.append(doc)
    if not ndocs:
        return "None"
    return "<br>".join(ndocs)


def get_population():
    """Queries the census block population within the neighborhood."""
    arcpy.SelectLayerByLocation_management(
        layers["Blocks"], "HAVE_THEIR_CENTER_IN",
        layers["Nhoods"], "", "NEW_SELECTION")
    pop = int(sum([float(row[0]) for row in
                   arcpy.da.SearchCursor(layers["Blocks"], "TOTAL_POP.D001")]))
    arcpy.SelectLayerByAttribute_management(layers["Blocks"],
                                            "CLEAR_SELECTION")
    return pop


def get_new_population():
    """Queries permit_blocks layer (population form permit data)."""
    arcpy.SelectLayerByLocation_management(
        layers["permit_blocks"], "HAVE_THEIR_CENTER_IN",
        layers["Nhoods"], "", "NEW_SELECTION")
    new_pop = int(sum([float(row[0]) for row in
                  arcpy.da.SearchCursor(layers["permit_blocks"], "new_pop")]))
    arcpy.SelectLayerByAttribute_management(layers["permit_blocks"],
                                            "CLEAR_SELECTION")
    return new_pop


def sum_field(layer_name, field_name):
    """Sums a field."""
    arcpy.SelectLayerByLocation_management(
        layers[layer_name], "HAVE_THEIR_CENTER_IN",
        layers["Nhoods"], "", "NEW_SELECTION")
    field_sum = sum([float(row[0]) for row in
                     arcpy.da.SearchCursor(layers[layer_name], field_name)])
    arcpy.SelectLayerByAttribute_management(layers[layer_name],
                                            "CLEAR_SELECTION")
    return field_sum


def clean_name(n):
    """Removes characters from neighborhood names."""
    return sub("&|/", "", n.replace(" ", "_"))


def get_desc(nhood_name):
    """Gets the neighborhood extent description from the nhood's text file.

        Args:
            nhood_name (str): the name of the neighborhood.
        Returns the nhood's description.
    """
    txt_file = clean_name(nhood_name) + ".txt"
    desc_file = os.path.join(desc_dir, txt_file)
    if not os.path.exists(desc_file):
        return "None"
    with open(desc_file, "r") as f:
        desc = f.readline()
    return desc


def get_reps(nhood):
    """Queries the WardReps.csv file for the Ward(s) and Reps for each nhood.
    """
    wards = []
    reps = pd.read_csv(wards_dir).to_dict()
    for key, value in reps.items():
        if nhood in value.values():
            wards.append(key)
    wards.sort()
    return "<br>".join(wards)


def get_data(nhood_name):
    """Runs all queries for a single neighborhood by name. Returns dict.

        Args:
            nhood_name (str): neighborhood name.
        Returns dictionary of data collected from queries.
    """
    data = {}
    data["neighborhood_name"] = nhood_name
    arcpy.SelectLayerByAttribute_management(
        layers["Nhoods"],
        "NEW_SELECTION",
        "Name = '{}'".format(nhood_name))
    arcpy.SelectLayerByAttribute_management(
        layers["nhood_buffers"],
        "NEW_SELECTION",
        "Name = '{}'".format(nhood_name))
    data["loc_desc"] = get_desc(nhood_name)
    data["date_est"] = query_nhood("Year_Created")
    data["area"] = round(float(query_nhood("Acres")), 1)
    data["council_reps"] = get_reps(nhood_name)
    data["parks"] = query_assets("ParksAndCommons", "Name")
    data["park_acres"] = round(sum_field("ParksAndCommons", "Acres"), 1)  # TODO: IDENT?
    data["trail_mi"] = get_trail_mi()
    data["pub_fac"] = query_assets("PublicFacilities", "FACILITY_NAME")
    data["schools"] = query_assets("Schools", "School")  # NEW
    data["groceries"] = query_assets("SuperMarkets", "STORE_NAME")
    data["hist_res"] = query_assets("HistoricSites", "Name")
    data["current_year"] = year
    data["pop10"] = get_population()
    #data["pop_current"] = get_new_population() + data["pop10"]  # NEW
    data["house10"] = "PENDING"  # TODO: get_housing()
    data["house_current"] = "PENDING"  # TODO: cal_new_housing()
    data["new_dev"] = "PENDING"  # TODO:
    data["guide_docs"] = get_guidedocs(nhood_name)
    return data


def make_profile(data):
    """Converts dict of queried data to HTML and outputs an HTML profile.

        Args:
            data (dict): dictionary of data collected in queries.
        Returns None.
    """
    html_out = template.render(data)
    outfile = os.path.join(profile_dir,
                           clean_name(data["neighborhood_name"]) + ".html")
    with open(outfile, "wb") as f:
        f.write(html_out)
    return


# =============================================================================
# RUN IT

if __name__ == '__main__':
    # Check that directories exist
    status.write("Checking environments...")
    try:
        if not all([os.path.exists(_dir) for _dir in _all_dirs]):
            raise IOError("Directory does not exist: {}".format(_dir))
            # Prevent any possibility of overwriting the PDFs
        if glob(os.path.join(profile_dir, "*.pdf")):
            raise IOError("PDFs Exist")
        sleep(1)
        status.success()
    except IOError as e:
        status.failure()
        raw_input(e.message)  #cli.GetError(wait=True)
        sys.exit(1)

    # Load HTML and Map templates
    status.write("Loading templates...")
    try:
        # Set working directory to "templating" folder
        os.chdir(template_dir)

        # Set working directory / jinja2 environment
        env = Environment(loader=FileSystemLoader(template_dir))

        # Open template html template file
        template = env.get_template(profile_template)

        # Map (.mxd) and dataframe data
        mxd = arcpy.mapping.MapDocument(map_template)
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        status.success()
    except Exception as e:
        status.failure()
        raw_input(e.message)  #cli.GetError(wait=True)
        sys.exit(1)

    # Make dictionary of layers in mxd template
    status.write("Loading map layers...")
    try:
        layers = {layer.name: layer for layer in arcpy.mapping.ListLayers(df)}
        status.success()
    except Exception as e:
        status.failure()
        raw_input(e.message)  #cli.GetError(wait=True)
        sys.exit(1)

    # List neighborhood names
    status.write("Loading neighborhood names...")
    try:
        nhood_names = [n[0] for n in arcpy.da.SearchCursor(layers["Nhoods"],
                                                           "NAME")]
        status.success()
    except Exception as e:
        status.failure()
        raw_input(e.message)  #cli.GetError(wait=True)
        sys.exit(1)

    # Load misc data
    status.write("Loading other datasets...")
    try:
        guide_docs = pd.read_excel(guides_dir, sheetname="Main")
        links = pd.read_excel(guides_dir, "PlanList")
        urls = {v[0]: v[2] for k, v in links.iterrows()}
        status.success()
    except Exception as e:
        status.failure()
        raw_input(e.message)  #cli.GetError(wait=True)
        sys.exit(1)

    # Make profiles
    status.write("Beginning profile generation...")
    try:
        # List comprehension to make all profiles
        [make_profile(get_data(nhood)) for nhood in set(nhood_names)]
        status.success()
    except Exception as e:
        status.failure()
        print(cli.GetError(wait=True))
        raw_input()
        sys.exit(1)

    # Convert all HTML profiles into PDFs
    status.write("Exporting to pdf...")
    try:
        # List comprehension to convert all profiles to PDF  # TODO: Change?
        [pdftools.to_pdf(os.path.join(profile_dir, f)) for f in
         os.listdir(profile_dir)]
        status.success()
    except Exception as e:
        status.failure()
        raw_input(e.message)  #cli.GetError(wait=True)
        sys.exit(1)

    # TODO: push pdfs & html files to separate folders on FTP

    print("\n")
    status.custom("Complete.", "cyan", wait=True)
