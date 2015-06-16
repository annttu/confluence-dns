# encoding: utf-8


import requests


class Confluence(object):
    def __init__(self, base_url, username, password, verify_ssl=True):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.r = requests.session()
        self.r.auth = (self.username, self.password)
        self.r.headers.update({'User-Agent': 'Confluence-DNS updater'})


    def get_page(self, page_id):
        """
        Get page with id {page_id}
        :param page_id: page id
        :return: content as json
        """
        url = "%s/rest/api/content/%s?expand=body.storage" % (self.base_url, page_id)
        response = self.r.get(url, verify=self.verify_ssl)
        if response.status_code != 200:
            return None
        else:
            return response.json()['body']['storage']['value']
