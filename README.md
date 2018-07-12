Barotropic-Python
=================
-----------------------------------------------------------------

A simple barotropic model written in Python using the ``spharm`` package for spherical harmonics.

Currently set up to use __linearized__ initial conditions

Written by Luke Madaus (5/2012) - University of Washington

Restructured by Nick Weber (10/2017) - University of Washington

Features added by Greg Blumberg and Tim Supinie (7/2018) - University of Oklahoma

-----------------------------------------------------------------

__**Requires**__:

  - PySPHARM -- Python interface to NCAR SPHEREPACK library:  
	https://code.google.com/p/pyspharm/
  - netCDF4 -- Python interface to netCDF4 library  
  - numpy, datetime, matplotlib  

These can be obtained through conda (e.g., `conda install spharm` and `conda install netcdf4` and `conda install basemap`).  Numpy, datetime, and matplotlib come default with the Anaconda Python distribution.

Based on the Held-Suarez Barotropic model, including hyperdiffusion.  
A brief description of their model may be found at:  
http://data1.gfdl.noaa.gov/~arl/pubrel/m/atm_dycores/src/atmos_spectral_barotropic/barotropic.pdf

The basic premise of the code is to take upper-level u and v winds from any dataset  
(forecast or analysis), extract the non-divergent component, compute vorticity, and  
advect along this vorticity using the barotropic vorticity equation. As this model  
uses "real" atmospheric data (which is not barotropic), the results are rarely stable  
beyond ~5 days of forecasting.

-----------------------------------------------------------------

__**Contents**__:

 - **``barotropic_spectral.py``** -- contains the ``Model`` class, which handles the initialization,  
 integration, plotting, and I/O for the barotropic model
 - **``namelist.py``** -- functions as a traditional model namelist, containing the various  
 configuration parameters for the barotropic model
 - **``hyperdiffusion.py``** -- contains functions for applying hyperdiffusion to the vorticity  
 tendecy equation (helps prevent the model from blowing up)

 To run the model use: `python barotropic_spectral.py`
 
 __**Options**__
 
 These options may be changed in the namelist.py file that comes with the program.
 
 - Add terrain into the model (Earth, Mars, flat, isolated mountain, longitudinal block)
 - Change integration method (RK4, leapfrog).
 - Fluid height.
 - Time step and plot frequency.
 - Spin up an artifical vortex for the first X seconds of the simulation at a point (can be used to place "tropical cyclones" in the flow.)
 - Hyperdiffusion parameters (Use DES if you chose to use RK4).
 - Modify the initial conditions (background u and v, and perturbation u and v) to simulate different flow patterns.
 - Change the radius of the sphere, rotation rate, and gravity.
 
 
 
 
