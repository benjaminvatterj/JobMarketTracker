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
            [sg.Button("Close")]
        ]
        window = sg.Window('Job Market Tracker', layout, size=(600, 150))
        while True:
            event, values = window.read()
            if event == sg.WIN_CLOSED or event == "Close":
                window.close()
                return
            elif event == "-UPDATE POSTINGS-":
                window.close()
                self.manual_update_files_gui()
                return self.main_gui()
            elif event == "-NEW-":
                window.close()
                self.review_new_postings()
                return self.main_gui()

        return

    def manual_update_files_gui(self):
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
        window = sg.Window('Refresh Listings', layout, size=size)
        AEA_done = False
        EJM_done = False
        while True:
            event, values = window.read()
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
                window = sg.Window('Refresh Listings', layout, size=size)
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
                window = sg.Window('Refresh Listings', layout, size=size)
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

    def review_new_postings(self):
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
        window_location = (None, None)

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
                window_location = window.CurrentLocation()
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
