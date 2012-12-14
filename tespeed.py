#!/usr/bin/env python2
"""
Invokes SpeedTest.net and show results on the standard output.

Copyright 2012 Janis Jansons (janis.jansons@janhouse.lv)
Pylint, PEP8 (almost full) compliance and some docstrings by Wagner Andreoli (wagnerandreoli@gmail.com)
"""
import argparse
import urllib
import urllib2
import gzip
import sys
from multiprocessing import Process, Pipe, Manager
from lxml import etree
import time
from math import radians, cos, sin, asin, sqrt
from StringIO import StringIO


class CallbackStringIO(StringIO):
    """
    Using StringIO with callback to measure upload progress.
    """
    def __init__(self, num, thread, download, buf=''):
        StringIO.__init__(self)

        # Force self.buf to be a string or unicode
        if not isinstance(buf, basestring):
            buf = str(buf)

        self.buf = buf
        self.len = len(buf)
        self.buflist = []
        self.pos = 0
        self.closed = False
        self.softspace = 0
        self.thread = thread
        self.num = num
        self.download = download
        self.total = self.len * self.thread

    def read(self, n_value=10240):
        """
        ?
        """
        next_string = StringIO.read(self, n_value)

        self.download[self.num] = self.pos
        down = 0
        for i in range(self.thread):
            down = down + self.download.get(i, 0)
        if self.num == 0:
            percent = float(down) / (self.total)
            percent = round(percent * 100, 2)
            print_debug("Uploaded %d of %d bytes (%0.2f%%) in %d threads\r" % (down, self.total, percent, self.thread))

        return next_string

    def __len__(self):
        return self.len


class TeSpeed:
    """
    Invokes SpeedTest.net and show results on the standard output.
    """
    def __init__(self, server="", num_top=0, servercount=3, store=False, suppress=False, unit=False):
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:11.0) Gecko/20100101 Firefox/11.0',
            'Accept-Language': 'en-us,en;q=0.5',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate',
        }

        self.num_servers = servercount
        self.servers = []
        if server != "":
            self.servers = [server]

        self.config = None
        self.server_list = None

        self.server = server
        self.down_speed = -1
        self.up_speed = -1
        self.latencycount = 10
        self.best_servers = 5

        self.units = "Mbit"
        self.unit = 0

        if unit:
            self.units = "MiB"
            self.unit = 1

        self.store = store
        self.suppress = suppress
        if store:
            print_debug("Printing CSV formated results to STDOUT.\n")
        self.num_top = int(num_top)

        self.down_list = [
            '350x350', '350x350', '500x500', '500x500', '750x750', '750x750', '1000x1000', '1500x1500', '2000x2000', '2500x2500',
            '3000x3000', '3500x3500', '4000x4000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000',
            '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000',
            '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000',
            '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000',
            '4000x4000', '4000x4000', '4000x4000', '4000x4000', '4000x4000']

        self.up_sizes = [
            1024 * 256, 1024 * 256, 1024 * 512, 1024 * 512, 1024 * 1024, 1024 * 1024, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2,  1024 * 512,
            1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256,
            1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512,
            1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512,
            1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256, 1024 * 256,
            1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512, 1024 * 512,
            1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2,  1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2,
            1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2,  1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2, 1024 * 1024 * 2]

        self.post_data = ""
        self.test_speed()

    def test_latency(self, servers):
        """
        Finding servers with lowest latency.
        """
        print_debug("Testing latency...\n")
        po_value = []
        for server in servers:
            now = self.test_single_latency(server['url'] + "latency.txt?x=" + str(time.time())) * 1000
            now = now / 2  # Evil hack or just pure stupidity? Nobody knows...
            if now == -1 or now == 0:
                continue
            print_debug(
                "%0.0f ms latency for %s (%s, %s, %s) [%0.2f km]\n" %
                (now, server['url'], server['sponsor'], server['name'],
                server['country'], server['distance']))

            server['latency'] = now

            # Pick specified amount of servers with best latency for testing
            if int(len(po_value)) < int(self.num_servers):
                po_value.append(server)
            else:
                largest = -1

                for i in range(len(po_value)):
                    if largest < 0:
                        if now < po_value[i]['latency']:
                            largest = i
                    elif po_value[largest]['latency'] < po_value[i]['latency']:
                        largest = i

                if largest >= 0:
                    po_value[largest] = server

        return po_value

    def test_single_latency(self, dest_addr):
        """
        Checking latency for single server.
        Does that by loading latency.txt (empty page).
        """
        request = self.get_request(dest_addr)

        averagetime = 0
        total = 0
        for i in range(self.latencycount):
            error = 0 * i
            start_time = time.time()
            try:
                urllib2.urlopen(request, timeout=5)
            except urllib2.URLError:
                error = 1

            if error == 0:
                averagetime = averagetime + (time.time() - start_time)
                total = total + 1

            if total == 0:
                return False

        return averagetime / total

    def get_request(self, uri):
        """
        Generates a GET request to be used with urlopen.
        """
        req = urllib2.Request(uri, headers=self.headers)
        return req

    def post_request(self, uri, stream):
        """
        Generate a POST request to be used with urlopen.
        """
        req = urllib2.Request(uri, stream, headers=self.headers)
        return req

    def async_get(self, conn, uri, num, thread, download):
        """
        Execute an asynchronous GET request.
        """
        request = self.get_request(uri)
        start = 0
        end = 0
        size = 0

        try:
            response = urllib2.urlopen(request, timeout=30)
            size, start, end = chunk_read(response, num, thread, download, report_hook=chunk_report)
        except:
            print_debug('                                                                                           \r')
            print_debug("Failed downloading.\n")
            conn.send([0, 0, False])
            conn.close()
            return

        conn.send([size, start, end])
        conn.close()

    def async_post(self, conn, uri, num, thread, download):
        """
        Execute an asynchronous POST request.
        """
        postlen = len(self.post_data)
        stream = CallbackStringIO(num, thread, download, self.post_data)
        request = self.post_request(uri, stream)

        start = 0
        end = 0

        try:
            response = urllib2.urlopen(request, timeout=30)
            size, start, end = chunk_read(response, num, thread, download, 1, report_hook=chunk_report)
        except:
            print_debug('                                                                                           \r')
            print_debug("Failed uploading (size=%d).\n" % size)
            conn.send([0, 0, False])
            conn.close()
            return

        conn.send([postlen, start, end])
        conn.close()

    def load_config(self):
        """
        Load the configuration file.
        """
        print_debug("Loading speedtest configuration...\n")
        uri = "http://speedtest.net/speedtest-config.php?x=" + str(time.time())
        request = self.get_request(uri)
        response = urllib2.urlopen(request)

        # Load etree from XML data
        config = etree.fromstring(decompress_response(response))

        ip_address = config.find("client").attrib['ip']
        isp = config.find("client").attrib['isp']
        lat = float(config.find("client").attrib['lat'])
        lon = float(config.find("client").attrib['lon'])

        print_debug("IP: %s; Lat: %f; Lon: %f; ISP: %s\n" % (ip_address, lat, lon, isp))

        return {'ip': ip_address, 'lat': lat, 'lon': lon, 'isp': isp}

    def load_servers(self):
        """
        Load server list.
        """
        print_debug("Loading server list...\n")
        uri = "http://speedtest.net/speedtest-servers.php?x=" + str(time.time())
        request = self.get_request(uri)
        response = urllib2.urlopen(request)

        # Load etree from XML data
        servers_xml = etree.fromstring(decompress_response(response))
        servers = servers_xml.find("servers").findall("server")
        server_list = []

        for server in servers:
            server_list.append(
                {'lat': float(server.attrib['lat']),
                    'lon': float(server.attrib['lon']),
                    'url': server.attrib['url'].rsplit('/', 1)[0] + '/',
                    'url2': server.attrib['url2'].rsplit('/', 1)[0] + '/',
                    'name': server.attrib['name'],
                    'country': server.attrib['country'],
                    'sponsor': server.attrib['sponsor'],
                    'id': server.attrib['id']})

        return server_list

    def find_best_server(self):
        """
        Find the closest server with the best latency.
        """
        print_debug("Looking for closest and best server...\n")
        best = self.test_latency(closest([self.config['lat'], self.config['lon']], self.server_list, self.best_servers))
        for server in best:
            self.servers.append(server['url'])

    def async_request(self, url, num, upload=0):
        """
        Executes an asynchronous request.
        """
        connections = []
        download = Manager().dict()
        start = time.time()
        for i in range(num):
            full_url = self.servers[i % len(self.servers)] + url
            connection = {}
            connection['parent'], connection['child'] = Pipe()
            if upload == 1:
                connection['connection'] = Process(target=self.async_post, args=(connection['child'], full_url, i, num, download))
            else:
                connection['connection'] = Process(target=self.async_get, args=(connection['child'], full_url, i, num, download))
            connection['connection'].start()
            connections.append(connection)

        for i in range(num):
            connections[i]['size'], connections[i]['start'], connections[i]['end'] = connections[i]['parent'].recv()
            connections[i]['connection'].join()

        end = time.time()

        print_debug('                                                                                           \r')

        sizes = 0
        for i in range(num):
            if connections[i]['end'] is not False:
                sizes = sizes + connections[i]['size']

                # Using more precise times for downloads
                if upload == 0:
                    if i == 0:
                        start = connections[i]['start']
                        end = connections[i]['end']
                    else:
                        if connections[i]['start'] < start:
                            start = connections[i]['start']
                        if connections[i]['end'] > end:
                            end = connections[i]['end']

        took = end - start

        return [sizes, took]

    def test_upload(self):
        """
        Testing upload speed.
        """
        url = "upload.php?x=" + str(time.time())

        sizes, took = [0, 0]
        data = ""
        for i in range(0, len(self.up_sizes)):
            if len(data) == 0 or self.up_sizes[i] != self.up_sizes[i - 1]:
                data = ''.join("1" for x in xrange(self.up_sizes[i]))
            self.post_data = urllib.urlencode({'upload6': data})

            if i < 2:
                thrds = 1
            elif i < 5:
                thrds = 2
            elif i < 7:
                thrds = 2
            elif i < 10:
                thrds = 3
            elif i < 25:
                thrds = 6
            elif i < 45:
                thrds = 4
            elif i < 65:
                thrds = 3
            else:
                thrds = 2

            sizes, took = self.async_request(url, thrds, 1)
            if sizes == 0:
                continue

            size = self.speed_conversion(sizes)
            speed = size / took
            print_debug(
                "Upload size: %0.2f MiB; Uploaded in %0.2f s\n" %
                (size, took))
            print_debug(
                "\033[92mUpload speed: %0.2f %s/s\033[0m\n" %
                (speed, self.units))

            if self.up_speed < speed:
                self.up_speed = speed

            if took > 5:
                break

    def speed_conversion(self, data):
        """
        Perform unit conversion in the speed value.
        """
        if self.unit == 1:
            result = float(data) / 1024 / 1024
        else:
            result = (float(data) / 1024 / 1024) * 1.048576 * 8
        return result

    def test_download(self):
        """
        Testing download speed.
        """
        sizes, took = [0, 0]
        for i in range(0, len(self.down_list)):
            url = "random" + self.down_list[i] + ".jpg?x=" + str(time.time()) + "&y=3"

            if i < 2:
                thrds = 1
            elif i < 5:
                thrds = 2
            elif i < 11:
                thrds = 2
            elif i < 13:
                thrds = 4
            elif i < 25:
                thrds = 2
            elif i < 45:
                thrds = 3
            elif i < 65:
                thrds = 2
            else:
                thrds = 2

            sizes, took = self.async_request(url, thrds)
            if sizes == 0:
                continue

            size = self.speed_conversion(sizes)
            speed = size / took
            print_debug("Download size: %0.2f MiB; Downloaded in %0.2f s\n" % (size, took))
            print_debug("\033[91mDownload speed: %0.2f %s/s\033[0m\n" % (speed, self.units))

            if self.down_speed < speed:
                self.down_speed = speed

            if took > 5:
                break

    def test_speed(self):
        """
        Executes the speed test.
        """
        if self.server == 'list-servers':
            self.config = self.load_config()
            self.server_list = self.load_servers()
            self.list_servers(self.num_top)
            return

        if self.server == '':
            self.config = self.load_config()
            self.server_list = self.load_servers()
            self.find_best_server()

        self.test_download()
        self.test_upload()

        print_result("%0.2f,%0.2f,\"%s\",\"%s\"\n" % (self.down_speed, self.up_speed, self.units, self.servers))

    def list_servers(self, num=0):
        """
        List closest servers.
        """
        all_sorted = closest([self.config['lat'], self.config['lon']], self.server_list, num)

        for i in range(0, len(all_sorted)):
            print_result(
                "%s. %s (%s, %s, %s) [%0.2f km]\n" %
                (i + 1, all_sorted[i]['url'], all_sorted[i]['sponsor'],
                all_sorted[i]['name'], all_sorted[i]['country'],
                all_sorted[i]['distance']))


def closest(center, points, num=5):
    """
    Returns object that is closest to center.
    """
    closest_servers = {}
    for i in range(len(points)):
        now = distance(center, [points[i]['lat'], points[i]['lon']])
        points[i]['distance'] = now
        while True:
            if now in closest_servers:
                now = now + 00.1
            else:
                break
        closest_servers[now] = points[i]
    n_value = 0
    ret = []
    for key in sorted(closest_servers):
        ret.append(closest_servers[key])
        n_value += 1
        if n_value >= num and num != 0:
            break
    return ret


def distance(one, two):
    """
    Calculate the great circle distance between two points
    on the earth specified in decimal degrees (haversine formula)
    (http://stackoverflow.com/posts/4913653/revisions)
    Convert decimal degrees to radians.
    """
    lon1, lat1, lon2, lat2 = map(radians, [one[0], one[1], two[0], two[1]])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    value_a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    value_c = 2 * asin(sqrt(value_a))
    kilometers = 6367 * value_c
    return kilometers


def chunk_read(response, num, thread, download, w_value=0, chunk_size=10240, report_hook=None):
    """
    Read a chunk.
    """
    if w_value == 1:
        return [0, 0, 0]

    total_size = response.info().getheader('Content-Length').strip()
    total_size = int(total_size)
    bytes_so_far = 0

    start = 0
    while 1:
        chunk = 0
        if start == 0:
            chunk = response.read(1)
            start = time.time()

        else:
            chunk = response.read(chunk_size)
        if not chunk:
            break
        bytes_so_far += len(chunk)
        if report_hook:
            report_hook(bytes_so_far, chunk_size, total_size, num, thread, download, w_value)
    end = time.time()

    return [bytes_so_far, start, end]


def chunk_report(bytes_so_far, chunk_size, total_size, num, thread, download, w_value):
    """
    Receiving status update from download thread.
    """
    if w_value == 1:
        return
    download[num] = bytes_so_far
    down = 0
    for i in range(thread):
        down = down + download.get(i, 0)

    if num == 0 or down >= total_size * thread:

        percent = float(down) / (total_size * thread)
        percent = round(percent * 100, 2)

        print_debug(
            "Downloaded %d of %d bytes (%0.2f%%) in %d threads (chunk size=%d)\r" %
            (down, total_size * thread, percent, thread, chunk_size))


def decompress_response(response):
    """
    Decompress gzipped response.
    """
    data = StringIO(response.read())
    gzipper = gzip.GzipFile(fileobj=data)
    return gzipper.read()


def print_debug(string):
    """
    Print a string for debbuging purposes.
    """
    if not ARGS.suppress:
        sys.stderr.write(string.encode('utf8'))


def print_result(string):
    """
    Print results in the standard output.
    """
    if ARGS.store:
        sys.stdout.write(string.encode('utf8'))


def main(args):
    """
    Main function (this module's entry point).
    """
    if args.listservers:
        args.store = True

    if not args.listservers and args.server == '' and not args.store:
        print_debug("Getting ready. Use parameter -h or --help to see available features.\n")
    else:
        print_debug("Getting ready\n")
    try:
        TeSpeed(
            args.listservers and 'list-servers'
            or args.server, args.listservers, args.servercount, args.store
            and True or False, args.suppress and True or False, args.unit
            and True or False)
    except (KeyboardInterrupt, SystemExit):
        print_debug("\nTesting stopped.\n")


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description='TeSpeed, CLI SpeedTest.net')
    PARSER.add_argument('server', nargs='?', type=str, default='', help='Use the specified server for testing (skip checking for location and closest server).')
    PARSER.add_argument('-ls', '--list-servers', dest='listservers', nargs='?', default=0, const=10, help='List the servers sorted by distance, nearest first. Optionally specify number of servers to show.')
    PARSER.add_argument('-w', '--csv', dest='store', action='store_const', const=True, help='Print CSV formated output to STDOUT.')
    PARSER.add_argument('-s', '--suppress', dest='suppress', action='store_const', const=True, help='Suppress debugging (STDERR) output.')
    PARSER.add_argument('-mib', '--mebibit', dest='unit', action='store_const', const=True, help='Show results in mebibits.')
    PARSER.add_argument('-n', '--server-count', dest='servercount', nargs='?', default=1, const=1, help='Specify how many different servers should be used in paralel. (Defaults to 1.) (Increase it for >100Mbit testing.)')

    ARGS = PARSER.parse_args()
    main(ARGS)
