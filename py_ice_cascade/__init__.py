"""
Python ICE-CASCADE landscape evolution model

Note: simulation progress is reported using the *logging* module, with the
level set at the package level logger *py_ice_cascade.logger*. The logging
level can be modified by explicitly updating this logger, like so:

.. code-block:: python

   import py_ice_cascade
   import logging
   py_ice_cascade.logger.setLevel(logging.WARNING)
"""
# TODO: add top-level usage documentation

# shared project metadata
# # __XXX__ indicates standard metadata vars
# # _XXX    indicates custom   metadata vars
__name__ = 'py_ice_cascade'
__version__ = '0.0.1'
_description = 'Python implementation of ICE-CASCADE landscape evolution model'
_url = 'https://github.com/keithfma/py_ice_cascade'
_author = 'Keith F. Ma'
_author_email = 'keithfma@gmail.com'

# load submodules
from .main import main_model
from . import hillslope
from . import uplift

# setup package-level logger
import logging
import sys
logger = logging.getLogger(name=__name__) 
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(name)s | %(levelname)s | %(message)s | %(asctime)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
