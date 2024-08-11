# This file contains the WSGI configuration required to serve up your
# web application at http://chasecab.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.
#

# +++++++++++ GENERAL DEBUGGING TIPS +++++++++++
# getting imports and sys.path right can be fiddly!
# We've tried to collect some general tips here:
# https://help.pythonanywhere.com/pages/DebuggingImportError



# +++++++++++ VIRTUALENV +++++++++++
# If you want to use a virtualenv, set its path on the web app setup tab.
# Then come back here and import your application object as per the
# instructions below



# +++++++++++ FLASK +++++++++++
# Flask works like any other WSGI-compatible framework, we just need
# to import the application.  Often Flask apps are called "app" so we
# may need to rename it during the import:
#
#
import sys
import os
os.environ['NOTION_API_KEY'] = 'secret_ojPwTo9nMCHFBVlSFD4QuNCKghIvXFuxkpprLg3YVn1'
os.environ['NOTION_DATABASE_ID'] = '6c2660ed272a42ef8802413289afd183'
#
## The "/home/chasecab" below specifies your home
## directory -- the rest should be the directory you uploaded your Flask
## code to underneath the home directory.  So if you just ran
## "git clone git@github.com/myusername/myproject.git"
## ...or uploaded files to the directory "myproject", then you should
## specify "/home/chasecab/myproject"
path = '/home/chasecab/my-notion-agent/'
if path not in sys.path:
    sys.path.append(path)
#
from app import app as application
#
# NB -- many Flask guides suggest you use a file called run.py; that's
# not necessary on PythonAnywhere.  And you should make sure your code
# does *not* invoke the flask development server with app.run(), as it
# will prevent your wsgi file from working.
