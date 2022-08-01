import pandas as pd
from JMTracker.auxiliary import (
    validate_unique_id, validator_generator, validate_extension
)


"""
An example customized settings file. Uncomment and modify lines according
to your preferences and needs.
"""

settings = {
    # Color theme for GUI from PySimpleGui
    # To see the full list of available themes, execute the following in a
    # python console:
    #    import PySimpleGUI as sg
    #    sg.list_of_look_and_feel_values()
    # 'gui_theme': 'Material1',

    # Decide whether custom input settings are overriden or updated. False will
    # mean that any inputs you setup below will be added to the list of input
    # sources. True will make it override the default list of inputs. If you
    # override and set no sources, the system will likely crash and papa will
    # be very mad at you.
    # 'custom_overrides_default': False,
}


# == Input Type Configuration === #
"""
The following options determine where we get information from and how process
it.


Required Columns:
-----------------
The system requires the following columns in any input file:
 - origin_id: an integer indexing the listings. This should be a unique
          identifier of a posting within a system.
 - title: the title of the posting
 - location: the location of the posting
 - institution: the name of the institution
 - deadline: the application deadline in year-month-day
 - url: the url to the full posting

Optional Columns:
-----------------
Besides these, the system also stores any column given a name in the renaming
rules, unless explicitly included in the "to_drop" list. The following columns
are also shown to users, if they exist:
    - section, division, department, keywords, full_text

Column Generators:
------------------
If, after renaming some of the required or optional columns are missing, the system
will see if a generator missing exist. This generator should have a key
equal to {column name}_generator and should be a function that takes a row
of the data and the dataframe of postings already included (or None if its the
first usage) and return a value for the row.

Important:
----------
there's a series of column names that are protected and will be overwritten
even if present in the data:
"origin", "status", "updated", 'date_received', 'reveiewed', 'update_notes',
'notes', 'origin_id'

Also, 'origin_id' must be unique within each source, such that the tuple
('origin', 'origin_id') uniquely identifies a posting.



See the example below for more details or look at the original
setting file within the project folder


input_option_settings = [
    {
        # Name for the origin
        'origin': 'CustomDocs',
        # Download url
        'download_url': '..',
        # Expected extension for download hint
        'expected_extension': 'csv',
        # A validator for the path given for the file to load
        'url_validator': validator_generator(
            [validate_extension], 'CustomDocs', [('csv', 'CustomDocs')]
        ),
        # Input file name to move ans store
        'input_file_name': 'latest_nu.csv',
        # A validator for the data
        'validator': validator_generator(
            [validate_unique_id], 'CustomDocs', [('ID', 'CustomDocs')]
        ),
        # Download instructions
        'download_instructions': 'Download as CSV!',
        # Custom loader
        'loader': pd.read_csv,
        # Renaming rules to match the requirements of the system
        'renaming_rules': {
            'ID': 'origin_id',
            'Title': 'title',
            'Institution': 'institution',
            'Department': 'department',
            'Deadline': 'deadline',
            'URL': 'url'
        },
        # Location generator if not provided.
        'location_generator': (lambda x, y: 'unknown')
    },
]

"""
