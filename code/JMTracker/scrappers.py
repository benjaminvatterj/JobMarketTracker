import re
import time
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

    def __init__(self, max_errors=5):
        """Initialize a scrapper

        :drugnames: (list) names of drugs to find
        """
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

    def get_page(self, url, tree_only=True, redirect=False):
        """
        Fetches a page from url.

        :url: (str) url
        :tree_only: (bool) return the html tree only
                    else return the page object, the soup object and
                    the tree
        """
        err_count = 0
        tree = None
        while err_count < self._max_errors:
            page = self._session.get(url,
                                     headers=self._header,
                                     allow_redirects=redirect)
            try:
                soup = BeautifulSoup(page.text, "lxml")
                tree = html.fromstring(soup.prettify())
            except Exception as err:
                err_count += 1
                self._session.close()
                self._session = requests.Session()
                self._agent_index = self._agent_index + \
                    1 if (self._agent_index + 1 < len(self._agents)) else 0
                self._header = {
                    'User-Agent': self._agents[self._agent_index]}
                print("\t Warning: failed to get an answer, changing agent."
                      f"\n caught error {err}")
                time.sleep(1)
            else:
                break
        if tree_only:
            return tree
        else:
            return (page, soup, tree)


class drugsDotCom(Scrapper):
    """
    Scrappes drugs.com
    """

    base_url = 'https://www.drugs.com/'
    search_url = 'search.php?sources%5B%5D=availability&searchterm={:s}'
    valid_link = re.compile(r'https://www\.drugs\.com/availability/.*\.html')
    rating_re = re.compile(r'(\d\.\d)\s*/\s*10')
    consumers_re = re.compile(r'^(\d+)\s*user.*')
    name_re = re.compile(r'(.*)\s+\((.*)\s+-\s+(.*)\)')
    manufacturer_re = re.compile(
        r'manufacturer:\s+(.*)\s+(?:(?:approval date:)|' +
        r'(?:approved prior to))\s+(.*)\s+strength\(s\):\s*(.*)'
    )
    generic_name_re = re.compile(r'(.*)\s*,\s+(.*)')
    patent_re = re.compile(r'.*issued:\s*(\w+ \d+, \d+).*')

    def scrape(self):
        new_drug_names = pd.DataFrame(
            columns=['drugname', 'new_drugid', 'found_name', 'compound',
                     'formulation', 'manufacturer', 'approval_date',
                     'strenghts', 'rating', 'rating_consumers', 'availability',
                     'discontinued', 'has_generic', 'has_patent',
                     'has_exclusivity'])
        new_drug_generics = pd.DataFrame(
            columns=['drugname', 'new_drugid', 'generic_name',
                     'generic_manufacturer', 'generic_approval_date',
                     'generic_strenghts', 'generic_unorganized'])
        new_drug_patents = pd.DataFrame(
            columns=['drugname', 'new_drugid', 'patent_text', 'issue_date',
                     'expiration_date', 'patent_type'])
        new_drug_exclusivities = pd.DataFrame(
            columns=['drugname', 'new_drugid', 'exclusivity_expiration_date',
                     'exclusivity_type'])
        new_drugid = -1

        for drug_name in self._drugnames:
            print("Searching from drug {:s}".format(drug_name))

            err_count = 0
            while err_count < self._max_errors:
                page = self._session.get(self.base_url +
                                         self.search_url.format(drug_name),
                                         headers=self._header)
                try:
                    soup = BeautifulSoup(page.text, "lxml")
                    tree = html.fromstring(soup.prettify())
                except Exception as err:
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

            if err_count >= self._max_errors:
                print("\t ERROR: Failed to get anything coherent for this drug")
                continue

            links = tree.xpath(
                '//div[@class="contentBox"]//'
                'div[contains(@class, "search-result")]/h3/a')
            if len(links) == 0:
                print("\t No match found for this drug")
                continue
            print("\t Found {:d} matches for the drug".format(len(links)))

            for l in links:
                url = l.get('href')
                if self.valid_link.match(url) is None:
                    print("\t This link is not valid {:s}".format(url))
                    continue

                print("\t reading {:s}".format(url))
                while err_count < self._max_errors:
                    page = self._session.get(url, headers=self._header)
                    try:
                        soup = BeautifulSoup(page.text, "lxml")
                        page_tree = html.fromstring(soup.prettify())
                    except Exception as err:
                        err_count += 1
                        self._session.close()
                        self._session = requests.Session()
                        self._agent_index = self._agent_index + \
                            1 if (self._agent_index + 1 <
                                  len(self._agents)) else 0
                        self._header = {
                            'User-Agent': self._agents[self._agent_index]}
                        print("\t\t Warning: failed to get an answer, changing agent")
                        time.sleep(60)
                    else:
                        break

                if err_count >= self._max_errors:
                    print("\t\t ERROR: Failed to get anything coherent for this drug")
                    continue

                print("\t\t Getting contents")
                new_drugid += 1
                # recenter the tree
                tree = page_tree.xpath('//div[@class="contentBox"]')[0]
                # Get the names
                names = tree.xpath('./h2[1]/preceding-sibling::h3')
                # This will contains: drug name, scientifc name,
                # formulations, manufacturer, approval date, strength

                full_names = []
                for n in names:
                    name = self.clean_text(n.text_content())
                    m = self.name_re.match(name)
                    if m is None:
                        print(
                            "WARNING: Name '{:s}' doesnt match pattern".format(name))
                        if name.find('all of the above formulations have been discontinued') != -1:
                            print(
                                "WARNING: name {:s} has all discountinued".format(
                                    name)
                            )
                            full_names = []
                            break
                        else:
                            continue
                    name = m.group(1)
                    scientific = m.group(2)
                    formulations = m.group(3)

                    manufs = n.xpath('./following-sibling::ul[1]/li')
                    for m in manufs:
                        manuf_txt = self.clean_text(m.text_content())
                        m = self.manufacturer_re.match(manuf_txt)
                        if m is None:
                            print("WARNING: Manufacturer"
                                  " '{:s}' doesnt match the pattern".format(
                                      manuf_txt)
                                  )

                        full_names.append((drug_name, new_drugid, name,
                                           scientific, formulations,
                                           m.group(1), m.group(2), m.group(3)))
                if full_names == []:
                    print("WARNING: Full names is empty for this drug")
                    continue
                full_names = np.array(full_names)
                full_names_col = new_drug_names.columns[:full_names.shape[1]]
                full_names = pd.DataFrame(full_names, columns=full_names_col)

                print("\t\t Got {:d} names for this drug".format(len(names)))

                # Check if discontinued
                disc = self.clean_text(tree.xpath('./h2[1]')[0].text_content())
                discontinued = False
                if disc.find('discontinued') > -1:
                    discontinued = True
                    print("\t\t This drug has been discontinued")
                full_names['discontinued'] = discontinued

                # Get generic
                generic = self.clean_text(tree.xpath(
                    './h2[1]/following-sibling::p[1]')[0].text_content())
                # This will have: generic name, formulation, manufcaturer,
                # approval date, strengths
                generic_content = []
                if generic.find('no') == 0:
                    has_generic = False
                    print("\t\t This drug doesnt have a generic")
                else:
                    if generic.find('yes') != 0 and \
                       generic.find('has been approved') == -1:
                        raise Exception("""
                        generic text {:s} doesnt start with yes or no
                        """.format(generic))
                    has_generic = True
                    print('\t\t This drug has a generic')
                    generic = tree.xpath('./h2[1]/following-sibling::h3[1]')
                    if len(generic) > 0:
                        generic = generic[0]
                        generic_name = self.clean_text(
                            generic.xpath('./a')[0].text_content())
                        manufs = generic.xpath('./following-sibling::ul[1]/li')
                        for m in manufs:
                            manuf_name = self.clean_text(m.text_content())
                            rem = self.manufacturer_re.match(manuf_name)
                            if rem is None:
                                raise Exception("""
                                generic manufacturer {:s} doesnt match
                                """.format(manuf_name))
                            generic_content.append([drug_name, new_drugid,
                                                    generic_name, rem.group(1),
                                                    rem.group(2), rem.group(3),
                                                    ''])
                    else:
                        print("\t\t This drug generic is unorganized")
                        generic_txt = self.clean_text(
                            tree.xpath(
                                './h2[1]/following-sibling::p[1]'
                            )[0].text_content())
                        generic_content.append([drug_name, new_drugid, '', '',
                                                '', '', generic_txt])

                    generic_content = np.array(generic_content)
                    generic_content = pd.DataFrame(
                        generic_content, columns=new_drug_generics.columns)

                    print("\t\t got {:d} generics".format(
                        generic_content.shape[0]))
                    # End of has generic

                full_names['has_generic'] = has_generic

                # Get patents
                patents = tree.xpath('./h2[contains(text(), "Patents")]')
                # Will have patent description, issue date, expiration date,
                # exlcusivity type
                patent_info = []
                has_patent = False
                if len(patents) > 0:
                    has_patent = True
                    patents = patents[0]
                    print("\t\t Found patents for this drug")
                    lis = patents.xpath('./following-sibling::ul[1]/li')
                    for l in lis:
                        content = self.clean_text(l.text_content())
                        m = self.patent_re.match(content)
                        if m is None:
                            print("WARNING: patent text doesnt fit:" +
                                  " {:s}".format(content))
                            issue_date = ''
                        else:
                            issue_date = m.group(1)
                        dates = l.xpath('./ul/li')
                        for d in dates:
                            d1 = self.clean_text(
                                d.xpath('./b')[0].text_content())
                            patent_type = d.xpath('./div[2]')
                            if len(patent_type) > 0:
                                d2 = self.clean_text(
                                    patent_type[0].text_content())
                            else:
                                d2 = ''
                            patent_info.append([drug_name, new_drugid,
                                                content, issue_date, d1, d2])
                    patent_info = np.array(patent_info)
                    patent_info = pd.DataFrame(
                        patent_info, columns=new_drug_patents.columns)
                    print("\t\t found {:d} patents for this drug".format(
                        patent_info.shape[0]))
                    # end of has patents

                full_names['has_patent'] = has_patent

                # Get exclusivities
                exclusive = tree.xpath(
                    './h2[contains(text(), "Exclusivities")]')
                exclusive_info = []
                has_exclusivity = False
                if len(exclusive) > 0:
                    has_exclusivity = True
                    exclusive = exclusive[0]
                    print("\t\t Found exclusivity for this drug")
                    li = exclusive.xpath('./following-sibling::ul[1]/li/ul/li')
                    for l in li:
                        d = self.clean_text(l.xpath('./b')[0].text_content())
                        txt = self.clean_text(l.text_content())
                        txt = "-".join(txt.split("-")[1:]).strip()
                        exclusive_info.append([drug_name, new_drugid, d, txt])

                    exclusive_info = np.array(exclusive_info)
                    exclusive_info = pd.DataFrame(
                        exclusive_info, columns=new_drug_exclusivities.columns)
                    print("\t\t found {:d} exclusivities for this drug".format(
                        exclusive_info.shape[0]))

                full_names['has_exclusivity'] = has_exclusivity

                # Get ratings
                try:
                    rating = self.clean_text(page_tree.xpath(
                        '//span[@class="rating-score"]')[0].text_content())
                except IndexError:
                    rating = np.nan
                else:
                    m = self.rating_re.match(rating)
                    if m is None:
                        print("\t\t WARNING: This drug doesnt have a valid " +
                              "rating: {:s}".format(rating))
                        rating = np.nan
                    else:
                        rating = float(m.group(1))

                numbers = page_tree.xpath('//span[@class="ratings-total"]/a/b')
                if len(numbers) > 0:
                    numbers = self.clean_text(
                        numbers[0].text_content()
                    )
                    m = self.consumers_re.match(numbers)
                    if m is None:
                        print("\t\t WARNING: This drug doesnt have a valid"
                              " number of consumer ratings {:s}".format(numbers))
                        numbers = 0
                    else:
                        numbers = int(m.group(1))
                else:
                    print("\t\t WARNING: This drug doesnt have a ratings number")
                    numbers = 0

                print("\t\t This drug has a rating of " +
                      "{} with {} reviews".format(rating, numbers))
                # Get availability
                availability = self.clean_text(
                    page_tree.xpath(
                        '//div[contains(@class, "drugInfoRx1") or ' +
                        'contains(@class, "drugInfoRx2") or ' +
                        'contains(@class, "drugInfoRx") or ' +
                        'contains(@class, "drugInfoRx3")' +
                        ']/following' +
                        '-sibling::div[1]/span')[0].text_content()
                )
                print("\t\t This drug availability is : {}".format(availability))

                full_names['rating'] = rating
                full_names['rating_consumers'] = numbers
                full_names['availability'] = availability

                # sort columns
                full_names = full_names.loc[:, new_drug_names.columns]

                print("\t\t appending to stack")
                new_drug_names = new_drug_names.append(
                    full_names, ignore_index=True)
                if has_generic:
                    new_drug_generics = new_drug_generics.append(
                        generic_content, ignore_index=True)
                if has_patent:
                    new_drug_patents = new_drug_patents.append(
                        patent_info, ignore_index=True)
                if has_exclusivity:
                    new_drug_exclusivities = new_drug_exclusivities.append(
                        exclusive_info, ignore_index=True)

        print('--- exclusive info ---')
        print(new_drug_exclusivities)

        # Combine all result and return
        print("Merging results and combining")
        new_drug_names = new_drug_names.merge(new_drug_generics.drop_duplicates(),
                                              on=['drugname', 'new_drugid'],
                                              how='left')
        new_drug_names = new_drug_names.merge(new_drug_patents.drop_duplicates(),
                                              on=['drugname', 'new_drugid'],
                                              how='left')
        new_drug_names = new_drug_names.merge(new_drug_exclusivities.drop_duplicates(),
                                              on=['drugname', 'new_drugid'],
                                              how='left')
        new_drug_names = self.fix_columns(new_drug_names)
        new_drug_names.drop_duplicates(inplace=True)
        return new_drug_names

    def fix_columns(self, df):
        """Sets the correct data types for the columns

        :df: (dataframe) dataframe to correct columns
        :returns: (dataframe)
        """
        int_cols = ['rating_consumers']
        float_cols = ['rating']
        bool_cols = ['discontinued', 'has_generic',
                     'has_patent', 'has_exclusivity']
        str_cols = ['drugname', 'clean_drugname', 'new_drugid', 'found_name',
                    'compound', 'formulation', 'manufacturer', 'approval_date',
                    'strenghts', 'rating_consumers', 'availability',
                    'discontinued', 'issue_date', 'expiration_date',
                    'has_generic', 'has_patent', 'has_exclusivity',
                    'generic_name', 'generic_manufacturer',
                    'generic_approval_date', 'generic_strenghts',
                    'generic_unorganized', 'patent_text', 'patent_type',
                    'exclusivity_expiration_date', 'exclusivity_type']

        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')

        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], downcast='float')

        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)

        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str)

        return df
