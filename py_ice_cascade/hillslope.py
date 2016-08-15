"""
Python ICE-CASCADE hillslope erosion-deposition model component

References:

    (1) Becker, T. W., & Kaus, B. J. P. (2016). Numerical Modeling of Earth
    Systems: Lecture Notes for USC GEOL557 (1.1.4)
"""

import numpy as np
import matplotlib.pyplot as plt
import time
import scipy.sparse

class ftcs():
    """
    Hillslope diffusion model using forward-time center-space (FTCS) finite
    diffence scheme with "open" boundary conditions. 
    
    For an overview of FTCS see reference (1). 
    
    At the "open" boundaries, incoming and outgoing flux normal to the boundary
    is equal. In other words, material is allowed to pass through the boundary
    node. This condition means dq/dx = 0, and the boundary-normal component of
    the diffusion equation goes to 0 as well. Note that boundary-parallel flux
    gradients are not necessarily 0, and so boundary heights may not be
    constant. 
    """

    # NOTE: attributes and methods with the "_" prefix are considered private,
    #       use outside the object at your own risk

    def __init__(self, height, delta, kappa):
        """
        Arguments:
            height = 2D Numpy array, surface elevation in model domain, [m]
            delta = Scalar double, grid spacing, assumed square, [m]
            kappa = Scalar double, diffusion coefficient, [m**2/a]
        """

        self._height = None
        self._delta = None
        self._kappa = None
        self._nx = None
        self._ny = None

        self.set_height(height)
        self.set_diffusivity(kappa)
        self._delta = np.double(delta)
        self._set_coeff_matrix() # TODO: use BC names to adapt boundary coefficients

    def set_height(self, new):
        """Set height grid internal attribute"""
        new_array = np.double(new)
        if new_array.ndim != 2:
            print("hillslope: height is not a 2D array"); sys.exit()
        if (self._height != None) and (new_array.shape != (self._ny, self._nx)):
            print("hillslope: cannot change shape of height grid"); sys.exit()
        self._ny, self._nx = new_array.shape
        self._height = np.ravel(new_array, order='C')

    def get_height(self):
        """Return height grid as 2D numpy array"""
        return self._height.reshape((self._ny, self._nx), order='C')

    def set_diffusivity(self, new):
        """Set diffusivity grid internal attribute"""
        self._kappa = np.double(new)
        if self._kappa.ndim != 2:
            print("hillslope: diffusivity is not a 2D array"); sys.exit()
        if self._kappa.shape != (self._ny, self._nx):
            print("hillslope: diffusitity grid dims do not match height grid"); sys.exit()

    def _set_coeff_matrix(self):
        """Define sparse coefficient matrix for dHdt stencil"""
        # NOTE: FTCS is a 5-point stencil, since diffusivity is a grid, all
        # coefficients are potentially unique. The approach here is to compute
        # coefficients for each diagonal as a matrix including BCs, then
        # convert to a sparse penta-diagonal. Special care is needed to allow
        # for the general case where some diagonals may wrap around.
        
        # declare coefficient arrays
        i_j   = np.zeros((self._ny, self._nx), dtype = np.double)
        im1_j = np.zeros((self._ny, self._nx), dtype = np.double)
        ip1_j = np.zeros((self._ny, self._nx), dtype = np.double)
        i_jm1 = np.zeros((self._ny, self._nx), dtype = np.double)
        i_jp1 = np.zeros((self._ny, self._nx), dtype = np.double)

        # populate coefficients for interior points
        inv2delta2 = 1.0/(2.0*self._delta*self._delta)
        kappa_i_j   = self._kappa[1:-1,1:-1] # just views, should be efficient
        kappa_ip1_j = self._kappa[2:  ,1:-1]
        kappa_im1_j = self._kappa[ :-2,1:-1]
        kappa_i_jp1 = self._kappa[1:-1,2:  ]
        kappa_i_jm1 = self._kappa[1:-1, :-2]

        i_j[1:-1,1:-1] = -inv2delta2*(4.0*kappa_i_j + kappa_im1_j + kappa_ip1_j + kappa_i_jm1 + kappa_i_jp1)
        im1_j[1:-1,1:-1] = inv2delta2*(kappa_i_j + kappa_im1_j)
        ip1_j[1:-1,1:-1] = inv2delta2*(kappa_i_j + kappa_ip1_j)
        i_jm1[1:-1,1:-1] = inv2delta2*(kappa_i_j + kappa_i_jm1)
        i_jp1[1:-1,1:-1] = inv2delta2*(kappa_i_j + kappa_i_jp1)

        # convert coeffs to vectors
        i_j = np.ravel(i_j, order='C')
        ip1_j = np.ravel(ip1_j, order='C')
        im1_j = np.ravel(im1_j, order='C')
        i_jp1 = np.ravel(i_jp1, order='C')
        i_jm1 = np.ravel(i_jm1, order='C')

        # NOTE: leaving boundary coefficients as 0 is equivalent to a constant
        # boundary condition. I leave this for now and move on to test the
        # whole pipeline.

        # construct sparse coefficient matrix
        dd = [];                       kk = [] 
        # # center diagonal 
        dd.append(i_j);                kk.append(0)
        # # upper diagonal, last element wraps
        dd.append(i_jp1[:-1]);         kk.append(1) 
        dd.append(i_jp1[-1:]);         kk.append(-self._ny*self._nx+1)  
        # # lower diagonal, first element wraps
        dd.append(i_jm1[1:]);          kk.append(-1) 
        dd.append(i_jm1[:1]);          kk.append(self._ny*self._nx-1)
        # # outer upper diagonal, last nx elements wrap
        dd.append(ip1_j[0:-self._nx]); kk.append(self._nx)
        dd.append(ip1_j[-self._nx:]);  kk.append(-self._ny*self._nx+self._nx)
        # # outer lower diagonal, first nx elements wrap 
        dd.append(im1_j[self._nx:]);   kk.append(-self._nx)
        dd.append(im1_j[:self._nx]);   kk.append(self._ny*self._nx-self._nx)
        # # construct compressed-row matrix from diagonals 
        self._A = scipy.sparse.diags(dd, offsets=kk, format="csr", dtype=np.double)

        # # backup: inefficient, clear, working
        # A  = np.diag(i_j       , k=0) 
        #
        # A += np.diag(i_jp1[:-1], k=1) # upper diagonal, last element wraps to first
        # A += np.diag(i_jp1[-1:], k=-self._ny*self._nx+1)  
        # 
        # A += np.diag(i_jm1[1:], k=-1) # lower diagonal, first element wraps to last
        # A += np.diag(i_jm1[:1], k=self._ny*self._nx-1)
        #
        # A += np.diag(ip1_j[0:-self._nx], k=self._nx) # outer upper diagonal, last nx wrap to first
        # A += np.diag(ip1_j[-self._nx:], k=-self._ny*self._nx+self._nx)
        #
        # A += np.diag(im1_j[self._nx:], k=-self._nx) # outer lower diagonal, first nx wrap to last
        # A += np.diag(im1_j[:self._nx], k=self._ny*self._nx-self._nx)
        #
        # self._A = scipy.sparse.csr_matrix(A)


    def run(self, run_time):
        """
        Run numerical integration for specified time period

        Arguments:
            run_time = Scalar double, model run time, [a]
        """
        
        run_time = np.double(run_time)
        time = np.double(0.0)    
        max_step = 0.95*self._delta*self._delta/(4.0*np.max(self._kappa)) # stable time step, note ref (1) has error

        while time < run_time:
            step = min(run_time-time, max_step)
            self._height += step*self._A.dot(self._height)
            time += step

if __name__ == '__main__':
    
    # basic usage example and "smell test": relaxation to height==0 steady state
    # # initialize model
    nx = 100
    ny = 100
    max_time = 5.0
    time_step = 0.05
    h0 = np.random.rand(ny, nx).astype(np.double)-0.5
    h0[:,0] = np.double(0.0) # constant values are compatible with "open" BC treatment
    h0[:,-1] = np.double(0.0)
    h0[0,:] = np.double(0.0)
    h0[-1,:] = np.double(0.0)
    dd = np.double(1.0)
    kk = np.ones((ny, nx), dtype=np.double)
    model = ftcs(h0, dd, kk)

    # # update and plot model
    plt.imshow(model.get_height(), interpolation='nearest', clim=(-0.5,0.5))
    plt.colorbar()
    plt.ion()
    time = 0.0
    while time < max_time: 
        model.run(time_step)
        time += time_step
        plt.cla()
        plt.imshow(model.get_height(), interpolation='nearest', clim=(-0.5,0.5))
        plt.title("TIME = {:.2f}".format(time))
        plt.pause(0.05)
