"""City Weather: run with Python 3 (Tkinter required). No API keys needed.
City rankings: US Census Bureau July 1, 2025 population estimates (Vintage 2025).
https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/sub-est2025.csv
Coordinates: 2025 Census Gazetteer place internal points, joined by GEOID.
https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_place_national.zip
Weather/geocoding: Open-Meteo (https://open-meteo.com), GeoNames.
Radar: RainViewer imagery over OpenStreetMap tiles, rendered inside Tkinter.
"""
import json
import math
import queue
import threading
import tkinter as tk
import unicodedata
import hashlib
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
import base64
from datetime import datetime
from difflib import get_close_matches
from tkinter import ttk, messagebox
from urllib.parse import urlencode
from urllib.request import urlopen, Request

CITIES = [{'name': 'New York, New York', 'lat': 40.662712, 'lon': -73.938677, 'population': 8584629, 'population_year': 2025, 'rank': 1, 'geoid': '3651000'}, {'name': 'Los Angeles, California', 'lat': 34.019394, 'lon': -118.410825, 'population': 3869089, 'population_year': 2025, 'rank': 2, 'geoid': '0644000'}, {'name': 'Chicago, Illinois', 'lat': 41.837045, 'lon': -87.684939, 'population': 2731585, 'population_year': 2025, 'rank': 3, 'geoid': '1714000'}, {'name': 'Houston, Texas', 'lat': 29.785743, 'lon': -95.388806, 'population': 2397315, 'population_year': 2025, 'rank': 4, 'geoid': '4835000'}, {'name': 'Phoenix, Arizona', 'lat': 33.572154, 'lon': -112.090132, 'population': 1665481, 'population_year': 2025, 'rank': 5, 'geoid': '0455000'}, {'name': 'Philadelphia, Pennsylvania', 'lat': 40.009376, 'lon': -75.133346, 'population': 1574281, 'population_year': 2025, 'rank': 6, 'geoid': '4260000'}, {'name': 'San Antonio, Texas', 'lat': 29.462809, 'lon': -98.524635, 'population': 1548422, 'population_year': 2025, 'rank': 7, 'geoid': '4865000'}, {'name': 'San Diego, California', 'lat': 32.830391, 'lon': -117.120923, 'population': 1406106, 'population_year': 2025, 'rank': 8, 'geoid': '0666000'}, {'name': 'Dallas, Texas', 'lat': 32.793333, 'lon': -96.766513, 'population': 1329491, 'population_year': 2025, 'rank': 9, 'geoid': '4819000'}, {'name': 'Fort Worth, Texas', 'lat': 32.781954, 'lon': -97.348573, 'population': 1028117, 'population_year': 2025, 'rank': 10, 'geoid': '4827000'}, {'name': 'Jacksonville, Florida', 'lat': 30.336864, 'lon': -81.661603, 'population': 1017689, 'population_year': 2025, 'rank': 11, 'geoid': '1235000'}, {'name': 'Austin, Texas', 'lat': 30.298622, 'lon': -97.754134, 'population': 1002632, 'population_year': 2025, 'rank': 12, 'geoid': '4805000'}, {'name': 'San Jose, California', 'lat': 37.296011, 'lon': -121.814552, 'population': 989814, 'population_year': 2025, 'rank': 13, 'geoid': '0668000'}, {'name': 'Charlotte, North Carolina', 'lat': 35.209045, 'lon': -80.83099, 'population': 964784, 'population_year': 2025, 'rank': 14, 'geoid': '3712000'}, {'name': 'Columbus, Ohio', 'lat': 39.985531, 'lon': -82.985594, 'population': 938396, 'population_year': 2025, 'rank': 15, 'geoid': '3918000'}, {'name': 'Indianapolis (balance), Indiana', 'lat': 39.776664, 'lon': -86.145935, 'population': 901116, 'population_year': 2025, 'rank': 16, 'geoid': '1836003'}, {'name': 'San Francisco, California', 'lat': 37.727239, 'lon': -123.032229, 'population': 826079, 'population_year': 2025, 'rank': 17, 'geoid': '0667000'}, {'name': 'Seattle, Washington', 'lat': 47.619335, 'lon': -122.351538, 'population': 784777, 'population_year': 2025, 'rank': 18, 'geoid': '5363000'}, {'name': 'Denver, Colorado', 'lat': 39.76185, 'lon': -104.881105, 'population': 740613, 'population_year': 2025, 'rank': 19, 'geoid': '0820000'}, {'name': 'Nashville-Davidson metropolitan government (balance), Tennessee', 'lat': 36.1718, 'lon': -86.785002, 'population': 721074, 'population_year': 2025, 'rank': 20, 'geoid': '4752006'}, {'name': 'Oklahoma City, Oklahoma', 'lat': 35.467079, 'lon': -97.513657, 'population': 719849, 'population_year': 2025, 'rank': 21, 'geoid': '4055000'}, {'name': 'Washington, District of Columbia', 'lat': 38.904243, 'lon': -77.016524, 'population': 693645, 'population_year': 2025, 'rank': 22, 'geoid': '1150000'}, {'name': 'El Paso, Texas', 'lat': 31.84778, 'lon': -106.431106, 'population': 683012, 'population_year': 2025, 'rank': 23, 'geoid': '4824000'}, {'name': 'Las Vegas, Nevada', 'lat': 36.233499, 'lon': -115.264037, 'population': 679817, 'population_year': 2025, 'rank': 24, 'geoid': '3240000'}, {'name': 'Boston, Massachusetts', 'lat': 42.338551, 'lon': -71.018253, 'population': 672973, 'population_year': 2025, 'rank': 25, 'geoid': '2507000'}, {'name': 'Detroit, Michigan', 'lat': 42.383037, 'lon': -83.102237, 'population': 649095, 'population_year': 2025, 'rank': 26, 'geoid': '2622000'}, {'name': 'Louisville/Jefferson County metro government (balance), Kentucky', 'lat': 38.165376, 'lon': -85.647377, 'population': 641962, 'population_year': 2025, 'rank': 27, 'geoid': '2148006'}, {'name': 'Portland, Oregon', 'lat': 45.536951, 'lon': -122.649971, 'population': 635109, 'population_year': 2025, 'rank': 28, 'geoid': '4159000'}, {'name': 'Memphis, Tennessee', 'lat': 35.109164, 'lon': -89.968511, 'population': 609647, 'population_year': 2025, 'rank': 29, 'geoid': '4748000'}, {'name': 'Baltimore, Maryland', 'lat': 39.300032, 'lon': -76.610476, 'population': 569997, 'population_year': 2025, 'rank': 30, 'geoid': '2404000'}, {'name': 'Milwaukee, Wisconsin', 'lat': 43.063348, 'lon': -87.966695, 'population': 562407, 'population_year': 2025, 'rank': 31, 'geoid': '5553000'}, {'name': 'Albuquerque, New Mexico', 'lat': 35.10478, 'lon': -106.646809, 'population': 556588, 'population_year': 2025, 'rank': 32, 'geoid': '3502000'}, {'name': 'Fresno, California', 'lat': 36.782684, 'lon': -119.793359, 'population': 555549, 'population_year': 2025, 'rank': 33, 'geoid': '0627000'}, {'name': 'Tucson, Arizona', 'lat': 32.153036, 'lon': -110.870773, 'population': 548371, 'population_year': 2025, 'rank': 34, 'geoid': '0477000'}, {'name': 'Sacramento, California', 'lat': 38.567694, 'lon': -121.468161, 'population': 536449, 'population_year': 2025, 'rank': 35, 'geoid': '0664000'}, {'name': 'Atlanta, Georgia', 'lat': 33.762909, 'lon': -84.422675, 'population': 529110, 'population_year': 2025, 'rank': 36, 'geoid': '1304000'}, {'name': 'Kansas City, Missouri', 'lat': 39.125155, 'lon': -94.550313, 'population': 521220, 'population_year': 2025, 'rank': 37, 'geoid': '2938000'}, {'name': 'Mesa, Arizona', 'lat': 33.399355, 'lon': -111.715968, 'population': 513656, 'population_year': 2025, 'rank': 38, 'geoid': '0446000'}, {'name': 'Raleigh, North Carolina', 'lat': 35.831868, 'lon': -78.641042, 'population': 506306, 'population_year': 2025, 'rank': 39, 'geoid': '3755000'}, {'name': 'Colorado Springs, Colorado', 'lat': 38.867255, 'lon': -104.760749, 'population': 494743, 'population_year': 2025, 'rank': 40, 'geoid': '0816000'}, {'name': 'Miami, Florida', 'lat': 25.775163, 'lon': -80.208615, 'population': 489812, 'population_year': 2025, 'rank': 41, 'geoid': '1245000'}, {'name': 'Omaha, Nebraska', 'lat': 41.262705, 'lon': -96.053475, 'population': 488797, 'population_year': 2025, 'rank': 42, 'geoid': '3137000'}, {'name': 'Virginia Beach, Virginia', 'lat': 36.779525, 'lon': -76.029142, 'population': 453737, 'population_year': 2025, 'rank': 43, 'geoid': '5182000'}, {'name': 'Long Beach, California', 'lat': 33.780791, 'lon': -118.16818, 'population': 450469, 'population_year': 2025, 'rank': 44, 'geoid': '0643000'}, {'name': 'Oakland, California', 'lat': 37.769846, 'lon': -122.22569, 'population': 440838, 'population_year': 2025, 'rank': 45, 'geoid': '0653000'}, {'name': 'Minneapolis, Minnesota', 'lat': 44.963324, 'lon': -93.26832, 'population': 430324, 'population_year': 2025, 'rank': 46, 'geoid': '2743000'}, {'name': 'Bakersfield, California', 'lat': 35.353171, 'lon': -119.037919, 'population': 422165, 'population_year': 2025, 'rank': 47, 'geoid': '0603526'}, {'name': 'Tulsa, Oklahoma', 'lat': 36.127949, 'lon': -95.902316, 'population': 416209, 'population_year': 2025, 'rank': 48, 'geoid': '4075000'}, {'name': 'Tampa, Florida', 'lat': 27.970086, 'lon': -82.479673, 'population': 413554, 'population_year': 2025, 'rank': 49, 'geoid': '1271000'}, {'name': 'Aurora, Colorado', 'lat': 39.709537, 'lon': -104.720509, 'population': 410053, 'population_year': 2025, 'rank': 50, 'geoid': '0804000'}, {'name': 'Arlington, Texas', 'lat': 32.700708, 'lon': -97.124691, 'population': 402134, 'population_year': 2025, 'rank': 51, 'geoid': '4804000'}, {'name': 'Wichita, Kansas', 'lat': 37.690638, 'lon': -97.345836, 'population': 400987, 'population_year': 2025, 'rank': 52, 'geoid': '2079000'}, {'name': 'Cleveland, Ohio', 'lat': 41.478462, 'lon': -81.679435, 'population': 363608, 'population_year': 2025, 'rank': 53, 'geoid': '3916000'}, {'name': 'New Orleans, Louisiana', 'lat': 30.05342, 'lon': -89.934502, 'population': 362154, 'population_year': 2025, 'rank': 54, 'geoid': '2255000'}, {'name': 'Henderson, Nevada', 'lat': 36.008958, 'lon': -115.0268, 'population': 353289, 'population_year': 2025, 'rank': 55, 'geoid': '3231900'}, {'name': 'Urban Honolulu, Hawaii', 'lat': 21.324347, 'lon': -157.84764, 'population': 341868, 'population_year': 2025, 'rank': 56, 'geoid': '1571550'}, {'name': 'Anaheim, California', 'lat': 33.855502, 'lon': -117.758657, 'population': 341008, 'population_year': 2025, 'rank': 57, 'geoid': '0602000'}, {'name': 'Orlando, Florida', 'lat': 28.472818, 'lon': -81.320242, 'population': 333888, 'population_year': 2025, 'rank': 58, 'geoid': '1253000'}, {'name': 'Lexington-Fayette urban county, Kentucky', 'lat': 38.040678, 'lon': -84.458272, 'population': 329751, 'population_year': 2025, 'rank': 59, 'geoid': '2146027'}, {'name': 'Stockton, California', 'lat': 37.976553, 'lon': -121.308598, 'population': 324597, 'population_year': 2025, 'rank': 60, 'geoid': '0675000'}, {'name': 'Newark, New Jersey', 'lat': 40.72422, 'lon': -74.172574, 'population': 323808, 'population_year': 2025, 'rank': 61, 'geoid': '3451000'}, {'name': 'Riverside, California', 'lat': 33.938143, 'lon': -117.393168, 'population': 323057, 'population_year': 2025, 'rank': 62, 'geoid': '0662000'}, {'name': 'Irvine, California', 'lat': 33.678399, 'lon': -117.771254, 'population': 318764, 'population_year': 2025, 'rank': 63, 'geoid': '0636770'}, {'name': 'Corpus Christi, Texas', 'lat': 27.754252, 'lon': -97.173385, 'population': 317247, 'population_year': 2025, 'rank': 64, 'geoid': '4817000'}, {'name': 'Santa Ana, California', 'lat': 33.736332, 'lon': -117.8829, 'population': 315586, 'population_year': 2025, 'rank': 65, 'geoid': '0669000'}, {'name': 'Cincinnati, Ohio', 'lat': 39.140183, 'lon': -84.505829, 'population': 314367, 'population_year': 2025, 'rank': 66, 'geoid': '3915000'}, {'name': 'Greensboro, North Carolina', 'lat': 36.09485, 'lon': -79.823624, 'population': 308667, 'population_year': 2025, 'rank': 67, 'geoid': '3728000'}, {'name': 'Pittsburgh, Pennsylvania', 'lat': 40.439936, 'lon': -79.975676, 'population': 307632, 'population_year': 2025, 'rank': 68, 'geoid': '4261000'}, {'name': 'St. Paul, Minnesota', 'lat': 44.948901, 'lon': -93.104063, 'population': 306684, 'population_year': 2025, 'rank': 69, 'geoid': '2758000'}, {'name': 'Durham, North Carolina', 'lat': 35.977928, 'lon': -78.898109, 'population': 305561, 'population_year': 2025, 'rank': 70, 'geoid': '3719000'}, {'name': 'Jersey City, New Jersey', 'lat': 40.711417, 'lon': -74.06476, 'population': 302013, 'population_year': 2025, 'rank': 71, 'geoid': '3436000'}, {'name': 'Lincoln, Nebraska', 'lat': 40.810284, 'lon': -96.674856, 'population': 301522, 'population_year': 2025, 'rank': 72, 'geoid': '3128000'}, {'name': 'North Las Vegas, Nevada', 'lat': 36.289865, 'lon': -115.089181, 'population': 296653, 'population_year': 2025, 'rank': 73, 'geoid': '3251800'}, {'name': 'Plano, Texas', 'lat': 33.050769, 'lon': -96.747944, 'population': 293028, 'population_year': 2025, 'rank': 74, 'geoid': '4858016'}, {'name': 'Gilbert, Arizona', 'lat': 33.310345, 'lon': -111.743121, 'population': 287285, 'population_year': 2025, 'rank': 75, 'geoid': '0427400'}, {'name': 'Anchorage, Alaska', 'lat': 61.17425, 'lon': -149.284329, 'population': 287155, 'population_year': 2025, 'rank': 76, 'geoid': '0203000'}, {'name': 'Madison, Wisconsin', 'lat': 43.087815, 'lon': -89.429856, 'population': 286233, 'population_year': 2025, 'rank': 77, 'geoid': '5548000'}, {'name': 'Reno, Nevada', 'lat': 39.549097, 'lon': -119.849907, 'population': 283621, 'population_year': 2025, 'rank': 78, 'geoid': '3260600'}, {'name': 'Chandler, Arizona', 'lat': 33.282765, 'lon': -111.851819, 'population': 278748, 'population_year': 2025, 'rank': 79, 'geoid': '0412000'}, {'name': 'St. Louis, Missouri', 'lat': 38.635699, 'lon': -90.244582, 'population': 278144, 'population_year': 2025, 'rank': 80, 'geoid': '2965000'}, {'name': 'Chula Vista, California', 'lat': 32.62767, 'lon': -117.01517, 'population': 275533, 'population_year': 2025, 'rank': 81, 'geoid': '0613392'}, {'name': 'Fort Wayne, Indiana', 'lat': 41.088193, 'lon': -85.142791, 'population': 275203, 'population_year': 2025, 'rank': 82, 'geoid': '1825000'}, {'name': 'Buffalo, New York', 'lat': 42.892492, 'lon': -78.859686, 'population': 274613, 'population_year': 2025, 'rank': 83, 'geoid': '3611000'}, {'name': 'Lubbock, Texas', 'lat': 33.561901, 'lon': -101.888883, 'population': 273071, 'population_year': 2025, 'rank': 84, 'geoid': '4845000'}, {'name': 'Laredo, Texas', 'lat': 27.560379, 'lon': -99.489181, 'population': 269515, 'population_year': 2025, 'rank': 85, 'geoid': '4841464'}, {'name': 'Port St. Lucie, Florida', 'lat': 27.280554, 'lon': -80.388261, 'population': 268062, 'population_year': 2025, 'rank': 86, 'geoid': '1258715'}, {'name': 'St. Petersburg, Florida', 'lat': 27.762727, 'lon': -82.644131, 'population': 264033, 'population_year': 2025, 'rank': 87, 'geoid': '1263000'}, {'name': 'Toledo, Ohio', 'lat': 41.664071, 'lon': -83.581861, 'population': 263423, 'population_year': 2025, 'rank': 88, 'geoid': '3977000'}, {'name': 'Glendale, Arizona', 'lat': 33.533111, 'lon': -112.189901, 'population': 260572, 'population_year': 2025, 'rank': 89, 'geoid': '0427820'}, {'name': 'Winston-Salem, North Carolina', 'lat': 36.102863, 'lon': -80.260829, 'population': 257271, 'population_year': 2025, 'rank': 90, 'geoid': '3775000'}, {'name': 'Irving, Texas', 'lat': 32.857748, 'lon': -96.970022, 'population': 257076, 'population_year': 2025, 'rank': 91, 'geoid': '4837000'}, {'name': 'Chesapeake, Virginia', 'lat': 36.679376, 'lon': -76.301788, 'population': 255332, 'population_year': 2025, 'rank': 92, 'geoid': '5116000'}, {'name': 'Garland, Texas', 'lat': 32.909826, 'lon': -96.630334, 'population': 249625, 'population_year': 2025, 'rank': 93, 'geoid': '4829000'}, {'name': 'Scottsdale, Arizona', 'lat': 33.684272, 'lon': -111.861448, 'population': 243006, 'population_year': 2025, 'rank': 94, 'geoid': '0465000'}, {'name': 'Boise City, Idaho', 'lat': 43.59805, 'lon': -116.231596, 'population': 238429, 'population_year': 2025, 'rank': 95, 'geoid': '1608830'}, {'name': 'Richmond, Virginia', 'lat': 37.531399, 'lon': -77.476009, 'population': 237257, 'population_year': 2025, 'rank': 96, 'geoid': '5167000'}, {'name': 'Frisco, Texas', 'lat': 33.155427, 'lon': -96.822596, 'population': 236955, 'population_year': 2025, 'rank': 97, 'geoid': '4827684'}, {'name': 'Cape Coral, Florida', 'lat': 26.643192, 'lon': -81.997364, 'population': 236264, 'population_year': 2025, 'rank': 98, 'geoid': '1210275'}, {'name': 'McKinney, Texas', 'lat': 33.201125, 'lon': -96.664161, 'population': 236001, 'population_year': 2025, 'rank': 99, 'geoid': '4845744'}, {'name': 'Huntsville, Alabama', 'lat': 34.69772, 'lon': -86.67667, 'population': 233627, 'population_year': 2025, 'rank': 100, 'geoid': '0137000'}, {'name': 'Norfolk, Virginia', 'lat': 36.923015, 'lon': -76.244641, 'population': 231013, 'population_year': 2025, 'rank': 101, 'geoid': '5157000'}, {'name': 'Hialeah, Florida', 'lat': 25.869941, 'lon': -80.302865, 'population': 230968, 'population_year': 2025, 'rank': 102, 'geoid': '1230000'}, {'name': 'Spokane, Washington', 'lat': 47.666935, 'lon': -117.433322, 'population': 230783, 'population_year': 2025, 'rank': 103, 'geoid': '5367000'}, {'name': 'Tacoma, Washington', 'lat': 47.252199, 'lon': -122.459832, 'population': 229816, 'population_year': 2025, 'rank': 104, 'geoid': '5370000'}, {'name': 'Santa Clarita, California', 'lat': 34.416504, 'lon': -118.500693, 'population': 228430, 'population_year': 2025, 'rank': 105, 'geoid': '0669088'}, {'name': 'Fremont, California', 'lat': 37.49446, 'lon': -121.94115, 'population': 226442, 'population_year': 2025, 'rank': 106, 'geoid': '0626000'}, {'name': 'Baton Rouge, Louisiana', 'lat': 30.442174, 'lon': -91.130894, 'population': 222795, 'population_year': 2025, 'rank': 107, 'geoid': '2205000'}, {'name': 'San Bernardino, California', 'lat': 34.14114, 'lon': -117.294635, 'population': 222044, 'population_year': 2025, 'rank': 108, 'geoid': '0665000'}, {'name': 'Fontana, California', 'lat': 34.109686, 'lon': -117.462888, 'population': 221223, 'population_year': 2025, 'rank': 109, 'geoid': '0624680'}, {'name': 'Modesto, California', 'lat': 37.637533, 'lon': -121.003049, 'population': 219652, 'population_year': 2025, 'rank': 110, 'geoid': '0648354'}, {'name': 'Salt Lake City, Utah', 'lat': 40.776928, 'lon': -111.930991, 'population': 218428, 'population_year': 2025, 'rank': 111, 'geoid': '4967000'}, {'name': 'Moreno Valley, California', 'lat': 33.923253, 'lon': -117.205685, 'population': 214263, 'population_year': 2025, 'rank': 112, 'geoid': '0649270'}, {'name': 'Worcester, Massachusetts', 'lat': 42.269478, 'lon': -71.807783, 'population': 213862, 'population_year': 2025, 'rank': 113, 'geoid': '2582000'}, {'name': 'Sioux Falls, South Dakota', 'lat': 43.540696, 'lon': -96.731962, 'population': 213748, 'population_year': 2025, 'rank': 114, 'geoid': '4659020'}, {'name': 'Yonkers, New York', 'lat': 40.945862, 'lon': -73.867446, 'population': 212603, 'population_year': 2025, 'rank': 115, 'geoid': '3684000'}, {'name': 'Des Moines, Iowa', 'lat': 41.57259, 'lon': -93.610243, 'population': 212086, 'population_year': 2025, 'rank': 116, 'geoid': '1921000'}, {'name': 'Grand Prairie, Texas', 'lat': 32.67893, 'lon': -97.020743, 'population': 209434, 'population_year': 2025, 'rank': 117, 'geoid': '4830464'}, {'name': 'Fayetteville, North Carolina', 'lat': 35.082766, 'lon': -78.973515, 'population': 209120, 'population_year': 2025, 'rank': 118, 'geoid': '3722920'}, {'name': 'Little Rock, Arkansas', 'lat': 34.725393, 'lon': -92.358556, 'population': 206427, 'population_year': 2025, 'rank': 119, 'geoid': '0541000'}, {'name': 'Rochester, New York', 'lat': 43.169927, 'lon': -77.616891, 'population': 206108, 'population_year': 2025, 'rank': 120, 'geoid': '3663000'}, {'name': 'Amarillo, Texas', 'lat': 35.199903, 'lon': -101.830194, 'population': 205130, 'population_year': 2025, 'rank': 121, 'geoid': '4803000'}, {'name': 'Tallahassee, Florida', 'lat': 30.453529, 'lon': -84.252272, 'population': 204902, 'population_year': 2025, 'rank': 122, 'geoid': '1270600'}, {'name': 'Overland Park, Kansas', 'lat': 38.889042, 'lon': -94.690584, 'population': 203677, 'population_year': 2025, 'rank': 123, 'geoid': '2053775'}, {'name': 'Columbus, Georgia', 'lat': 32.510191, 'lon': -84.874946, 'population': 202171, 'population_year': 2025, 'rank': 124, 'geoid': '1319000'}, {'name': 'Knoxville, Tennessee', 'lat': 35.97068, 'lon': -83.94927, 'population': 202021, 'population_year': 2025, 'rank': 125, 'geoid': '4740000'}, {'name': 'Augusta-Richmond County consolidated government (balance), Georgia', 'lat': 33.365531, 'lon': -82.073422, 'population': 201999, 'population_year': 2025, 'rank': 126, 'geoid': '1304204'}, {'name': 'Grand Rapids, Michigan', 'lat': 42.961156, 'lon': -85.65557, 'population': 201183, 'population_year': 2025, 'rank': 127, 'geoid': '2634000'}, {'name': 'Peoria, Arizona', 'lat': 33.786186, 'lon': -112.308042, 'population': 200881, 'population_year': 2025, 'rank': 128, 'geoid': '0454050'}, {'name': 'Mobile, Alabama', 'lat': 30.668246, 'lon': -88.107853, 'population': 200824, 'population_year': 2025, 'rank': 129, 'geoid': '0150000'}, {'name': 'Vancouver, Washington', 'lat': 45.637156, 'lon': -122.596567, 'population': 199698, 'population_year': 2025, 'rank': 130, 'geoid': '5374060'}, {'name': 'Oxnard, California', 'lat': 34.199436, 'lon': -119.207515, 'population': 199651, 'population_year': 2025, 'rank': 131, 'geoid': '0654652'}, {'name': 'Birmingham, Alabama', 'lat': 33.527174, 'lon': -86.797036, 'population': 195893, 'population_year': 2025, 'rank': 132, 'geoid': '0107000'}, {'name': 'Providence, Rhode Island', 'lat': 41.823056, 'lon': -71.418784, 'population': 195310, 'population_year': 2025, 'rank': 133, 'geoid': '4459000'}, {'name': 'Montgomery, Alabama', 'lat': 32.348503, 'lon': -86.267307, 'population': 195300, 'population_year': 2025, 'rank': 134, 'geoid': '0151000'}, {'name': 'Chattanooga, Tennessee', 'lat': 35.065958, 'lon': -85.248386, 'population': 194144, 'population_year': 2025, 'rank': 135, 'geoid': '4714000'}, {'name': 'Brownsville, Texas', 'lat': 25.989404, 'lon': -97.480625, 'population': 192957, 'population_year': 2025, 'rank': 136, 'geoid': '4810768'}, {'name': 'Huntington Beach, California', 'lat': 33.698007, 'lon': -118.003834, 'population': 191451, 'population_year': 2025, 'rank': 137, 'geoid': '0636000'}, {'name': 'Tempe, Arizona', 'lat': 33.388414, 'lon': -111.931782, 'population': 190571, 'population_year': 2025, 'rank': 138, 'geoid': '0473000'}, {'name': 'Akron, Ohio', 'lat': 41.080456, 'lon': -81.521429, 'population': 189691, 'population_year': 2025, 'rank': 139, 'geoid': '3901000'}, {'name': 'Clarksville, Tennessee', 'lat': 36.56643, 'lon': -87.345216, 'population': 188829, 'population_year': 2025, 'rank': 140, 'geoid': '4715160'}, {'name': 'Fort Lauderdale, Florida', 'lat': 26.141227, 'lon': -80.146731, 'population': 188677, 'population_year': 2025, 'rank': 141, 'geoid': '1224000'}, {'name': 'Glendale, California', 'lat': 34.181393, 'lon': -118.24583, 'population': 187160, 'population_year': 2025, 'rank': 142, 'geoid': '0630000'}, {'name': 'Ontario, California', 'lat': 34.037042, 'lon': -117.605956, 'population': 187013, 'population_year': 2025, 'rank': 143, 'geoid': '0653896'}, {'name': 'Elk Grove, California', 'lat': 38.414621, 'lon': -121.384961, 'population': 185007, 'population_year': 2025, 'rank': 144, 'geoid': '0622020'}, {'name': 'Cary, North Carolina', 'lat': 35.781302, 'lon': -78.823444, 'population': 183582, 'population_year': 2025, 'rank': 145, 'geoid': '3710740'}, {'name': 'Newport News, Virginia', 'lat': 37.076136, 'lon': -76.52198, 'population': 183230, 'population_year': 2025, 'rank': 146, 'geoid': '5156000'}, {'name': 'Salem, Oregon', 'lat': 44.9239, 'lon': -123.023007, 'population': 181779, 'population_year': 2025, 'rank': 147, 'geoid': '4164900'}, {'name': 'Aurora, Illinois', 'lat': 41.763455, 'lon': -88.290099, 'population': 181505, 'population_year': 2025, 'rank': 148, 'geoid': '1703012'}, {'name': 'Santa Rosa, California', 'lat': 38.445824, 'lon': -122.706181, 'population': 179437, 'population_year': 2025, 'rank': 149, 'geoid': '0670098'}, {'name': 'Eugene, Oregon', 'lat': 44.056848, 'lon': -123.119019, 'population': 178618, 'population_year': 2025, 'rank': 150, 'geoid': '4123850'}, {'name': 'Rancho Cucamonga, California', 'lat': 34.130306, 'lon': -117.566067, 'population': 177856, 'population_year': 2025, 'rank': 151, 'geoid': '0659451'}, {'name': 'Pembroke Pines, Florida', 'lat': 26.014716, 'lon': -80.340171, 'population': 176714, 'population_year': 2025, 'rank': 152, 'geoid': '1255775'}, {'name': 'Shreveport, Louisiana', 'lat': 32.466879, 'lon': -93.792193, 'population': 175902, 'population_year': 2025, 'rank': 153, 'geoid': '2270000'}, {'name': 'Surprise, Arizona', 'lat': 33.670801, 'lon': -112.452546, 'population': 175304, 'population_year': 2025, 'rank': 154, 'geoid': '0471510'}, {'name': 'Fort Collins, Colorado', 'lat': 40.548216, 'lon': -105.064833, 'population': 171500, 'population_year': 2025, 'rank': 155, 'geoid': '0827425'}, {'name': 'Murfreesboro, Tennessee', 'lat': 35.853915, 'lon': -86.421224, 'population': 171178, 'population_year': 2025, 'rank': 156, 'geoid': '4751560'}, {'name': 'Oceanside, California', 'lat': 33.224601, 'lon': -117.306291, 'population': 170483, 'population_year': 2025, 'rank': 157, 'geoid': '0653322'}, {'name': 'Garden Grove, California', 'lat': 33.778782, 'lon': -117.960472, 'population': 170455, 'population_year': 2025, 'rank': 158, 'geoid': '0629000'}, {'name': 'Lancaster, California', 'lat': 34.693558, 'lon': -118.175305, 'population': 170084, 'population_year': 2025, 'rank': 159, 'geoid': '0640130'}, {'name': 'Springfield, Missouri', 'lat': 37.194157, 'lon': -93.292642, 'population': 169847, 'population_year': 2025, 'rank': 160, 'geoid': '2970000'}, {'name': 'Denton, Texas', 'lat': 33.217449, 'lon': -97.141346, 'population': 169431, 'population_year': 2025, 'rank': 161, 'geoid': '4819972'}, {'name': 'Roseville, California', 'lat': 38.770296, 'lon': -121.319634, 'population': 167302, 'population_year': 2025, 'rank': 162, 'geoid': '0662938'}, {'name': 'Killeen, Texas', 'lat': 31.077669, 'lon': -97.731952, 'population': 161883, 'population_year': 2025, 'rank': 163, 'geoid': '4839148'}, {'name': 'Palmdale, California', 'lat': 34.591038, 'lon': -118.105403, 'population': 161845, 'population_year': 2025, 'rank': 164, 'geoid': '0655156'}, {'name': 'Paterson, New Jersey', 'lat': 40.914766, 'lon': -74.162829, 'population': 161793, 'population_year': 2025, 'rank': 165, 'geoid': '3457000'}, {'name': 'Corona, California', 'lat': 33.861969, 'lon': -117.565495, 'population': 161734, 'population_year': 2025, 'rank': 166, 'geoid': '0616350'}, {'name': 'Alexandria, Virginia', 'lat': 38.819251, 'lon': -77.08367, 'population': 160662, 'population_year': 2025, 'rank': 167, 'geoid': '5101000'}, {'name': 'Charleston, South Carolina', 'lat': 32.828017, 'lon': -79.972896, 'population': 159423, 'population_year': 2025, 'rank': 168, 'geoid': '4513330'}, {'name': 'Salinas, California', 'lat': 36.690217, 'lon': -121.633793, 'population': 159134, 'population_year': 2025, 'rank': 169, 'geoid': '0664224'}, {'name': 'Kansas City, Kansas', 'lat': 39.122539, 'lon': -94.741781, 'population': 157805, 'population_year': 2025, 'rank': 170, 'geoid': '2036000'}, {'name': 'Macon-Bibb County, Georgia', 'lat': 32.80899, 'lon': -83.69406, 'population': 157556, 'population_year': 2025, 'rank': 171, 'geoid': '1349008'}, {'name': 'Hayward, California', 'lat': 37.626826, 'lon': -122.104015, 'population': 157113, 'population_year': 2025, 'rank': 172, 'geoid': '0633000'}, {'name': 'Hollywood, Florida', 'lat': 26.030967, 'lon': -80.164609, 'population': 157019, 'population_year': 2025, 'rank': 173, 'geoid': '1232000'}, {'name': 'Lakewood, Colorado', 'lat': 39.698939, 'lon': -105.117573, 'population': 156927, 'population_year': 2025, 'rank': 174, 'geoid': '0843000'}, {'name': 'Sunnyvale, California', 'lat': 37.385797, 'lon': -122.026316, 'population': 156577, 'population_year': 2025, 'rank': 175, 'geoid': '0677000'}, {'name': 'Springfield, Massachusetts', 'lat': 42.115454, 'lon': -72.539978, 'population': 154702, 'population_year': 2025, 'rank': 176, 'geoid': '2567000'}, {'name': 'Bellevue, Washington', 'lat': 47.597837, 'lon': -122.15648, 'population': 154193, 'population_year': 2025, 'rank': 177, 'geoid': '5305210'}, {'name': 'Naperville, Illinois', 'lat': 41.749173, 'lon': -88.162019, 'population': 153114, 'population_year': 2025, 'rank': 178, 'geoid': '1751622'}, {'name': 'Bridgeport, Connecticut', 'lat': 41.187393, 'lon': -73.195757, 'population': 152273, 'population_year': 2025, 'rank': 179, 'geoid': '0908000'}, {'name': 'Joliet, Illinois', 'lat': 41.516866, 'lon': -88.147963, 'population': 152241, 'population_year': 2025, 'rank': 180, 'geoid': '1738570'}, {'name': 'Mesquite, Texas', 'lat': 32.75955, 'lon': -96.584164, 'population': 150693, 'population_year': 2025, 'rank': 181, 'geoid': '4847892'}, {'name': 'McAllen, Texas', 'lat': 26.224966, 'lon': -98.246083, 'population': 150640, 'population_year': 2025, 'rank': 182, 'geoid': '4845384'}, {'name': 'Olathe, Kansas', 'lat': 38.882031, 'lon': -94.820054, 'population': 150025, 'population_year': 2025, 'rank': 183, 'geoid': '2052575'}, {'name': 'Savannah, Georgia', 'lat': 32.012457, 'lon': -81.194157, 'population': 149440, 'population_year': 2025, 'rank': 184, 'geoid': '1369000'}, {'name': 'Gainesville, Florida', 'lat': 29.679537, 'lon': -82.346793, 'population': 148671, 'population_year': 2025, 'rank': 185, 'geoid': '1225175'}, {'name': 'Pasadena, Texas', 'lat': 29.654996, 'lon': -95.151055, 'population': 148539, 'population_year': 2025, 'rank': 186, 'geoid': '4856000'}, {'name': 'Palm Bay, Florida', 'lat': 27.954802, 'lon': -80.664962, 'population': 148092, 'population_year': 2025, 'rank': 187, 'geoid': '1254000'}, {'name': 'Pomona, California', 'lat': 34.058494, 'lon': -117.761091, 'population': 147807, 'population_year': 2025, 'rank': 188, 'geoid': '0658072'}, {'name': 'Waco, Texas', 'lat': 31.557994, 'lon': -97.18975, 'population': 147788, 'population_year': 2025, 'rank': 189, 'geoid': '4876000'}, {'name': 'Thornton, Colorado', 'lat': 39.920433, 'lon': -104.941413, 'population': 147766, 'population_year': 2025, 'rank': 190, 'geoid': '0877290'}, {'name': 'Midland, Texas', 'lat': 32.024642, 'lon': -102.113467, 'population': 147615, 'population_year': 2025, 'rank': 191, 'geoid': '4848072'}, {'name': 'Rockford, Illinois', 'lat': 42.2593, 'lon': -89.063478, 'population': 147384, 'population_year': 2025, 'rank': 192, 'geoid': '1765000'}, {'name': 'Columbia, South Carolina', 'lat': 34.040519, 'lon': -80.906099, 'population': 147035, 'population_year': 2025, 'rank': 193, 'geoid': '4516000'}, {'name': 'Visalia, California', 'lat': 36.32921, 'lon': -119.326984, 'population': 146541, 'population_year': 2025, 'rank': 194, 'geoid': '0682954'}, {'name': 'Escondido, California', 'lat': 33.133053, 'lon': -117.074043, 'population': 146030, 'population_year': 2025, 'rank': 195, 'geoid': '0622804'}, {'name': 'Syracuse, New York', 'lat': 43.040998, 'lon': -76.143554, 'population': 144896, 'population_year': 2025, 'rank': 196, 'geoid': '3673000'}, {'name': 'Meridian, Idaho', 'lat': 43.61149, 'lon': -116.400662, 'population': 142988, 'population_year': 2025, 'rank': 197, 'geoid': '1652120'}, {'name': 'Miramar, Florida', 'lat': 25.972529, 'lon': -80.338582, 'population': 142570, 'population_year': 2025, 'rank': 198, 'geoid': '1245975'}, {'name': 'Elizabeth, New Jersey', 'lat': 40.666367, 'lon': -74.193503, 'population': 141675, 'population_year': 2025, 'rank': 199, 'geoid': '3421000'}, {'name': 'Victorville, California', 'lat': 34.527735, 'lon': -117.353579, 'population': 141395, 'population_year': 2025, 'rank': 200, 'geoid': '0682590'}, {'name': 'Round Rock, Texas', 'lat': 30.526146, 'lon': -97.663532, 'population': 141282, 'population_year': 2025, 'rank': 201, 'geoid': '4863500'}, {'name': 'Jackson, Mississippi', 'lat': 32.315834, 'lon': -90.21285, 'population': 141196, 'population_year': 2025, 'rank': 202, 'geoid': '2836000'}, {'name': 'Stamford, Connecticut', 'lat': 41.079611, 'lon': -73.54608, 'population': 139535, 'population_year': 2025, 'rank': 203, 'geoid': '0973000'}, {'name': 'Lewisville, Texas', 'lat': 33.050725, 'lon': -96.974623, 'population': 139006, 'population_year': 2025, 'rank': 204, 'geoid': '4842508'}, {'name': 'Coral Springs, Florida', 'lat': 26.270722, 'lon': -80.259301, 'population': 138783, 'population_year': 2025, 'rank': 205, 'geoid': '1214400'}, {'name': 'New Haven, Connecticut', 'lat': 41.310809, 'lon': -72.924953, 'population': 138774, 'population_year': 2025, 'rank': 206, 'geoid': '0952000'}, {'name': 'Fullerton, California', 'lat': 33.885716, 'lon': -117.928025, 'population': 138675, 'population_year': 2025, 'rank': 207, 'geoid': '0628000'}, {'name': 'Torrance, California', 'lat': 33.830453, 'lon': -118.356618, 'population': 138391, 'population_year': 2025, 'rank': 208, 'geoid': '0680000'}, {'name': 'Orange, California', 'lat': 33.786971, 'lon': -117.861265, 'population': 138365, 'population_year': 2025, 'rank': 209, 'geoid': '0653980'}, {'name': 'Cedar Rapids, Iowa', 'lat': 41.96419, 'lon': -91.67917, 'population': 137935, 'population_year': 2025, 'rank': 210, 'geoid': '1912000'}, {'name': 'West Valley City, Utah', 'lat': 40.688493, 'lon': -112.011759, 'population': 137491, 'population_year': 2025, 'rank': 211, 'geoid': '4983470'}, {'name': 'Hampton, Virginia', 'lat': 37.047961, 'lon': -76.297293, 'population': 137315, 'population_year': 2025, 'rank': 212, 'geoid': '5135000'}, {'name': 'Warren, Michigan', 'lat': 42.492904, 'lon': -83.025001, 'population': 137138, 'population_year': 2025, 'rank': 213, 'geoid': '2684000'}, {'name': 'Dayton, Ohio', 'lat': 39.784743, 'lon': -84.199632, 'population': 136688, 'population_year': 2025, 'rank': 214, 'geoid': '3921000'}, {'name': 'Fargo, North Dakota', 'lat': 46.8647, 'lon': -96.82908, 'population': 136275, 'population_year': 2025, 'rank': 215, 'geoid': '3825700'}, {'name': 'Pasadena, California', 'lat': 34.160602, 'lon': -118.137954, 'population': 135804, 'population_year': 2025, 'rank': 216, 'geoid': '0656000'}, {'name': 'Kent, Washington', 'lat': 47.390008, 'lon': -122.213528, 'population': 134871, 'population_year': 2025, 'rank': 217, 'geoid': '5335415'}, {'name': 'Carrollton, Texas', 'lat': 32.989386, 'lon': -96.89994, 'population': 134562, 'population_year': 2025, 'rank': 218, 'geoid': '4813024'}, {'name': 'Sterling Heights, Michigan', 'lat': 42.581206, 'lon': -83.030316, 'population': 133931, 'population_year': 2025, 'rank': 219, 'geoid': '2676460'}, {'name': 'Santa Clara, California', 'lat': 37.364621, 'lon': -121.967973, 'population': 133446, 'population_year': 2025, 'rank': 220, 'geoid': '0669084'}, {'name': 'Abilene, Texas', 'lat': 32.454514, 'lon': -99.738147, 'population': 131588, 'population_year': 2025, 'rank': 221, 'geoid': '4801000'}, {'name': 'Norman, Oklahoma', 'lat': 35.240569, 'lon': -97.345299, 'population': 130943, 'population_year': 2025, 'rank': 222, 'geoid': '4052500'}, {'name': 'Columbia, Missouri', 'lat': 38.94729, 'lon': -92.326387, 'population': 130851, 'population_year': 2025, 'rank': 223, 'geoid': '2915670'}, {'name': 'Pearland, Texas', 'lat': 29.555732, 'lon': -95.323012, 'population': 129930, 'population_year': 2025, 'rank': 224, 'geoid': '4856348'}, {'name': 'Clovis, California', 'lat': 36.827809, 'lon': -119.681843, 'population': 129347, 'population_year': 2025, 'rank': 225, 'geoid': '0614218'}, {'name': 'North Charleston, South Carolina', 'lat': 32.917881, 'lon': -80.065, 'population': 129245, 'population_year': 2025, 'rank': 226, 'geoid': '4550875'}, {'name': 'Athens-Clarke County unified government (balance), Georgia', 'lat': 33.949597, 'lon': -83.370088, 'population': 128612, 'population_year': 2025, 'rank': 227, 'geoid': '1303440'}, {'name': 'College Station, Texas', 'lat': 30.58516, 'lon': -96.29636, 'population': 127472, 'population_year': 2025, 'rank': 228, 'geoid': '4815976'}, {'name': 'West Palm Beach, Florida', 'lat': 26.745114, 'lon': -80.127038, 'population': 127189, 'population_year': 2025, 'rank': 229, 'geoid': '1276600'}, {'name': 'Wilmington, North Carolina', 'lat': 34.209225, 'lon': -77.885767, 'population': 126809, 'population_year': 2025, 'rank': 230, 'geoid': '3774440'}, {'name': 'Allentown, Pennsylvania', 'lat': 40.593648, 'lon': -75.478393, 'population': 126044, 'population_year': 2025, 'rank': 231, 'geoid': '4202000'}, {'name': 'Topeka, Kansas', 'lat': 39.034673, 'lon': -95.696191, 'population': 125795, 'population_year': 2025, 'rank': 232, 'geoid': '2071000'}, {'name': 'Lakeland, Florida', 'lat': 28.055496, 'lon': -81.954772, 'population': 125520, 'population_year': 2025, 'rank': 233, 'geoid': '1238250'}, {'name': 'Buckeye, Arizona', 'lat': 33.431573, 'lon': -112.641626, 'population': 125445, 'population_year': 2025, 'rank': 234, 'geoid': '0407940'}, {'name': 'Goodyear, Arizona', 'lat': 33.254031, 'lon': -112.366472, 'population': 125359, 'population_year': 2025, 'rank': 235, 'geoid': '0428380'}, {'name': 'Broken Arrow, Oklahoma', 'lat': 36.036529, 'lon': -95.780996, 'population': 124991, 'population_year': 2025, 'rank': 236, 'geoid': '4009050'}, {'name': 'Simi Valley, California', 'lat': 34.266887, 'lon': -118.748458, 'population': 124861, 'population_year': 2025, 'rank': 237, 'geoid': '0672016'}, {'name': 'Rochester, Minnesota', 'lat': 44.014299, 'lon': -92.478592, 'population': 124292, 'population_year': 2025, 'rank': 238, 'geoid': '2754880'}, {'name': 'Lafayette, Louisiana', 'lat': 30.2056, 'lon': -92.028058, 'population': 123311, 'population_year': 2025, 'rank': 239, 'geoid': '2240735'}, {'name': 'Vallejo, California', 'lat': 38.106909, 'lon': -122.262339, 'population': 123287, 'population_year': 2025, 'rank': 240, 'geoid': '0681666'}, {'name': 'Concord, California', 'lat': 37.972184, 'lon': -122.001587, 'population': 123261, 'population_year': 2025, 'rank': 241, 'geoid': '0616000'}, {'name': 'Arvada, Colorado', 'lat': 39.833728, 'lon': -105.150306, 'population': 122901, 'population_year': 2025, 'rank': 242, 'geoid': '0803455'}, {'name': 'Odessa, Texas', 'lat': 31.880461, 'lon': -102.345314, 'population': 122707, 'population_year': 2025, 'rank': 243, 'geoid': '4853388'}, {'name': 'Cambridge, Massachusetts', 'lat': 42.376043, 'lon': -71.11868, 'population': 122588, 'population_year': 2025, 'rank': 244, 'geoid': '2511000'}, {'name': 'New Braunfels, Texas', 'lat': 29.699306, 'lon': -98.115127, 'population': 122492, 'population_year': 2025, 'rank': 245, 'geoid': '4850820'}, {'name': 'Fairfield, California', 'lat': 38.261965, 'lon': -122.032389, 'population': 122489, 'population_year': 2025, 'rank': 246, 'geoid': '0623182'}, {'name': 'Ann Arbor, Michigan', 'lat': 42.276147, 'lon': -83.73086, 'population': 122233, 'population_year': 2025, 'rank': 247, 'geoid': '2603000'}, {'name': 'Thousand Oaks, California', 'lat': 34.19329, 'lon': -118.874235, 'population': 122230, 'population_year': 2025, 'rank': 248, 'geoid': '0678582'}, {'name': 'Hartford, Connecticut', 'lat': 41.765933, 'lon': -72.681579, 'population': 121981, 'population_year': 2025, 'rank': 249, 'geoid': '0937000'}, {'name': 'Berkeley, California', 'lat': 37.865673, 'lon': -122.298725, 'population': 121911, 'population_year': 2025, 'rank': 250, 'geoid': '0606000'}, {'name': 'Independence, Missouri', 'lat': 39.085469, 'lon': -94.352082, 'population': 121675, 'population_year': 2025, 'rank': 251, 'geoid': '2935000'}, {'name': 'Billings, Montana', 'lat': 45.788538, 'lon': -108.552475, 'population': 121239, 'population_year': 2025, 'rank': 252, 'geoid': '3006550'}, {'name': 'High Point, North Carolina', 'lat': 35.990803, 'lon': -79.992713, 'population': 120571, 'population_year': 2025, 'rank': 253, 'geoid': '3731400'}, {'name': 'Nampa, Idaho', 'lat': 43.586441, 'lon': -116.56389, 'population': 120384, 'population_year': 2025, 'rank': 254, 'geoid': '1656260'}, {'name': 'Lowell, Massachusetts', 'lat': 42.638995, 'lon': -71.32102, 'population': 119971, 'population_year': 2025, 'rank': 255, 'geoid': '2537000'}, {'name': 'League City, Texas', 'lat': 29.490064, 'lon': -95.109093, 'population': 119905, 'population_year': 2025, 'rank': 256, 'geoid': '4841980'}, {'name': 'Conroe, Texas', 'lat': 30.328717, 'lon': -95.4846, 'population': 119564, 'population_year': 2025, 'rank': 257, 'geoid': '4816432'}, {'name': 'Antioch, California', 'lat': 37.978336, 'lon': -121.796064, 'population': 118958, 'population_year': 2025, 'rank': 258, 'geoid': '0602252'}, {'name': 'Menifee, California', 'lat': 33.689858, 'lon': -117.184383, 'population': 118592, 'population_year': 2025, 'rank': 259, 'geoid': '0646842'}, {'name': 'Richardson, Texas', 'lat': 32.972291, 'lon': -96.708069, 'population': 118542, 'population_year': 2025, 'rank': 260, 'geoid': '4861796'}, {'name': 'Pompano Beach, Florida', 'lat': 26.241622, 'lon': -80.133851, 'population': 117211, 'population_year': 2025, 'rank': 261, 'geoid': '1258050'}, {'name': 'Las Cruces, New Mexico', 'lat': 32.326444, 'lon': -106.789695, 'population': 116978, 'population_year': 2025, 'rank': 262, 'geoid': '3539380'}, {'name': 'Manchester, New Hampshire', 'lat': 42.984941, 'lon': -71.444131, 'population': 116818, 'population_year': 2025, 'rank': 263, 'geoid': '3345140'}, {'name': 'West Jordan, Utah', 'lat': 40.602666, 'lon': -112.001255, 'population': 116812, 'population_year': 2025, 'rank': 264, 'geoid': '4982950'}, {'name': 'Westminster, Colorado', 'lat': 39.880122, 'lon': -105.061513, 'population': 116182, 'population_year': 2025, 'rank': 265, 'geoid': '0883835'}, {'name': 'Evansville, Indiana', 'lat': 37.987737, 'lon': -87.534705, 'population': 116176, 'population_year': 2025, 'rank': 266, 'geoid': '1822000'}, {'name': 'Waterbury, Connecticut', 'lat': 41.5585, 'lon': -73.036685, 'population': 115771, 'population_year': 2025, 'rank': 267, 'geoid': '0980000'}, {'name': 'Elgin, Illinois', 'lat': 42.038963, 'lon': -88.325671, 'population': 115476, 'population_year': 2025, 'rank': 268, 'geoid': '1723074'}, {'name': 'Greeley, Colorado', 'lat': 40.414034, 'lon': -104.771043, 'population': 115073, 'population_year': 2025, 'rank': 269, 'geoid': '0832155'}, {'name': 'Temecula, California', 'lat': 33.493073, 'lon': -117.131734, 'population': 114865, 'population_year': 2025, 'rank': 270, 'geoid': '0678120'}, {'name': 'Richmond, California', 'lat': 37.952278, 'lon': -122.360609, 'population': 114861, 'population_year': 2025, 'rank': 271, 'geoid': '0660620'}, {'name': 'Concord, North Carolina', 'lat': 35.392094, 'lon': -80.63551, 'population': 114598, 'population_year': 2025, 'rank': 272, 'geoid': '3714100'}, {'name': 'Provo, Utah', 'lat': 40.245312, 'lon': -111.645057, 'population': 114527, 'population_year': 2025, 'rank': 273, 'geoid': '4962470'}, {'name': 'Rio Rancho, New Mexico', 'lat': 35.28507, 'lon': -106.698867, 'population': 114419, 'population_year': 2025, 'rank': 274, 'geoid': '3563460'}, {'name': 'Clearwater, Florida', 'lat': 27.979419, 'lon': -82.771256, 'population': 114364, 'population_year': 2025, 'rank': 275, 'geoid': '1212875'}, {'name': 'Tuscaloosa, Alabama', 'lat': 33.234404, 'lon': -87.5283, 'population': 114316, 'population_year': 2025, 'rank': 276, 'geoid': '0177256'}, {'name': 'Murrieta, California', 'lat': 33.573214, 'lon': -117.191007, 'population': 114124, 'population_year': 2025, 'rank': 277, 'geoid': '0650076'}, {'name': 'Lansing, Michigan', 'lat': 42.714341, 'lon': -84.560889, 'population': 113884, 'population_year': 2025, 'rank': 278, 'geoid': '2646000'}, {'name': 'Tyler, Texas', 'lat': 32.317334, 'lon': -95.306399, 'population': 113723, 'population_year': 2025, 'rank': 279, 'geoid': '4874144'}, {'name': 'Miami Gardens, Florida', 'lat': 25.948892, 'lon': -80.243585, 'population': 113579, 'population_year': 2025, 'rank': 280, 'geoid': '1245060'}, {'name': 'Everett, Washington', 'lat': 47.965413, 'lon': -122.189895, 'population': 113567, 'population_year': 2025, 'rank': 281, 'geoid': '5322640'}, {'name': 'Allen, Texas', 'lat': 33.107224, 'lon': -96.674676, 'population': 113447, 'population_year': 2025, 'rank': 282, 'geoid': '4801924'}, {'name': 'Springfield, Illinois', 'lat': 39.791063, 'lon': -89.644572, 'population': 112989, 'population_year': 2025, 'rank': 283, 'geoid': '1772000'}, {'name': 'Beaumont, Texas', 'lat': 30.084912, 'lon': -94.14533, 'population': 112967, 'population_year': 2025, 'rank': 284, 'geoid': '4807000'}, {'name': 'South Fulton, Georgia', 'lat': 33.63572, 'lon': -84.583417, 'population': 112820, 'population_year': 2025, 'rank': 285, 'geoid': '1372122'}, {'name': 'Carlsbad, California', 'lat': 33.129284, 'lon': -117.284183, 'population': 112260, 'population_year': 2025, 'rank': 286, 'geoid': '0611194'}, {'name': 'Sparks, Nevada', 'lat': 39.574341, 'lon': -119.715154, 'population': 111902, 'population_year': 2025, 'rank': 287, 'geoid': '3268400'}, {'name': 'Gresham, Oregon', 'lat': 45.502319, 'lon': -122.441609, 'population': 111513, 'population_year': 2025, 'rank': 288, 'geoid': '4131250'}, {'name': 'Santa Maria, California', 'lat': 34.933076, 'lon': -120.443559, 'population': 111390, 'population_year': 2025, 'rank': 289, 'geoid': '0669196'}, {'name': 'Hillsboro, Oregon', 'lat': 45.526798, 'lon': -122.935395, 'population': 111126, 'population_year': 2025, 'rank': 290, 'geoid': '4134100'}, {'name': 'Peoria, Illinois', 'lat': 40.751641, 'lon': -89.617198, 'population': 110920, 'population_year': 2025, 'rank': 291, 'geoid': '1759000'}, {'name': 'Davie, Florida', 'lat': 26.079169, 'lon': -80.283013, 'population': 110851, 'population_year': 2025, 'rank': 292, 'geoid': '1216475'}, {'name': 'Edinburg, Texas', 'lat': 26.318374, 'lon': -98.15348, 'population': 110700, 'population_year': 2025, 'rank': 293, 'geoid': '4822660'}, {'name': 'Pueblo, Colorado', 'lat': 38.269228, 'lon': -104.610816, 'population': 110404, 'population_year': 2025, 'rank': 294, 'geoid': '0862000'}, {'name': 'San Buenaventura (Ventura), California', 'lat': 34.26778, 'lon': -119.254206, 'population': 109914, 'population_year': 2025, 'rank': 295, 'geoid': '0665042'}, {'name': 'Palm Coast, Florida', 'lat': 29.536837, 'lon': -81.242627, 'population': 109886, 'population_year': 2025, 'rank': 296, 'geoid': '1254200'}, {'name': 'Costa Mesa, California', 'lat': 33.665905, 'lon': -117.912336, 'population': 108881, 'population_year': 2025, 'rank': 297, 'geoid': '0616532'}, {'name': 'St. George, Utah', 'lat': 37.077006, 'lon': -113.576534, 'population': 108713, 'population_year': 2025, 'rank': 298, 'geoid': '4965330'}, {'name': 'Centennial, Colorado', 'lat': 39.590856, 'lon': -104.863754, 'population': 108658, 'population_year': 2025, 'rank': 299, 'geoid': '0812815'}, {'name': 'Downey, California', 'lat': 33.938237, 'lon': -118.130856, 'population': 108468, 'population_year': 2025, 'rank': 300, 'geoid': '0619766'}, {'name': 'Spokane Valley, Washington', 'lat': 47.663353, 'lon': -117.23278, 'population': 108405, 'population_year': 2025, 'rank': 301, 'geoid': '5367167'}, {'name': 'Sugar Land, Texas', 'lat': 29.592764, 'lon': -95.633801, 'population': 107726, 'population_year': 2025, 'rank': 302, 'geoid': '4870808'}, {'name': "Lee's Summit, Missouri", 'lat': 38.921601, 'lon': -94.384763, 'population': 107514, 'population_year': 2025, 'rank': 303, 'geoid': '2941348'}, {'name': 'Bend, Oregon', 'lat': 44.056683, 'lon': -121.307991, 'population': 107342, 'population_year': 2025, 'rank': 304, 'geoid': '4105800'}, {'name': 'Jurupa Valley, California', 'lat': 34.002591, 'lon': -117.467612, 'population': 107311, 'population_year': 2025, 'rank': 305, 'geoid': '0637692'}, {'name': 'Georgetown, Texas', 'lat': 30.668136, 'lon': -97.698744, 'population': 106907, 'population_year': 2025, 'rank': 306, 'geoid': '4829336'}, {'name': 'Green Bay, Wisconsin', 'lat': 44.521542, 'lon': -87.986568, 'population': 106675, 'population_year': 2025, 'rank': 307, 'geoid': '5531000'}, {'name': 'Fayetteville, Arkansas', 'lat': 36.071455, 'lon': -94.166564, 'population': 106623, 'population_year': 2025, 'rank': 308, 'geoid': '0523290'}, {'name': 'Rialto, California', 'lat': 34.117427, 'lon': -117.389211, 'population': 106554, 'population_year': 2025, 'rank': 309, 'geoid': '0660466'}, {'name': 'Brockton, Massachusetts', 'lat': 42.082543, 'lon': -71.024638, 'population': 106134, 'population_year': 2025, 'rank': 310, 'geoid': '2509000'}, {'name': 'Boulder, Colorado', 'lat': 40.024431, 'lon': -105.251251, 'population': 105689, 'population_year': 2025, 'rank': 311, 'geoid': '0807850'}, {'name': 'Carmel, Indiana', 'lat': 39.965479, 'lon': -86.148369, 'population': 105634, 'population_year': 2025, 'rank': 312, 'geoid': '1810342'}, {'name': 'Dearborn, Michigan', 'lat': 42.313057, 'lon': -83.211488, 'population': 105611, 'population_year': 2025, 'rank': 313, 'geoid': '2621000'}, {'name': 'West Covina, California', 'lat': 34.055941, 'lon': -117.909937, 'population': 105301, 'population_year': 2025, 'rank': 314, 'geoid': '0684200'}, {'name': 'Yuma, Arizona', 'lat': 32.516286, 'lon': -114.521782, 'population': 105227, 'population_year': 2025, 'rank': 315, 'geoid': '0485540'}, {'name': 'Chico, California', 'lat': 39.758951, 'lon': -121.81772, 'population': 105081, 'population_year': 2025, 'rank': 316, 'geoid': '0613014'}, {'name': 'El Monte, California', 'lat': 34.074633, 'lon': -118.029136, 'population': 105075, 'population_year': 2025, 'rank': 317, 'geoid': '0622230'}, {'name': 'Sandy Springs, Georgia', 'lat': 33.931501, 'lon': -84.368886, 'population': 105013, 'population_year': 2025, 'rank': 318, 'geoid': '1368516'}, {'name': 'Renton, Washington', 'lat': 47.47919, 'lon': -122.194613, 'population': 104975, 'population_year': 2025, 'rank': 319, 'geoid': '5357745'}, {'name': 'Fishers, Indiana', 'lat': 39.96183, 'lon': -85.968364, 'population': 104812, 'population_year': 2025, 'rank': 320, 'geoid': '1823278'}, {'name': 'Suffolk, Virginia', 'lat': 36.697157, 'lon': -76.634781, 'population': 104699, 'population_year': 2025, 'rank': 321, 'geoid': '5176432'}, {'name': 'Lynn, Massachusetts', 'lat': 42.474762, 'lon': -70.96203, 'population': 104236, 'population_year': 2025, 'rank': 322, 'geoid': '2537490'}, {'name': 'Vacaville, California', 'lat': 38.358621, 'lon': -121.968601, 'population': 103850, 'population_year': 2025, 'rank': 323, 'geoid': '0681554'}, {'name': 'San Mateo, California', 'lat': 37.56031, 'lon': -122.3106, 'population': 103337, 'population_year': 2025, 'rank': 324, 'geoid': '0668252'}, {'name': 'South Bend, Indiana', 'lat': 41.676643, 'lon': -86.268809, 'population': 103201, 'population_year': 2025, 'rank': 325, 'geoid': '1871000'}, {'name': 'Quincy, Massachusetts', 'lat': 42.261006, 'lon': -71.008988, 'population': 103173, 'population_year': 2025, 'rank': 326, 'geoid': '2555745'}, {'name': 'Burbank, California', 'lat': 34.190079, 'lon': -118.326405, 'population': 102988, 'population_year': 2025, 'rank': 327, 'geoid': '0608954'}, {'name': 'Hesperia, California', 'lat': 34.397038, 'lon': -117.315198, 'population': 102605, 'population_year': 2025, 'rank': 328, 'geoid': '0633434'}, {'name': 'Wichita Falls, Texas', 'lat': 33.906654, 'lon': -98.525848, 'population': 101951, 'population_year': 2025, 'rank': 329, 'geoid': '4879000'}, {'name': 'Tracy, California', 'lat': 37.727396, 'lon': -121.452195, 'population': 101901, 'population_year': 2025, 'rank': 330, 'geoid': '0680238'}, {'name': 'New Bedford, Massachusetts', 'lat': 41.661303, 'lon': -70.937913, 'population': 101834, 'population_year': 2025, 'rank': 331, 'geoid': '2545000'}, {'name': 'El Cajon, California', 'lat': 32.801673, 'lon': -116.960468, 'population': 101755, 'population_year': 2025, 'rank': 332, 'geoid': '0621712'}, {'name': 'Albany, New York', 'lat': 42.665745, 'lon': -73.798353, 'population': 101698, 'population_year': 2025, 'rank': 333, 'geoid': '3601000'}, {'name': 'Inglewood, California', 'lat': 33.956068, 'lon': -118.344274, 'population': 101662, 'population_year': 2025, 'rank': 334, 'geoid': '0636546'}, {'name': 'Boca Raton, Florida', 'lat': 26.37269, 'lon': -80.103711, 'population': 101582, 'population_year': 2025, 'rank': 335, 'geoid': '1207300'}, {'name': 'Fort Myers, Florida', 'lat': 26.617839, 'lon': -81.831725, 'population': 101581, 'population_year': 2025, 'rank': 336, 'geoid': '1224125'}, {'name': 'Daly City, California', 'lat': 37.701684, 'lon': -122.464968, 'population': 101261, 'population_year': 2025, 'rank': 337, 'geoid': '0617918'}, {'name': 'Avondale, Arizona', 'lat': 33.313236, 'lon': -112.328928, 'population': 100983, 'population_year': 2025, 'rank': 338, 'geoid': '0404720'}, {'name': 'San Angelo, Texas', 'lat': 31.441078, 'lon': -100.450499, 'population': 100640, 'population_year': 2025, 'rank': 339, 'geoid': '4864472'}, {'name': 'Edmond, Oklahoma', 'lat': 35.673807, 'lon': -97.413076, 'population': 100479, 'population_year': 2025, 'rank': 340, 'geoid': '4023200'}, {'name': 'Davenport, Iowa', 'lat': 41.55682, 'lon': -90.603948, 'population': 100358, 'population_year': 2025, 'rank': 341, 'geoid': '1919000'}, {'name': 'Deltona, Florida', 'lat': 28.905121, 'lon': -81.210978, 'population': 100267, 'population_year': 2025, 'rank': 342, 'geoid': '1217200'}, {'name': 'Longmont, Colorado', 'lat': 40.168199, 'lon': -105.100522, 'population': 100109, 'population_year': 2025, 'rank': 343, 'geoid': '0845970'}, {'name': 'Federal Way, Washington', 'lat': 47.311596, 'lon': -122.337757, 'population': 99729, 'population_year': 2025, 'rank': 344, 'geoid': '5323515'}, {'name': 'Merced, California', 'lat': 37.31138, 'lon': -120.470408, 'population': 99724, 'population_year': 2025, 'rank': 345, 'geoid': '0646898'}, {'name': 'Kenosha, Wisconsin', 'lat': 42.587526, 'lon': -87.879996, 'population': 99239, 'population_year': 2025, 'rank': 346, 'geoid': '5539225'}, {'name': 'Plantation, Florida', 'lat': 26.125573, 'lon': -80.261818, 'population': 99183, 'population_year': 2025, 'rank': 347, 'geoid': '1257425'}, {'name': 'Roanoke, Virginia', 'lat': 37.278458, 'lon': -79.958174, 'population': 99111, 'population_year': 2025, 'rank': 348, 'geoid': '5168000'}, {'name': 'Sunrise, Florida', 'lat': 26.171601, 'lon': -80.261633, 'population': 98846, 'population_year': 2025, 'rank': 349, 'geoid': '1269700'}, {'name': 'Temple, Texas', 'lat': 31.104936, 'lon': -97.388512, 'population': 98412, 'population_year': 2025, 'rank': 350, 'geoid': '4872176'}, {'name': 'Vista, California', 'lat': 33.189528, 'lon': -117.238582, 'population': 98274, 'population_year': 2025, 'rank': 351, 'geoid': '0682996'}, {'name': 'Beaverton, Oregon', 'lat': 45.478054, 'lon': -122.817075, 'population': 97842, 'population_year': 2025, 'rank': 352, 'geoid': '4105350'}, {'name': 'Yakima, Washington', 'lat': 46.590938, 'lon': -120.5494, 'population': 97458, 'population_year': 2025, 'rank': 353, 'geoid': '5380010'}, {'name': 'Kirkland, Washington', 'lat': 47.696658, 'lon': -122.20417, 'population': 97410, 'population_year': 2025, 'rank': 354, 'geoid': '5335940'}, {'name': 'Norwalk, California', 'lat': 33.9076, 'lon': -118.083453, 'population': 97104, 'population_year': 2025, 'rank': 355, 'geoid': '0652526'}, {'name': 'Chino, California', 'lat': 33.975627, 'lon': -117.667351, 'population': 96957, 'population_year': 2025, 'rank': 356, 'geoid': '0613210'}, {'name': 'Portsmouth, Virginia', 'lat': 36.859339, 'lon': -76.356973, 'population': 96777, 'population_year': 2025, 'rank': 357, 'geoid': '5164000'}, {'name': 'Manteca, California', 'lat': 37.792839, 'lon': -121.226076, 'population': 96693, 'population_year': 2025, 'rank': 358, 'geoid': '0645484'}, {'name': 'North Port, Florida', 'lat': 27.058166, 'lon': -82.198044, 'population': 96551, 'population_year': 2025, 'rank': 359, 'geoid': '1249675'}, {'name': 'Greenville, North Carolina', 'lat': 35.596431, 'lon': -77.375256, 'population': 96443, 'population_year': 2025, 'rank': 360, 'geoid': '3728080'}, {'name': 'Bellingham, Washington', 'lat': 48.753442, 'lon': -122.470179, 'population': 96395, 'population_year': 2025, 'rank': 361, 'geoid': '5305280'}, {'name': 'Lawrence, Kansas', 'lat': 38.959551, 'lon': -95.265468, 'population': 96367, 'population_year': 2025, 'rank': 362, 'geoid': '2038900'}, {'name': "O'Fallon, Missouri", 'lat': 38.778825, 'lon': -90.72178, 'population': 96101, 'population_year': 2025, 'rank': 363, 'geoid': '2954074'}, {'name': 'Reading, Pennsylvania', 'lat': 40.33922, 'lon': -75.926277, 'population': 95832, 'population_year': 2025, 'rank': 364, 'geoid': '4263624'}, {'name': 'Mount Pleasant, South Carolina', 'lat': 32.808382, 'lon': -79.865038, 'population': 95469, 'population_year': 2025, 'rank': 365, 'geoid': '4548535'}, {'name': 'Lehi, Utah', 'lat': 40.41708, 'lon': -111.871147, 'population': 95313, 'population_year': 2025, 'rank': 366, 'geoid': '4944320'}, {'name': 'Fall River, Massachusetts', 'lat': 41.725351, 'lon': -71.094162, 'population': 95298, 'population_year': 2025, 'rank': 367, 'geoid': '2523000'}, {'name': 'Orem, Utah', 'lat': 40.298067, 'lon': -111.699463, 'population': 95214, 'population_year': 2025, 'rank': 368, 'geoid': '4957300'}, {'name': 'San Marcos, California', 'lat': 33.132567, 'lon': -117.169892, 'population': 94908, 'population_year': 2025, 'rank': 369, 'geoid': '0668196'}, {'name': 'Norwalk, Connecticut', 'lat': 41.092739, 'lon': -73.419796, 'population': 94508, 'population_year': 2025, 'rank': 370, 'geoid': '0955990'}, {'name': 'Indio, California', 'lat': 33.731639, 'lon': -116.235971, 'population': 94269, 'population_year': 2025, 'rank': 371, 'geoid': '0636448'}, {'name': 'Redding, California', 'lat': 40.570277, 'lon': -122.366766, 'population': 94092, 'population_year': 2025, 'rank': 372, 'geoid': '0659920'}, {'name': 'Hemet, California', 'lat': 33.734068, 'lon': -116.996808, 'population': 93649, 'population_year': 2025, 'rank': 373, 'geoid': '0633182'}, {'name': 'Hoover, Alabama', 'lat': 33.375128, 'lon': -86.809416, 'population': 93550, 'population_year': 2025, 'rank': 374, 'geoid': '0135896'}, {'name': 'Asheville, North Carolina', 'lat': 35.570972, 'lon': -82.552725, 'population': 93523, 'population_year': 2025, 'rank': 375, 'geoid': '3702140'}, {'name': 'Livonia, Michigan', 'lat': 42.397183, 'lon': -83.372319, 'population': 92603, 'population_year': 2025, 'rank': 376, 'geoid': '2649000'}, {'name': 'Nashua, New Hampshire', 'lat': 42.749074, 'lon': -71.490544, 'population': 92435, 'population_year': 2025, 'rank': 377, 'geoid': '3350260'}, {'name': 'Sandy, Utah', 'lat': 40.571714, 'lon': -111.84987, 'population': 92386, 'population_year': 2025, 'rank': 378, 'geoid': '4967440'}, {'name': 'Frederick, Maryland', 'lat': 39.436891, 'lon': -77.411952, 'population': 92059, 'population_year': 2025, 'rank': 379, 'geoid': '2430325'}, {'name': 'Bryan, Texas', 'lat': 30.666016, 'lon': -96.381049, 'population': 91996, 'population_year': 2025, 'rank': 380, 'geoid': '4810912'}, {'name': 'Folsom, California', 'lat': 38.666597, 'lon': -121.141635, 'population': 91983, 'population_year': 2025, 'rank': 381, 'geoid': '0624638'}, {'name': 'Erie, Pennsylvania', 'lat': 42.116594, 'lon': -80.073503, 'population': 91838, 'population_year': 2025, 'rank': 382, 'geoid': '4224000'}, {'name': 'Trenton, New Jersey', 'lat': 40.223841, 'lon': -74.763624, 'population': 91506, 'population_year': 2025, 'rank': 383, 'geoid': '3474000'}, {'name': 'Roswell, Georgia', 'lat': 34.039453, 'lon': -84.350946, 'population': 91505, 'population_year': 2025, 'rank': 384, 'geoid': '1367284'}, {'name': 'Champaign, Illinois', 'lat': 40.114099, 'lon': -88.274619, 'population': 91195, 'population_year': 2025, 'rank': 385, 'geoid': '1712385'}, {'name': 'Leander, Texas', 'lat': 30.574273, 'lon': -97.861741, 'population': 91132, 'population_year': 2025, 'rank': 386, 'geoid': '4842016'}, {'name': 'Clifton, New Jersey', 'lat': 40.862137, 'lon': -74.160393, 'population': 91127, 'population_year': 2025, 'rank': 387, 'geoid': '3413690'}, {'name': 'Fort Smith, Arkansas', 'lat': 35.349276, 'lon': -94.370883, 'population': 90855, 'population_year': 2025, 'rank': 388, 'geoid': '0524550'}, {'name': 'Carson, California', 'lat': 33.840367, 'lon': -118.249574, 'population': 90808, 'population_year': 2025, 'rank': 389, 'geoid': '0611530'}, {'name': 'Newton, Massachusetts', 'lat': 42.331768, 'lon': -71.2084, 'population': 90741, 'population_year': 2025, 'rank': 390, 'geoid': '2545560'}, {'name': 'Springdale, Arkansas', 'lat': 36.191438, 'lon': -94.155062, 'population': 90685, 'population_year': 2025, 'rank': 391, 'geoid': '0566080'}, {'name': 'Lawton, Oklahoma', 'lat': 34.617172, 'lon': -98.4214, 'population': 90503, 'population_year': 2025, 'rank': 392, 'geoid': '4041850'}, {'name': 'Compton, California', 'lat': 33.894047, 'lon': -118.227469, 'population': 90500, 'population_year': 2025, 'rank': 393, 'geoid': '0615044'}, {'name': 'Mission Viejo, California', 'lat': 33.609335, 'lon': -117.656471, 'population': 90484, 'population_year': 2025, 'rank': 394, 'geoid': '0648256'}, {'name': 'Franklin, Tennessee', 'lat': 35.914025, 'lon': -86.852161, 'population': 90226, 'population_year': 2025, 'rank': 395, 'geoid': '4727740'}, {'name': 'Santa Monica, California', 'lat': 34.010911, 'lon': -118.498245, 'population': 90082, 'population_year': 2025, 'rank': 396, 'geoid': '0670000'}, {'name': 'South Gate, California', 'lat': 33.944159, 'lon': -118.192761, 'population': 90071, 'population_year': 2025, 'rank': 397, 'geoid': '0673080'}, {'name': 'Santa Fe, New Mexico', 'lat': 35.661981, 'lon': -105.981815, 'population': 89837, 'population_year': 2025, 'rank': 398, 'geoid': '3570500'}, {'name': 'Queen Creek, Arizona', 'lat': 33.239425, 'lon': -111.613319, 'population': 89770, 'population_year': 2025, 'rank': 399, 'geoid': '0458150'}, {'name': 'Ogden, Utah', 'lat': 41.228391, 'lon': -111.968147, 'population': 89510, 'population_year': 2025, 'rank': 400, 'geoid': '4955980'}, {'name': 'Deerfield Beach, Florida', 'lat': 26.311716, 'lon': -80.125378, 'population': 89339, 'population_year': 2025, 'rank': 401, 'geoid': '1216725'}, {'name': 'Lawrence, Massachusetts', 'lat': 42.700273, 'lon': -71.161357, 'population': 89320, 'population_year': 2025, 'rank': 402, 'geoid': '2534550'}, {'name': 'Bloomington, Minnesota', 'lat': 44.829666, 'lon': -93.315217, 'population': 89034, 'population_year': 2025, 'rank': 403, 'geoid': '2706616'}, {'name': 'Danbury, Connecticut', 'lat': 41.398741, 'lon': -73.478103, 'population': 89033, 'population_year': 2025, 'rank': 404, 'geoid': '0918430'}, {'name': 'Mission, Texas', 'lat': 26.20406, 'lon': -98.325221, 'population': 88992, 'population_year': 2025, 'rank': 405, 'geoid': '4848768'}, {'name': 'Westminster, California', 'lat': 33.752292, 'lon': -117.993868, 'population': 88966, 'population_year': 2025, 'rank': 406, 'geoid': '0684550'}, {'name': 'Troy, Michigan', 'lat': 42.583882, 'lon': -83.145533, 'population': 88733, 'population_year': 2025, 'rank': 407, 'geoid': '2680700'}, {'name': 'Daytona Beach, Florida', 'lat': 29.19071, 'lon': -81.097083, 'population': 88471, 'population_year': 2025, 'rank': 408, 'geoid': '1216525'}, {'name': 'Kennewick, Washington', 'lat': 46.197622, 'lon': -119.175923, 'population': 88366, 'population_year': 2025, 'rank': 409, 'geoid': '5335275'}, {'name': 'Duluth, Minnesota', 'lat': 46.774458, 'lon': -92.134135, 'population': 88330, 'population_year': 2025, 'rank': 410, 'geoid': '2717000'}, {'name': 'Waukegan, Illinois', 'lat': 42.369447, 'lon': -87.870898, 'population': 87940, 'population_year': 2025, 'rank': 411, 'geoid': '1779293'}, {'name': 'Warner Robins, Georgia', 'lat': 32.597096, 'lon': -83.653936, 'population': 87761, 'population_year': 2025, 'rank': 412, 'geoid': '1380508'}, {'name': 'South Jordan, Utah', 'lat': 40.555007, 'lon': -111.992337, 'population': 87614, 'population_year': 2025, 'rank': 413, 'geoid': '4970850'}, {'name': 'Rancho Cordova, California', 'lat': 38.577079, 'lon': -121.236187, 'population': 87554, 'population_year': 2025, 'rank': 414, 'geoid': '0659444'}, {'name': 'Melbourne, Florida', 'lat': 28.110438, 'lon': -80.662717, 'population': 87097, 'population_year': 2025, 'rank': 415, 'geoid': '1243975'}, {'name': 'Gastonia, North Carolina', 'lat': 35.248999, 'lon': -81.184834, 'population': 87067, 'population_year': 2025, 'rank': 416, 'geoid': '3725580'}, {'name': 'Baytown, Texas', 'lat': 29.76478, 'lon': -94.967457, 'population': 86561, 'population_year': 2025, 'rank': 417, 'geoid': '4806128'}, {'name': 'Medford, Oregon', 'lat': 42.336006, 'lon': -122.851762, 'population': 86494, 'population_year': 2025, 'rank': 418, 'geoid': '4147000'}, {'name': 'Santa Barbara, California', 'lat': 34.403592, 'lon': -119.713714, 'population': 86422, 'population_year': 2025, 'rank': 419, 'geoid': '0669070'}, {'name': 'Sioux City, Iowa', 'lat': 42.49538, 'lon': -96.389495, 'population': 86356, 'population_year': 2025, 'rank': 420, 'geoid': '1973335'}, {'name': 'Citrus Heights, California', 'lat': 38.69481, 'lon': -121.287953, 'population': 86348, 'population_year': 2025, 'rank': 421, 'geoid': '0613588'}, {'name': 'Lake Forest, California', 'lat': 33.654946, 'lon': -117.675848, 'population': 86333, 'population_year': 2025, 'rank': 422, 'geoid': '0639496'}, {'name': 'Auburn, Washington', 'lat': 47.304657, 'lon': -122.210696, 'population': 86301, 'population_year': 2025, 'rank': 423, 'geoid': '5303180'}, {'name': 'Homestead, Florida', 'lat': 25.465912, 'lon': -80.445993, 'population': 86242, 'population_year': 2025, 'rank': 424, 'geoid': '1232275'}, {'name': 'San Ramon, California', 'lat': 37.765258, 'lon': -121.931987, 'population': 86209, 'population_year': 2025, 'rank': 425, 'geoid': '0668378'}, {'name': 'New Rochelle, New York', 'lat': 40.923243, 'lon': -73.779344, 'population': 85864, 'population_year': 2025, 'rank': 426, 'geoid': '3650617'}, {'name': 'Whittier, California', 'lat': 33.966827, 'lon': -118.020122, 'population': 85815, 'population_year': 2025, 'rank': 427, 'geoid': '0685292'}, {'name': 'Kissimmee, Florida', 'lat': 28.30278, 'lon': -81.417831, 'population': 85591, 'population_year': 2025, 'rank': 428, 'geoid': '1236950'}, {'name': 'Mountain View, California', 'lat': 37.399686, 'lon': -122.079269, 'population': 85438, 'population_year': 2025, 'rank': 429, 'geoid': '0649670'}, {'name': 'San Leandro, California', 'lat': 37.703368, 'lon': -122.163036, 'population': 85353, 'population_year': 2025, 'rank': 430, 'geoid': '0668084'}, {'name': 'Layton, Utah', 'lat': 41.077423, 'lon': -111.960727, 'population': 85308, 'population_year': 2025, 'rank': 431, 'geoid': '4943660'}, {'name': 'Auburn, Alabama', 'lat': 32.607122, 'lon': -85.490959, 'population': 85113, 'population_year': 2025, 'rank': 432, 'geoid': '0103076'}, {'name': 'Cranston, Rhode Island', 'lat': 41.769734, 'lon': -71.485049, 'population': 84647, 'population_year': 2025, 'rank': 433, 'geoid': '4419180'}, {'name': 'Mansfield, Texas', 'lat': 32.569188, 'lon': -97.120532, 'population': 84444, 'population_year': 2025, 'rank': 434, 'geoid': '4846452'}, {'name': 'Somerville, Massachusetts', 'lat': 42.390445, 'lon': -71.101033, 'population': 84211, 'population_year': 2025, 'rank': 435, 'geoid': '2562535'}, {'name': 'Warwick, Rhode Island', 'lat': 41.703085, 'lon': -71.42031, 'population': 84187, 'population_year': 2025, 'rank': 436, 'geoid': '4474300'}, {'name': 'Castle Rock, Colorado', 'lat': 39.376194, 'lon': -104.852922, 'population': 83815, 'population_year': 2025, 'rank': 437, 'geoid': '0812415'}, {'name': 'Brooklyn Park, Minnesota', 'lat': 45.110906, 'lon': -93.349088, 'population': 83543, 'population_year': 2025, 'rank': 438, 'geoid': '2707966'}, {'name': 'Livermore, California', 'lat': 37.686977, 'lon': -121.759781, 'population': 83457, 'population_year': 2025, 'rank': 439, 'geoid': '0641992'}, {'name': 'Bloomington, Indiana', 'lat': 39.1637, 'lon': -86.524264, 'population': 83307, 'population_year': 2025, 'rank': 440, 'geoid': '1805860'}, {'name': 'Jonesboro, Arkansas', 'lat': 35.819755, 'lon': -90.679033, 'population': 83296, 'population_year': 2025, 'rank': 441, 'geoid': '0535710'}, {'name': 'Farmington Hills, Michigan', 'lat': 42.485648, 'lon': -83.375961, 'population': 83291, 'population_year': 2025, 'rank': 442, 'geoid': '2627440'}, {'name': 'Perris, California', 'lat': 33.789849, 'lon': -117.222171, 'population': 83237, 'population_year': 2025, 'rank': 443, 'geoid': '0656700'}, {'name': 'Longview, Texas', 'lat': 32.520234, 'lon': -94.761114, 'population': 83236, 'population_year': 2025, 'rank': 444, 'geoid': '4843888'}, {'name': 'Pasco, Washington', 'lat': 46.266113, 'lon': -119.121426, 'population': 82848, 'population_year': 2025, 'rank': 445, 'geoid': '5353545'}, {'name': 'Hawthorne, California', 'lat': 33.914775, 'lon': -118.348083, 'population': 82741, 'population_year': 2025, 'rank': 446, 'geoid': '0632548'}, {'name': 'Lake Charles, Louisiana', 'lat': 30.19902, 'lon': -93.210835, 'population': 82676, 'population_year': 2025, 'rank': 447, 'geoid': '2241155'}, {'name': 'Redmond, Washington', 'lat': 47.677924, 'lon': -122.115336, 'population': 82506, 'population_year': 2025, 'rank': 448, 'geoid': '5357535'}, {'name': 'Boynton Beach, Florida', 'lat': 26.528334, 'lon': -80.080722, 'population': 82396, 'population_year': 2025, 'rank': 449, 'geoid': '1207875'}, {'name': 'Westland, Michigan', 'lat': 42.319173, 'lon': -83.380778, 'population': 82333, 'population_year': 2025, 'rank': 450, 'geoid': '2686000'}, {'name': 'Redwood City, California', 'lat': 37.515274, 'lon': -122.213672, 'population': 82178, 'population_year': 2025, 'rank': 451, 'geoid': '0660102'}, {'name': 'Newport Beach, California', 'lat': 33.626595, 'lon': -117.865392, 'population': 81977, 'population_year': 2025, 'rank': 452, 'geoid': '0651182'}, {'name': 'Cicero, Illinois', 'lat': 41.844537, 'lon': -87.75929, 'population': 81858, 'population_year': 2025, 'rank': 453, 'geoid': '1714351'}, {'name': 'Buena Park, California', 'lat': 33.857353, 'lon': -118.007373, 'population': 81741, 'population_year': 2025, 'rank': 454, 'geoid': '0608786'}, {'name': 'Doral, Florida', 'lat': 25.815956, 'lon': -80.357556, 'population': 81634, 'population_year': 2025, 'rank': 455, 'geoid': '1217935'}, {'name': 'Miami Beach, Florida', 'lat': 25.810596, 'lon': -80.148852, 'population': 81594, 'population_year': 2025, 'rank': 456, 'geoid': '1245025'}, {'name': 'Woodbury, Minnesota', 'lat': 44.906283, 'lon': -92.923703, 'population': 81558, 'population_year': 2025, 'rank': 457, 'geoid': '2771428'}, {'name': 'Loveland, Colorado', 'lat': 40.416905, 'lon': -105.063111, 'population': 81387, 'population_year': 2025, 'rank': 458, 'geoid': '0846465'}, {'name': 'Lynchburg, Virginia', 'lat': 37.399016, 'lon': -79.195458, 'population': 81347, 'population_year': 2025, 'rank': 459, 'geoid': '5147672'}, {'name': 'Pharr, Texas', 'lat': 26.163436, 'lon': -98.19389, 'population': 80830, 'population_year': 2025, 'rank': 460, 'geoid': '4857200'}, {'name': 'Largo, Florida', 'lat': 27.908685, 'lon': -82.774174, 'population': 80690, 'population_year': 2025, 'rank': 461, 'geoid': '1239425'}, {'name': 'Rapid City, South Dakota', 'lat': 44.071071, 'lon': -103.217924, 'population': 80589, 'population_year': 2025, 'rank': 462, 'geoid': '4652980'}, {'name': 'Apex, North Carolina', 'lat': 35.725577, 'lon': -78.879919, 'population': 80419, 'population_year': 2025, 'rank': 463, 'geoid': '3701520'}, {'name': 'Johns Creek, Georgia', 'lat': 34.032739, 'lon': -84.203848, 'population': 80401, 'population_year': 2025, 'rank': 464, 'geoid': '1342425'}, {'name': 'Alhambra, California', 'lat': 34.083571, 'lon': -118.136444, 'population': 79820, 'population_year': 2025, 'rank': 465, 'geoid': '0600884'}, {'name': 'Bethlehem, Pennsylvania', 'lat': 40.626424, 'lon': -75.367898, 'population': 79644, 'population_year': 2025, 'rank': 466, 'geoid': '4206088'}, {'name': 'Flower Mound, Texas', 'lat': 33.03792, 'lon': -97.113319, 'population': 79540, 'population_year': 2025, 'rank': 467, 'geoid': '4826232'}, {'name': 'Upland, California', 'lat': 34.116073, 'lon': -117.659922, 'population': 79446, 'population_year': 2025, 'rank': 468, 'geoid': '0681344'}, {'name': 'Flint, Michigan', 'lat': 43.02442, 'lon': -83.691971, 'population': 79306, 'population_year': 2025, 'rank': 469, 'geoid': '2629000'}, {'name': 'Lakeville, Minnesota', 'lat': 44.676134, 'lon': -93.251743, 'population': 79270, 'population_year': 2025, 'rank': 470, 'geoid': '2735180'}, {'name': 'Broomfield, Colorado', 'lat': 39.953877, 'lon': -105.050898, 'population': 79174, 'population_year': 2025, 'rank': 471, 'geoid': '0809280'}, {'name': 'Cedar Park, Texas', 'lat': 30.510177, 'lon': -97.818626, 'population': 79032, 'population_year': 2025, 'rank': 472, 'geoid': '4813552'}, {'name': 'Plymouth, Minnesota', 'lat': 45.022312, 'lon': -93.462883, 'population': 78942, 'population_year': 2025, 'rank': 473, 'geoid': '2751730'}, {'name': 'Missoula, Montana', 'lat': 46.874359, 'lon': -114.026136, 'population': 78903, 'population_year': 2025, 'rank': 474, 'geoid': '3050200'}, {'name': 'Mableton, Georgia', 'lat': 33.812998, 'lon': -84.576946, 'population': 78820, 'population_year': 2025, 'rank': 475, 'geoid': '1348288'}, {'name': 'Bloomington, Illinois', 'lat': 40.475777, 'lon': -88.969912, 'population': 78804, 'population_year': 2025, 'rank': 476, 'geoid': '1706613'}, {'name': 'Milpitas, California', 'lat': 37.433136, 'lon': -121.890934, 'population': 78596, 'population_year': 2025, 'rank': 477, 'geoid': '0647766'}, {'name': 'Wyoming, Michigan', 'lat': 42.890317, 'lon': -85.706733, 'population': 78588, 'population_year': 2025, 'rank': 478, 'geoid': '2688940'}, {'name': 'Parma, Ohio', 'lat': 41.383569, 'lon': -81.728641, 'population': 78581, 'population_year': 2025, 'rank': 479, 'geoid': '3961000'}, {'name': 'St. George, Louisiana', 'lat': 30.363994, 'lon': -91.026354, 'population': 78536, 'population_year': 2025, 'rank': 480, 'geoid': '2267303'}, {'name': 'Bowling Green, Kentucky', 'lat': 36.976832, 'lon': -86.433661, 'population': 78505, 'population_year': 2025, 'rank': 481, 'geoid': '2108902'}, {'name': 'Maricopa, Arizona', 'lat': 33.041942, 'lon': -111.999259, 'population': 78362, 'population_year': 2025, 'rank': 482, 'geoid': '0444410'}, {'name': 'Lakewood, California', 'lat': 33.847135, 'lon': -118.121894, 'population': 78010, 'population_year': 2025, 'rank': 483, 'geoid': '0639892'}, {'name': 'Bismarck, North Dakota', 'lat': 46.814572, 'lon': -100.768568, 'population': 77963, 'population_year': 2025, 'rank': 484, 'geoid': '3807200'}, {'name': 'Racine, Wisconsin', 'lat': 42.725569, 'lon': -87.814224, 'population': 77908, 'population_year': 2025, 'rank': 485, 'geoid': '5566000'}, {'name': 'Tustin, California', 'lat': 33.730927, 'lon': -117.810596, 'population': 77843, 'population_year': 2025, 'rank': 486, 'geoid': '0680854'}, {'name': 'Ankeny, Iowa', 'lat': 41.731281, 'lon': -93.601074, 'population': 77833, 'population_year': 2025, 'rank': 487, 'geoid': '1902305'}, {'name': 'San Marcos, Texas', 'lat': 29.87361, 'lon': -97.936725, 'population': 77830, 'population_year': 2025, 'rank': 488, 'geoid': '4865600'}, {'name': 'Marysville, Washington', 'lat': 48.080214, 'lon': -122.154312, 'population': 77686, 'population_year': 2025, 'rank': 489, 'geoid': '5343955'}, {'name': 'Pittsburg, California', 'lat': 38.01769, 'lon': -121.900395, 'population': 77542, 'population_year': 2025, 'rank': 490, 'geoid': '0657456'}, {'name': 'Rochester Hills, Michigan', 'lat': 42.663484, 'lon': -83.159196, 'population': 77539, 'population_year': 2025, 'rank': 491, 'geoid': '2669035'}, {'name': 'Chino Hills, California', 'lat': 33.942969, 'lon': -117.725648, 'population': 77519, 'population_year': 2025, 'rank': 492, 'geoid': '0613214'}, {'name': 'Missouri City, Texas', 'lat': 29.562944, 'lon': -95.535999, 'population': 77327, 'population_year': 2025, 'rank': 493, 'geoid': '4848804'}, {'name': 'Flagstaff, Arizona', 'lat': 35.185212, 'lon': -111.620698, 'population': 77260, 'population_year': 2025, 'rank': 494, 'geoid': '0423620'}, {'name': 'Schaumburg, Illinois', 'lat': 42.0289, 'lon': -88.083773, 'population': 77249, 'population_year': 2025, 'rank': 495, 'geoid': '1768003'}, {'name': 'Pawtucket, Rhode Island', 'lat': 41.874824, 'lon': -71.373323, 'population': 77065, 'population_year': 2025, 'rank': 496, 'geoid': '4454640'}, {'name': 'Rogers, Arkansas', 'lat': 36.318085, 'lon': -94.152287, 'population': 76956, 'population_year': 2025, 'rank': 497, 'geoid': '0560410'}, {'name': 'Alameda, California', 'lat': 37.741911, 'lon': -122.259914, 'population': 76876, 'population_year': 2025, 'rank': 498, 'geoid': '0600562'}, {'name': 'Rocklin, California', 'lat': 38.806868, 'lon': -121.249696, 'population': 76821, 'population_year': 2025, 'rank': 499, 'geoid': '0662364'}, {'name': 'Caldwell, Idaho', 'lat': 43.64588, 'lon': -116.659336, 'population': 76629, 'population_year': 2025, 'rank': 500, 'geoid': '1612250'}, {'name': 'Perth, Australia', 'lat': -31.9523, 'lon': 115.8613}, {'name': 'Punta Cana, DR', 'lat': 18.5601, 'lon': -68.3725}]
WEATHER_CODES = {0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Depositing rime fog', 51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle', 56: 'Light freezing drizzle', 57: 'Dense freezing drizzle', 61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain', 66: 'Light freezing rain', 67: 'Heavy freezing rain', 71: 'Slight snow fall', 73: 'Moderate snow fall', 75: 'Heavy snow fall', 77: 'Snow grains', 80: 'Slight rain showers', 81: 'Moderate rain showers', 82: 'Violent rain showers', 85: 'Slight snow showers', 86: 'Heavy snow showers', 95: 'Thunderstorm', 96: 'Thunderstorm with slight hail', 99: 'Thunderstorm with heavy hail'}

def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c)).strip()


def fetch_json(url):
    with urlopen(Request(url, headers={'User-Agent': 'CityWeather/2.0'}), timeout=20) as response:
        result = json.load(response)
    if result.get('error'):
        raise ValueError(result.get('reason', 'Weather service error'))
    return result


def distance(a, b):
    lat1, lat2 = math.radians(a['lat']), math.radians(b['lat'])
    dlat = lat2-lat1
    dlon = math.radians(b['lon']-a['lon'])
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 3958.7613 * 2 * math.asin(math.sqrt(min(1, h)))


def suggestions(query):
    term = normalize(query)
    if not term:
        return []
    matches = [c for c in CITIES if term in normalize(c['name'])]
    matches.sort(key=lambda c: (not normalize(c['name']).startswith(term), -c.get('population', 0)))
    if not matches:
        names = {normalize(c['name']): c for c in CITIES}
        matches = [names[n] for n in get_close_matches(term, names, n=8, cutoff=.45)]
    return matches[:8]


def resolve_city(query):
    term = normalize(query)
    exact = [c for c in CITIES if normalize(c['name']) == term]
    if exact:
        return exact[0], ''
    # A bare city name may identify multiple states; never silently choose one.
    named = [c for c in CITIES if normalize(c['name'].split(',')[0]) == term]
    if len(named) == 1:
        return named[0], ''
    if len(named) > 1:
        raise ValueError('More than one city matches. Choose a suggestion with its state.')
    data = fetch_json('https://geocoding-api.open-meteo.com/v1/search?' + urlencode(
        {'name': query, 'count': 20, 'language': 'en', 'countryCode': 'US'}))
    locations = [r for r in data.get('results', []) if r.get('country_code') == 'US']
    if not locations:
        raise ValueError('City not found. Check spelling or choose a suggested city. Try including the state.')
    # A typed prefix must not silently resolve to a different city.
    name = term.split(',')[0].strip()
    locations = [r for r in locations if normalize(r['name']) == name]
    if not locations:
        raise ValueError('No exact location found. Choose a suggestion, or enter the full city and state.')
    if len(locations) > 1:
        choices = ', '.join(dict.fromkeys(r.get('admin1', '') for r in locations))
        raise ValueError('Please include the state to identify this city: ' + choices)
    location = locations[0]
    point = {'lat': location['latitude'], 'lon': location['longitude']}
    closest = min(CITIES[:500], key=lambda c: distance(point, c))
    miles = distance(point, closest)
    return closest, f"Nearest supported city to {location['name']}, {location.get('admin1', '')}: {closest['name']} ({miles:.1f} miles)."


def forecast_url(city, days):
    if days not in (3, 5, 10):
        raise ValueError('Choose a 3, 5 or 10 day forecast.')
    return 'https://api.open-meteo.com/v1/forecast?' + urlencode({
        'latitude': city['lat'], 'longitude': city['lon'], 'timezone': 'auto',
        'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,snowfall_sum,sunrise,sunset,wind_speed_10m_max,uv_index_max',
        'hourly': 'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m',
        'precipitation_unit': 'inch',
        'temperature_unit': 'fahrenheit', 'wind_speed_unit': 'mph', 'forecast_days': days})


def weather_kind(code):
    if code == 0:
        return 'sun'
    if code in (1, 2):
        return 'partly'
    if code == 3:
        return 'cloud'
    if code in (45, 48):
        return 'fog'
    if code in (71, 73, 75, 77, 85, 86):
        return 'snow'
    if code in (95, 96, 99):
        return 'storm'
    if isinstance(code, int) and 51 <= code <= 82:
        return 'rain'
    return 'unknown'


def weather_symbol(code):
    return {'sun': '☀', 'partly': '⛅', 'cloud': '☁', 'rain': '☂', 'snow': '❄', 'storm': 'ϟ', 'fog': '≋', 'unknown': '—'}[weather_kind(code)]


def draw_weather(canvas, code):
    """Draw crisp local illustrations; no downloads or image dependencies."""
    canvas.delete('all')
    kind = weather_kind(code)
    if kind == 'unknown':
        canvas.create_text(48, 44, text='—', fill='#B7CEED', font=('Segoe UI', 28))
        return
    if kind in ('sun', 'partly'):
        x, y = (48, 42) if kind == 'sun' else (33, 29)
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            canvas.create_line(x+23*math.cos(a), y+23*math.sin(a), x+31*math.cos(a), y+31*math.sin(a), fill='#FBBF24', width=3)
        canvas.create_oval(x-18, y-18, x+18, y+18, fill='#FBBF24', outline='')
    if kind != 'sun':
        cloud = '#D9E6F5' if kind in ('partly', 'cloud', 'snow', 'fog') else '#9AB2D1'
        canvas.create_oval(17, 35, 55, 66, fill=cloud, outline='')
        canvas.create_oval(34, 23, 76, 66, fill=cloud, outline='')
        canvas.create_oval(53, 39, 88, 66, fill=cloud, outline='')
        canvas.create_rectangle(34, 46, 73, 66, fill=cloud, outline='')
    if kind == 'rain':
        for x in (29, 49, 69):
            canvas.create_line(x+3, 72, x-1, 83, fill='#60A5FA', width=3)
    elif kind == 'snow':
        for x in (28, 50, 72):
            for dx, dy in ((5, 0), (3, 4), (3, -4)):
                canvas.create_line(x-dx, 78-dy, x+dx, 78+dy, fill='#D7F4FF', width=2)
    elif kind == 'storm':
        canvas.create_polygon(49, 59, 38, 76, 49, 75, 43, 89, 66, 68, 54, 69, 60, 59, fill='#FBBF24', outline='')
    elif kind == 'fog':
        for y in (72, 79, 86):
            canvas.create_line(20, y, 83, y, fill='#A4BACF', width=3)


class RadarWindow:
    """Native in-app map. Workers download bytes; only Tk's thread draws images."""
    def __init__(self, root, city, animate=False):
        self.window = tk.Toplevel(root)
        self.window.title('Weather radar · ' + city['name'])
        self.window.geometry('800x820')
        self.window.minsize(680, 820)
        self.city, self.zoom = city, 7
        self.playing, self.closed, self.busy = animate, False, False
        self.frames, self.host = [], ''
        self.index, self.generation = 0, 0
        self.data = queue.Queue()
        self.cache, self.images = {}, []
        self.executor = ThreadPoolExecutor(max_workers=4)
        panel = ttk.Frame(self.window, padding=20)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Weather radar', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(panel, text=city['name'], foreground='#60718A', font=('Segoe UI', 12)).pack(anchor='w', pady=(0, 12))
        controls = ttk.Frame(panel)
        controls.pack(fill='x', pady=(0, 10))
        self.play_button = ttk.Button(controls, text='Pause' if animate else 'Play', command=self.toggle, style='Primary.TButton')
        self.play_button.pack(side='left')
        ttk.Button(controls, text='Latest', command=self.latest, style='Radar.TButton').pack(side='left', padx=6)
        ttk.Button(controls, text='Refresh', command=self.refresh, style='Radar.TButton').pack(side='left')
        ttk.Button(controls, text='−', command=lambda: self.change_zoom(-1), style='Radar.TButton').pack(side='right')
        ttk.Button(controls, text='+', command=lambda: self.change_zoom(1), style='Radar.TButton').pack(side='right', padx=6)
        self.label = ttk.Label(panel, text='Loading recent radar frames…', foreground='#60718A', wraplength=720)
        self.label.pack(fill='x', pady=(0, 8))
        # Fixed map viewport keeps tiles aligned and only downloads visible tiles.
        self.canvas = tk.Canvas(panel, width=600, height=512, bg='#DCE6EF', highlightthickness=0)
        self.canvas.pack()
        self.slider = ttk.Scale(panel, from_=0, to=1, command=self.scrub)
        self.slider.pack(fill='x', pady=(10, 4))
        ttk.Label(panel, text='Radar: RainViewer  ·  Map: © OpenStreetMap contributors', foreground='#334B6C', font=('Segoe UI', 9)).pack(anchor='w')
        ttk.Label(panel, text='Rain: green → yellow → red / purple (stronger)  •  Snow: blue tones\nRecent observations, not a future forecast. Frame times are UTC. Refreshes every 5 minutes.\nBlank areas may mean no precipitation or unavailable radar coverage.', foreground='#60718A', font=('Segoe UI', 9), wraplength=720).pack(anchor='w', pady=(5, 0))
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.after(100, self.poll)
        self.window.after(1800, self.tick)
        self.window.after(300000, self.auto_refresh)
        self.refresh()

    def refresh(self):
        if self.closed:
            return
        self.label.configure(text='Updating radar frames…')
        def work():
            try:
                payload = fetch_json('https://api.rainviewer.com/public/weather-maps.json')
                self.data.put(('metadata', payload))
            except Exception as exc:
                self.data.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def auto_refresh(self):
        if not self.closed:
            self.refresh()
            self.window.after(300000, self.auto_refresh)

    def tile_positions(self):
        n = 2 ** self.zoom
        latitude = max(-85, min(85, self.city['lat']))
        x = (self.city['lon'] + 180) / 360 * n
        y = (1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2 * n
        left, top = x*256-300, y*256-256
        return [(tx % n, ty, tx*256-left, ty*256-top)
                for tx in range(math.floor(left/256), math.floor((left+599)/256)+1)
                for ty in range(math.floor(top/256), math.floor((top+511)/256)+1) if 0 <= ty < n]

    def load_frame(self):
        if not self.frames or self.closed:
            return
        self.generation += 1
        generation, frame = self.generation, self.frames[self.index]
        self.busy = True
        zoom, host, positions = self.zoom, self.host, self.tile_positions()
        def tile_bytes(url, base=False):
            if url in self.cache:
                return self.cache[url]
            cache_file = Path(tempfile.gettempdir()) / 'CityWeatherMapCache' / (hashlib.sha256(url.encode()).hexdigest()+'.png')
            if base and cache_file.exists() and time.time()-cache_file.stat().st_mtime < 7*86400:
                raw = cache_file.read_bytes()
            else:
                with urlopen(Request(url, headers={'User-Agent': 'CityWeatherDesktop/3.0 (personal weather map)'}), timeout=15) as response:
                    raw = response.read()
                if base:
                    try:
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        cache_file.write_bytes(raw)
                    except OSError:
                        pass
            return raw
        def work():
            try:
                tasks = []
                for x, y, px, py in positions:
                    base_url = f'https://tile.openstreetmap.org/{zoom}/{x}/{y}.png'
                    radar_url = f"{host}{frame['path']}/256/{zoom}/{x}/{y}/2/1_1.png"
                    tasks.append((px, py, base_url, radar_url, self.executor.submit(tile_bytes, base_url, True), self.executor.submit(tile_bytes, radar_url)))
                tiles, errors = [], []
                for px, py, base_url, radar_url, base_task, radar_task in tasks:
                    base_raw, radar_raw = None, None
                    for task, url, kind in ((base_task, base_url, 'map'), (radar_task, radar_url, 'radar')):
                        try:
                            raw = task.result()
                            if kind == 'map': base_raw = raw
                            else: radar_raw = raw
                        except Exception as exc:
                            errors.append(kind + ': ' + str(exc))
                    tiles.append((px, py, base_url, radar_url, base_raw, radar_raw))
                self.data.put(('tiles', generation, frame, tiles, errors))
            except Exception as exc:
                self.data.put(('frame_error', generation, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                result = self.data.get_nowait()
                if result[0] == 'metadata':
                    payload = result[1]
                    frames = payload.get('radar', {}).get('past', [])
                    host = payload.get('host', '')
                    if not frames or not host.startswith('https://'):
                        self.label.configure(text='No radar imagery is currently available. Try Refresh.')
                        continue
                    self.frames, self.host = frames, host
                    self.index = len(frames)-1
                    self.slider.configure(to=max(1, len(frames)-1))
                    self.slider.set(self.index)
                    self.load_frame()
                elif result[0] == 'error':
                    self.label.configure(text='Radar unavailable. Check your connection and press Refresh. ' + result[1])
                elif result[0] == 'frame_error':
                    if result[1] == self.generation:
                        self.busy = False
                        self.label.configure(text='Could not load radar imagery. Try Refresh. ' + result[2])
                elif result[0] == 'tiles':
                    _, generation, frame, tiles, errors = result
                    if generation != self.generation:
                        continue
                    self.busy = False
                    self.canvas.delete('all')
                    self.images = []
                    for x, y, base_url, radar_url, base_raw, radar_raw in tiles:
                        for url, raw in ((base_url, base_raw), (radar_url, radar_raw)):
                            if raw:
                                try:
                                    image = tk.PhotoImage(master=self.window, data=base64.b64encode(raw))
                                    self.images.append(image)
                                    self.canvas.create_image(x, y, image=image, anchor='nw')
                                    self.cache[url] = raw
                                except tk.TclError:
                                    errors.append('Invalid map image')
                    # Keep memory bounded while retaining recently viewed imagery.
                    while len(self.cache) > 160:
                        del self.cache[next(iter(self.cache))]
                    self.canvas.create_oval(293, 249, 307, 263, fill='#2563EB', outline='white', width=3)
                    self.canvas.create_text(300, 236, text=self.city['name'], fill='#142E4D', font=('Segoe UI', 10, 'bold'))
                    timestamp = datetime.fromtimestamp(frame['time'], timezone.utc).strftime('%b %d, %Y · %H:%M UTC')
                    age = max(0, int((time.time()-frame['time'])/60))
                    status = f'Frame {self.index+1}/{len(self.frames)} · {timestamp} · Zoom {self.zoom} · {age} min old'
                    if age > 30:
                        status += ' · Delayed imagery'
                    if errors:
                        status += ' · Some map/radar tiles unavailable; try Refresh.'
                    self.label.configure(text=status)
        except queue.Empty:
            pass
        self.window.after(100, self.poll)

    def toggle(self):
        self.playing = not self.playing
        self.play_button.configure(text='Pause' if self.playing else 'Play')

    def latest(self):
        self.playing = False
        self.play_button.configure(text='Play')
        if self.frames:
            self.index = len(self.frames)-1
            self.slider.set(self.index)
            self.load_frame()

    def scrub(self, value):
        if self.frames:
            index = min(len(self.frames)-1, int(float(value)+.5))
            if index != self.index:
                self.index = index
                self.playing = False
                self.play_button.configure(text='Play')
                self.load_frame()

    def tick(self):
        if self.closed:
            return
        if self.playing and self.frames and not self.busy:
            self.index = (self.index+1) % len(self.frames)
            self.slider.set(self.index)
            self.load_frame()
        self.window.after(1800, self.tick)

    def change_zoom(self, amount):
        zoom = max(4, min(7, self.zoom+amount))
        if zoom != self.zoom:
            self.zoom = zoom
            self.load_frame()

    def close(self):
        if not self.closed:
            self.closed = True
            self.executor.shutdown(wait=False, cancel_futures=True)
            if self.window.winfo_exists():
                self.window.destroy()


class WeatherApp:
    def __init__(self, root):
        self.root = root
        root.title('City Weather')
        root.geometry('1100x860')
        root.minsize(900, 780)
        self.query = tk.StringVar(value='Cleveland, Ohio')
        self.days = tk.IntVar(value=3)
        self.status = tk.StringVar()
        self.city = None
        self.matches = []
        self.forecast_payload = None
        self.forecast_city = None
        self.detail_window = None
        self.radar_windows = []
        self.results = queue.Queue()
        self.request_id = 0
        self.closed = False
        self.build_ui()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(100, self.poll)
        self.refresh_weather()

    def build_ui(self):
        bg, ink, muted, blue = '#F3F6FB', '#18273F', '#60718A', '#2563EB'
        self.root.configure(bg=bg)
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background=bg, foreground=ink)
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg)
        style.configure('Primary.TButton', background=blue, foreground='white', borderwidth=0, padding=(20, 11), font=('Segoe UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('active', '#1D4ED8'), ('disabled', '#D6DFEC')], foreground=[('disabled', '#718198')])
        style.configure('Radar.TButton', background='#E7EEFC', foreground='#234BA2', borderwidth=0, padding=(16, 10), font=('Segoe UI', 10, 'bold'))
        style.map('Radar.TButton', background=[('active', '#D8E4FC'), ('disabled', '#EDF1F7')], foreground=[('disabled', '#8190A5')])
        style.configure('Segment.TRadiobutton', indicatoron=False, background='#E7EDF6', foreground=muted, padding=(18, 9), borderwidth=0, font=('Segoe UI', 10, 'bold'))
        style.layout('Segment.TRadiobutton', [('Radiobutton.padding', {'sticky': 'nswe', 'children': [('Radiobutton.label', {'sticky': 'nswe'})]})])
        style.map('Segment.TRadiobutton', background=[('selected', blue), ('active', '#DBE5F4')], foreground=[('selected', 'white')])
        style.configure('City.TEntry', fieldbackground='white', foreground=ink, bordercolor='#CFD9E8', lightcolor='#CFD9E8', darkcolor='#CFD9E8', padding=11)
        style.map('City.TEntry', bordercolor=[('focus', blue)], lightcolor=[('focus', blue)], darkcolor=[('focus', blue)])
        style.configure('Weather.Treeview', background='white', fieldbackground='white', foreground=ink, rowheight=35, borderwidth=0, font=('Segoe UI', 10))
        style.configure('Weather.Treeview.Heading', background='#EDF2F9', foreground=muted, padding=(12, 10), relief='flat', font=('Segoe UI', 9, 'bold'))
        style.map('Weather.Treeview', background=[('selected', '#DBEAFE')], foreground=[('selected', '#173F87')])
        panel = ttk.Frame(self.root, padding=(28, 22))
        panel.pack(fill='both', expand=True)
        header = ttk.Frame(panel)
        header.pack(fill='x')
        ttk.Label(header, text='City Weather', font=('Segoe UI', 24, 'bold')).pack(side='left')
        ttk.Label(header, text='500 US CITIES  /  2025 CENSUS', foreground=muted, font=('Segoe UI', 9, 'bold')).pack(side='right')
        ttk.Label(panel, text='Your next few days, at a glance.', foreground=muted, font=('Segoe UI', 11)).pack(anchor='w', pady=(2, 18))
        search = ttk.Frame(panel)
        search.pack(fill='x')
        ttk.Label(search, text='FIND A CITY', foreground=muted, font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(0, 6))
        row = ttk.Frame(search)
        row.pack(fill='x')
        self.entry = ttk.Entry(row, textvariable=self.query, style='City.TEntry', font=('Segoe UI', 12))
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', lambda e: self.refresh_weather())
        self.entry.bind('<Down>', self.focus_matches)
        self.entry.bind('<Escape>', lambda e: self.listbox.pack_forget())
        ttk.Button(row, text='Show weather', style='Primary.TButton', command=self.refresh_weather).pack(side='left', padx=(10, 0))
        self.match_slot = ttk.Frame(search)
        self.match_slot.pack(fill='x')
        self.listbox = tk.Listbox(self.match_slot, height=4, exportselection=False, font=('Segoe UI', 11), bg='white', fg=ink, selectbackground='#DBEAFE', selectforeground='#173F87', relief='flat', highlightthickness=1, highlightbackground='#CFD9E8', activestyle='none')
        self.listbox.bind('<ButtonRelease-1>', self.pick)
        self.listbox.bind('<Return>', self.pick)
        self.query.trace_add('write', self.update_matches)
        ttk.Label(search, text='Start typing a city and state. Smaller towns resolve to the nearest supported city.', foreground=muted, font=('Segoe UI', 9)).pack(anchor='w', pady=(6, 12))
        hero = tk.Frame(panel, bg='#152C4C', padx=24, pady=18)
        hero.pack(fill='x')
        hero.columnconfigure(0, weight=1)
        self.location = tk.Label(hero, text='Finding your forecast', font=('Segoe UI', 19, 'bold'), bg='#152C4C', fg='white', anchor='w')
        self.location.grid(row=0, column=0, sticky='w')
        self.current = tk.Label(hero, text='Loading…', font=('Segoe UI', 12), bg='#152C4C', fg='#B7CEED', anchor='w', wraplength=620, justify='left')
        self.current.grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.temperature = tk.Label(hero, text='—', font=('Segoe UI', 46, 'bold'), bg='#152C4C', fg='white')
        self.temperature.grid(row=0, column=1, rowspan=2, padx=(18, 0), sticky='e')
        self.hero_icon = tk.Canvas(hero, width=96, height=90, bg='#152C4C', highlightthickness=0)
        self.hero_icon.grid(row=0, column=2, rowspan=2, padx=(16, 0))
        metrics = ttk.Frame(panel)
        metrics.pack(fill='x', pady=(12, 0))
        self.metrics = {}
        for column, (key, title) in enumerate((('feels', 'FEELS LIKE'), ('humidity', 'HUMIDITY'), ('wind', 'WIND SPEED'))):
            metrics.columnconfigure(column, weight=1, uniform='metric')
            card = tk.Frame(metrics, bg='white', padx=18, pady=12)
            card.grid(row=0, column=column, sticky='ew', padx=(0 if column == 0 else 10, 0))
            tk.Label(card, text=title, bg='white', fg=muted, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
            value = tk.Label(card, text='—', bg='white', fg=ink, font=('Segoe UI', 19, 'bold'))
            value.pack(anchor='w', pady=(4, 0))
            self.metrics[key] = value
        self.status_label = ttk.Label(panel, textvariable=self.status, wraplength=1000, foreground=muted, font=('Segoe UI', 9))
        self.status_label.pack(fill='x', pady=(10, 12))
        options = ttk.Frame(panel)
        options.pack(fill='x', pady=(0, 10))
        self.forecast_title = ttk.Label(options, text='Your forecast', font=('Segoe UI', 16, 'bold'))
        self.forecast_title.pack(side='left')
        for days in (3, 5, 10):
            ttk.Radiobutton(options, text=f'{days} days', style='Segment.TRadiobutton', variable=self.days, value=days, command=self.refresh_weather).pack(side='left', padx=(12 if days == 3 else 2, 0))
        self.live_radar = ttk.Button(options, text='▶  Live radar', style='Primary.TButton', command=lambda: self.open_radar(True), state='disabled')
        self.live_radar.pack(side='right')
        self.radar = ttk.Button(options, text='Radar map', style='Radar.TButton', command=lambda: self.open_radar(False), state='disabled')
        self.radar.pack(side='right', padx=(8, 8))
        self.forecast_box = ttk.Frame(panel)
        self.forecast_box.pack(fill='both', expand=True)
        columns = ('day', 'condition', 'high', 'low', 'rain')
        self.table = ttk.Treeview(self.forecast_box, columns=columns, show='headings', height=10, style='Weather.Treeview', selectmode='browse')
        for key, heading, width in zip(columns, ('DAY', 'CONDITIONS', 'HIGH °F', 'LOW °F', 'RAIN CHANCE'), (160, 300, 110, 110, 140)):
            self.table.heading(key, text=heading, anchor='w')
            self.table.column(key, width=width, minwidth=70, anchor='w')
        self.table.bind('<<TreeviewSelect>>', self.show_day)
        self.table.bind('<Return>', self.show_day)
        self.table.tag_configure('alternate', background='#F6F8FC')
        scroll = ttk.Scrollbar(self.forecast_box, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.table.pack(fill='both', expand=True)
        ttk.Label(panel, text='Click a forecast day for hourly details. Radar opens inside the app; observations arrive with a delay.', foreground=muted, font=('Segoe UI', 9)).pack(anchor='w', pady=(10, 3))
        ttk.Label(panel, text='Open-Meteo / GeoNames  ·  RainViewer radar / © OpenStreetMap contributors  ·  Census July 1, 2025 population ranks 1–500  ·  Plus Perth & Punta Cana', foreground=muted, font=('Segoe UI', 8)).pack(anchor='w')

    def update_matches(self, *_):
        self.matches = suggestions(self.query.get())
        self.listbox.delete(0, 'end')
        for city in self.matches:
            self.listbox.insert('end', city['name'])
        if self.matches and self.root.focus_get() == self.entry:
            self.listbox.pack(fill='x', pady=(4, 0))
        else:
            self.listbox.pack_forget()

    def focus_matches(self, _):
        if self.matches:
            self.listbox.focus_set()
            self.listbox.selection_set(0)
        return 'break'

    def pick(self, _=None):
        selection = self.listbox.curselection()
        if selection:
            city = self.matches[selection[0]]
            self.query.set(city['name'])
            self.refresh_weather()
        return 'break'

    def refresh_weather(self):
        self.listbox.pack_forget()
        self.forecast_payload = None
        if self.detail_window and self.detail_window.winfo_exists():
            self.detail_window.destroy()
        self.hero_icon.delete('all')
        query, days = self.query.get().strip(), self.days.get()
        self.request_id += 1
        request_id = self.request_id
        self.city = None
        for button in (self.radar, self.live_radar):
            button.configure(state='disabled')
        self.table.delete(*self.table.get_children())
        self.location.configure(text='Finding your forecast' if query else 'Choose a city')
        self.temperature.configure(text='—')
        for metric in self.metrics.values():
            metric.configure(text='—')
        self.current.configure(text='Loading…' if query else 'Enter a city.')
        if not query:
            self.status.set('Enter a city and state.')
            return
        self.status.set('Finding location and loading weather…')
        def work():
            try:
                city, note = resolve_city(query)
                payload = fetch_json(forecast_url(city, days))
                self.results.put((request_id, city, note, payload, days, None))
            except Exception as exc:
                self.results.put((request_id, None, '', None, days, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                request_id, city, note, payload, days, error = self.results.get_nowait()
                if request_id != self.request_id:
                    continue
                if error:
                    self.status.set('Could not load weather: ' + error)
                    self.current.configure(text='Weather unavailable. Check your connection and try again.')
                    continue
                self.city = city
                for button in (self.radar, self.live_radar):
                    button.configure(state='normal')
                self.render(city, note, payload, days)
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self.poll)

    def render(self, city, note, payload, days):
        self.forecast_payload, self.forecast_city = payload, city
        current, daily = payload.get('current', {}), payload.get('daily', {})
        draw_weather(self.hero_icon, current.get('weather_code'))
        self.table.delete(*self.table.get_children())
        self.location.configure(text=city['name'])
        temp = current.get('temperature_2m')
        self.temperature.configure(text=f'{temp:.0f}°F' if isinstance(temp, (int, float)) else '—')
        self.current.configure(text=WEATHER_CODES.get(current.get('weather_code'), 'Unknown'))
        for key, field, unit in (('feels', 'apparent_temperature', '°F'), ('humidity', 'relative_humidity_2m', '%'), ('wind', 'wind_speed_10m', ' mph')):
            value_now = current.get(field)
            self.metrics[key].configure(text=f'{value_now}{unit}' if value_now is not None else '—')
        def value(key, index):
            values = daily.get(key, [])
            return values[index] if index < len(values) and values[index] is not None else 'N/A'
        self.forecast_title.configure(text='Your forecast')
        for i, date in enumerate(daily.get('time', [])[:days]):
            self.table.insert('', 'end', iid=str(i), tags=('alternate',) if i % 2 else (), values=(datetime.strptime(date, '%Y-%m-%d').strftime('%a, %b %d'),
                weather_symbol(value('weather_code', i)) + '  ' + WEATHER_CODES.get(value('weather_code', i), 'Unknown'), value('temperature_2m_max', i),
                value('temperature_2m_min', i), str(value('precipitation_probability_max', i))+'%'))
        observed = current.get('time', 'unavailable')
        self.status.set((note+'\n' if note else '') + f"Observation: {observed} ({payload.get('timezone', 'local time')}) • Retrieved {datetime.now():%H:%M:%S}")

    def show_day(self, _=None):
        selection = self.table.selection()
        if not selection or self.forecast_payload is None:
            return
        index = int(selection[0])
        daily = self.forecast_payload.get('daily', {})
        dates = daily.get('time', [])
        if index >= len(dates):
            return
        date = dates[index]
        if self.detail_window and self.detail_window.winfo_exists():
            window = self.detail_window
            for child in window.winfo_children():
                child.destroy()
        else:
            window = self.detail_window = tk.Toplevel(self.root)
            window.geometry('820x700')
            window.minsize(680, 520)
        window.title('Daily forecast · ' + self.forecast_city['name'])
        window.configure(bg='#F3F6FB')
        panel = ttk.Frame(window, padding=24)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text=datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d'), font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(panel, text=self.forecast_city['name'] + ' · ' + self.forecast_payload.get('timezone', 'local time'), foreground='#60718A').pack(anchor='w', pady=(2, 14))
        def value(key, unit=''):
            values = daily.get(key, [])
            v = values[index] if index < len(values) else None
            return 'Unavailable' if v is None else f'{v}{unit}'
        code = daily.get('weather_code', [])
        code = code[index] if index < len(code) else None
        banner = tk.Frame(panel, bg='#152C4C', padx=16, pady=14)
        banner.pack(fill='x')
        icon = tk.Canvas(banner, width=96, height=90, bg='#152C4C', highlightthickness=0)
        icon.pack(side='left', padx=(0, 14))
        draw_weather(icon, code)
        tk.Label(banner, text=WEATHER_CODES.get(code, 'Unknown') + '\n' + f"High {value('temperature_2m_max', '°F')}   /   Low {value('temperature_2m_min', '°F')}", bg='#152C4C', fg='white', font=('Segoe UI', 16, 'bold'), justify='left', wraplength=580).pack(side='left')
        summary = ttk.Frame(panel)
        summary.pack(fill='x', pady=14)
        details = [('Rain chance', value('precipitation_probability_max', '%')), ('Precipitation', value('precipitation_sum', ' in')), ('Snowfall', value('snowfall_sum', ' in')), ('Max wind', value('wind_speed_10m_max', ' mph')), ('UV index', value('uv_index_max'))]
        for key in ('sunrise', 'sunset'):
            raw = value(key)
            try:
                formatted = datetime.fromisoformat(raw).strftime('%I:%M %p').lstrip('0')
            except ValueError:
                formatted = 'Unavailable'
            details.append((key.title(), formatted))
        for i, (label, v) in enumerate(details):
            ttk.Label(summary, text=label + ': ' + v, foreground='#334B6C').grid(row=i//3, column=i%3, sticky='w', padx=(0, 20), pady=4)
        ttk.Label(panel, text='Hour by hour', font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(0, 8))
        frame = ttk.Frame(panel)
        frame.pack(fill='both', expand=True)
        columns = ('time', 'condition', 'temp', 'feels', 'rain', 'wind')
        table = ttk.Treeview(frame, columns=columns, show='headings', style='Weather.Treeview')
        for column, title, width in zip(columns, ('TIME', 'CONDITIONS', '°F', 'FEELS °F', 'RAIN %', 'MPH'), (90, 250, 70, 80, 80, 70)):
            table.heading(column, text=title, anchor='w')
            table.column(column, width=width, minwidth=45, anchor='w')
        scroll = ttk.Scrollbar(frame, orient='vertical', command=table.yview)
        scroll.pack(side='right', fill='y')
        table.configure(yscrollcommand=scroll.set)
        table.pack(fill='both', expand=True)
        self.hourly_table = table
        hourly = self.forecast_payload.get('hourly', {})
        def hourly_value(key, i):
            values = hourly.get(key, [])
            return values[i] if i < len(values) and values[i] is not None else '—'
        for i, timestamp in enumerate(hourly.get('time', [])):
            if timestamp[:10] == date:
                hour_code = hourly_value('weather_code', i)
                table.insert('', 'end', values=(datetime.fromisoformat(timestamp).strftime('%I:%M %p').lstrip('0'), weather_symbol(hour_code) + ' ' + WEATHER_CODES.get(hour_code, 'Unknown'), hourly_value('temperature_2m', i), hourly_value('apparent_temperature', i), hourly_value('precipitation_probability', i), hourly_value('wind_speed_10m', i)))
        ttk.Label(panel, text='Times are local to the forecast location. Missing values are shown as unavailable.', foreground='#60718A', wraplength=700).pack(anchor='w', pady=(10, 0))
        window.lift()

    def open_radar(self, animate):
        if self.city:
            self.radar_windows = [w for w in self.radar_windows if w.window.winfo_exists()]
            self.radar_windows.append(RadarWindow(self.root, self.city, animate))

    def close(self):
        self.closed = True
        for radar in self.radar_windows:
            radar.close()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    WeatherApp(root)
    root.mainloop()
