# Petrophysical Analysis Project

## Table of Contents
1. [About the Project](#about-the-project)
2. [Workflow](#workflow)

## About The Project
Read, plot and analyze complete petrophysical analysis (CPI) for Oil & gas wells. (Created based on Interactive Petrophysics IP software export example)
The project was expanded to cover analytics on all wells in the company (over 2500 wells) and create field and zone level analysis.

## Workflow
1. Read las file content and store well information (Name, Field, KB, Latitude, Longtiude, logs' start, step and end depths)
2. Standardize log names (e.g. Density as RHOB) for better storage into SQLite and multi-well analysis
3. Plot CPI (either full well, or using depth limits from user inputs)

![alt_text](https://github.com/Yous3ry/Petrophysical_Analysis_Project/blob/main/CPI_Plot.png)

4. Plot Petrophysical paramters distribution (either full well, or using depth limits from user inputs)

![alt_text](https://github.com/Yous3ry/Petrophysical_Analysis_Project/blob/main/Distribution_Plot.png)
