"""
Unit tests for Python ICE-CASCADE hillslope erosion-deposition forward-time
centered-space model component

References:

(1) Holman, J. P. (2002). Heat transfer (pp. 75) 
"""

import unittest
import numpy as np
from py_ice_cascade import hillslope

class ftcs_TestCase(unittest.TestCase):
    """Tests for hillslope ftcs model component"""
    
    # arbitrary valid values for input arguments
    hh = np.random.rand(10,10)
    dd = 1.0
    mm = np.ones((10,10))
    kon = 1.0
    koff = 0.0
    bb = ['constant']*4

    def test_input_valid_bc(self):
        """Allow all supported BC names, and fail for others"""
        hillslope.ftcs_model(self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['constant', 'closed', 'open', 'mirror'])
        hillslope.ftcs_model(self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['cyclic', 'cyclic', 'constant', 'constant'])
        self.assertRaises(ValueError, hillslope.ftcs_model, self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['ooga_booga', 'cyclic', 'constant', 'constant'])

    def test_input_cyclic_bc(self):
        """Unmatched cyclic BCs should throw an error"""
        self.assertRaises(ValueError, hillslope.ftcs_model, self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['cyclic', 'constant', 'constant', 'constant'])
        self.assertRaises(ValueError, hillslope.ftcs_model, self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['constant', 'cyclic', 'constant', 'constant'])
        self.assertRaises(ValueError, hillslope.ftcs_model, self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['constant', 'constant', 'cyclic', 'constant'])
        self.assertRaises(ValueError, hillslope.ftcs_model, self.hh, self.mm, self.dd, self.kon, self.koff, 
            ['constant', 'constant', 'constant', 'cyclic'])

    def test_consistent_dims(self):
        """Unequal array dims for height and mask throws error"""
        self.assertRaises(ValueError, hillslope.ftcs_model, np.random.rand(11,11), self.mm, self.dd, self.kon, self.koff, self.bb)
        self.assertRaises(ValueError, hillslope.ftcs_model, self.hh, np.random.rand(11,11), self.dd, self.kon, self.koff, self.bb)

    def test_protect_model_dims(self):
        """Attempt to set model grid with incorrect size array throw error"""
        model = hillslope.ftcs_model(self.hh, self.mm, self.dd, self.kon, self.koff, self.bb)
        self.assertRaises(ValueError, model.set_height, np.random.rand(11,11))
        self.assertRaises(ValueError, model.set_mask, np.random.rand(11,11))

    def test_steady_bc_constant(self):
        """Compare against exact solution for sinusoid y=max and zero at other bnd"""
        
        # parameters
        h0 = 1.0
        nx = 100
        ny = 50
        lx = 1.0
        delta = lx/(nx-1)
        ly = delta*(ny-1)
        t_end = 0.25
        epsilon = 0.001

        # Case 1:
        # # exact solution
        xx = np.linspace(0, lx, nx, dtype=np.double).reshape(( 1,nx))
        yy = np.linspace(0, ly, ny, dtype=np.double).reshape((ny, 1))
        h_exact = h0/np.sinh(np.pi*ly/lx)*np.sin(np.pi*xx/lx)*np.sinh(np.pi*yy/lx)
        # # numerical solution
        h_init = np.zeros((ny, nx))
        h_init[-1,:] = h0*np.sin(np.pi*xx/lx)
        kappa = 1.0
        mask = np.ones((ny,nx))
        bcs = ['constant']*4
        model = hillslope.ftcs_model(h_init, mask, delta, kappa, kappa, bcs)
        model.run(t_end)
        # # check errors
        h_error = np.abs(model.get_height()-h_exact)
        self.assertTrue(np.max(h_error) < epsilon)

        # Case 2: rotate 90 degrees
        # # exact solution
        h_exact = np.rot90(h_exact)
        # # numerical solution
        h_init = np.rot90(h_init)
        mask = np.rot90(mask)
        bcs = ['constant']*4
        model = hillslope.ftcs_model(h_init, mask, delta, kappa, kappa, bcs)
        model.run(t_end)
        # # check errors
        h_error = np.abs(model.get_height()-h_exact)
        self.assertTrue(np.max(h_error) < epsilon)

    def test_steady_layered_kappa(self):
        """Compare against exact solution for diffusion in 2 layered material"""

        # parameters
        nx = 100
        ny = 5 
        lx = 1.0
        delta = lx/(nx-1)
        xx = np.linspace(0, lx, nx, dtype=np.double).reshape((1,nx))*np.ones((ny,1))
        l0 = 0.5*(xx[0,50]+xx[0,51]) # transition at midpoint
        l1 = lx-l0
        h0 = 1.0
        h1 = 0.0
        k0 = 1.0
        k1 = 0.5
        t_end = 1.5
        epsilon = 0.001

        # Case 1:
        # # exact solution (resistance = l/k in series) 
        qq = (h0-h1)/(l0/k0+l1/k1)
        hb = h0-qq*l0/k0 # or: hb = qq*l1/k1-h1 
        xx = np.linspace(0, lx, nx, dtype=np.double).reshape((1,nx))*np.ones((ny,1))
        h_exact = np.where(xx <= l0, h0+(hb-h0)/l0*xx, hb+(h1-hb)/l1*(xx-l0))
        # # numerical solution
        h_init = np.zeros((ny, nx))
        h_init[:,0] = h0
        h_init[:,-1] = h1
        mask = np.where(xx <= l0, True, False)
        bcs = ['closed', 'closed', 'constant', 'constant'] 
        model = hillslope.ftcs_model(h_init, mask, delta, k0, k1, bcs)
        model.run(t_end)
        # # check errors
        h_error = np.abs(model.get_height()-h_exact)
        self.assertTrue(np.max(h_error) < epsilon)

        # Case 2: rotate 90 degrees
        # # exact solution
        h_exact = np.rot90(h_exact)
        # # numerical solution
        h_init = np.rot90(h_init)
        mask = np.rot90(mask)
        bcs = ['constant', 'constant', 'closed', 'closed']
        model = hillslope.ftcs_model(h_init, mask, delta, k0, k1, bcs)
        model.run(t_end)
        # # check errors
        h_error = np.abs(model.get_height()-h_exact)
        self.assertTrue(np.max(h_error) < epsilon)

    def test_mass_conservation(self):
        """Confirm mass conservation with closed and cyclic BCs"""

        # parameters
        nx = ny = 100
        delta = 1.0/(nx-1)
        h_init = np.linspace(0.0, 1.0, nx).reshape(1,nx)*np.linspace(0.0, 1.0, ny).reshape(ny,1)
        h_init += 0.1*(np.random.rand(ny, nx)-0.5)
        mask = np.where(np.random.rand(ny, nx)>0.5, True, False)
        kappa1 = 1.0
        kappa0 = 0.5
        t_end = 0.25
        epsilon = 0.0001

        # Case 1
        # # exact solution
        h_total = np.sum(h_init)
        # # numerical solution
        bcs = ['cyclic', 'cyclic', 'closed', 'closed']
        model = hillslope.ftcs_model(h_init, mask, delta, kappa1, kappa0, bcs)
        model.run(t_end)
        # # check error
        h_error = np.abs(h_total-np.sum(model.get_height()))
        self.assertTrue(h_error < epsilon)

        # Case 2: rotate 90 deg
        # # exact solution
        # # numerical solution
        h_init = np.rot90(h_init)
        mask = np.rot90(mask)
        bcs = ['closed', 'closed', 'cyclic', 'cyclic']
        model = hillslope.ftcs_model(h_init, mask, delta, kappa1, kappa0, bcs)
        model.run(t_end)
        # # check error
        h_error = np.abs(h_total-np.sum(model.get_height()))
        self.assertTrue(h_error < epsilon)

if __name__ == '__main__':
    unittest.main()
