#!/usr/bin/env python
import numpy as np
from netCDF4 import Dataset
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter
from mpl_toolkits.basemap import Basemap

from mpl_toolkits import basemap
import spharm
import os
from hyperdiffusion import del4_filter, apply_des_filter
import namelist as NL # <---- IMPORTANT! Namelist containing constants and other model parameters


class Model:
    """
    Class for storing/plotting flow fields for a homogeneous (constant density), 
    non-divergent, and incompressible fluid on a sphere and integrating them forward 
    with the barotropic vorticity equation.
    """
    
    def __init__(self, ics, forcing=None):
        """
        Initializes the model.
        
        Requires:
        ics -----> Dictionary of linearized fields and space/time dimensions
                   keys: u_bar, v_bar, u_prime, v_prime, lats, lons, start_time
        forcing -> a 2D array (same shape as model fields) containing a
                   vorticity tendency [s^-2] to be imposed at each integration time step
        """
        # 1) STORE SPACE/TIME VARIABLES (DIMENSIONS)
        # Get the latitudes and longitudes (as lists)
        self.lats = ics['lats']
        self.lons = ics['lons']
        self.start_time = ics['start_time']  # datetime
        self.curtime = self.start_time
        
        
        # 2) GENERATE/STORE NONDIVERGENT INITIAL STATE
        # Set up the spherical harmonic transform object
        self.s = spharm.Spharmt(self.nlons(), self.nlats(), rsphere=NL.Re,
                                gridtype='regular', legfunc='computed')
        # Truncation for the spherical transformation
        if NL.M is None:
            self.ntrunc = self.nlats()
        else:
            self.ntrunc = NL.M
        # Use the object to get the initial conditions
        # First convert to vorticity using spharm object
        vortb_spec, div_spec = self.s.getvrtdivspec(ics['u_bar'], ics['v_bar'])
        vortp_spec, div_spec = self.s.getvrtdivspec(ics['u_prime'], ics['v_prime'])
        div_spec = np.zeros(vortb_spec.shape)  # Only want NON-DIVERGENT part of wind 
        # Re-convert this to u-v winds to get the non-divergent component
        # of the wind field
        self.ub, self.vb = self.s.getuv(vortb_spec, div_spec)    # MEAN WINDS
        self.up, self.vp = self.s.getuv(vortp_spec, div_spec)    # PERTURBATION WINDS
        # Use these winds to get the streamfunction (psi) and 
        # velocity potential (chi)
        self.psib,chi = self.s.getpsichi(self.ub, self.vb)       # MEAN STREAMFUNCTION
        self.psip,chi = self.s.getpsichi(self.up, self.vp)       # PERTURBATION STREAMFUNCTION
        # Convert the spectral vorticity to grid
        self.vort_bar = self.s.spectogrd(vortb_spec)             # MEAN RELATIVE VORTICITY
        self.vortp = self.s.spectogrd(vortp_spec)                # PERTURBATION RELATIVE VORTICITY
        
        
        # 3) STORE A COUPLE MORE VARIABLES
        # Map projections for plotting
        self.bmaps = create_basemaps(self.lons, self.lats)
        # Get the vorticity tendency forcing (if any) for integration
        self.forcing = forcing
        self.topography(ics['lats'], ics['lons'], planet=NL.topo) 
        
    #==== Some simple dimensional functions ==========================================    
    def nlons(self):
        return len(self.lons)
    def nlats(self):
        return len(self.lats)
    
    def topography(self, lats, lons, planet='Earth'):
        if planet == 'Earth':
            # From: http://research.jisao.washington.edu/data/elevation/
            d = Dataset('elev.0.25-deg.nc')
            #print(d.variables.keys())
            topo_lat = np.flipud(d['lat'])
            topo_lon = d['lon'][:]
            topo_elev = np.flipud(d['data'][0])
            
            # Mask out oceans
            idx = np.where(topo_elev < 0)
            topo_elev[idx[0], idx[1]] = 0
            
            # Interpolate topography data to the known grid
        elif planet == 'Mars':
            d = np.load('mars.npz')
            topo_lat = d['lats'][:,0][::-1]
            topo_lon = d['lons'][0,1:]+180
            topo_elev = d['data'][:,1:][::-1,:]                  
        elif planet == 'flat':
            d = Dataset('elev.0.25-deg.nc')
            topo_lat = np.flipud(d['lat'])
            topo_lon = d['lon'][:]
            topo_elev = np.flipud(d['data'][0])
            topo_elev[:,:] = 0
        elif planet == 'isolated_mountain':
            # From: http://research.jisao.washington.edu/data/elevation/
            d = Dataset('elev.0.25-deg.nc')
            #print(d.variables.keys())
            topo_lat = np.flipud(d['lat'])
            topo_lon = d['lon'][:]
            topo_elev = np.flipud(d['data'][0])
            
            # Mask out oceans
            idx = np.where(topo_elev < 4000)
            topo_elev[idx[0], idx[1]] = 0
            
        new_lon, new_lat = np.meshgrid(self.lons, self.lats)
        self.topo = basemap.interp(topo_elev, topo_lon, topo_lat, new_lon, new_lat, order=1)
        ##plt.title("Terrain")
        #plt.pcolormesh(new_lon, new_lat, self.topo)
        #cb = plt.colorbar()
        #cb.ax.set_ylabel("Elevation [m]")
        #plt.ylabel("Latitude")
        #plt.xlabel("Longitude")
        #plt.show()
        self.topo = gaussian_filter(self.topo, NL.smooth_topo)
        #plt.title("Terrain")
        #plt.pcolormesh(new_lon, new_lat, self.topo)
        #cb = plt.colorbar()
        #cb.ax.set_ylabel("Elevation [m]")
        #plt.ylabel("Latitude")
        #plt.xlabel("Longitude")
        #plt.show()
 
        #stop 
    #==== Primary function: model integrator =========================================    
    def integrate(self):
        """ 
        Integrates the barotropic model using spherical harmonics.
        Simulation configuration is set in namelist.py
        """
        # Create a radian grid
        lat_list_r = [x * np.pi/180. for x in self.lats]
        lon_list_r = [x * np.pi/180. for x in self.lons]

        # Meshgrid
        lons,lats = np.meshgrid(self.lons, self.lats)
        lamb, theta = np.meshgrid(lon_list_r, lat_list_r)

        # Need these for derivatives later
        dlamb = np.gradient(lamb)[1]
        dtheta = np.gradient(theta)[0]

        # Plot Initial Conditions
        if NL.plot_freq != 0:
            self.plot_figures(0)

        # Now loop through the timesteps
        for n in range(NL.ntimes):
           
            #if n > 150:
            #    self.topo[:,:] = 0
            # Leapfrog:
            integration = 'rk4'
            #integration = 'leapfrog'
            if integration == 'leapfrog':
                vort_tend = self.gettend(self.vortp, dlamb, dtheta, theta)
                print(np.max(vort_tend), np.min(vort_tend))
                if n == 0:
                    # First step just do forward difference
                    # Vorticity at next time is just vort + vort_tend * dt
                    vortp_next = self.vortp + vort_tend * NL.dt
                else:
                    # Otherwise do leapfrog
                    vortp_next = vortp_prev + vort_tend * 2 * NL.dt 

                # Invert this new vort to get the new psi (or rather, uv winds)
                # First go back to spectral space
                vortp_spec = self.s.grdtospec(vortp_next)
                div_spec = np.zeros(np.shape(vortp_spec))  # Divergence is zero in barotropic vorticity

                # Now use the spharm methods to update the u and v grid
                self.up, self.vp = self.s.getuv(vortp_spec, div_spec)
                self.psip, chi = self.s.getpsichi(self.up, self.vp)

                # Change vort_now to vort_prev
                # and if not first step, add Robert filter to dampen out crazy modes
                if n == 0:
                    vortp_prev = self.vortp
                else:
                    vortp_prev = (1.-2.*NL.r)*self.vortp + NL.r*(vortp_next + vortp_prev)
                    
                # Update the vorticity
                self.vortp = self.s.spectogrd(vortp_spec)

            elif integration == 'rk4':
                if n == 0:
                    vortp_prev = 0
                h = NL.dt
                k1 = self.gettend(self.vortp, dlamb, dtheta, theta)
                print("k1:",np.max(k1), np.min(k1))
                k2 = self.gettend(self.vortp + 0.5 * h * k1, dlamb, dtheta, theta)
                print("k2:",np.max(k2), np.min(k2))
                k3 = self.gettend(self.vortp + 0.5 * h * k2, dlamb, dtheta, theta)
                print("k3:",np.max(k3), np.min(k3))
                k4 = self.gettend(self.vortp + h * k3, dlamb, dtheta, theta)
                print("k4:",np.max(k4), np.min(k4))
                vortp_next = vortp_prev + h*(k1 + 2*k2 + 2*k3 + k4)/6.
                print("VORTP NEXT:",np.max(vortp_next), np.min(vortp_next))
                stop 
            # Update the current time  
            cur_fhour = (n+1) * NL.dt / 3600.
            self.curtime = self.start_time + timedelta(hours = cur_fhour)

            # Make figure(s) every <plot_freq> hours
            if NL.plot_freq!=0 and cur_fhour % NL.plot_freq == 0:
                # Go from psi to geopotential
                print("Plotting hour", cur_fhour)
                self.plot_figures(int(cur_fhour))
                
    def gettend(self,vortp, dlamb, dtheta, theta):
        # self.psip, self.psib, self.vortp, self.vort_bar
        # 
        # Here we actually compute vorticity tendency
        # Compute tendency with beta as only forcing
        vort_tend = -2. * NL.omega/(NL.Re**2) * d_dlamb(self.psip + self.psib, dlamb) - \
                        Jacobian(self.psip+self.psib, vortp+self.vort_bar, theta, dtheta, dlamb)
            
        # Apply hyperdiffusion if requested for smoothing
        if NL.diff_opt==1:
            vort_tend -= del4_filter(vortp, self.lats, self.lons)
        elif NL.diff_opt==2:
            vort_tend = apply_des_filter(self.s, vortp, vort_tend, self.ntrunc,
                                             t = (n+1) * NL.dt / 3600.).squeeze()
                    
        # Now add any imposed vorticity tendency forcing
        if self.forcing is not None:
            vort_tend += self.forcing

        # Now add any geographical vorticity tendency forcing
        f = 2 * NL.omega * np.sin(theta)
        vort_tend += -(f * \
                     Jacobian(self.psip+self.psib, self.topo, theta, dtheta, dlamb)) / \
                     6000. 

        return vort_tend


    #==== Plotting utilities =========================================================
    def plot_figures(self, n, winds='total', vorts='total', psis='pert', showforcing=True,
                     vortlevs=np.array([-10,-8,-6,-4,-2,2,4,6,8,10])*1e-5,
                     windlevs=np.arange(20,61,4), hgtlevs=np.linspace(-500,500,26),
                     forcelevs=np.array([-15,-12,-9,-6,-3,3,6,9,12,15])*1e-10):
        """
        Make global and regional plots of the flow.
        
        Requires:
        n ------------------> timestep number
        winds, vorts, psis -> are we plotting the 'mean', 'pert', or 'total' field?
        showforcing --------> if True, contour the vorticity tendency forcing
        *levs --------------> contour/fill levels for the respective variables
        """
        # What wind component(s) are we plotting?
        if winds=='pert':   u = self.up; v = self.vp
        elif winds=='mean': u = self.ub; v = self.vb
        else:               u = self.up+self.ub; v = self.vp+self.vb
        # What vorticity component(s) are we plotting?
        if vorts=='pert':   vort = self.vortp
        elif vorts=='mean': vort = self.vort_bar
        else:               vort = self.vortp + self.vort_bar
        # What streamfunction component(s) are we plotting?
        if psis=='pert':   psi = self.psip
        elif psis=='mean': psi = self.psib
        else:              psi = self.psip + self.psib

        # MAKE GLOBAL ZETA & WIND BARB MAP
        fig, ax = plt.subplots(figsize=(10,8))
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95)
        
        xx, yy = self.bmaps['global_x'], self.bmaps['global_y']
        plt.pcolormesh(xx, yy, self.topo, alpha=1, cmap='gist_earth', vmin=np.min(self.topo), vmax=np.max(self.topo))
        cs = ax.contourf(xx, yy, vort, vortlevs, cmap=plt.cm.RdBu_r, extend='both', alpha=0.5)
        plt.xlim(xx.min(), xx.max())
        plt.ylim(yy.min(), yy.max())
        if NL.topo == 'Earth':
            self.bmaps['global'].drawcoastlines()
        parallels = np.arange(-70.,81,10.)
        meridians = np.arange(10.,351.,20.)
        self.bmaps['global'].drawmeridians(meridians,labels=[True,False,False,True])
        self.bmaps['global'].drawparallels(parallels,labels=[True,False,False,True])
        ax.quiver(xx[::2,::2], yy[::2,::2], u[::2,::2], v[::2,::2])
        # Plot the forcing
        if showforcing and self.forcing is not None:
            ax.contour(xx, yy, self.forcing, forcelevs, linewidths=2, colors='darkorchid')
        ax.set_title('relative vorticity [s$^{-1}$] and winds [m s$^{-1}$] at %03d hours' % n)
        # Colorbar
        cax = fig.add_axes([0.05, 0.12, 0.9, 0.03])
        plt.colorbar(cs, cax=cax, orientation='horizontal')
        # Save figure
        if not os.path.isdir(NL.figdir+'/global'): os.makedirs(NL.figdir+'/global')
        plt.savefig('{}/global/zeta_wnd_{:03d}.png'.format(NL.figdir,n), bbox_inches='tight')
        plt.close()

        # MAKE REGIONAL HEIGHT & WIND SPEED MAP
        phi = np.divide(psi * NL.omega, NL.g)
        fig, ax = plt.subplots(figsize=(10,6))
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95)
        xx, yy = self.bmaps['regional_x'], self.bmaps['regional_y']
        # Calculate wind speed
        wspd = np.sqrt(u**2 + v**2)
        cs = ax.contourf(xx, yy, wspd, windlevs, cmap=plt.cm.viridis, extend='max')
        self.bmaps['regional'].drawcoastlines()
        self.bmaps['regional'].drawcountries()
        self.bmaps['regional'].drawstates()
        hgtconts = ax.contour(xx, yy, phi, hgtlevs, colors='k')
        # Plot the forcing
        if showforcing and self.forcing is not None:
            ax.contour(xx, yy, self.forcing, forcelevs, linewidths=2, colors='darkorchid')
        ax.set_title('geopotential height [m] and wind speed [m s$^{-1}$] at %03d hours' % n)
        # Colorbar
        cax = fig.add_axes([0.05, 0.12, 0.9, 0.03])
        plt.colorbar(cs, cax=cax, orientation='horizontal')
        # Save figure
        if not os.path.isdir(NL.figdir+'/regional'): os.makedirs(NL.figdir+'/regional')
        plt.savefig('{}/regional/hgt_wspd_{:03d}.png'.format(NL.figdir,n), bbox_inches='tight')
        plt.close()
            
            
###########################################################################################################
##### Other Utilities #####################################################################################
###########################################################################################################


def create_basemaps(lons,lats):
    """ Setup global and regional basemaps for eventual plotting """
    print("Creating basemaps for plotting")

    long, latg = np.meshgrid(lons,lats)

    # Set up a global map
    bmap_globe = Basemap(projection='merc',llcrnrlat=-70, urcrnrlat=70,
                         llcrnrlon=0,urcrnrlon=360,lat_ts=20,resolution='c')
    xg,yg = bmap_globe(long,latg)
    
    # Set up a regional map (currently Pacific and N. America)
    bmap_reg = Basemap(projection='merc',llcrnrlat=0,urcrnrlat=65,llcrnrlon=80, 
                       urcrnrlon=290, lat_ts=20,resolution='l')
    xr,yr = bmap_reg(long,latg)

    return {'global' : bmap_globe, 
            'global_x' : xg, 
            'global_y' : yg,
            'regional' : bmap_reg,
            'regional_x' : xr, 
            'regional_y' : yr, 
            }

def d_dlamb(field,dlamb):
    """ Finds a finite-difference approximation to gradient in
    the lambda (longitude) direction"""
    out = np.divide(np.gradient(field)[1],dlamb) 
    return out

def d_dtheta(field,dtheta):
    """ Finds a finite-difference approximation to gradient in
    the theta (latitude) direction """
    out = np.divide(np.gradient(field)[0],dtheta)
    return out

def Jacobian(A,B,theta,dtheta,dlamb):
    """ Returns the Jacobian of two fields in spherical coordinates """
    term1 = d_dlamb(A,dlamb) * d_dtheta(B,dtheta)
    term2 = d_dlamb(B,dlamb) * d_dtheta(A,dtheta)
    return 1./(NL.Re**2 * np.cos(theta)) * (term1 - term2)

###########################################################################################################

def test_case():
    """
    Runs an example case: extratropical zonal jets with superimposed sinusoidal NH vorticity
    perturbations and a gaussian vorticity tendency forcing.
    """
    from time import time
    start = time()
    
    # 1) LET'S CREATE SOME INITIAL CONDITIONS
    lons = np.arange(0, 360.1, 2.5)
    lats = np.arange(-87.5, 88, 2.5)[::-1]
    lamb, theta = np.meshgrid(lons * np.pi/180., lats * np.pi/180.)
    # Mean state: zonal extratropical jets
    mag = 25
    ubar = mag * np.cos(theta) - 30 * np.cos(theta)**3 + 300 * np.sin(theta)**2 * np.cos(theta)**6
    #ubar[:,:] = 20
    vbar = np.zeros(np.shape(ubar))
    # Initial perturbation: sinusoidal vorticity perturbations
    A = 1.5 * 8e-5 # vorticity perturbation amplitude
    m = 2          # zonal wavenumber
    theta0 = np.deg2rad(45)  # center lat = 45 N
    thetaW = np.deg2rad(15) #15
    vort_pert = 0.5*A*np.cos(theta)*np.exp(-((theta-theta0)/thetaW)**2)*np.cos(m*lamb)
    #vort_pert[:,:] = 0
    # Get U' and V' from this vorticity perturbation
    s = spharm.Spharmt(len(lons), len(lats), gridtype='regular', legfunc='computed', rsphere=NL.Re)
    uprime, vprime = s.getuv(s.grdtospec(vort_pert), np.zeros(np.shape(s.grdtospec(vort_pert))))
    # Full initial conditions dictionary:
    ics = {'u_bar'  : ubar,
           'v_bar'  : vbar,
           'u_prime': uprime,
           'v_prime': vprime,
           'lons'   : lons,
           'lats'   : lats,
           'start_time' : datetime(2017,1,1,0)}

    # 2) LET'S ALSO FEED IN A GAUSSIAN NH RWS FORCING
    amplitude = 10e-10              # s^-2
    forcing = np.zeros(np.shape(ubar))
    x, y = np.meshgrid(np.linspace(-1,1,10), np.linspace(-1,1,10))
    d = np.sqrt(x*x+y*y)
    sigma, mu = 0.5, 0.0
    g = np.exp(-( (d-mu)**2 / ( 2.0 * sigma**2 ) ) )   # GAUSSIAN CURVE
    lat_i = np.where(lats==35.)[0][0]
    lon_i = np.where(lons==160.)[0][0]
    forcing[lat_i:lat_i+10, lon_i:lon_i+10] = g*amplitude
    forcing[:,:] = 0
    # 3) INTEGRATE!
    model = Model(ics, forcing=forcing)
    model.integrate()
    print('TOTAL INTEGRATION TIME: {:.02f} minutes'.format((time()-start)/60.))

if __name__ == '__main__':
    test_case()
