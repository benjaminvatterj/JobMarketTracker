import re
import os
import logging
import time
from urllib.parse import urljoin
import PySimpleGUI as sg
from bs4 import BeautifulSoup
from lxml import html
import numpy as np
import pandas as pd
import requests

"""
This script contains the scrapping classes for different websites
"""


class Scrapper:

    _agents = [
        "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:46.0) Gecko/20100101 Firefox/46.0",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    ]

    def __init__(self, base_url, max_errors=5):
        """Initialize a scrapper

        Parameters
        ---------
        base_url: str
            starting point for scrapping
        max_errors: int, optional
            maximum number of errors before declaring failure
        """
        self._base_url = base_url
        self._agent_index = 1
        self._max_errors = 5
        self._session = requests.Session()
        self._header = {'User-Agent': self._agents[self._agent_index]}
        return

    def clean_text(self, txt, lower=True):
        txt = BeautifulSoup(txt, "lxml").text
        txt = " ".join(txt.split())
        if lower:
            txt = txt.lower()
        return txt

    def get_page(self, url=None, tree_only=False, redirect=False):
        """
        Fetches a page from url.

        Parameters
        ----------
        url: str, optional
            url to page, otherwise picks up the base url
        tree_only: bool, optional
            return the html tree only else return the page object, the soup
            object and the tree
        redirect: bool, optional
            follow page redirections

        Returns
        -------
        tree: XMLTree
            tree representation of the website
        soup: BeautifulSoup object
            a beautification of the content
        page: request object
            the session object
        """
        if url is None:
            url = self._base_url
        err_count = 0
        while err_count < self._max_errors:
            page = self._session.get(url,
                                     headers=self._header,
                                     allow_redirects=redirect)
            try:
                soup = BeautifulSoup(page.text, "lxml")
                tree = html.fromstring(soup.prettify())
            except Exception:
                err_count += 1
                self._session.close()
                self._session = requests.Session()
                self._agent_index = self._agent_index + \
                    1 if (self._agent_index + 1 < len(self._agents)) else 0
                self._header = {
                    'User-Agent': self._agents[self._agent_index]}
                print("\t Warning: failed to get an answer, changing agent")
                time.sleep(60)
            else:
                break
        if tree_only:
            return tree
        else:
            return (tree, soup, page)
        return


class AJOScrapper(Scrapper):

    """A scrapper for AJO postings"""

    def __init__(self):
        """Initialize the object"""
        base_url = 'https://academicjobsonline.org/ajo/econ'
        Scrapper.__init__(self, base_url)
        return

    def get_postings(self):
        """Get current postings from AJO and store to file


        Returns
        -------
        status: bool
            indicates if scrapping was successfull
        message: str
            indicate failure source

        """
        tree, soup, page = self.get_page()

        # Traverse list to get positions
        dls = tree.xpath('//dl')
        links = []
        for item in dls:
            links.append(urljoin(
                self._base_url,
                item.xpath('dt/ol/li/a')[0].get('href')
            ))

        # Now iterate over links to get details
        success = True
        message = ''
        data = []
        for link in links:
            tree, soup, page = self.get_page(link)
            data_row = {}
            title = self.clean_text(tree.xpath('//h2')[0].text_content(), lower=False)
            splt = title.split(',')
            institution = splt[0]
            department = ','.join(splt[1:])
            data_row['institution'] = institution
            data_row['department'] = department
            data_row['url'] = link
            # Get the full description
            desc = self.clean_text(tree.xpath('//table')[1].text_content(), lower=False)
            data_row['full_text'] = desc

            # Split the id
            link_id = int(link.split('/')[-1].replace(r'[^0-9]', ''))
            data_row['origin_id'] = link_id


            table = tree.xpath('//table[@class="nobr"]')[0]
            rows = table.xpath('tr')
            for row in rows:
                row_text = self.clean_text(row.text_content(), lower=False)
                key = row_text.split(':')
                value = ':'.join(key[1:])
                value = value.strip()
                key = key[0].strip().lower()
                if ' id' in key:
                    continue
                elif 'location' in key:
                    key = 'location'
                    value = value.split('[ map ]')[0].strip()
                elif 'deadline' in key:
                    key = 'deadline'
                    value = value.lower()
                    group = re.findall(
                        r'\d{4}/\d{2}/\d{2}',
                        value
                    )
                    if len(group) == 0:
                        value = np.nan
                    else:
                        value = group[0]
                elif 'description' in key:
                    continue
                elif 'subject' in key:
                    key = 'keywords'
                elif 'title' in key:
                    key = 'title'
                elif 'type' in key:
                    key = 'division'

                data_row[key] = value
            data_row = pd.Series(data_row).to_frame().T
            data.append(data_row)

        data = pd.concat(data, ignore_index=True, axis=0)
        data['origin'] = 'AJO'

        from JMTracker.settings import settings
        test = data['origin_id'].isna().any()
        if test:
            success = False
            message = 'Failed to collect some ids for AOJ'
            # store
            path = os.path.join(settings['output_directory'], 'aoj_failures.csv')
            data.to_csv(path)
            return success, message

        logging.info("Storing AOJ files to input")
        path = os.path.join(settings['input_directory'], 'latest_aoj_postings.csv')
        data.to_csv(path)

        return success, message

    @staticmethod
    def gui_scrape(window_location=(None, None)):
        """Create an instance and scrape with user messages.

        Returns
        -------
        None
        """
        sg.popup("Downloading posting data from AOJ", location=window_location)
        scrapper = AJOScrapper()
        success, message = scrapper.get_postings()
        if success:
            sg.popup("Done processing. The data should be in the input folder"
                     " and called latest_aoj_postings.csv\n"
                     "Please review it and include it as with the other sources.",
                     location=window_location)
        else:
            sg.popup(message, location=window_location)

        return
