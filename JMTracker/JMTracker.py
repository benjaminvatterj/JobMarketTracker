import os
from distutils.dir_util import copy_tree
import pickle
import importlib
import numpy as np
from textwrap import dedent, shorten
import pandas as pd
import webbrowser
from shutil import copyfile
from JMTracker import settings, input_option_settings
import logging
import PySimpleGUI as sg
import humanize


class Tracker():

    """A class that collects functionalities to keep track of
    job market applications"""

    def __init__(self):
        """Initialize the tracker obejct"""
        logging.info("Initializing tracker object")
        self._input_dir = settings['input_directory']
        if not os.path.isdir(self._input_dir):
            os.mkdir(self._input_dir)
        self._output_dir = settings['output_directory']
        if not os.path.isdir(self._output_dir):
            os.mkdir(self._output_dir)
        self._storage_dir = settings['storage_directory']
        if not os.path.isdir(self._storage_dir):
            os.mkdir(self._storage_dir)

        custom_settings_url = settings['custom_settings']
        self._input_option_settings = input_option_settings
        if os.path.isfile(custom_settings_url):
            spec = importlib.util.spec_from_file_location(
                'settings', custom_settings_url
            )
            if spec is not None:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'settings'):
                    # Update current setting
                    custom_settings = module.settings
                    settings.update(custom_settings)
            spec = importlib.util.spec_from_file_location(
                'input_option_settings', custom_settings_url
            )
            if spec is not None:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'input_option_settings'):
                    # Update input option settings
                    new_inputs = module.input_option_settings
                    if not settings['custom_overrides_default']:
                        self._input_option_settings += new_inputs
                    else:
                        self._input_option_settings = new_inputs.copy()

        # Set the GUI theme
        sg.theme(settings['gui_theme'])

        # Check if we have the key storage
        self._postings_url = os.path.join(
            self._storage_dir, 'all_postings.pkl'
        )
        self._first_run = False
        if not os.path.isfile(self._postings_url):
            logging.info("Tracker is being used for the first time.\n"
                         "This tool will store its internal data in \n"
                         f"{self._postings_url}.")
            self._first_run = True

        # Check if we have the settings file
        self._personal_settings_url = os.path.join(
            self._storage_dir, "personal_settings.pkl"
        )
        if not os.path.isfile(self._personal_settings_url):
            logging.info(
                "No personal setting file found. Creating a default one")
            self._personal_settings = {
                'custom_posting_cols': [],
                'custom_application_cols': [],
                'letters': [],
                'scaffolding_base': None,
                'scaffolding_output_dir': None
            }
            with open(self._personal_settings_url, 'wb') as handle:
                pickle.dump(self._personal_settings, handle)
        else:
            with open(self._personal_settings_url, 'rb') as handle:
                self._personal_settings = pickle.load(handle)

        self._pending_updates_url = os.path.join(
            self._storage_dir, 'updates_pending_review.pkl'
        )
        return

    def main_gui(self):
        """Show the main GUI for this system
        """
        layout = [
            [sg.Text("Update postings:"), sg.Button(
                "view", key="-UPDATE POSTINGS-")],
            [sg.Text("Manual entry:"), sg.Button("view", key='-MANUAL-')],
            [sg.Text("Review new postings:"), sg.Button("new", key="-NEW-")],
            [sg.Text("Manage updates:"), sg.Button("view", key="-UPDATES-")],
            [sg.Text("Edit ignored postings:"),
             sg.Button("view", key="-IGNORED-")],
            [sg.Text("View deadlines:"), sg.Button("view", key="-DEADLINES-")],
            [sg.Text("Manage applications:"), sg.Button(
                "view", key="-APPLICATIONS-")],
            [sg.Text("Settings:"), sg.Button("view", key="-SETTINGS-")],
            [sg.Text("View help:"), sg.Button("view", key="-HELP-")],
            [sg.Button("Close")]
        ]
        window = sg.Window('Job Market Tracker', layout, resizable=True)
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == "Close":
                window.close()
                return
            elif event == "-UPDATE POSTINGS-":
                window.close()
                self.update_postings_gui(window_location)
                return self.main_gui()
            elif event == "-NEW-":
                window.close()
                self.review_new_postings(window_location)
                return self.main_gui()
            elif event == '-IGNORED-':
                window.close()
                self.review_ignored_gui(window_location)
                return self.main_gui()
            elif event == "-MANUAL-":
                window.close()
                self.manual_entry(window_location)
                return self.main_gui()
            elif event == "-DEADLINES-":
                window.close()
                self.review_interested_gui(window_location)
                return self.main_gui()
            elif event == "-APPLICATIONS-":
                window.close()
                self.review_applications_gui(window_location)
                return self.main_gui()
            elif event == "-SETTINGS-":
                window.close()
                self.set_configuration_gui(window_location)
                return self.main_gui()
            elif event == "-UPDATES-":
                window.close()
                self.review_updates()
                return self.main_gui()
            elif event == "-HELP-":
                help_text = dedent(
                    """
                    The process for managing applications is as follows:

                    1) Go to \"update postings\" and download the AEA and EJM files
                    to your local computer. For the AEA download the native XML
                    and for the EJM download in CVS. This system does not provide
                    any type of filtering, so if you want to exclude rows, you should
                    do so manually in the XML/CSV files. Once you're ready, set the
                    location of each file in the finder, and click the update.
                    The system will review each posting in each file and evaluate
                    whether there are new postings or updates to existings ones.
                    New postings will be added to your local new-posting list,
                    while updates will be added to your pending update review list.

                    2) To manage new postings, go to \"Review new postings\"
                    This will show each posting, one by one, allowing you to classify
                    each as interested, maybe interested, or ignore. You can also see
                    the details of postings or go directly to the website.

                    3) To manage updates, go to \"Manage updates\". The system
                    will list all new collected updates and will allow you to
                    accept or reject each update for each posting.

                    4) To see your application deadline go to \"View deadlines\"
                    there you will find all the postings you marked as
                    interested or maybes. Note that some employers do a very
                    bad job of marking the correct deadline in AEA and EJM,
                    and some even don't write any. Often the correct deadline
                    is in the full text. So it is recommended for you to review
                    each deadline (particularly those that show up as very far
                    in the future). The system allows you to modify the deadline
                    of each interested posting manually at this stage.

                    If you have any questions or found a bug, please submit an issues
                    to the github page. If there's a new version and you would
                    like to update, you just need to copy the files found
                    in the storage/ folder and move them to your new copy
                    of the new version. If you would like to start a new
                    application process from scratch, just delete those same
                    files from your storage folder. If you would like to contribute
                    please visit the github page.
                    """
                )
                sg.popup_scrolled(help_text, title='help', location=window_location,
                                  size=(65, 35), font='Helvetica 12')
            else:
                logging.info(f"Got unkown event {event}")
                return

        return

    def update_postings_gui(self, window_location=(None, None)):
        """Prompt to update files from AEA and EJM
        """
        updated_origins = {x['origin']: False for x in self._input_option_settings}

        def core_layout(updated_origins):
            """Produces the layout for the posting update"""
            mid_layouts = []
            for source_setting in self._input_option_settings:
                origin = source_setting['origin']
                if updated_origins.get(origin, False):
                    mid_layouts.append(
                        [sg.Text(f"{origin} listings updated successfully")]
                    )
                    continue
                expected_extension = source_setting.get(
                    'expected_extension', None)
                hint = 'hint: download from here'
                if expected_extension is not None:
                    hint = f'hint: download from here as {expected_extension}'
                layout = [
                    [sg.Text(f"{origin} file: "), sg.Input(),
                     sg.FileBrowse(key=f"-IN-{origin}-")],
                    [sg.Text(hint),
                     sg.Button("link", key=f"-LINK-{origin}-"),
                     sg.Button("help", key=f"-HELP-{origin}-")],
                    [sg.Button(f"Update {origin}", key=f"-UPDATE-{origin}-")],
                ]
                # Add a separator
                if len(mid_layouts) > 0:
                    mid_layouts.append([sg.HSeparator()])
                    mid_layouts += layout
                else:
                    mid_layouts = layout

            layout = [
                [sg.Column(mid_layouts)],
                [sg.HSeparator()],
                [sg.Button("Close and Save", key="-CLOSE-")]
            ]

            return layout

        # Building Window
        layout = core_layout(updated_origins)
        size = (None, None)
        window = sg.Window('Refresh Listings', layout, size=size,
                           location=window_location)
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == "-CLOSE-":
                window.close()
                break
            elif 'UPDATE' in event:
                origin = event.split("-")[2]
                source_setting = [x for x in self._input_option_settings if
                                  x['origin'] == origin][0]

                url = values[f"-IN-{origin}-"]
                if not os.path.isfile(url):
                    sg.popup(f"{origin} file {url} not found!")
                    continue
                status, message = self.update_source_postings(
                    url, source_setting, window_location
                )
                if not status:
                    sg.popup(message, location=window_location)
                    continue
                window.close()
                updated_origins[origin] = True
                layout = core_layout(updated_origins)
                window = sg.Window('Refresh Listings', layout, size=size,
                                   location=window_location)
            elif 'LINK' in event:
                origin = event.split("-")[2]
                source_setting = [x for x in self._input_option_settings if
                                  x['origin'] == origin][0]
                url = source_setting.get('download_url', None)
                if url is not None:
                    webbrowser.open(url)
                else:
                    action = source_setting.get('download_action', None)
                    if action is None:
                        sg.popup_error("Something went wrong. Couldn't find a link"
                                       " or an action for downloading")
                        continue
                    else:
                        action(window_location)
                        continue

            elif 'HELP' in event:
                origin = event.split("-")[2]
                source_setting = [x for x in self._input_option_settings if
                                  x['origin'] == origin][0]
                txt = source_setting['download_instructions']
                sg.popup(txt, location=window_location)
            else:
                logging.warning(f"Got unkown event {event}")

        window.close()

        return

    def update_source_postings(self, url, source_setting,
                               window_location=(None, None)):
        """Process the postings for a specific source.

        Parameters
        ----------
        url: str
            path to the file the user indicated when updating in the GUI

        source_setting : dict
            the dictionary containing the source's settings

        window_location : tuple, optional
            window location for any popup

        Returns
        -------
        status: bool
            success status of the update process

        message: str
            in case of failure a descriptive message

        """

        # --- 1) Copy, load, validate, and parse --- #
        url_validator = source_setting.get('url_validator', None)
        if url_validator is not None:
            status, message = url_validator(url)
            if not status:
                return status, message

        # Copy to new locations
        new_url = source_setting.get('input_file_name', None)
        if new_url is not None:
            new_url = os.path.join(self._input_dir, new_url)
            copyfile(url, new_url)
        else:
            new_url = url

        origin = source_setting['origin']

        if not os.path.isfile(new_url):
            message = (
                f"Couldnt locate the {origin} file. This can happen if "
                f" you already updated the {origin} file, forgot "
                " to browse to the file in the menu, or manually included "
                " the path to the file. Please try again."
            )
            return False, message

        # Load the data
        df = source_setting['loader'](new_url)
        # Validate it if requested
        validator = source_setting.get('validator', None)
        if validator is not None:
            status, message = validator(df)
            if not status:
                return status, message

        # Renaming rules
        renaming_rules = source_setting.get('renaming_rules', {})
        df.rename(columns=renaming_rules, inplace=True)

        # Keep columns
        required_columns = ['origin_id', 'title', 'location', 'institution',
                            'deadline', 'url']
        optional_columns = ['section', 'division', 'department', 'keywords',
                            'full_text']

        keep = (
            set(required_columns) | set(optional_columns) |
            set([x for x in renaming_rules.values()])
        ) & set(df.columns)
        keep = list(keep)
        df = df.loc[:, keep].copy()

        # Load the current postings for reference
        if os.path.isfile(self._postings_url):
            all_postings = pd.read_pickle(self._postings_url)
        else:
            all_postings = None

        # Handle missing required
        missing_required = [x for x in required_columns if x not in df.columns]
        for col in missing_required:
            generator = source_setting.get(f'{col}_generator', None)
            if generator is None:
                message = dedent(f"""
                The file for {origin} is missing required columns {col}
                and a generator was not supplied in the setting. This
                likely indicates your file is corrupted or wrong, or that
                you modified the system setting erronously.
                """)
                return False, message
            df[col] = df.apply(lambda x: generator(x, all_postings), axis=1)

        # Handle missing optional
        missing_optional = [x for x in optional_columns if x not in df.columns]
        for col in missing_optional:
            generator = source_setting.get(f'{col}_generator', None)
            if generator is None:
                df[col] = ''
            else:
                df[col] = df.apply(
                    lambda x: generator(x, all_postings), axis=1)

        # Order the right way, just for easier inspection
        col_order = required_columns + optional_columns
        col_order += [x for x in df.columns if x not in col_order]
        df = df.loc[:, col_order].copy()

        # Add the custom columns
        df['date_received'] = "{}".format(settings['today'])
        df['origin'] = origin
        df['reviewed'] = False
        df['status'] = 'new'
        df['notes'] = ''
        df['update_notes'] = ''
        df['updated'] = False

        # --- 2) Compare with stored values --- #

        if self._first_run:
            # In this case we just add the extra info and store
            logging.info(f"First time storing {origin} data")
            df.to_pickle(self._postings_url)
            self._first_run = False
            return True, ''

        postings = pd.read_pickle(self._postings_url)
        previous = postings.loc[postings['origin'] == origin, ['origin_id']]
        if previous.shape[0] == 0:
            logging.info(f"First time storing {origin} data, appending")
            postings = pd.concat([postings,df], ignore_index=True)
            postings.to_pickle(self._postings_url)
            return True, ''

        new_ix = ~df['origin_id'].isin(previous['origin_id'].values)
        if new_ix.any():
            logging.info(
                f"Found {new_ix.sum()} new {origin} postings! appending")
            sg.popup(f"Found {new_ix.sum()} new {origin} postings, adding to list.\n"
                     "==== PLEASE REVIEW ALL DEADLINES ===\n"
                     "They are quite often wrong or not available in the platforms.")
            new_postings = df.loc[new_ix, :].copy()
            postings = pd.concat([postings,new_postings], ignore_index=True)
            postings.to_pickle(self._postings_url)
            df = df.loc[~new_ix, :].copy()

        # No more to add
        if df.shape[0] == 0:
            logging.info(f"All {origin} postings were new")
            return True, ''

        # Check the overlapp to see if there's anything new
        check_cols = ['url', 'title', 'section', 'division', 'deadline',
                      'institution']
        sel = (postings['origin'] == origin) & \
            (postings['status'].isin(['interested', 'maybe']))
        previous = postings.loc[sel, :].copy()

        df = df.loc[:, check_cols + ['origin', 'origin_id']]
        df = previous.merge(df, on=['origin', 'origin_id'], how='left',
                            validate='1:1', suffixes=('', '_new'))

        total_updated = 0
        for col in check_cols:
            base_col = col
            if col == 'deadline' and 'original_deadline' in df.columns:
                base_col = 'original_deadline'
            sel = (df[base_col] != df[col + '_new']
                   ) & (df[col + '_new'].notna())
            if sel.any() and col == 'deadline':
                test = pd.to_datetime(df[base_col]) - \
                    pd.to_datetime(df[col + '_new'])
                test = test.dt.days != 0
                sel = sel & test
            total_updated = max(total_updated, sel.sum())
            df.loc[sel, 'updated'] = True
            df.loc[sel, 'update_notes'] += f'new {col},'

        if total_updated > 0:
            logging.info(
                f"Found {total_updated} updated in {origin} postings!")
            sg.popup(f"Found {total_updated} updates for {origin} listings. \n"
                     "You can review them in the `review updates' menu.")

            # Store the updates separately for review
            df = df.loc[df['updated'], :].drop('updated', axis=1).copy()
            # Check if we need to merge with any past updates
            if not os.path.isfile(self._pending_updates_url):
                df.to_pickle(self._pending_updates_url)
                return True, ''

            updates = pd.read_pickle(self._pending_updates_url)
            # In this case we just want to update whatever we have included
            updates['version'] = 0
            df['version'] = 1
            updates = pd.concat([updates,df], ignore_index=True)
            updates.sort_values('version', inplace=True)
            updates.drop_duplicates(['origin', 'origin_id', 'version'],
                                    inplace=True, keep='last')
            updates.drop('version', axis=1, inplace=True)
            updates.to_pickle(self._pending_updates_url)
        else:
            logging.info(f"No new postings in {origin}")

        return True, ''

    def review_new_postings(self, window_location=(None, None),
                            postings=None, window_title=None,
                            allow_delete=False):
        """Look among the new postings

        Parameters
        ----------
        window_location: tuple, optional
            the position to locate the postings

        postings: dataframe, optional
            you can pass this method a different dataframe of postings
            to edit their status. Otherwise will load all new postings

        window_title: str, optional
            custom window title to display

        allow_delete: str, optional
            allows deleting a posting

        Returns
        -------
        None
            edits the posting data
        """
        if postings is None:
            postings = pd.read_pickle(self._postings_url)
            # Restrict to new
            postings.query('status == "new"', inplace=True)

        postings.fillna('', inplace=True)
        break_loop = False
        status_updates = []
        font = 'Helvetica 12'

        num_postings = postings.shape[0]
        if num_postings == 0:
            sg.popup("No new postings to display")
            return

        current_posting = 0
        for ix, row in postings.iterrows():
            current_posting += 1
            # unpack
            section = row['section']
            institution = row['institution']
            division = shorten(row['division'], 100)
            department = shorten(row['department'], 100)
            keywords = shorten(row['keywords'], 100)
            title = row['title']
            text = row['full_text']
            location = row['location']
            deadline = row['deadline']
            origin = row['origin']
            url = row['url']
            origin_id = row['origin_id']
            action_list = [
                sg.Button("Skip"), sg.Button(
                    "Interested"), sg.Button("Ignore"),
                sg.Button("Maybe"), sg.Button("Stop Review", key='-CLOSE-')
            ]
            if allow_delete:
                action_list.append(sg.Button("DELETE"))
            layout = [
                [sg.Text('Title:', font=font + ' underline'),
                 sg.Text(f'{title}', font=font),
                 sg.Text('Institution:', font=font + ' underline'),
                 sg.Text(f'{institution}', font=font)],
                [sg.Text(department + " | "), sg.Text(division + " | "),
                 sg.Text(section + " | ")],
                [sg.Text(f'Location: {location}')],
                [sg.Text(f'Deadline: {deadline}')],
                [sg.Text(f'keywords: {keywords}')],
                [sg.Text(f'Source: {origin}'), sg.Button('See posting', key='-VISIT-'),
                 sg.Button("See full text", key='-FULL-')],
                action_list
            ]

            # size = (600, 400)
            if window_title is None:
                wt = f'New posting ({current_posting} / {num_postings})'
            else:
                wt = window_title
            window = sg.Window(wt, layout, location=window_location)
            while True:
                event, values = window.read()
                # update the window location
                window_location = window.CurrentLocation(True)
                if event == sg.WIN_CLOSED or event in ["-CLOSE-", "Skip"]:
                    window.close()
                    if event == '-CLOSE-':
                        break_loop = True
                    break
                elif event == '-VISIT-':
                    webbrowser.open(url)
                elif event == "Interested":
                    window.close()
                    status_updates.append([origin, origin_id, 'interested'])
                    break
                elif event == "Ignore":
                    status_updates.append([origin, origin_id, 'ignore'])
                    window.close()
                    break
                elif event == "Maybe":
                    status_updates.append([origin, origin_id, 'maybe'])
                    window.close()
                    break
                elif event == 'DELETE':
                    res = sg.popup_ok_cancel(
                        "Are you sure you wish to delete this posting?",
                        location=window_location
                    )
                    if res == 'OK':
                        status_updates.append([origin, origin_id, 'deleted'])
                        window.close()
                        break
                elif event == "-FULL-":
                    self.large_text_popup(text, location=window_location)

            if break_loop:
                break

        # Update status
        if len(status_updates) > 0:
            status_updates = pd.DataFrame(
                status_updates, columns=['origin', 'origin_id', 'status']
            )
            logging.info(
                f"Updating {status_updates.shape[0]} posting statuses")
            postings = pd.read_pickle(self._postings_url)
            postings = postings.merge(status_updates, on=['origin', 'origin_id'],
                                      how='left', validate='1:1',
                                      suffixes=('', '_new'))
            sel = postings['status_new'].notna()
            postings.loc[sel, 'status'] = postings.loc[sel, 'status_new']
            postings.drop('status_new', axis=1, inplace=True)
            postings.to_pickle(self._postings_url)

        return

    def view_deadlines(self, window_location=(None, None)):
        """Display the window with the ongoing deadlines

        Returns
        -------
        None
        """

        # Prepare data
        if not os.path.isfile(self._postings_url):
            sg.popup_error("The postings files was not found. You must first "
                           "update your postings before viewing deadlines.",
                           location=window_location)
            return

        all_postings = pd.read_pickle(self._postings_url)
        posting_cols = ['institution', 'title', 'status'] + \
            self._personal_settings['custom_posting_cols']

        def filter_postings(all_postings, maybe=True, expired=True, applied=False):
            status = ['interested']
            if maybe:
                status.append('maybe')
            if applied:
                status.append('applied')
            postings = (
                all_postings.loc[all_postings['status'].isin(status), :]
                .copy()
            )
            if not expired:
                sel = (
                    pd.to_datetime(postings['deadline']
                                   ) >= pd.Timestamp("today")
                ) | (
                    postings['deadline'].isna()
                )
                postings = postings.loc[sel, :].copy()
            return postings

        def deadlines_from_postings(postings):
            # Ensure we have the right columns

            postings = postings.copy()
            postings['deadline_str'] = pd.to_datetime(
                postings['deadline']).astype(str)
            sel = postings['deadline_str'] == 'NaT'
            postings.loc[sel, 'deadline_str'] = 'Unknown'
            sel = postings['deadline'].notna()
            postings.loc[sel, 'deadline'] =\
                pd.to_datetime(postings.loc[sel, 'deadline'])
            postings['unique_id'] = postings.groupby(
                ['origin', 'origin_id']).ngroup()
            postings['deadline'].fillna('Unknown', inplace=True)
            # Get the number of applications per deadline
            current_deadlines = postings.groupby(
                ['deadline'], as_index=False
            ).agg({'unique_id': 'nunique', 'deadline_str': 'first'})
            today = settings['today']

            def _human_date_delta(x, today=today):
                if x == 'Unknown':
                    return "Unkown deadline"
                x = pd.to_datetime(x).to_pydatetime().date()
                return humanize.naturaltime(today - x).replace("from now", "").strip()

            current_deadlines['time_left'] = current_deadlines['deadline'].apply(
                _human_date_delta
            )
            # Convert to str
            current_deadlines['deadline'] = current_deadlines['deadline'].astype(
                str)

            current_deadlines = (
                current_deadlines.loc[:, [
                    'deadline_str', 'unique_id', 'time_left']]
                .rename(columns={'deadline_str': 'deadline'})
                .copy()
            )

            # starting values
            tbl = current_deadlines.values.tolist()
            return tbl, current_deadlines

        def gen_layout(deadline_values, application_values, selected_deadline=None,
                       date=None, maybe=True, expired=True, applied=False):

            columns = ['Deadline', 'Applications', 'Time left']
            color1 = sg.theme_input_background_color()
            row_colors = None
            if selected_deadline is not None:
                row_colors = [(selected_deadline, color1)]

            dates_list_columns = [
                [sg.Text("Upcoming deadlines:", font='Helvetica 12 underline')],
                [sg.Table(values=deadline_values, enable_events=True,
                          headings=columns, key='-DATE LIST-',
                          auto_size_columns=True, expand_x=True,
                          def_col_width=50,
                          num_rows=20,
                          expand_y=True, row_colors=row_colors)],
                [sg.CB("show maybes", key='-MAYBE-', enable_events=True,
                       default=maybe),
                 sg.CB("show past", key="-EXPIRED-", default=expired,
                       enable_events=True),
                 sg.CB("show applied", key="-APPLIED-", enable_events=True,
                       default=applied)]
            ]
            applications_text = "Applications:"
            if date is not None:
                applications_text = f"Applications due {date}"
            results_columns = [
                [sg.Text(applications_text, font="Helvetica 12 underline")],
                [sg.Table(values=application_values, enable_events=True,
                          headings=['Institution', 'Title', 'Status'],
                          auto_size_columns=True,
                          def_col_width=80,
                          num_rows=20,
                          expand_y=True, key='-APPLICATIONS-',
                          expand_x=True)],
                [sg.Button("Clear", key="-CLEAR-"),
                 sg.Button("Show All", key="-ALL-")]
            ]
            header = [[sg.Text("Select date from left, click on item on the right"
                               " to edit")]]
            footer = [[sg.Button("Close", key='-EXIT-'),
                       sg.Button("Export to excel", key='-EXPORT-')]]

            layout = [[header], [sg.HSeparator()], [
                sg.Column(dates_list_columns),
                sg.VSeparator(),
                sg.Column(results_columns),
            ], [sg.HSeparator()], [footer]]
            return layout

        size = (None, None)
        postings = filter_postings(all_postings)
        if postings.shape[0] == 0:
            sg.popup_error("You have not marked any posting as interested or maybe"
                           " so the deadline list is empty.")
            return
        tbl, current_deadlines = deadlines_from_postings(postings)
        posting_values = [['', '', '']]
        selected_postings = None
        selected_row = None
        selected_date = None
        layout = gen_layout(tbl, posting_values, selected_row, selected_date)
        window = sg.Window("Deadlines", layout, location=window_location,
                           size=size, resizable=True)
        layout_kwargs = {
            'maybe': True,
            'expired': True,
            'applied': False
        }
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == '-EXIT-':
                window.close()
                break
            elif event == '-EXPORT-':
                url = os.path.join(self._output_dir, 'deadlines.xlsx')
                postings.to_excel(url, index=False)
                sg.popup("All currently filtered deadlines have been exported\n"
                         "to your output folder in the file deadlines.xlsx",
                         location=window_location)
                continue
            elif event == "-DATE LIST-":
                row = values['-DATE LIST-']
                if not isinstance(row, int):
                    row = row[0]
                # Get the associated date and posting
                date = current_deadlines['deadline'].values[row]
                if date == 'Unknown':
                    sel = postings['deadline'].isna()
                else:
                    sel = pd.to_datetime(postings['deadline']) == date
                selected_postings = postings.loc[sel, :]
                if selected_postings.shape[0] == 0:
                    posting_values = [['', '', '']]
                else:
                    posting_values = (
                        selected_postings.loc[:, posting_cols]
                        .values.tolist()
                    )
                selected_row = row
                selected_date = date
                new_layout = gen_layout(tbl, posting_values, row, date,
                                        **layout_kwargs)
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location,
                                   size=size, resizable=True)
            elif event == "-CLEAR-":
                posting_values = [['', '', '']]
                selected_date = None
                selected_row = None
                selected_postings = None
                new_layout = gen_layout(tbl, posting_values, **layout_kwargs)
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location,
                                   size=size, resizable=True)
            elif event == "-ALL-":
                posting_values = (
                    postings.loc[:, posting_cols].values.tolist()
                )
                selected_postings = postings
                selected_row = None
                selected_date = "any date"
                new_layout = gen_layout(tbl, posting_values, selected_row,
                                        selected_date,
                                        **layout_kwargs)
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location,
                                   size=size, resizable=True)
            elif event in ['-MAYBE-', '-EXPIRED-', '-APPLIED-']:
                layout_kwargs['maybe'] = values['-MAYBE-']
                layout_kwargs['expired'] = values['-EXPIRED-']
                layout_kwargs['applied'] = values['-APPLIED-']
                postings = filter_postings(all_postings, **layout_kwargs)
                tbl, current_deadlines = deadlines_from_postings(postings)
                new_layout = gen_layout(
                    tbl, posting_values, selected_row, selected_date,
                    **layout_kwargs
                )
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location,
                                   size=size, resizable=True)
            elif event == "-APPLICATIONS-":
                if selected_postings is None:
                    sg.popup_error("Got a request to show a posting but the posting"
                                   " list appears to be empty!")
                    continue
                row = values['-APPLICATIONS-']
                if not isinstance(row, int):
                    row = row[0]
                posting_row = selected_postings.iloc[row, :]
                changes = self.view_detailed_posting(
                    posting_row, window_location)
                # reload and recreate in case we modified something
                if changes:
                    all_postings = pd.read_pickle(self._postings_url)
                    postings = filter_postings(all_postings, **layout_kwargs)
                    tbl, current_deadlines = deadlines_from_postings(postings)
                    date = selected_date
                    if date == 'Unknown':
                        sel = postings['deadline'].isna()
                    else:
                        sel = pd.to_datetime(postings['deadline']) == date
                    selected_postings = postings.loc[sel, :]
                    if selected_postings.shape[0] == 0:
                        posting_values = [['', '', '']]
                    else:
                        posting_values = (
                            selected_postings.loc[:, posting_cols]
                            .values.tolist()
                        )
                    new_layout = gen_layout(
                        tbl, posting_values, selected_row, selected_date,
                        **layout_kwargs
                    )
                    window.close()
                    window = sg.Window("Deadlines", new_layout,
                                       location=window_location,
                                       size=size, resizable=True)

            else:
                logging.info(f"Got unknown event {event} with values {values}")

        return

    def view_detailed_posting(self, row, window_location=(None, None)):
        """Review and edit a post as shown in the deadline menu

        Parameters
        ----------
        row : Series
             a row from the postings dataframe to review

        Returns
        -------
        Status:
            indicates whether any edit was done to the postings
        """
        status_change = False
        font = 'Helvetica 12'

        row = row.copy()
        # unpack
        section = row['section']
        institution = row['institution']
        division = row['division']
        department = row['department']
        keywords = row['keywords']
        title = row['title']
        text = row['full_text']
        location = row['location']
        deadline = row['deadline']
        origin = row['origin']
        url = row['url']
        status = row['status']
        notes = row['notes']
        alt_status = 'maybe'
        alt_status_txt = alt_status
        if status == 'maybe':
            alt_status = 'interested'
            alt_status_txt = alt_status
        elif status == 'applied':
            alt_status_txt = 'not applied'
            alt_status = 'interested'

        update_list = ['title', 'institution', 'division', 'section',
                       'department', 'deadline', 'location']

        custom_cols = [[sg.Text("Custom columns:")]]
        for col in self._personal_settings['custom_posting_cols']:
            crow = [sg.Text(f"{col}:"), sg.InputText(row[col], key=col)]
            custom_cols.append(crow)
            update_list.append(col)
        if len(self._personal_settings['custom_posting_cols']) == 0:
            custom_cols.append([sg.Text("you can add columns in the "
                                        "configuration menu")])

        alt_status = 'maybe' if status == 'interested' else 'interested'
        footer = [
            sg.Button("Close", key='-CLOSE-'),
            sg.Button(f"Mark as {alt_status_txt}", key="-SWITCH-"),
            sg.Button("Mark as Applied", key='-APPLIED-'),
            sg.Button("Remove from deadlines", key='-IGNORE-'),
            sg.Button("Update posting", key='-UPDATE-'),
            sg.Button("Edit/View Notes", key='-NOTES-'),
            sg.Button("Create application folder", key="-FOLDER-")
        ]
        layout = [
            [sg.Text('Title:', font=font + ' underline'),
             sg.InputText(default_text=f'{title}', font=font, key='title'),
             sg.Text('Institution:', font=font + ' underline'),
             sg.InputText(default_text=f'{institution}', font=font,
                          key='institution')],
            [sg.InputText(f"{department}", key="department"),
             sg.Text(" | "),
             sg.InputText(f"{division}", key="division"),
             sg.Text(" | "),
             sg.InputText(f"{section}", key="section")],
            [sg.HSeparator()],
            [sg.Text(f"Current status: {status}")],
            [sg.Text('Location'), sg.InputText(f"{location}", key='location')],
            [sg.Text('Deadline:'),
             sg.Input(deadline, key='deadline', size=(20, 1)),
             sg.CalendarButton('select deadline', close_when_date_chosen=True,
                               target='deadline', location=window_location,
                               no_titlebar=False)],
            [sg.Text(f'keywords: {keywords}')],
            [sg.Text(f'Source: {origin}'), sg.Button('See posting', key='-VISIT-'),
             sg.Button("See full text", key='-FULL-')],
            [sg.HSeparator()]
        ] + custom_cols + [
            [sg.HSeparator()],
            footer
        ]

        # size = (600, 400)
        modified_cols = []
        window = sg.Window('New posting', layout, location=window_location)
        while True:
            event, values = window.read()
            # update the window location
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event in ["-CLOSE-"]:
                window.close()
                break
            elif event == '-VISIT-':
                webbrowser.open(url)
            elif event == "-APPLIED-":
                window.close()
                status_change = True
                row['status'] = 'applied'
                break
            elif event == '-SWITCH-':
                window.close()
                status_change = True
                row['status'] = alt_status
                break
            elif event == '-IGNORE-':
                status_change = True
                res = sg.popup_ok_cancel(
                    "Are you sure you wish to ignore this posting?",
                    location=window_location
                )
                if res == 'OK' or res is None:
                    window.close()
                    row['status'] = 'ignore'
                    break
            elif event == '-UPDATE-':
                for col in update_list:
                    if col == 'deadline':
                        new_deadline = values['deadline']
                        if new_deadline != deadline:
                            modified_cols.append('deadline')
                            new_deadline = (
                                pd.to_datetime(new_deadline)
                                .to_pydatetime().date().__str__()
                            )
                            # Note: this is a patch for those already using the system
                            if 'original_deadline' not in row.index:
                                row['original_deadline'] = deadline
                            row['deadline'] = new_deadline
                            status_change = True
                    else:
                        new_val = values[col].strip()
                        if new_val != row[col]:
                            modified_cols.append(col)
                            row[col] = new_val
                            status_change = True

                window.close()
                break
            elif event == "-FULL-":
                self.large_text_popup(text, location=window_location)
            elif event == "-NOTES-":
                changed, notes = self.modify_notes(
                    notes, location=window_location)
                if changed:
                    row['notes'] = notes
                    status_change = True
                    modified_cols.append('notes')
            elif event == "-FOLDER-":
                base = self._personal_settings['scaffolding_base']
                out_dir = self._personal_settings['scaffolding_output_dir']
                if base is None or out_dir is None:
                    sg.popup_error("To crate a folder you must first configure"
                                   " the scaffolding paths in the configuration menu")
                    continue
                
                name = sg.popup_get_text("Select a name for the application folder",
                                         title="Application scaffolding",
                                         location=window_location)
                url = os.path.join(out_dir, name)
                if os.path.isdir(url):
                    sg.popup_error(f"The folder path {url}\n"
                                   "is already in use")
                    continue
                copy_tree(base, url)
                sg.popup(f"Application folder created successfuly at {url}")
                continue
            else:
                logging.warning(f"Got unkown event {event}")

        if status_change:
            # Update
            postings = pd.read_pickle(self._postings_url)
            sel = (postings['origin'] == row['origin']) & \
                (postings['origin_id'] == row['origin_id'])
            if not sel.any():
                logging.warning(
                    f"Failed to find a match for row {row} in postings")
                os.popup_error("Failed to match update row to postings. Is the "
                               " postings file corrupt?")
                status_change = False
                return status_change
            if sel.sum() > 1:
                logging.warning("Single row selected multiple lines in postings.\n"
                                "this suggests a corrupted postings file.\n"
                                f"requested: {row}\n got \n {postings.loc[sel, :]}")
                os.popup_error("Failed to match update row to postings. Is the "
                               " postings file corrupt?")
                status_change = False
                return status_change

            ix = postings.loc[sel, :].index.values[0]
            row = row.to_frame().T
            row.index = [ix]
            # Test one more time to be sure
            test = (postings.loc[sel, 'origin'] == row['origin']) & \
                (postings.loc[sel, 'origin_id'] == row['origin_id'])
            if not test.all():
                logging.warning("Failed to match the row with the data. "
                                " This suggests a corrupted postings file."
                                f"requested: {row}\n got \n {postings.loc[sel, :]}")
                os.popup_error("Failed to match update row to postings. Is the "
                               " postings file corrupt?")
                status_change = False
                return status_change

            modified_cols = list(set(modified_cols))
            row = row.loc[:, ['status'] + modified_cols]
            logging.info(f"Modifying row to \n{row}")
            postings.update(row)
            postings.to_pickle(self._postings_url)

        return status_change

    def large_text_popup(self, text, title="full text", size=(800, 800),
                         location=(None, None)):

        layout = [[sg.Text(text, size=(100, None))]]
        popup = sg.Window(title, location=location).Layout([[
            sg.Column(layout, size=size, scrollable=True)
        ]])
        popup.read()

        return

    def review_updates(self, window_location=(None, None)):
        """Display a screen for reviewing updates

        Returns
        -------
        TODO

        """
        if not os.path.isfile(self._pending_updates_url):
            sg.popup("There are no pending updates")
            return

        updates = pd.read_pickle(self._pending_updates_url)

        if updates.shape[0] == 0:
            sg.popup("There are no pending updates")
            return

        # Get the updates in presentable form
        updates.reset_index(inplace=True, drop=True)

        def get_update_list(updates):
            update_list = []
            for ix, row in updates.iterrows():
                update_notes = row['update_notes'].split(',')
                update_notes = set([x.replace('new', '').strip() for x in
                                    update_notes])
                update_notes = [x for x in update_notes if len(x) > 0]

                update_notes = ", ".join(update_notes)
                update_list.append([
                    row['origin'], row['title'], row['institution'], update_notes
                ])
            return update_list

        update_list = get_update_list(updates)

        columns = ['Origin', 'Title', 'Institution', 'Updated values']

        table_layout = [[
            sg.Table(values=update_list, enable_events=True, headings=columns,
                     key='-UPDATE_LIST-', auto_size_columns=True,
                     expand_y=True)
        ]]

        layout = [
            [sg.Text("Updates pending review:", font='Helvetica 12 underline')],
            [sg.Text("(click on row to edit)")],
            [sg.Column(table_layout)],
            [sg.HSeparator()],
            [sg.Button("Clear all", key="-CLEAR-"),
             sg.Button("Close", key="-EXIT-")]
        ]

        window = sg.Window("Updates", layout, location=window_location,
                           resizable=True)

        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == '-EXIT-':
                window.close()
                break
            elif event == "-CLEAR-":
                res = sg.popup_ok_cancel(
                    "Do you want to clear all updates?\n"
                    "This will keep all data at its current value"
                )
                if res == 'OK':
                    os.remove(self._pending_updates_url)
                    window.close()
                    break
            elif event == "-UPDATE_LIST-":
                row = values['-UPDATE_LIST-']
                if row is None or row == []:
                    logging.debug(
                        f"Got empty event {event} with values {values}")
                    continue
                if not isinstance(row, int):
                    row = row[0]

                update_row = updates.iloc[row, :].copy()
                changes = self.manage_update_request(
                    update_row, window_location)
                if changes:
                    # Reload
                    updates = pd.read_pickle(self._pending_updates_url)
                    if updates.shape[0] == 0:
                        sg.popup("Finished reviewing all updates!")
                        window.close()
                        break

                    updates.reset_index(inplace=True, drop=True)
                    update_list = get_update_list(updates)
                    window['-UPDATE_LIST-'].update(values=update_list)
            else:
                logging.warning(f"Got unkown event {event}")

        return

    def manage_update_request(self, row, window_location=(None, None)):
        """Review and edit an update row as shown in the update menu"""

        status_change = False
        font = 'Helvetica 12'

        row = row.copy()
        # Mini
        title = row['title']

        section = row['section']
        institution = row['institution']
        division = row['division']
        department = row['department']
        keywords = row['keywords']
        text = row['full_text']
        location = row['location']
        deadline = row['deadline']
        origin = row['origin']
        url = row['url']
        status = row['status']

        header = [
            [sg.Text('-------- Original Posting -------',
                     font=font + ' underline')],
            [sg.HSeparator()],
            [sg.Text('Title:', font=font + ' underline'),
             sg.Text(f'{title}', font=font),
             sg.Text('Institution:', font=font + ' underline'),
             sg.Text(f'{institution}', font=font)],
            [sg.Text(f"{department} | {division} | {section} ")],
            [sg.HSeparator()],
            [sg.Text(f"Current status: {status}")],
            [sg.Text(f'Location: {location}')],
            [sg.Text(f'Deadline: {deadline}')],
            [sg.Text(f'keywords: {keywords}')],
            [sg.Text(f'Source: {origin}'), sg.Button('See posting', key='-VISIT-'),
             sg.Button("See full text", key='-FULL-')],
            [sg.HSeparator()],
            [sg.Text('------ Updates -----', font=font + ' underline')],
        ]

        footer = [
            [sg.HSeparator()],
            [
                sg.Button("Close", key='-CLOSE-'),
                sg.Button("Accept all", key="-ALL-"),
                sg.Button("Reject all", key='-NONE-')
            ]
        ]

        def get_update_layout_from_row(row):
            update_notes = row['update_notes'].split(',')
            update_notes = set([x.replace('new', '').strip() for x in
                                update_notes])
            update_notes = [x for x in update_notes if len(x) > 0]
            update_layout = []
            for col in update_notes:
                list_element = [
                    sg.Text(f"New {col}: {row[col + '_new']}"),
                    sg.Button("Accept", key=f"-ACCEPT-{col}-"),
                ]
                update_layout.append(list_element)
            return update_layout, update_notes

        def update_files(row, update_cols=None):
            # Get the update file
            updates = pd.read_pickle(self._pending_updates_url)
            sel = (
                (updates['origin'] == row['origin'].values[0]) &
                (updates['origin_id'] == row['origin_id'].values[0])
            )
            to_update = updates.loc[sel, :].copy()
            updates = updates.loc[~sel, :].copy()
            if update_cols is None:
                updates.to_pickle(self._pending_updates_url)
                # In this case we have rejected all updates we're done
                return None

            # Check if we have any leftover updates
            update_notes = to_update['update_notes'].values[0].split(',')
            update_notes = set([x.replace('new', '').strip() for x in
                                update_notes])
            update_notes = [x for x in update_notes if len(x) > 0]

            leftovers = set(update_notes) - set(update_cols)
            new_row = None
            if len(leftovers) == 0:
                # nothing is left so we can erase the row
                updates.to_pickle(self._pending_updates_url)
            else:
                # update the list to update
                lbl = ", ".join(update_notes)
                to_update['update_notes'] = lbl
                updates = updates.append(to_update, ignore_index=True)
                updates.to_pickle(self._pending_updates_url)
                new_row = to_update

            # Now actually update the data
            data = pd.read_pickle(self._postings_url)
            sel = (
                (data['origin'] == row['origin'].values[0]) &
                (data['origin_id'] == row['origin_id'].values[0])
            )
            for col in update_cols:
                data.loc[sel, col] = row[col].values[0]
            data.to_pickle(self._postings_url)
            return new_row

        update_layout, update_cols = get_update_layout_from_row(row)
        layout = header + update_layout + footer

        window = sg.Window('Update Review', layout, location=window_location,
                           resizable=True)
        while True:
            event, values = window.read()
            # update the window location
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event in ["-CLOSE-"]:
                window.close()
                return False
            elif event == '-VISIT-':
                webbrowser.open(url)
            elif event == "-ALL-":
                keep = ['origin', 'origin_id']
                for col in update_cols:
                    keep.append(col + '_new')
                renames = {col + '_new': col for col in update_cols}
                row = row.loc[keep].to_frame().T.rename(columns=renames).copy()
                update_files(row, update_cols)
                window.close()
                return True
            elif event == '-NONE-':
                keep = ['origin', 'origin_id']
                row = row.loc[keep].to_frame().T.copy()
                update_files(row)
                window.close()
                return True
            elif event == '-VISIT-':
                webbrowser.open(url)
            elif event == "-FULL-":
                self.large_text_popup(text, location=window_location)
            elif '-ACCEPT-' in event:
                to_update = event.split('-')[2]
                keep = ['origin', 'origin_id', to_update]
                row = row.loc[keep].to_frame().T.copy()
                new_row = update_files(row)
                window.close()
                if new_row is None:
                    return True
                else:
                    return self.manage_update_request(new_row, window_location)
            else:
                logging.warning(f"Got unkown event {event}")

        return status_change

    def manual_entry(self, window_location=(None, None)):
        """Manual entry menu for a new postings

        Parameters
        ----------
        window_location : tuple
            window location in pixels

        Returns
        -------
        None
        """
        if not os.path.isfile(self._postings_url):
            all_postings = None
            next_id = 0
        else:
            all_postings = pd.read_pickle(self._postings_url)
            sel = all_postings['origin'] == 'manual entry'
            if not sel.any():
                next_id = 0
            else:
                next_id = all_postings.loc[sel, 'origin_id'].max() + 1

        layout = [
            [sg.Text("Enter the following job posting details")],
            [sg.Text("Title:"), sg.InputText(key='title')],
            [sg.Text("Institution:"), sg.InputText(key='institution')],
            [sg.Text("Deadline"),
             sg.Input(key="deadline"),
             sg.CalendarButton("select deadline", close_when_date_chosen=True,
                               target='deadline', location=window_location,
                               no_titlebar=False)],
            [sg.Text("Department:"), sg.InputText(key='department')],
            [sg.Text("Division:"), sg.InputText(key="division")],
            [sg.Text("Section:"), sg.InputText(key="section")],
            [sg.Text("Keywords:"), sg.InputText(key="keywords")],
            [sg.Text("Location:"), sg.InputText(key="location")],
            [sg.Text("Posting URL:"), sg.InputText(key="url")],
            [sg.Button("Save and close", key="-SAVE-"),
             sg.Button("Exit without saving", key="-EXIT-")]
        ]

        default_row = {
            'origin': 'manual entry',
            'origin_id': next_id,
            'title': 'no title',
            'institution': 'unknown',
            'deadline': np.nan,
            'status': 'interested',
            'department': 'unknown',
            'division': '',
            'section': '',
            'keywords': '',
            'url': '',
            'reviewed': True,
            'full_text': '',
            'updated': False,
        }
        window = sg.Window('Manual entry', layout, location=window_location)
        while True:
            event, values = window.read()
            # update the window location
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event in ["-EXIT-"]:
                res = sg.popup_ok_cancel("Are you sure you want to exit "
                                         "without saving?",
                                         location=window_location)
                if res == 'OK' or res is None:
                    window.close()
                    break
                else:
                    continue
            elif event == '-SAVE-':
                window.close()
                default_row.update(values)
                row = pd.Series(default_row).to_frame().T
                row['deadline'] = pd.to_datetime(
                    row['deadline'], errors='coerce')
                sel = row['deadline'].notna()
                if sel.all():
                    row['deadline'] = row['deadline'].dt.date.astype(str)
                logging.info(f"Adding new postings:\n{row}")
                if all_postings is None and not os.path.isfile(self._postings_url):
                    row.to_pickle(self._postings_url)
                else:
                    all_postings = pd.read_pickle(self._postings_url)
                    all_postings = all_postings.append(row, ignore_index=True)
                    all_postings.to_pickle(self._postings_url)
                break

        return

    def review_ignored_gui(self, window_location=(None, None)):
        """Review postings marked as ignored and change their status

        Parameters
        ----------
        window_location : tuple, optional
            location in which to draw the window

        Returns
        -------
        TODO
        """
        # Prepare data
        if not os.path.isfile(self._postings_url):
            sg.popup_error("The postings files was not found. You must first "
                           "update your postings before viewing ignored.",
                           location=window_location)
            return

        all_postings = pd.read_pickle(self._postings_url)

        def filter_postings(all_postings, expired=True, sort_by='deadline'):
            status = ['ignore']
            postings = (
                all_postings.loc[all_postings['status'].isin(status), :]
                .copy()
            )
            if not expired:
                sel = (
                    pd.to_datetime(postings['deadline']
                                   ) >= pd.Timestamp("today")
                ) | (
                    postings['deadline'].isna()
                )
                postings = postings.loc[sel, :].copy()
            postings.sort_values(by=[sort_by], inplace=True)
            return postings

        def table_from_postings(postings):
            # Ensure we have the right columns

            postings = postings.copy()
            sel = postings['deadline'].notna()
            postings.loc[sel, 'deadline'] =\
                pd.to_datetime(postings.loc[sel, 'deadline'])
            postings['deadline'].fillna('Unknown', inplace=True)
            # Get the number of applications per deadline
            today = settings['today']

            def _human_date_delta(x, today=today):
                if x == 'Unknown':
                    return "Unknown deadline"
                x = pd.to_datetime(x).to_pydatetime().date()
                return humanize.naturaltime(today - x).replace("from now", "").strip()

            postings['time_left'] = postings['deadline'].apply(
                _human_date_delta
            )
            columns = [
                'origin',
                'institution',
                'title',
                'department',
                'location',
                'time_left'
            ]
            for col in columns:
                postings[col].fillna('', inplace=True)
                postings[col] = postings[col].astype(str)

            # starting values
            tbl = postings.loc[:, columns].values.tolist()
            return tbl

        def gen_layout(table, expired=True, sort_by='deadline'):

            columns = ['Source', 'Institution',
                       'Title', 'Department', 'Location', 'Deadline']
            row_colors = None
            num_rows = len(table)

            dates_list_columns = [
                [sg.Table(values=table, enable_events=True,
                          headings=columns, key='-IGNORED LIST-',
                          auto_size_columns=True, expand_x=True,
                          col_widths=[10, 50, 50, 50, 10],
                          num_rows=20,
                          expand_y=True, row_colors=row_colors)],
                [sg.CB("show past", key="-EXPIRED-", default=expired,
                       enable_events=True),
                 sg.Text("Sort by:"),
                 sg.Combo(['deadline', 'source', 'institution',
                           'department', 'deadline', 'title',
                           'location'], default_value=sort_by,
                          key='-ORDER-', enable_events=True)]
            ]
            header = [[sg.Text(f"{num_rows:d} ignored postings, click on an item to review"
                               " and modify status")]]
            footer = [[sg.Button("Close", key='-EXIT-')]]

            layout = [[header], [sg.HSeparator()],
                      [sg.Column(dates_list_columns, key='-COL-')],
                      [sg.HSeparator()], [footer]]
            return layout

        def gen_window(layout, size, location):
            window = sg.Window('Ignored Postings', size=size, location=location,
                               auto_size_text=True, auto_size_buttons=True,
                               grab_anywhere=False, resizable=True,
                               layout=layout, finalize=True)
            window['-COL-'].expand(True, True)
            window['-IGNORED LIST-'].expand(True, True)
            window['-IGNORED LIST-'].table_frame.pack(expand=True, fill='both')
            return window

        sort_by = 'deadline'
        size = (None, None)
        postings = filter_postings(all_postings, sort_by)
        if postings.shape[0] == 0:
            sg.popup_error("You have not marked any posting as ignored"
                           " so the list is empty.")
            return
        table = table_from_postings(postings)
        layout = gen_layout(table, sort_by=sort_by)
        window = gen_window(layout, size, window_location)
        layout_kwargs = {
            'expired': True,
            'sort_by': sort_by
        }
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            size = window.size

            if event == sg.WIN_CLOSED or event == '-EXIT-':
                window.close()
                break
            elif event == "-IGNORED LIST-":
                row = values['-IGNORED LIST-']
                if not isinstance(row, int):
                    row = row[0]
                selected_postings = postings.iloc[[row], :].copy()
                if selected_postings.shape[0] == 0:
                    continue

                self.review_new_postings(window_location, selected_postings,
                                         'Ignored posting edit', allow_delete=True)

                all_postings = pd.read_pickle(self._postings_url)
                postings = filter_postings(all_postings, **layout_kwargs)
                table = table_from_postings(postings)
                new_layout = gen_layout(table, **layout_kwargs)
                window.close()
                window = gen_window(new_layout, size, window_location)
            elif event in ['-EXPIRED-', '-ORDER-']:
                if event == '-EXPIRED-':
                    layout_kwargs['expired'] = values['-EXPIRED-']
                else:
                    layout_kwargs['sort_by'] = values['-ORDER-']
                postings = filter_postings(all_postings, **layout_kwargs)
                table = table_from_postings(postings)
                new_layout = gen_layout(table, **layout_kwargs)
                window.close()
                window = gen_window(new_layout, size, window_location)
            else:
                logging.info(f"Got unknown event {event} with values {values}")
        return

    def review_interested_gui(self, window_location=(None, None)):
        """Review postings marked as interested and change their status

        Parameters
        ----------
        window_location : tuple, optional
            location in which to draw the window

        Returns
        -------
        TODO
        """
        # Prepare data
        if not os.path.isfile(self._postings_url):
            sg.popup_error("The postings files was not found. You must first "
                           "update your postings before viewing interested postings.",
                           location=window_location)
            return

        all_postings = pd.read_pickle(self._postings_url)
        order_cols = ['status', 'institution', 'title',
                      'department', 'location', 'deadline'] + \
            self._personal_settings['custom_posting_cols']
        posting_cols = ['status', 'institution', 'title',
                        'department', 'location', 'time_left'] + \
            self._personal_settings['custom_posting_cols']

        def filter_postings(postings, maybe=False, applied=False,
                            expired=False, sort_by='deadline'):
            status = ['interested']
            if maybe:
                status.append('maybe')
            if applied:
                status.append('applied')
            postings = (
                all_postings.loc[all_postings['status'].isin(status), :]
                .copy()
            )
            if not expired:
                sel = (
                    pd.to_datetime(postings['deadline']
                                   ) >= pd.Timestamp("today")
                ) | (
                    postings['deadline'].isna()
                )
                postings = postings.loc[sel, :].copy()
            postings.sort_values(by=sort_by, inplace=True)
            logging.info(f"Filtered to {postings.shape[0]:d} posting rows")
            return postings

        def table_from_postings(postings, posting_cols=posting_cols):
            # Ensure we have the right columns

            postings = postings.copy()
            sel = postings['deadline'].notna()
            postings.loc[sel, 'deadline'] =\
                pd.to_datetime(postings.loc[sel, 'deadline'])
            postings['deadline'].fillna('Unknown', inplace=True)
            # Get the number of applications per deadline
            today = settings['today']

            def _human_date_delta(x, today=today):
                if x == 'Unknown':
                    return "Unknown deadline"
                x = pd.to_datetime(x).to_pydatetime().date()
                return humanize.naturaltime(today - x).replace("from now", "").strip()

            postings['time_left'] = postings['deadline'].apply(
                _human_date_delta
            )
            columns = posting_cols
            for col in columns:
                postings[col].fillna('', inplace=True)
                postings[col] = postings[col].astype(str)

            # starting values
            tbl = postings.loc[:, columns].values.tolist()
            return tbl

        def gen_layout(table, maybe=False, expired=False, applied=False,
                       sort_by='deadline', order_cols=order_cols):

            columns = [x.capitalize() for x in order_cols]
            row_colors = None

            num_rows = len(table)
            dates_list_columns = [
                [sg.Table(values=table, enable_events=True,
                          headings=columns, key='-POSTING LIST-',
                          auto_size_columns=True, expand_x=True,
                          col_widths=[10, 50, 50, 50, 10],
                          num_rows=20,
                          expand_y=True, row_colors=row_colors)],
                [sg.CB("show past", key="-EXPIRED-", default=expired,
                       enable_events=True),
                 sg.CB("show maybes", key="-MAYBE-", default=maybe,
                       enable_events=True),
                 sg.CB("show applied", key="-APPLIED-", default=applied,
                       enable_events=True),
                 sg.Text("Sort by:"),
                 sg.Combo(order_cols, default_value=sort_by,
                          key='-ORDER-', enable_events=True)]
            ]
            header = [[sg.Text(f"{num_rows:d} postings marked as interested, "
                               "click on an item to review"
                               " and modify status")]]
            footer = [[sg.Button("Close", key='-EXIT-'),
                       sg.Button("Export to excel", key='-EXPORT-')]]

            layout = [[header], [sg.HSeparator()],
                      [sg.Column(dates_list_columns, key='-COL-')],
                      [sg.HSeparator()], [footer]]
            return layout

        def gen_window(layout, size, location):
            window = sg.Window('Applications', size=size, location=location,
                               auto_size_text=True, auto_size_buttons=True,
                               grab_anywhere=False, resizable=True,
                               layout=layout, finalize=True)
            window['-COL-'].expand(True, True)
            window['-POSTING LIST-'].expand(True, True)
            window['-POSTING LIST-'].table_frame.pack(expand=True, fill='both')
            return window

        sort_by = 'deadline'
        size = (None, None)
        postings = filter_postings(all_postings, sort_by=sort_by)
        if postings.shape[0] == 0:
            sg.popup_error("You have not marked any posting as interested"
                           " so the list is empty.")
            return
        table = table_from_postings(postings)
        layout = gen_layout(table, sort_by=sort_by)
        window = gen_window(layout, size, window_location)
        layout_kwargs = {
            'expired': False,
            'sort_by': sort_by,
            'maybe': False,
            'applied': False
        }
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            size = window.size

            if event == sg.WIN_CLOSED or event == '-EXIT-':
                window.close()
                break
            elif event == '-EXPORT-':
                url = os.path.join(self._output_dir, 'deadlines.xlsx')
                postings.to_excel(url, index=False)
                sg.popup("All currently filtered deadlines have been exported\n"
                         "to your output folder in the file deadlines.xlsx",
                         location=window_location)
                continue
            elif event == "-POSTING LIST-":
                row = values['-POSTING LIST-']
                if not isinstance(row, int):
                    row = row[0]
                selected_postings = postings.iloc[row, :].copy()
                if selected_postings.shape[0] == 0:
                    continue

                changes = self.view_detailed_posting(
                    selected_postings, window_location
                )

                if changes:
                    order_cols = ['status', 'institution', 'title',
                                  'department', 'location', 'deadline'] + \
                        self._personal_settings['custom_posting_cols']
                    posting_cols = ['status', 'institution', 'title',
                                    'department', 'location', 'time_left'] + \
                        self._personal_settings['custom_posting_cols']
                    all_postings = pd.read_pickle(self._postings_url)
                    postings = filter_postings(all_postings, **layout_kwargs)
                    table = table_from_postings(postings, posting_cols)
                    new_layout = gen_layout(table, order_cols=order_cols,
                                            **layout_kwargs)
                    window.close()
                    window = gen_window(new_layout, size, window_location)
            elif event in ['-EXPIRED-', '-ORDER-', '-MAYBE-', '-APPLIED-']:
                layout_kwargs['maybe'] = values['-MAYBE-']
                layout_kwargs['expired'] = values['-EXPIRED-']
                layout_kwargs['applied'] = values['-APPLIED-']
                layout_kwargs['sort_by'] = values['-ORDER-']
                postings = filter_postings(all_postings, **layout_kwargs)
                table = table_from_postings(postings, posting_cols)
                new_layout = gen_layout(table, order_cols=order_cols,
                                        **layout_kwargs)
                window.close()
                window = gen_window(new_layout, size, window_location)
            else:
                logging.info(f"Got unknown event {event} with values {values}")
        return

    def review_applications_gui(self, window_location=(None, None)):
        """Review ongoing applications and mark answers received

        Parameters
        ----------
        window_location : tuple, optional
            location in which to draw the window

        Returns
        -------
        None

        """
        # Prepare data
        if not os.path.isfile(self._postings_url):
            sg.popup_error("The postings files was not found. You must first "
                           "update your postings before viewing applications",
                           location=window_location)
            return

        all_postings = pd.read_pickle(self._postings_url)
        # verify we have the new "letters_recieved" columns
        if 'letters_recieved' not in all_postings.columns:
            all_postings['letters_recieved'] = ''
            all_postings['letters_status'] = ''
            all_postings.to_pickle(self._postings_url)

        # filter applied
        sel = all_postings['status'] == 'applied'
        if not sel.any():
            sg.popup_error(
                "There aren't any postings marked as applied. To manage "
                " applications first mark any posting as applied in the "
                " deadline menu.",
                location=window_location
            )
            return

        order_cols = ['application_status', 'institution', 'title',
                      'department', 'location', 'letters_status']
        posting_cols = ['application_status', 'institution', 'title',
                        'department', 'location', 'letters_status']

        resolved_statuses = ['no interview', 'no flyout', 'no offer',
                             'offer accepted', 'offer rejected']
        # unresolved_statuses = ['got interview', 'got flyout',
        #                        'got offer']

        # Add the new columns if they don't exist
        if 'application_status' not in all_postings.columns:
            all_postings['application_status'] = ''
            all_postings.loc[sel, 'application_status'] = 'awaiting response'
            # overwrite if its a new column
            all_postings.to_pickle(self._postings_url)
        else:
            # Check if any application became applied and has no status
            sel2 = sel & (
                (all_postings['application_status'] == '') |
                (all_postings['application_status'].isna())
            )
            all_postings.loc[sel2, 'application_status'] = 'awaiting response'
            # and the same for the letter status
            sel2 = sel & (
                (all_postings['letters_recieved'] == '') |
                (all_postings['letters_recieved'].isna())
            )
            writers = self._personal_settings['letters']
            num_let = len(writers)
            all_postings.loc[sel2, 'letters_status'] = f'0/{num_let:d}'
            all_postings.loc[sel2, 'letters_recieved'] = ''

            all_postings.to_pickle(self._postings_url)

        def filter_postings(all_postings, resolved=True, sort_by='institution'):
            sel = all_postings['status'] == 'applied'
            postings = all_postings.loc[sel, :].copy()
            if not resolved:
                sel = postings['application_status'].isin(resolved_statuses)
                postings = postings.loc[~sel, :].copy()
            postings.sort_values(by=sort_by, inplace=True)
            return postings

        def table_from_postings(postings, posting_cols=posting_cols):
            # Ensure we have the right columns

            postings = postings.copy()

            columns = posting_cols
            for col in columns:
                postings[col].fillna('', inplace=True)
                postings[col] = postings[col].astype(str)

            # starting values
            tbl = postings.loc[:, columns].values.tolist()
            return tbl

        def gen_layout(table, resolved=True,
                       sort_by='institution', order_cols=order_cols):

            columns = [x.replace('_', ' ').capitalize() for x in order_cols]
            row_colors = None
            num_rows = len(table)

            dates_list_columns = [
                [sg.Table(values=table, enable_events=True,
                          headings=columns, key='-APPLICATION LIST-',
                          auto_size_columns=True, expand_x=True,
                          col_widths=[10, 50, 50, 50, 10],
                          num_rows=20,
                          expand_y=True, row_colors=row_colors)],
                [sg.CB("show resolved", key="-RESOLVED-", default=resolved,
                       enable_events=True),
                 sg.Text("Sort by:"),
                 sg.Combo(order_cols, default_value=sort_by,
                          key='-ORDER-', enable_events=True)]
            ]
            header = [[sg.Text(f"{num_rows:d} ongoing applications, "
                               "click on an item to modify status")]]
            footer = [[sg.Button("Close", key='-EXIT-'),
                       sg.Button("Export to excel", key='-EXPORT-')]]

            layout = [[header], [sg.HSeparator()],
                      [sg.Column(dates_list_columns, key='-COL-')],
                      [sg.HSeparator()], [footer]]
            return layout

        def gen_window(layout, size, location):
            window = sg.Window('Awaiting applications', size=size, location=location,
                               auto_size_text=True, auto_size_buttons=True,
                               grab_anywhere=False, resizable=True,
                               layout=layout, finalize=True)
            window['-COL-'].expand(True, True)
            window['-APPLICATION LIST-'].expand(True, True)
            window['-APPLICATION LIST-'].table_frame.pack(
                expand=True, fill='both')
            return window

        sort_by = 'institution'
        size = (None, None)
        postings = filter_postings(all_postings, sort_by=sort_by)
        if postings.shape[0] == 0:
            sg.popup_error("You have not marked any posting as applied"
                           " so the list is empty.")
            return
        table = table_from_postings(postings)
        layout = gen_layout(table, sort_by=sort_by)
        window = gen_window(layout, size, window_location)
        layout_kwargs = {
            'resolved': True,
            'sort_by': sort_by,
        }
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            size = window.size

            if event == sg.WIN_CLOSED or event == '-EXIT-':
                window.close()
                break
            elif event == '-EXPORT-':
                url = os.path.join(self._output_dir, 'applications.xlsx')
                postings.to_excel(url, index=False)
                sg.popup("All currently filtered applications have been exported\n"
                         "to your output folder in the file applications.xlsx",
                         location=window_location)
                continue
            elif event == "-APPLICATION LIST-":
                row = values['-APPLICATION LIST-']
                if not isinstance(row, int):
                    row = row[0]
                selected_postings = postings.iloc[row, :].copy()
                if selected_postings.shape[0] == 0:
                    continue

                changes = self.view_awaiting_application(
                    selected_postings, window_location
                )

                if changes:
                    all_postings = pd.read_pickle(self._postings_url)
                    postings = filter_postings(all_postings, **layout_kwargs)
                    table = table_from_postings(postings)
                    new_layout = gen_layout(table, **layout_kwargs)
                    window.close()
                    window = gen_window(new_layout, size, window_location)
            elif event in ['-RESOLVED-', '-ORDER-']:
                layout_kwargs['resolved'] = values['-RESOLVED-']
                layout_kwargs['sort_by'] = values['-ORDER-']
                postings = filter_postings(all_postings, **layout_kwargs)
                table = table_from_postings(postings)
                new_layout = gen_layout(table, **layout_kwargs)
                window.close()
                window = gen_window(new_layout, size, window_location)
            else:
                logging.info(f"Got unknown event {event} with values {values}")
        return

    def view_awaiting_application(self, row, window_location=(None, None)):
        """Review and edit a post as shown in the application menu

        Parameters
        ----------
        row : Series
             a row from the applications dataframe to review

        Returns
        -------
        Status:
            indicates whether any edit was done to the postings
        """
        status_change = False
        font = 'Helvetica 12'

        row = row.copy()
        # unpack
        section = row['section']
        institution = row['institution']
        division = row['division']
        department = row['department']
        title = row['title']
        text = row['full_text']
        location = row['location']
        origin = row['origin']
        url = row['url']
        status = row['application_status']
        letters_recieved = row['letters_recieved']

        writers = self._personal_settings['letters']
        letters = [[sg.Text("Recommendation letters received:")]]
        if len(writers) == 0:
            letters.append([sg.Text("you can add letter writers in "
                                    "the configuration file")])
        for n, writer in enumerate(writers):
            letter_status = writer in letters_recieved
            letters.append([sg.Text(writer), sg.CB("Received", key=f"-L-{n}",
                                                   default=letter_status,
                                                   enable_events=True)])


        layout = [
            [sg.Text('Title:', font=font + ' underline'),
             sg.Text(f'{title}', font=font),
             sg.Text('Institution:', font=font + ' underline'),
             sg.Text(f'{institution}', font=font)],
            [sg.Text(f"{department} | {division} | {section} ")],
            [sg.HSeparator()],
            [sg.Text(f"Current status: {status}", font=font + ' bold')],
            [sg.HSeparator()],
            letters,
            [sg.HSeparator()],
            [sg.Text(f'Location: {location}')],
            [sg.Text(f'Source: {origin}'), sg.Button('See posting', key='-VISIT-'),
             sg.Button("See full text", key='-FULL-')],
            [sg.HSeparator()],
            [sg.Button("Close", key='-CLOSE-'),
             sg.Button("Progress status", key="-PROGRESS-"),
             sg.Button("Interrupt application", key='-INTERRUPT-'),
             sg.Button("Revert status", key='-REGRESS-'),
             ]
        ]

        # size = (600, 400)
        window = sg.Window('Application status', layout,
                           location=window_location)
        while True:
            event, values = window.read()
            # update the window location
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event in ["-CLOSE-"]:
                window.close()
                break
            elif event == '-VISIT-':
                webbrowser.open(url)
            elif event == "-PROGRESS-":
                window.close()
                status_change = True
                ll = (window_location[0] + 300, window_location[1] + 200)
                sg.popup_quick_message("Congrats!", location=ll,
                                       font='Helvetica 16 bold',
                                       auto_close_duration=2)
                if status in ['awaiting response', 'no interview']:
                    row['application_status'] = 'got interview'
                elif status in ['got interview', 'no flyout']:
                    row['application_status'] = 'got flyout'
                elif status in ['got flyout', 'no offer']:
                    row['application_status'] = 'got offer'
                elif status in ['got offer', 'offer rejected']:
                    row['application_status'] = 'offer accepted'
                break
            elif event == "-INTERRUPT-":
                window.close()
                status_change = True
                if status == 'awaiting response':
                    row['application_status'] = 'no interview'
                elif status == 'got interview':
                    row['application_status'] = 'no flyout'
                elif status == 'got flyout':
                    row['application_status'] = 'no offer'
                elif status == 'got offer':
                    row['application_status'] = 'offer rejected'
                break
            elif event == "-REGRESS-":
                window.close()
                status_change = True
                if status == 'got interview':
                    row['application_status'] = 'awaiting response'
                elif status == 'got flyout':
                    row['application_status'] = 'got interview'
                elif status == 'got offer':
                    row['application_status'] = 'got flyout'
                elif status == 'offer accepted':
                    row['application_status'] = 'got offer'
                break
            elif event == "-FULL-":
                self.large_text_popup(text, location=window_location)
            elif '-L-' in event:
                received = []
                for num, writer in enumerate(writers):
                    stat = values[f'-L-{num}']
                    if stat:
                        received.append(writer)
                received.sort()
                row['letters_recieved'] = ",".join(received)
                num_s = f"{len(received):d}/{len(writers):d}"
                row['letters_status'] = num_s
                status_change = True
            else:
                logging.warning(f"Got unkown event {event}")

        if status_change:
            # Update
            postings = pd.read_pickle(self._postings_url)
            sel = (postings['origin'] == row['origin']) & \
                (postings['origin_id'] == row['origin_id'])
            if not sel.any():
                logging.warning(
                    f"Failed to find a match for row {row} in postings")
                os.popup_error("Failed to match update row to postings. Is the "
                               " postings file corrupt?")
                status_change = False
                return status_change
            if sel.sum() > 1:
                logging.warning("Single row selected multiple lines in postings.\n"
                                "this suggests a corrupted postings file.\n"
                                f"requested: {row}\n got \n {postings.loc[sel, :]}")
                os.popup_error("Failed to match update row to postings. Is the "
                               " postings file corrupt?")
                status_change = False
                return status_change

            ix = postings.loc[sel, :].index.values[0]
            row = row.to_frame().T
            row.index = [ix]
            # Test one more time to be sure
            test = (postings.loc[sel, 'origin'] == row['origin']) & \
                (postings.loc[sel, 'origin_id'] == row['origin_id'])
            if not test.all():
                logging.warning("Failed to match the row with the data. "
                                " This suggests a corrupted postings file."
                                f"requested: {row}\n got \n {postings.loc[sel, :]}")
                os.popup_error("Failed to match update row to postings. Is the "
                               " postings file corrupt?")
                status_change = False
                return status_change

            row = row.loc[:, ['application_status', 'deadline', 'letters_recieved',
                              'letters_status']]
            postings.update(row)
            postings.to_pickle(self._postings_url)

        return status_change

    def set_configuration_gui(self, window_location=(None, None)):
        """A window to set basic configuration

        Parameters
        ----------
        window_location : tuple, optional
            window location

        Returns
        -------
        None
        """

        def gen_layout():
            letters = []
            if len(self._personal_settings['letters']) > 0:
                for n, letter in enumerate(self._personal_settings['letters']):
                    row = [
                        sg.InputText(default_text=letter, key=f"-LETTER-{n}-"),
                        sg.Button("Update", key=f"-UPDATE-LETTER-{n}"),
                        sg.Button("Delete", key=f"-DELETE-LETTER-{n}")
                    ]
                    letters.append(row)
            letters.append([sg.InputText(key="-LETTER-NEW-"),
                            sg.Button("Add", key="-ADD-LETTER-")])

            posting_cols = []
            for n, col in enumerate(self._personal_settings['custom_posting_cols']):
                row = [
                    sg.Text(col),
                    sg.Button("Delete", key=f"-DELETE-PC-{n}")
                ]
                posting_cols.append(row)

            posting_cols.append([sg.InputText(key="-PC-NEW-"),
                                 sg.Button("Add", key="-ADD-PC-")])

            scaf_in = "None selected"
            if self._personal_settings['scaffolding_base'] is not None:
                scaf_in = self._personal_settings['scaffolding_base']

            scaf_out = "None selected"
            if self._personal_settings['scaffolding_output_dir'] is not None:
                scaf_out = self._personal_settings['scaffolding_output_dir']

            layout = [
                [sg.Text("Letter Writers:")],
                letters,
                [sg.HSeparator()],
                [sg.Text("Application scaffolding:")],
                [sg.Text("Folder to copy:"),
                 sg.Input(default_text=scaf_in, key='-SCAF-IN-'),
                 sg.FolderBrowse(key="-SCAF-IN-BROWSE-"),
                 sg.Button("Update", key="-SCAF-IN-UPDATE-")],
                [sg.Text("Base folder for application:"),
                 sg.Input(default_text=scaf_out, key='-SCAF-OUT-'),
                 sg.FolderBrowse(key="-SCAF-OUT-BROWSE-"),
                 sg.Button("Update", key="-SCAF-OUT-UPDATE-")],
                [sg.HSeparator()],
                [sg.Text("Custom posting columns:")],
                posting_cols,
                [sg.HSeparator()],
                [sg.Button("Close", key="-CLOSE-")]
            ]
            return layout

        def save_setting():
            with open(self._personal_settings_url, 'wb') as handle:
                pickle.dump(self._personal_settings, handle)
            return

        layout = gen_layout()
        window = sg.Window('Personal Settings', layout,
                           location=window_location)
        while True:
            event, values = window.read()
            # update the window location
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == '-CLOSE-':
                window.close()
                break
            elif event == "-SCAF-IN-UPDATE-":
                val = values['-SCAF-IN-']
                if val == 'None selected':
                    continue
                elif not os.path.isdir(val):
                    sg.popup_error(f"The scaffolding base folder {val} could "
                                   "not be found")
                    continue
                else:
                    self._personal_settings['scaffolding_base'] = val
                    save_setting()
                    window.close()
                    layout = gen_layout()
                    window = sg.Window('Personal Settings', layout,
                                       location=window_location)
                    continue
            elif event == "-SCAF-OUT-UPDATE-":
                val = values['-SCAF-OUT-']
                if val == 'None selected':
                    continue
                elif not os.path.isdir(val):
                    sg.popup_error(f"The scaffolding output folder {val} could "
                                   "not be found")
                    continue
                else:
                    self._personal_settings['scaffolding_output_dir'] = val
                    save_setting()
                    window.close()
                    layout = gen_layout()
                    window = sg.Window('Personal Settings', layout,
                                       location=window_location)
                    continue
            elif event == "-ADD-LETTER-":
                val = values['-LETTER-NEW-'].strip()
                if len(val) == 0:
                    sg.popup_error("Letter writer name must be non-empty")
                    continue
                else:
                    self._personal_settings['letters'].append(val)
                    save_setting()
                    window.close()
                    layout = gen_layout()
                    window = sg.Window('Personal Settings', layout,
                                       location=window_location)
                    continue
            elif '-UPDATE-LETTER' in event:
                num = int(event.split('-')[-1])
                val = values[f'-LETTER-{num:d}-'].strip()
                self._personal_settings['letters'][num] = val
                save_setting()
                window.close()
                layout = gen_layout()
                window = sg.Window('Personal Settings', layout,
                                   location=window_location)
                continue
            elif '-DELETE-LETTER' in event:
                num = int(event.split('-')[-1])
                letters = self._personal_settings['letters'].copy()
                del letters[num]
                self._personal_settings['letters'] = letters
                save_setting()
                window.close()
                layout = gen_layout()
                window = sg.Window('Personal Settings', layout,
                                   location=window_location)
                continue
            elif event == "-ADD-PC-":
                val = values['-PC-NEW-'].strip()
                if len(val) == 0:
                    sg.popup_error("column name must be non-empty")
                    continue
                else:
                    # Validate its not taken
                    all_postings = pd.read_pickle(self._postings_url)
                    if val in all_postings.columns:
                        sg.popup_error(f"column name {val} already in use")
                        continue
                    all_postings[val] = ''
                    all_postings.to_pickle(self._postings_url)
                    self._personal_settings['custom_posting_cols'].append(val)
                    save_setting()
                    window.close()
                    layout = gen_layout()
                    window = sg.Window('Personal Settings', layout,
                                       location=window_location)
                    continue
            elif '-DELETE-PC-' in event:
                num = int(event.split('-')[-1])
                letters = self._personal_settings['custom_posting_cols'].copy()
                val = letters[num]
                res = sg.popup_ok_cancel(
                    f"Are you sure you wish to delete this column ({val})?\n"
                    "ALL information related to this column will be "
                    "deleted permanently",
                    location=window_location
                )
                if res == 'OK':
                    all_postings = pd.read_pickle(self._postings_url)
                    all_postings.drop(val, axis=1, inplace=True)
                    all_postings.to_pickle(self._postings_url)

                    del letters[num]
                    self._personal_settings['custom_posting_cols'] = letters
                    save_setting()
                    window.close()
                    layout = gen_layout()
                    window = sg.Window('Personal Settings', layout,
                                       location=window_location)

        return

    def modify_notes(self, notes, location=(None, None)):
        """show and update posting notes

        Parameters
        ----------
        notes : str
        location: tuple

        Returns
        -------
        changed : bool
            whether the new notes are different from the previous
        notes: str
            new set of notes
        """
        layout = [
            [sg.Text("Custom Notes:")],
            [sg.Multiline(notes, enter_submits=False, autoscroll=True, key='notes',
                          auto_size_text=True)],
            [sg.Button("Close", key='-SAVE-'),
             sg.Button("Close without saving", key="-CLOSE-")]
        ]
        window = sg.Window("Notes", layout, location=location,
                           auto_size_text=True, auto_size_buttons=True,
                           grab_anywhere=False, resizable=True,
                           finalize=True)
        window['notes'].expand(True, True)
        while True:
            event, value = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event in ["-CLOSE-"]:
                val = value['notes']
                if val != notes:
                    res = sg.popup_ok_cancel(
                        "Closing without saving. Please confirm",
                        location=window_location
                    )
                    if res == 'OK' or res is None:
                        window.close()
                        break
                else:
                    window.close()
                    break
            elif event == '-SAVE-':
                window.close()
                return True, value['notes']

        return False, notes
