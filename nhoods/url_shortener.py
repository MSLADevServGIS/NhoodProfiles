#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
URL Shortener Script
Garin Wally; March 2016

Shorten Neighborhood Profile FTP URLs using TinyURL.
"""

from __future__ import print_function
import os
import urllib

import pandas as pd

# Custom libs
from tkit.cli import StatusLine

print(__doc__.split("\n\n")[0])

status = StatusLine()

status.write("\nExecuting...")

# Get the location of the script -- the output Excel file will be put here
os.chdir(os.path.dirname(__file__))

# Output profiles directory (FTP)
ftp_dir = r"\\webserver\ftproot\DEV ftp files\Urban\Maps\nhood_profiles"

# FTP URL
ftp_site = "ftp://ftp.ci.missoula.mt.us/DEV%20ftp%20files/Urban/Maps/nhood_profiles/"


def tiny_url(url):
    """Converts an FTP url to a TinyURL.

        Args:
            url (str): url to a single file on the City's FTP site.
        Returns a tinyurl.
    """
    api = "http://tinyurl.com/api-create.php?url="
    tiny = urllib.urlopen(api + url).read()
    return tiny


def make_urls():
    url_dict = {f: tiny_url(os.path.join(ftp_site, f)) for f
                in os.listdir(ftp_dir)}
    url_df = pd.DataFrame({"Nhood": url_dict.keys(), "URL": url_dict.values()})
    url_df = url_df.sort("Nhood")
    url_df.to_excel("TinyURLs.xlsx", index=False)
    return


if __name__ == '__main__':
    make_urls()
    status.custom("[Complete]", "cyan", wait=True)
    #fprint("", wait_for_enter=True)
