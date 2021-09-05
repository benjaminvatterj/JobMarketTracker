import os
import pandas as pd
import xlrd
import webbrowser
from shutil import copyfile
from JMTracker import settings
from JMTracker.scrappers import Scrapper
import logging
import requests
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

        # Set the GUI theme
        sg.theme("DarkTeal2")

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
        return

    def main_gui(self):
        """Show the main GUI for this system
        """
        layout = [
            [sg.Text("Update postings:"), sg.Button("update", key="-UPDATE POSTINGS-")],
            [sg.Text("Review new loaded postings:"), sg.Button("new", key="-NEW-")],
            [sg.Text("View deadlines:"), sg.Button("view", key="-DEADLINES-")],
            [sg.Button("Close")]
        ]
        window = sg.Window('Job Market Tracker', layout, size=(600, 150))
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == "Close":
                window.close()
                return
            elif event == "-UPDATE POSTINGS-":
                window.close()
                self.manual_update_files_gui(window_location)
                return self.main_gui()
            elif event == "-NEW-":
                window.close()
                self.review_new_postings(window_location)
                return self.main_gui()
            elif event == "-DEADLINES-":
                window.close()
                self.view_deadlines(window_location)
                return self.main_gui()

        return

    def manual_update_files_gui(self, window_location=(None, None)):
        """Prompt to update files from AEA and EJM
        """

        def core_layout(AEA_done=False, EJM_done=False):
            if not AEA_done:
                AEA_layout = [
                    [sg.Text("AEA file: "), sg.Input(),
                     sg.FileBrowse(key="-IN AEA-")],
                    [sg.Text("hint: download from here"),
                     sg.Button("link", key="-AEA LINK-")],
                    [sg.Button("Update AEA", key="-UPDATE AEA-")],
                ]
            else:
                AEA_layout = [sg.Text("AEA listings updated successfully")]

            if not EJM_done:
                EJM_layout = [
                    [sg.Text("EJM File: "), sg.Input(),
                     sg.FileBrowse(key="-IN EJM-")],
                    [sg.Text("hint: download from here"),
                     sg.Button("link", key="-EJM LINK-")],
                    [sg.Button("Update EJM", key="-UPDATE EJM-")],
                ]
            else:
                EJM_layout = [sg.Text("EJM listings updated successfully")]

            header = [[sg.Text("=== Update market postings ===")]]
            footer = [[sg.Button("Close and Save", key="-CLOSE-")]]

            layout = [header, AEA_layout, EJM_layout, footer]
            return layout

        # Building Window
        size = (600, 300)
        layout = core_layout()
        window = sg.Window('Refresh Listings', layout, size=size,
                           location=window_location)
        AEA_done = False
        EJM_done = False
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == "-CLOSE-":
                break
            elif event == "-UPDATE AEA-":
                aea_url = values["-IN AEA-"]
                # copy to local input folder
                new_url = os.path.join(self._input_dir, "latest_aea.xls")
                if not os.path.isfile(aea_url):
                    sg.Popup(f"AEA File {aea_url} not found!")
                    continue
                copyfile(aea_url, new_url)
                status, message = self.update_aea_postings()
                if not status:
                    sg.Popup(message)
                    continue
                window.close()
                AEA_done = True
                layout = core_layout(AEA_done, EJM_done)
                window = sg.Window('Refresh Listings', layout, size=size,
                                   location=window_location)
            elif event == "-UPDATE EJM-":
                ejm_url = values["-IN EJM-"]
                if not os.path.isfile(ejm_url):
                    sg.Popup(f"EJM File {ejm_url} not found!")
                    continue
                # copy to local input folder
                new_url = os.path.join(self._input_dir, "latest_ejm.csv")
                copyfile(ejm_url, new_url)
                status, message = self.update_ejm_postings()
                if not status:
                    sg.Popup(message)
                    continue
                window.close()
                EJM_done = True
                layout = core_layout(AEA_done, EJM_done)
                window = sg.Window('Refresh Listings', layout, size=size,
                                   location=window_location)
            elif event == "-AEA LINK-":
                webbrowser.open(settings['AEA_url'])
            elif event == "-EJM LINK-":
                webbrowser.open(settings['EJM_url'])
            else:
                logging.warning(f"Got unkown event {event}")


        window.close()

        return

    def update_aea_postings(self):
        """Process the latest_aea.xls currently in the input folder
        and compare it against the listings we have stored.
        Add those that we are missing and mark them as new.

        Returns
        -------
        status: bool
            success status of the update process

        message: str
            in case of failure a descriptive message
        """
        logging.info("Updating AEA postings")

        # -- 1) Validate the input --- #
        url = os.path.join(self._input_dir, "latest_aea.xls")
        workbook = xlrd.open_workbook(url, ignore_workbook_corruption=True)
        df = pd.read_excel(workbook)

        # Verify we have all the columns we excpet
        renames = {
            'jp_id': 'origin_id',
            'jp_section': 'section',
            'jp_institution': 'institution',
            'jp_division': 'division',
            'jp_department': 'department',
            'jp_keywords': 'keywords',
            'jp_title': 'title',
            'jp_full_text': 'full_text',
            'jp_salary_range': 'salary_range',
            'locations': 'location',
            'Application_deadline': 'deadline'
        }
        required = [x for x in renames.keys()]
        missing = set(required) - set(df.columns)
        if len(missing) > 0:
            status = False
            message = "AEA file is missing some of its key columns\n{missing}"
            return status, message

        df = df.loc[:, required]
        df.rename(columns=renames, inplace=True)
        df['date_received'] = "{}".format(settings['today'])
        df['origin'] = 'AEA'
        # Create url for AEA
        df['url'] = 'https://www.aeaweb.org/joe/listing.php?JOE_ID=' + \
            df['origin_id'].astype(str)

        df['reviewed'] = False
        df['status'] = 'new'
        df['notes'] = ''
        df['update_notes'] = ''
        df['updated'] = False

        # --- 2) Compare with stored values --- #

        if self._first_run:
            # In this case we just add the extra info and store
            logging.info("First time storing AEA data")
            df.to_pickle(self._postings_url)
            self._first_run = False
            return True, ''

        postings = pd.read_pickle(self._postings_url)
        previous = postings.loc[postings['origin'] == 'AEA', ['origin_id']]
        if previous.shape[0] == 0:
            logging.info("First time storing AEA data, appending")
            postings = postings.append(df, ignore_index=True)
            postings.to_pickle(self._postings_url)
            return True, ''

        new_ix = ~df['origin_id'].isin(previous['origin_id'].values)
        if new_ix.any():
            logging.info(f"Found {new_ix.sum()} new AEA postings! appending")
            new_postings = df.loc[new_ix, :].copy()
            postings = postings.append(new_postings, ignore_index=True)
            postings.to_pickle(self._postings_url)
            df = df.loc[~new_ix, :].copy()

        # No more to add
        if df.shape[0] == 0:
            logging.info("All AEA postings were new")
            return True, ''


        # Check the overalpp to see if there's anything new
        check_cols = ['url', 'title', 'section', 'division', 'deadline',
                      'institution']
        previous = postings.loc[postings['origin'] == 'AEA', :].copy()

        df = df.loc[:, check_cols + ['origin', 'origin_id']]
        df = previous.merge(df, on=['origin', 'origin_id'], how='left',
                            validate='1:1', suffixes=('', '_new'))

        total_updated = 0
        for col in check_cols:
            sel = (df[col] != df[col + '_new']) & (df[col + '_new'].notna())
            total_updated = max(total_updated, sel.sum())
            df.loc[sel, 'updated'] = True
            df.loc[sel, 'update_notes'] += f'new {col},'
            df.loc[sel, col] = df.loc[sel, col + '_new']
            df.drop(col + '_new', axis=1, inplace=True)

        if total_updated > 0:
            logging.info(f"Found {total_updated} updated in AEA postings!")

            # Remove the updated once, and append
            sel = (postings['origin'] == 'AEA') & (
                postings['origin_id'].isin(df['origin_id'].unique())
            )
            postings = postings.loc[~sel, :].copy()
            postings = postings.append(df, ignore_index=True)
            postings.to_pickle(self._postings_url)
        else:
            logging.info("No new postings in AEA")

        return True, ''

    def update_ejm_postings(self):
        """Process the latest_ejm.csv currently in the input folder
        and compare it against the listings we have stored.
        Add those that we are missing and mark them as new.

        Returns
        -------
        status: bool
            success status of the update process

        message: str
            in case of failure a descriptive message

        """
        logging.info("Update EJM postings")
        # --- Validate the input --- #
        new_url = os.path.join(self._input_dir, "latest_ejm.csv")
        df = pd.read_csv(new_url, header=1)

        renames = {
            'Id': 'origin_id',
            'URL': 'url',
            'Ad title': 'title',
            'Types': 'section',
            'Categories': 'division',
            'Deadline': 'deadline',
            'Department': 'department',
            'Institution': 'institution',
            'City': 'city',
            'State/province': 'state',
            'Country': 'country',
            'Application method': 'application_method',
            'Application URL': 'application_url',
            'Application email': 'application_email',
            'Ad text (in markdown format)': 'full_text'
        }

        required = [x for x in renames.keys()]
        missing = set(required) - set(df.columns)
        if len(missing) > 0:
            status = False
            message = "EJM file is missing some of its key columns\n{missing}"
            return status, message

        df = df.loc[:, required]
        df.rename(columns=renames, inplace=True)
        df['date_received'] = "{}".format(settings['today'])
        df['origin'] = 'EJM'
        # combine location
        df['country'].fillna('', inplace=True)
        df['city'].fillna('', inplace=True)
        df['state'].fillna('', inplace=True)
        df['location'] = df.loc[:, ['city', 'state', 'country']].apply(
            lambda x: ", ".join([xi for xi in x if len(xi.strip()) > 0]),
            axis=1
        )
        df.drop(['country', 'state', 'city'], axis=1, inplace=True)
        df['reviewed'] = False
        df['status'] = 'new'
        df['notes'] = ''
        df['update_notes'] = ''
        df['updated'] = False

        if self._first_run:
            # In this case we just add the extra info and store
            logging.info("First time storing EJM data")
            df.to_pickle(self._postings_url)
            self._first_run = False
            return True, ''

        # Otherwise verify how to we compare to the currently held data

        postings = pd.read_pickle(self._postings_url)
        previous = postings.loc[postings['origin'] == 'EJM', ['origin_id']]
        if previous.shape[0] == 0:
            logging.info("First time storing EJM data, appending")
            postings = postings.append(df, ignore_index=True)
            postings.to_pickle(self._postings_url)
            return True, ''

        new_ix = ~df['origin_id'].isin(previous['origin_id'].values)
        if new_ix.any():
            logging.info(f"Found {new_ix.sum()} new EJM postings! appending")
            new_postings = df.loc[new_ix, :].copy()
            postings = postings.append(new_postings, ignore_index=True)
            postings.to_pickle(self._postings_url)
            df = df.loc[~new_ix, :].copy()

        # No more to add
        if df.shape[0] == 0:
            logging.info("All EJM postings were new")
            return True, ''

        # Check the overalpp to see if there's anything new
        check_cols = ['url', 'title', 'section', 'division', 'deadline',
                      'institution']
        previous = postings.loc[postings['origin'] == 'EJM', :].copy()

        df = df.loc[:, check_cols + ['origin', 'origin_id']]
        df = previous.merge(df, on=['origin', 'origin_id'], how='left',
                            validate='1:1', suffixes=('', '_new'))

        total_updated = 0
        for col in check_cols:
            sel = (df[col] != df[col + '_new']) & (df[col + '_new'].notna())
            total_updated = max(total_updated, sel.sum())
            df.loc[sel, 'updated'] = True
            df.loc[sel, 'update_notes'] += f'new {col},'
            df.loc[sel, col] = df.loc[sel, col + '_new']
            df.drop(col + '_new', axis=1, inplace=True)

        if total_updated > 0:
            logging.info(f"Found {total_updated} updated in EJM postings!")

            # Remove the updated once, and append
            sel = (postings['origin'] == 'EJM') & (
                postings['origin_id'].isin(df['origin_id'].unique())
            )
            postings = postings.loc[~sel, :].copy()
            postings = postings.append(df, ignore_index=True)
            postings.to_pickle(self._postings_url)
        else:
            logging.info("No new postings in EJM")

        return True, ''

    def review_new_postings(self, window_location=(None, None)):
        """Look among the new postings

        Returns
        -------
        None
        """
        postings = pd.read_pickle(self._postings_url)
        # Restrict to new
        postings.query('status == "new"', inplace=True)
        postings.fillna('', inplace=True)
        break_loop = False
        status_updates = []
        font = 'Helvetica 12'

        for ix, row in postings.iterrows():
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
            origin_id = row['origin_id']
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
                [sg.Button("Skip"), sg.Button("Interested"), sg.Button("Ignore"),
                 sg.Button("Maybe"), sg.Button("Stop Review", key='-CLOSE-')]
            ]

            # size = (600, 400)
            window = sg.Window('New posting', layout, location=window_location)
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
                elif event == "-FULL-":
                    self.large_text_popup(text, location=window_location)

            if break_loop:
                break

        # Update status
        if len(status_updates) > 0:
            status_updates = pd.DataFrame(
                status_updates, columns=['origin', 'origin_id', 'status']
            )
            logging.info(f"Updating {status_updates.shape[0]} posting statuses")
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
        all_postings = pd.read_pickle(self._postings_url)

        def filter_postings(all_postings, maybe=False, expired=True, applied=False):
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
                    pd.to_datetime(postings['deadline']) >= pd.Timestamp("today")
                ) | (
                    postings['deadline'].isna()
                )
                postings = postings.loc[sel, :].copy()
            return postings


        def deadlines_from_postings(postings):
            # Ensure we have the right columns

            postings = postings.copy()
            postings['deadline_str'] = pd.to_datetime(postings['deadline']).astype(str)
            sel = postings['deadline_str'] == 'NaT'
            postings.loc[sel, 'deadline_str'] = 'Unknown'
            sel = postings['deadline'].notna()
            postings.loc[sel, 'deadline'] =\
                pd.to_datetime(postings.loc[sel, 'deadline'])
            postings['unique_id'] = postings.groupby(['origin', 'origin_id']).ngroup()
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
            current_deadlines['deadline'] = current_deadlines['deadline'].astype(str)

            current_deadlines = (
                current_deadlines.loc[:, ['deadline_str', 'unique_id', 'time_left']]
                .rename(columns={'deadline_str': 'deadline'})
                .copy()
            )

            # starting values
            tbl = current_deadlines.values.tolist()
            return tbl, current_deadlines


        def gen_layout(deadline_values, application_values, selected_deadline=None,
                       date=None, maybe=False, expired=True, applied=False):

            columns = ['Deadline', 'Applications', 'Time left']
            color1 = sg.theme_input_background_color()
            row_colors = None
            if selected_deadline is not None:
                row_colors = [(selected_deadline, color1)]

            dates_list_columns = [
                [sg.Text("Upcoming deadlines:", font='Helvetica 12 underline')],
                [sg.Table(values=deadline_values, enable_events=True,
                          headings=columns, key='-DATE LIST-',
                          auto_size_columns=True,
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
                          headings=['Institution', 'Title'],
                          auto_size_columns=True,
                          expand_y=True, key='-APPLICATIONS-')],
                [sg.Button("Clear", key="-CLEAR-"), sg.Button("Show All", key="-ALL-")]
            ]
            header = [[sg.Text("Select date from left, click on item on the right"
                               " to edit")]]
            footer = [[sg.Button("Close", key='-EXIT-')]]

            layout = [[header], [sg.HSeparator()], [
                sg.Column(dates_list_columns),
                sg.VSeparator(),
                sg.Column(results_columns)
            ], [sg.HSeparator()], [footer]]
            return layout


        postings = filter_postings(all_postings)
        tbl, current_deadlines = deadlines_from_postings(postings)
        posting_values = [['', '']]
        selected_postings = None
        selected_row = None
        selected_date = None
        layout = gen_layout(tbl, posting_values, selected_row, selected_date)
        window = sg.Window("Deadlines", layout, location=window_location)
        layout_kwargs = {
            'maybe': False,
            'expired': True,
            'applied': False
        }
        while True:
            event, values = window.read()
            window_location = window.CurrentLocation(True)
            if event == sg.WIN_CLOSED or event == '-EXIT-':
                window.close()
                break
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
                    posting_values = [['', '']]
                else:
                    posting_values = (
                        selected_postings.loc[:, ['institution', 'title']]
                        .values.tolist()
                    )
                selected_row = row
                selected_date = date
                new_layout = gen_layout(tbl, posting_values, row, date, **layout_kwargs)
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location)
            elif event == "-CLEAR-":
                posting_values = [['', '']]
                selected_date = None
                selected_row = None
                selected_postings = None
                new_layout = gen_layout(tbl, posting_values, **layout_kwargs)
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location)
            elif event == "-ALL-":
                posting_values = (
                    postings.loc[:, ['institution', 'title']].values.tolist()
                )
                selected_row = None
                selected_date = "any date"
                new_layout = gen_layout(tbl, posting_values, selected_row,
                                        selected_date,
                                        **layout_kwargs)
                window.close()
                window = sg.Window("Deadlines", new_layout, location=window_location)
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
                window = sg.Window("Deadlines", new_layout, location=window_location)
            elif event == "-APPLICATIONS-":
                if selected_postings is None:
                    sg.popup_error("Got a request to show a posting but the posting"
                                   " list appears to be empty!")
                    continue
                row = values['-APPLICATIONS-']
                if not isinstance(row, int):
                    row = row[0]
                posting_row = selected_postings.iloc[row, :]
                changes = self.view_detailed_posting(posting_row, window_location)
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
                        posting_values = [['', '']]
                    else:
                        posting_values = (
                            selected_postings.loc[:, ['institution', 'title']]
                            .values.tolist()
                        )
                    new_layout = gen_layout(
                        tbl, posting_values, selected_row, selected_date,
                        **layout_kwargs
                    )
                    window.close()
                    window = sg.Window("Deadlines", new_layout,
                                       location=window_location)

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
        alt_status = 'maybe'
        alt_status_txt = alt_status
        if status == 'maybe':
            alt_status = 'interested'
            alt_status_txt = alt_status
        elif status == 'applied':
            alt_status_txt = 'not applied'
            alt_status = 'interested'

        alt_status = 'maybe' if status == 'interested' else 'interested'
        layout = [
            [sg.Text('Title:', font=font + ' underline'),
             sg.Text(f'{title}', font=font),
             sg.Text('Institution:', font=font + ' underline'),
             sg.Text(f'{institution}', font=font)],
            [sg.Text(f"{department} | {division} | {section} ")],
            [sg.HSeparator()],
            [sg.Text(f"Current status: {status}")],
            [sg.Text(f'Location: {location}')],
            [sg.Text('Deadline:'),
             sg.Input(deadline, key='-IN-DEADLINE-', size=(20, 1)),
             sg.CalendarButton('select deadline', close_when_date_chosen=True,
                               target='-IN-DEADLINE-', location=window_location,
                               no_titlebar=False)],
            [sg.Text(f'keywords: {keywords}')],
            [sg.Text(f'Source: {origin}'), sg.Button('See posting', key='-VISIT-'),
             sg.Button("See full text", key='-FULL-')],
            [sg.HSeparator()],
            [sg.Button("Close", key='-CLOSE-'),
             sg.Button(f"Mark as {alt_status_txt}", key="-SWITCH-"),
             sg.Button("Mark as Applied", key='-APPLIED-'),
             sg.Button("Remove from deadlines", key='-IGNORE-'),
             sg.Button("Update deadline", key='-DEADLINE-'),
             sg.Button("Edit/View Notes", key='-NOTES-')]
        ]

        # size = (600, 400)
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
            elif event == '-DEADLINE-':
                new_deadline = values['-IN-DEADLINE-']
                new_deadline = (
                    pd.to_datetime(new_deadline)
                    .to_pydatetime().date().__str__()
                )
                row['deadline'] = new_deadline
                status_change = True
                window.close()
                break
            elif event == '-NOTES-':
                logging.info("Got request to see notes")
                continue
            elif event == '-VISIT-':
                webbrowser.open(url)
            elif event == "-FULL-":
                self.large_text_popup(text, location=window_location)
            else:
                logging.warning(f"Got unkown event {event}")

        if status_change:
            # Update
            postings = pd.read_pickle(self._postings_url)
            sel = (postings['origin'] == row['origin']) & \
                (postings['origin_id'] == row['origin_id'])
            if not sel.any():
                logging.warning(f"Failed to find a match for row {row} in postings")
                status_change = False
                return status_change

            ix = postings.loc[sel, :].index.values[0]
            row = row.to_frame().T
            row.index = [ix]
            postings.update(row)
            postings.to_pickle(self._postings_url)

        return status_change


    def update_local_scrapping(self):
        """Update the local list of postings

        Returns
        -------
        None
        """
        raise Exception("Not implemented")
        logging.info("Connecting to AEA to find link for download")
        scrapper = Scrapper()
        url = settings['AEA_url']
        tree = scrapper.get_page(url, tree_only=True, redirect=True)
        links = tree.xpath(
            '//ul[@class="exportOptions"]/li[2]/a/'
        )

        r = requests.get(settings['AEA_url'], allow_redirects=True)
        out_url = os.path.join(self._storage_dir, "AEA_download.xls")
        with open(out_url, 'wb') as f:
            f.write(r.content)
        return links

    def large_text_popup(self, text, title="full text", size=(800, 800),
                         location=(None, None)):

        layout = [[sg.Text(text, size=(100, None))]]
        popup = sg.Window(title, location=location).Layout([[
            sg.Column(layout, size=size, scrollable=True)
        ]])
        popup.read()

        return
