#!/usr/bin/env python
# coding: utf-8

# In[4]:




import datashader as ds

import datashader.transfer_functions as tf
import datashader.glyphs
from datashader import reductions
from datashader.core import bypixel
from datashader.utils import lnglat_to_meters as webm, export_image
from datashader.colors import colormap_select, Greys9, viridis, inferno
import copy

import colorcet as cc
from pyproj import Proj, transform
import numpy as np
import pandas as pd
import urllib
import json
import datetime
import colorlover as cl
import geopandas as gpd

import plotly.offline as py
import plotly.graph_objs as go
from plotly import tools
import matplotlib.pyplot as plt

from shapely.geometry import Point, Polygon, shape
# In order to get shapley, you'll need to run [pip install shapely.geometry] from your terminal

from functools import partial

from IPython.display import GeoJSON

py.init_notebook_mode()


# For module 2 we'll be looking at techniques for dealing with big data. In particular binning strategies and the datashader library (which possibly proves we'll never need to bin large data for visualization ever again.)
# 
# To demonstrate these concepts we'll be looking at the PLUTO dataset put out by New York City's department of city planning. PLUTO contains data about every tax lot in New York City.
# 
# PLUTO data can be downloaded from [here](https://www1.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page). Unzip them to the same directory as this notebook, and you should be able to read them in using this (or very similar) code. Also take note of the data dictionary, it'll come in handy for this assignment.

# In[5]:


# Code to read in v17, column names have been updated (without upper case letters) for v18

rawData = pd.read_csv('C:/Users/John Ledesma/Desktop/MSDS Term2/pluto_22v3_1.csv')
bk = rawData[rawData['borough'] == 'BK']
bx = rawData[rawData['borough'] == 'BX']
mn =  rawData[rawData['borough'] == 'MN']
qn =  rawData[rawData['borough'] == 'QN']
si =  rawData[rawData['borough'] == 'SI']


ny = pd.concat([bk, bx, mn, qn, si], ignore_index=True)

#ny = pd.read_csv('nyc_pluto_21v2_csv/pluto_21v2.csv')


# Getting rid of some outliers
ny = ny[(ny['yearbuilt'] > 1850) & (ny['yearbuilt'] < 2020) & (ny['numfloors'] != 0)]

print(rawData.columns)


import os

import os

file_path = 'C:/Users/John Ledesma/Desktop/MSDS Term2/pluto_22v3_1.csv'
file_size_kb = os.path.getsize(file_path) / 1024 # convert from bytes to kilobytes
print(f"The size of the file is {file_size_kb:.2f} KB")


# I'll also do some prep for the geographic component of this data, which we'll be relying on for datashader.
# 
# You're not required to know how I'm retrieving the lattitude and longitude here, but for those interested: this dataset uses a flat x-y projection (assuming for a small enough area that the world is flat for easier calculations), and this needs to be projected back to traditional lattitude and longitude.

# In[6]:




wgs84 = Proj("+proj=longlat +ellps=GRS80 +datum=NAD83 +no_defs")
nyli = Proj("+proj=lcc +lat_1=40.66666666666666 +lat_2=41.03333333333333 +lat_0=40.16666666666666 +lon_0=-74 +x_0=300000 +y_0=0 +ellps=GRS80 +datum=NAD83 +to_meter=0.3048006096012192 +no_defs")
ny['xcoord'] = 0.3048*ny['xcoord']
ny['ycoord'] = 0.3048*ny['ycoord']
ny['lon'], ny['lat'] = transform(nyli, wgs84, ny['xcoord'].values, ny['ycoord'].values)

ny = ny[(ny['lon'] < -60) & (ny['lon'] > -100) & (ny['lat'] < 60) & (ny['lat'] > 20)]

#Defining some helper functions for DataShader
background = "black"
export = partial(export_image, background = background, export_path="export")
cm = partial(colormap_select, reverse=(background!="black"))


# ## Part 1: Binning and Aggregation
# 
# Binning is a common strategy for visualizing large datasets. Binning is inherent to a few types of visualizations, such as histograms and [2D histograms](https://plot.ly/python/2D-Histogram/) (also check out their close relatives: [2D density plots](https://plot.ly/python/2d-density-plots/) and the more general form: [heatmaps](https://plot.ly/python/heatmaps/).
# 
# While these visualization types explicitly include binning, any type of visualization used with aggregated data can be looked at in the same way. For example, lets say we wanted to look at building construction over time. This would be best viewed as a line graph, but we can still think of our results as being binned by year:

# In[7]:


trace = go.Scatter(
    # I'm choosing BBL here because I know it's a unique key.
    x = ny.groupby('yearbuilt').count()['bbl'].index,
    y = ny.groupby('yearbuilt').count()['bbl']
)

layout = go.Layout(
    xaxis = dict(title = 'Year Built'),
    yaxis = dict(title = 'Number of Lots Built')
)

fig = go.FigureWidget(data = [trace], layout = layout)

fig


# Something looks off... You're going to have to deal with this imperfect data to answer this first question. 
# 
# But first: some notes on pandas. Pandas dataframes are a different beast than R dataframes, here are some tips to help you get up to speed:
# 
# ---
# 
# Hello all, here are some pandas tips to help you guys through this homework:
# 
# [Indexing and Selecting](https://pandas.pydata.org/pandas-docs/stable/indexing.html): .loc and .iloc are the analogs for base R subsetting, or filter() in dplyr
# 
# [Group By](https://pandas.pydata.org/pandas-docs/stable/groupby.html):  This is the pandas analog to group_by() and the appended function the analog to summarize(). Try out a few examples of this, and display the results in Jupyter. Take note of what's happening to the indexes, you'll notice that they'll become hierarchical. I personally find this more of a burden than a help, and this sort of hierarchical indexing leads to a fundamentally different experience compared to R dataframes. Once you perform an aggregation, try running the resulting hierarchical datafrome through a [reset_index()](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.reset_index.html).
# 
# [Reset_index](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.reset_index.html): I personally find the hierarchical indexes more of a burden than a help, and this sort of hierarchical indexing leads to a fundamentally different experience compared to R dataframes. reset_index() is a way of restoring a dataframe to a flatter index style. Grouping is where you'll notice it the most, but it's also useful when you filter data, and in a few other split-apply-combine workflows. With pandas indexes are more meaningful, so use this if you start getting unexpected results.
# 
# Indexes are more important in Pandas than in R. If you delve deeper into the using python for data science, you'll begin to see the benefits in many places (despite the personal gripes I highlighted above.) One place these indexes come in handy is with time series data. The pandas docs have a [huge section](http://pandas.pydata.org/pandas-docs/stable/timeseries.html) on datetime indexing. In particular, check out [resample](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.resample.html), which provides time series specific aggregation.
# 
# [Merging, joining, and concatenation](https://pandas.pydata.org/pandas-docs/stable/merging.html): There's some overlap between these different types of merges, so use this as your guide. Concat is a single function that replaces cbind and rbind in R, and the results are driven by the indexes. Read through these examples to get a feel on how these are performed, but you will have to manage your indexes when you're using these functions. Merges are fairly similar to merges in R, similarly mapping to SQL joins.
# 
# Apply: This is explained in the "group by" section linked above. These are your analogs to the plyr library in R. Take note of the lambda syntax used here, these are anonymous functions in python. Rather than predefining a custom function, you can just define it inline using lambda.
# 
# Browse through the other sections for some other specifics, in particular reshaping and categorical data (pandas' answer to factors.) Pandas can take a while to get used to, but it is a pretty strong framework that makes more advanced functions easier once you get used to it. Rolling functions for example follow logically from the apply workflow (and led to the best google results ever when I first tried to find this out and googled "pandas rolling")
# 
# Google Wes Mckinney's book "Python for Data Analysis," which is a cookbook style intro to pandas. It's an O'Reilly book that should be pretty available out there.
# 
# ---
# 
# ### Question
# 
# After a few building collapses, the City of New York is going to begin investigating older buildings for safety. The city is particularly worried about buildings that were unusually tall when they were built, since best-practices for safety hadn’t yet been determined. Create a graph that shows how many buildings of a certain number of floors were built in each year (note: you may want to use a log scale for the number of buildings). Find a strategy to bin buildings (It should be clear 20-29-story buildings, 30-39-story buildings, and 40-49-story buildings were first built in large numbers, but does it make sense to continue in this way as you get taller?)

# In[8]:


# Start your answer here, inserting more cells as you go along
ny['decade'] = (ny['yearbuilt'] // 10) * 10

plt.scatter(ny['decade'], ny['numfloors'])

plt.show()


# ## Part 2: Datashader
# 
# Datashader is a library from Anaconda that does away with the need for binning data. It takes in all of your datapoints, and based on the canvas and range returns a pixel-by-pixel calculations to come up with the best representation of the data. In short, this completely eliminates the need for binning your data.
# 
# As an example, lets continue with our question above and look at a 2D histogram of YearBuilt vs NumFloors:

# In[ ]:


fig = go.FigureWidget(
    data = [
        go.Histogram2d(x=ny['yearbuilt'], y=ny['numfloors'], autobiny=False, ybins={'size': 1}, colorscale='Greens')
    ]
)

fig.show()


# This shows us the distribution, but it's subject to some biases discussed in the Anaconda notebook [Plotting Perils](https://anaconda.org/jbednar/plotting_pitfalls/notebook). 
# 
# Here is what the same plot would look like in datashader:
# 
# 

# In[ ]:


#Defining some helper functions for DataShader
background = "black"
export = partial(export_image, background = background, export_path="export")
cm = partial(colormap_select, reverse=(background!="black"))

cvs = ds.Canvas(800, 500, x_range = (ny['yearbuilt'].min(), ny['yearbuilt'].max()), 
                                y_range = (ny['numfloors'].min(), ny['numfloors'].max()))
agg = cvs.points(ny, 'yearbuilt', 'numfloors')
view = tf.shade(agg, cmap = cm(Greys9), how='log')
export(tf.spread(view, px=2), 'yearvsnumfloors')


# That's technically just a scatterplot, but the points are smartly placed and colored to mimic what one gets in a heatmap. Based on the pixel size, it will either display individual points, or will color the points of denser regions.
# 
# Datashader really shines when looking at geographic information. Here are the latitudes and longitudes of our dataset plotted out, giving us a map of the city colored by density of structures:

# In[ ]:


agg = ds.Canvas().points(ny, 'xcoord', 'ycoord')
ds.tf.set_background(ds.tf.shade(agg, cmap=cc.fire), "black")


# Interestingly, since we're looking at structures, the large buildings of Manhattan show up as less dense on the map. The densest areas measured by number of lots would be single or multi family townhomes.
# 
# Unfortunately, Datashader doesn't have the best documentation. Browse through the examples from their [github repo](https://github.com/bokeh/datashader/tree/master/examples). I would focus on the [visualization pipeline](https://anaconda.org/jbednar/pipeline/notebook) and the [US Census](https://anaconda.org/jbednar/census/notebook) Example for the question below. Feel free to use my samples as templates as well when you work on this problem.
# 
# ### Question
# 
# You work for a real estate developer and are researching underbuilt areas of the city. After looking in the [Pluto data dictionary](https://www1.nyc.gov/assets/planning/download/pdf/data-maps/open-data/pluto_datadictionary.pdf?v=17v1_1), you've discovered that all tax assessments consist of two parts: The assessment of the land and assessment of the structure. You reason that there should be a correlation between these two values: more valuable land will have more valuable structures on them (more valuable in this case refers not just to a mansion vs a bungalow, but an apartment tower vs a single family home). Deviations from the norm could represent underbuilt or overbuilt areas of the city. You also recently read a really cool blog post about [bivariate choropleth maps](http://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/), and think the technique could be used for this problem.
# 
# Datashader is really cool, but it's not that great at labeling your visualization. Don't worry about providing a legend, but provide a quick explanation as to which areas of the city are overbuilt, which areas are underbuilt, and which areas are built in a way that's properly correlated with their land value.

# In[10]:


zips = ny.drop_duplicates()

ny.head(10)

ny['L_B_Ratio']=ny['assesstot']/ny['assessland']

zips = pd.DataFrame({'zipcode': ny['zipcode'].unique()})
ratio = ny.groupby('zipcode').mean()

zr = ratio[['L_B_Ratio']]
zr = zr.reset_index()
print(zr.head)


# In[9]:


# Read in the shapefile of NYC zip code boundaries
zipcodes = gpd.read_file("C://Users//John Ledesma//Downloads//ZIP_CODE_040114//ZIP_CODE_040114.shp")

# Drop duplicates from the NYC property data and calculate the land-to-building ratio
zips = ny.drop_duplicates()
zips['L_B_Ratio'] = zips['assesstot'] / zips['assessland']

# Group the property data by zip code and calculate the mean land-to-building ratio for each zip code
zr = zips.groupby('zipcode').mean().reset_index()

# Convert data type of zipcode column to int
zipcodes['ZIPCODE'] = zipcodes['ZIPCODE'].astype(int)
zr['zipcode'] = zr['zipcode'].astype(int)

# Merge with the NYC zip code boundaries GeoDataFrame
zipcodes = zipcodes.merge(zr, left_on='ZIPCODE', right_on='zipcode')

# Set the figure size and axis labels
fig, ax = plt.subplots(figsize=(10,10))
ax.set_title("Structure Value over Land Value")
ax.set_xlabel("")
ax.set_ylabel("")

# Generate the choropleth map
zipcodes.plot(ax=ax, column='L_B_Ratio', cmap='YlGn', legend=False, edgecolor='black', alpha=1)

# Remove latitude and longitude numbers
ax.set_xticklabels([])
ax.set_yticklabels([])

# Add spectrum legend in lower right corner
sm = plt.cm.ScalarMappable(cmap='YlGn', norm=plt.Normalize(vmin=zr['L_B_Ratio'].min(), vmax=zr['L_B_Ratio'].max()))
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.03, aspect=30)
cbar.ax.tick_params(labelsize=8)

# Show the plot
plt.show()


# In[ ]:




