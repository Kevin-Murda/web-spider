#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""File that contains WebSpider class."""

import calendar
import json
import os
import time
import re
from urllib.parse import urlparse, urlsplit
import urllib3
from bs4 import BeautifulSoup
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class WebSpider:
    """Simple WebSpider."""
    settings = dict()
    settings['config_file'] = 'config.json'
    settings['headers'] = dict()
    loot = dict()

    def __init__(self):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.container = os.path.dirname(os.path.realpath(__file__))
        if not self.container.endswith('/'):
            self.container += '/'

        self.load_config()

    def load_config(self):
        """Parses and loads configuration from config.json file."""
        if os.path.isfile(self.settings['config_file']):
            with open(self.settings['config_file']) as data_file:
                data = json.load(data_file)
                self.settings = data
        else:
            print("> Can't find config file (" + self.settings['config_file'] + ").")
            print(
                '> You can create a new config file by copying "config.json.sample"'
                ' file and renaming it to "config.json".'
            )
            exit(1)

    @staticmethod
    def validate_url(value):
        """Helper method that checks if URL has valid format."""
        validator = URLValidator()
        try:
            validator(value)
            return True
        except ValidationError:
            return False

    @staticmethod
    def combine_uri(part_one, part_two):
        """Method that deals with combining URLs."""
        if not part_one.endswith('/'):
            part_one += '/'
        if part_two.startswith('/'):
            part_two = part_two[1:]

        return part_one + part_two

    @property
    def user_agent(self):
        """Returns value of user_agent property."""
        return self.settings['headers']['user-agent']

    @user_agent.setter
    def user_agent(self, value):
        """Assings new value to user_agent property."""
        self.settings['headers']['user-agent'] = value

    def get_page_source(self, target):
        """Makes request to target and returns result."""
        http = urllib3.PoolManager(headers=self.settings['headers'])
        request = http.request('GET', target['url'])
        page_source = request.data
        return page_source

    def save_loot(self):
        """Saves fetched results on drive."""
        for target in self.loot:
            if not os.path.isdir(self.container + 'loot/' + target):
                os.makedirs(self.container + 'loot/' + target, 0o700)

            cts = calendar.timegm(time.gmtime())
            path = self.container + 'loot/' + target + '/' + str(cts)

            if not os.path.isdir(path):
                os.mkdir(path, 0o700)

            try:
                if self.loot[target]['urls']:
                    with open(path + '/urls.txt', 'w+') as file_handle:
                        for url in self.loot[target]['urls']:
                            file_handle.write(url + "\n")
            except KeyError:
                pass

            try:
                if self.loot[target]['emails']:
                    with open(path + '/emails.txt', 'w+') as file_handle:
                        for email in self.loot[target]['emails']:
                            file_handle.write(email + "\n")
            except KeyError:
                pass

            try:
                if self.loot[target]['comments']:
                    with open(path + '/comments.txt', 'w+') as file_handle:
                        for comment in self.loot[target]['comments']:
                            file_handle.write(comment + "\n")
            except KeyError:
                pass

    def run(self):
        """Method that executes WebSpider."""
        for target in self.settings['targets']:
            netloc = urlsplit(target['url']).netloc
            self.loot[netloc] = dict()

            try:
                if target['fetch_urls']:
                    self.fetch_urls(target, self.loot[netloc])
            except KeyError:
                pass

            try:
                if target['fetch_emails']:
                    self.fetch_emails(target, self.loot[netloc])
            except KeyError:
                pass

            try:
                if target['fetch_comments']:
                    self.fetch_comments(target, self.loot[netloc])
            except KeyError:
                pass

        self.save_loot()

    def fetch_urls(self, target, loot):
        """Method that fetches URLs."""
        protocol = urlparse(target['url'])[0]
        data = self.get_page_source(target)
        soup = BeautifulSoup(data, 'html.parser')

        loot['urls'] = list()

        for line in soup.find_all('a'):
            url = line.get('href')

            if not url:
                continue

            if url[:4] != 'http' and url[:2] != '//':
                url = self.combine_uri(target['url'], url)
            elif url[:2] == '//':
                url = protocol + ':' + url

            if url not in loot['urls']:
                loot['urls'].append(url)

    def fetch_emails(self, target, loot):
        """Method that fetches Emails."""
        data = self.get_page_source(target).decode('utf8')
        regex = re.compile(r'[\w\.-]+@[\w\.-]+')
        emails = re.findall(regex, data)

        loot['emails'] = list()

        for email in emails:
            if not email in loot['emails']:
                loot['emails'].append(email)

        if self.settings['escaped_email_symbols']:
            for escaped_symbol in self.settings['escaped_email_symbols']:
                regex = re.compile(r'[\w\.-]+' + re.escape(escaped_symbol) + r'[\w\.-]+')
                emails = re.findall(regex, data)

                for escaped_email in emails:
                    email = escaped_email.replace(escaped_symbol, '@')

                    if not email in loot['emails']:
                        loot['emails'].append(email)

    def fetch_comments(self, target, loot):
        """Method that fetches comments."""
        data = self.get_page_source(target).decode('utf8')
        regex = re.compile(r'<!--(.*)-->')
        comments = re.findall(regex, data)

        loot['comments'] = list()

        for comment in comments:
            comment = comment.strip()

            if not comment in loot['comments']:
                loot['comments'].append(comment)
