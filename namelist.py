#!/usr/bin/env python
"""
This module contains the variables used to run barotropic_spectral.py
"""
import os
    
# Integration options
dt = 200                 # Timestep (seconds)
ntimes = 1060               # Number of time steps to integrate
plot_freq = 6              # Frequency of output plots in hours (if 0, no plots are made)
M = None                   # Truncation (if None, defaults to # latitudes)
r = 0.2                    # Coefficient for Robert Filter
topo = 'isolated_mountain' #'isolated_mountain'   # Topography (Earth, Mars, flat, isolated_mountain, block)
smooth_topo = 1            # Smooth the topography by using a Guassian filter
integration_method = 'rk4'  # Integration method ('leapfrog', 'rk4')
fluid_height = 10000         # Fluid height (m).

# Idealized Initial Conditions (for idealized flow...future models will allow for realistic initial conditions)
mag = 0 # Max base state zonal wind speed.
A = 1.5 * 8e-5 # The vorticity perturbation of the flow (set to 0 for no perturbation).
m = 1 # Zonal wavenumber around the sphere for the perturbation.
theta0 = 45 # Center latitude of the sinusoidal vorticity perturbation
thetaW = 15 # Latitudinal width of the vorticity perturbation

# Extra vorticity forcing
use_forcing = False         # Add a synthetic hurricane or extra forcing to the model.
forcing_lat = 10            # Latitude center of the forcing
forcing_lon = 180           # Longitude center of the forcing
forcing_amp = 10e-10        # Amplitude of the forcing (s^-2)
forcing_time = 700         # Number of seconds to apply the forcing

# I/O parameters
figdir = os.path.join(os.getcwd(), 'figures')  # Figure directory

# Diffusion parameters
diff_opt = 'des'           # Hyperdiffusion option ('off' = none, 'del4' = del^4, 'des' = DES)
k = 2.338e16               # Diffusion coefficient for del^4 hyperdiffusion (diff_opt='del4')
nu = 1E-4                  # Dampening coefficient for DES hyperdiffusion (diff_opt='des')
fourier_inc = 1            # Fourier increment for computing dampening eddy sponge (diff_opt='des')

# Constants
Re = 6378100.              # Radius of earth (m)
omega = 7.292E-5           # Earth's angular momentum (s^-1)
g = 9.81                   # Gravity (m s^-2)
