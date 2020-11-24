import json
import os
from .esmond.api.client.perfsonar.query import ApiConnect
from .esmond.api.client.perfsonar.query import Metadata

import requests
requests.packages.urllib3.disable_warnings()


class SocksSSLApiConnect(ApiConnect):
    def get_metadata(self, cert=None, key=None, verify=False):
        if self.script_alias:
            archive_url = '{0}/{1}/perfsonar/archive/'.format(self.api_url, self.script_alias)
        else:
            archive_url = '{0}/perfsonar/archive/'.format(self.api_url)
        if cert and key:
            archive_url = archive_url.replace("http://", "https://", 1)
            r = requests.get(archive_url,
            params=dict(self.filters.metadata_filters, **self.filters.time_filters),
            headers = self.request_headers, verify=verify, cert=(cert,key))
        elif os.getenv('SOCKS5'):
            session = requesocks.session()
            session.proxies = {'http': os.getenv('SOCKS5'), 'https': os.getenv('SOCKS5')}
            session.verify = verify
            r = session.get(archive_url,
            params=dict(self.filters.metadata_filters, **self.filters.time_filters),
            headers = self.request_headers)
        else:
            r = requests.get(archive_url,
            params=dict(self.filters.metadata_filters, **self.filters.time_filters),
            headers = self.request_headers, verify=verify)
        self.inspect_request(r)
        data = list()

        if r.status_code == 200 and \
            r.headers['content-type'] == 'application/json':
            data = json.loads(r.text)
            
            if data:
                m_total = Metadata(data[0], self.api_url, self.filters).metadata_count_total
            else:
                m_total = 0
            # Check to see if we are geting paginated metadata, tastypie 
            # has a limit to how many results it will return even if 
            # ?limit=0
            if len(data) < m_total:
                # looks like we got paginated content.
                if self.filters.verbose: print('pagination - metadata_count_total: {0} got: {1}\n'.format(m_total, len(data)))
                initial_offset = len(data) # should be the tastypie internal limit of 1000
                offset = initial_offset
                while offset < m_total:
                    if self.filters.verbose:
                        print(('current total results: {0}'.format(len(data))))
                        print(('issuing request with offset: {0}'.format(offset)))
                    if cert and key:
                        r = requests.get(archive_url,
                            params=dict(self.filters.metadata_filters, **self.filters.time_filters),
                            headers = self.request_headers, verify=verify, cert=(cert,key))
                    else:
                        r = requests.get(archive_url,
                            params=dict(self.filters.metadata_filters, offset=offset, **self.filters.time_filters),
                            headers = self.request_headers)
                    self.inspect_request(r)

                    if r.status_code != 200:
                        print('error fetching paginated content')
                        self.http_alert(r)
                        return

                    tmp = json.loads(r.text)

                    if self.filters.verbose: print(('got {0} results\n'.format(len(tmp))))

                    data.extend(tmp)
                    offset += initial_offset

            if self.filters.verbose: print(('final result count: {0}\n'.format(len(data))))

            for i in data:
                yield Metadata(i, self.api_url, self.filters)
        else:
            raise Exception("Obtained responser error %s" % r.status_code )
            self.http_alert(r)
            return
            
