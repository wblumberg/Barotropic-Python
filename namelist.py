#!/usr/bin/env python
"""
This module contains the variables used to run barotropic_spectral.py
"""
import os
    
# Integration options
dt = 300                 # Timestep (seconds)
ntimes = 1360               # Number of time steps to integrate
plot_freq = 6              # Frequency of output plots in hours (if 0, no plots are made)
M = None                   # Truncation (if None, defaults to # latitudes)
r = 0.2                    # Coefficient for Robert Filter
topo = 'isolated_mountain'              # Topography (Earth, Mars, flat)
#topo = 'flat'
#topo = 'block'
smooth_topo = 1            # Smooth the topography by using a Guassian filter
integration_method = 'leapfrog'
integration_method = 'rk4'

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
g = 9.81                   # Gravitational acceleration (m s^-2)
Rd = 287.                  # Dry air gas constant
Ts = 300.                  # Surface tempreature? K 
