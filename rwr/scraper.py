from lxml import html, etree
from rwrs import app, cache
from .server import Server
from .player import Player
from . import constants
import geoip2.database
import requests

scraper_requests_session = requests.Session()
scraper_requests_adaptater = requests.adapters.HTTPAdapter(max_retries=1)

scraper_requests_session.mount('http://', scraper_requests_adaptater)
scraper_requests_session.mount('https://', scraper_requests_adaptater)


class DataScraper:
    servers_endpoint = 'http://rwr.runningwithrifles.com/rwr_server_list/'
    players_endpoint = 'http://rwr.runningwithrifles.com/rwr_stats/'

    def _call(self, endpoint, resource, parser, params=None):
        """Perform an HTTP GET request to the desired RWR list endpoint."""
        url = endpoint + resource

        headers = {
            'User-Agent': 'rwrstats.com'
        }

        response = scraper_requests_session.get(url, params=params, headers=headers, timeout=5)

        response.encoding = 'unicode'

        response.raise_for_status()

        if parser == 'html':
            return html.fromstring(response.text)
        elif parser == 'xml':
            return etree.fromstring(response.text)
        else:
            raise ValueError('Invalid parser')

    @cache.memoize(timeout=app.config['SERVERS_CACHE_TIMEOUT'])
    def get_servers(self):
        """Get and parse the list of all public RWR servers."""
        xml_servers = self._call(self.servers_endpoint, 'get_server_list.php', 'xml', params={'start': 0, 'size': 100})
        html_servers = self._call(self.servers_endpoint, 'view_servers.php', 'html')

        servers = []

        for xml_node in xml_servers.xpath('/result/server'):
            servers.append(Server.load(xml_node, html_servers))

        self.set_servers_location(servers)

        return servers

    def set_servers_location(self, servers):
        """Set the location of a list of servers."""
        if not servers:
            return

        geoip_db_reader = geoip2.database.Reader(app.config['GEOIP_DATABASE_FILE'])

        for server in servers:
            location = geoip_db_reader.city(server.ip)

            if location:
                if location.city.geoname_id:
                    server.location.city_name = location.city.names['en']

                if location.country.geoname_id:
                    server.location.country_code = location.country.iso_code.lower()
                    server.location.country_name = location.country.names['en']

                if location.continent.geoname_id:
                    server.location.continent_code = location.continent.code.lower()
                    server.location.continent_name = location.continent.names['en']

                server.location.text = '{}{}'.format(
                    server.location.city_name + ', ' if server.location.city_name else '',
                    server.location.country_name
                )

        geoip_db_reader.close()

    def get_server_by_ip_and_port(self, ip, port):
        """Search for a RWR public server based on its IP and port."""
        servers = self.get_servers()

        for server in servers:
            if server.ip == ip and server.port == port:
                return server

        return None

    def get_server_by_name(self, name):
        """Search for a RWR public server based on its name (partial match)."""
        servers = self.get_servers()

        name = name.lower()

        for server in servers:
            if name in server.name.lower():
                return server

        return None

    def _get_list(self, value_attribute, label_attribute):
        """Return a list of value -> label of the specified servers attributes."""
        servers = self.get_servers()
        ret = []
        already_handled = []

        for server in servers:
            value = value_attribute(server)
            label = label_attribute(server)

            if value and value not in already_handled:
                ret.append({
                    'value': value,
                    'label': label
                })

                already_handled.append(value)

        return sorted(ret, key=lambda k: k['label'])

    def get_all_servers_locations(self):
        """Return the location of all the servers."""
        servers = self.get_servers()
        locations = {}

        for server in servers:
            if not server.location.country_code:
                continue

            if server.location.continent_code not in locations:
                locations[server.location.continent_code] = {
                    'name': server.location.continent_name,
                    'countries': {}
                }

            if server.location.country_code not in locations[server.location.continent_code]['countries']:
                locations[server.location.continent_code]['countries'][server.location.country_code] = server.location.country_name

        ret = []

        for continent_code, continent in locations.items():
            group = {
                'type': 'group',
                'value': 'continent:' + continent_code,
                'label': continent['name'],
                'entries': []
            }

            for country_code, country_name in continent['countries'].items():
                group['entries'].append({
                    'value': 'country:' + country_code,
                    'label': country_name
                })

            group['entries'] = sorted(group['entries'], key=lambda k: k['label'])

            ret.append(group)

        return sorted(ret, key=lambda k: k['label'])

    def get_all_servers_types(self):
        """Return the type of all of the servers."""
        return self._get_list(
            lambda server: server.type if server.type not in ['vanilla.winter', 'pvp'] else False,
            lambda server: server.type_name
        )

    def get_all_servers_modes(self):
        """Return the mode of all of the servers."""
        return self._get_list(
            lambda server: server.mode,
            lambda server: server.mode_name_long
        )

    def get_all_servers_maps(self):
        """Return the map of all of the servers."""
        servers = self.get_servers()
        maps = {}

        for server in servers:
            if not server.map.id:
                continue

            if server.type.startswith('vanilla') or server.type == 'pvp':
                server_type = 'vanilla'
            else:
                server_type = server.type

            if server_type not in maps:
                maps[server_type] = {
                    'name': server.type_name,
                    'maps': {}
                }

            if server.map.id not in maps[server_type]['maps']:
                maps[server_type]['maps'][server.map.id] = server.map.name_display

        ret = []

        for game_type in maps.values():
            group = {
                'type': 'group',
                'label': game_type['name'],
                'entries': []
            }

            for map_id, map_name in game_type['maps'].items():
                group['entries'].append({
                    'value': map_id,
                    'label': map_name
                })

            group['entries'] = sorted(group['entries'], key=lambda k: k['label'])

            ret.append(group)

        return sorted(ret, key=lambda k: k['label'])

    def filter_servers(self, **filters):
        """Filter servers corresponding to the given criteria."""
        def _filter_server(server, filters):
            location = filters.get('location', 'any')
            map = filters.get('map', 'any')
            type = filters.get('type', 'any')
            mode = filters.get('mode', 'any')
            dedicated = filters.get('dedicated')
            ranked = filters.get('ranked')
            not_empty = filters.get('not_empty')
            not_full = filters.get('not_full')

            if location != 'any':
                if ':' in location:
                    location_type, location_code = location.split(':', maxsplit=1)
                else:
                    location_type = 'country'
                    location_code = location

                if location_type == 'continent':
                    if location_code != server.location.continent_code:
                        return False
                elif location_type == 'country':
                    if location_code != server.location.country_code:
                        return False

            if map != 'any' and map != server.map.id:
                return False

            if type != 'any':
                if type.startswith('vanilla'):
                    if not server.type.startswith('vanilla') and server.type != 'pvp':
                        return False
                else:
                    if type != server.type:
                        return False

            if mode != 'any' and mode != server.mode:
                return False

            if dedicated == 'yes' and not server.is_dedicated:
                return False

            if ranked == 'yes' and not server.is_ranked:
                return False

            if not_empty == 'yes' and server.players.current == 0:
                return False

            if not_full == 'yes' and server.players.free == 0:
                return False

            return True

        servers = [server for server in self.get_servers() if _filter_server(server, filters)]

        limit = filters.get('limit')

        if limit:
            return servers[:limit]

        return servers

    def get_counters(self):
        """Get the number of players online, the active servers as well as the total number of online servers."""
        servers = self.get_servers()

        online_players = sum([server.players.current for server in servers])
        active_servers = sum([1 for server in servers if server.players.current > 0])
        total_servers = len(servers)

        return (online_players, active_servers, total_servers)

    def get_all_players_with_servers_details(self):
        """Get all the players usernames along details about the servers they are playing on."""
        servers = self.get_servers()

        ret = []

        for server in servers:
            if not server.players.list:
                continue

            ret.append({
                'ip_and_port': server.ip_and_port,
                'name': server.name,
                'website': server.website,
                'is_ranked': server.is_ranked,
                'steam_join_link': server.steam_join_link,
                'type': server.type_name,
                'mode': server.mode_name,
                'database': server.database,
                'database_name': server.database_name,
                'link': server.link,
                'location': {
                    'city_name': server.location.city_name,
                    'country_code': server.location.country_code,
                    'country_name': server.location.country_name
                },
                'map': {
                    'id': server.map.id,
                    'name': server.map.name_display
                },
                'players': {
                    'current': server.players.current,
                    'max': server.players.max,
                    'free': server.players.free,
                    'list': server.players.list
                }
            })

        return ret

    @cache.memoize(timeout=app.config['PLAYERS_CACHE_TIMEOUT'])
    def get_players(self, database, sort=constants.PlayersSort.SCORE, target=None, start=0, limit=app.config['PLAYERS_LIST_PAGE_SIZES'][0], basic=False):
        """Get and parse a list of RWR players."""
        if limit > 100:
            raise ValueError('limit cannot be greater than 100')
        elif limit <= 0:
            raise ValueError('limit cannot be equal or lower than 0')

        if start < 0:
            raise ValueError('start cannot be lower than 0')

        if database not in constants.VALID_DATABASES:
            raise ValueError('database is invalid')

        params = {
            'db': database,
            'sort': sort,
            'start': start,
            'size': limit,
            'search': target
        }

        html_content = self._call(self.players_endpoint, 'view_players.php', 'html', params=params)

        players = []

        for node in html_content.xpath('//table/tr[position() > 1]'):
            players.append(Player.load(database, node, basic=basic))

        if target and target not in [player.username for player in players]:
            return []

        return players

    @cache.memoize(timeout=app.config['PLAYERS_CACHE_TIMEOUT'])
    def search_player_by_username(self, database, username):
        """Search for a RWR player (exact match)."""
        if database not in constants.VALID_DATABASES:
            raise ValueError('database is invalid')

        username = username.upper()

        params = {
            'db': database,
            'search': username
        }

        html_content = self._call(self.players_endpoint, 'view_player.php', 'html', params=params)

        node = html_content.xpath('(//table/tr[position() = 2])[1]')

        if not node:
            return None

        return Player.load(database, node[0], alternative=True)

    def get_current_server_of_player(self, target_username):
        """Return the server where the specified player is playing on, if any (partial match)."""
        servers = self.get_servers()

        target_username = target_username.lower()
        real_username = target_username
        found_server = None

        for server in servers:
            if not server.players.list:
                continue

            players_list = [player.lower() for player in server.players.list]

            for player in players_list:
                if target_username in player:
                    real_username = player
                    found_server = server

        return real_username.upper(), found_server

    def __repr__(self):
        return 'DataScraper'
