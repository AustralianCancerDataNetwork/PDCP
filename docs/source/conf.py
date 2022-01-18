# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# sphinx-build -b pdf source build to generate the pdf
import os
import sys
import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../code/'))

# -- Project information -----------------------------------------------------

project = 'PDCP'
copyright = '2021, Ali Haidar'
author = 'Ali Haidar'

# The full version, including alpha/beta/rc tags
release = '0.0.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.napoleon',
              'sphinx.ext.autosummary','sphinx_rtd_theme','rst2pdf.pdfbuilder']

pdf_documents = [('index', u'rst2pdf', u'Patient Data Collection and Processing (PDCP)', u'Ali Haidar'),]
# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []



autosummary_generate = True  # Turn on sphinx.ext.autosummary

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


#to use auto API
#extensions.append('autoapi.extension')
#autoapi_type = 'python'
#autoapi_dirs = ['../../code/']
#autoapi_ignore=['*LUNG2021*','*L_SEG_*','*L_*','*B_*','*HN_*','*EX_*','*convert*','*Example_*','*Copy*']


#using  automodapi

extensions.append('sphinx_automodapi.automodapi')
numpydoc_show_class_members = False
numpydoc_class_members_toctree = False